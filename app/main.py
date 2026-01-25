"""
Главный файл приложения Telegram AI Content Agent
"""
import asyncio
import logging
from typing import List, Dict, Any

from app.config import settings
from app.parsers.exa_searcher import ExaSearcher
from app.parsers.habr_parser import HabrParser
from app.agents.content_generator import ContentGenerator
from app.telegram.publisher import TelegramPublisher

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ContentPipeline:
    """Основной пайплайн для сбора, генерации и публикации контента"""

    def __init__(self):
        self.exa_searcher = ExaSearcher()
        self.habr_parser = HabrParser()
        self.content_generator = ContentGenerator()
        self.telegram_publisher = TelegramPublisher()

        logger.info("ContentPipeline initialized")

    async def collect_sources(self) -> List[Dict[str, Any]]:
        """
        Сбор источников информации

        Returns:
            Список собранных источников
        """
        logger.info("Collecting sources...")

        all_sources = []

        # Поисковые запросы для Exa (фокус на русские маркетплейсы)
        exa_queries = [
            "Ozon селлер новости обновления 2025",
            "Wildberries продавцы изменения комиссии",
            "Яндекс Маркет API изменения",
            "аналитика продаж Ozon Wildberries кейс"
        ]

        # Теги для Habr
        habr_tags = ['etl', 'ozon', 'wildberries', 'e-commerce', 'маркетплейсы']

        # Сбор из Exa
        try:
            exa_sources = await self.exa_searcher.search_all_sources(
                queries=exa_queries,
                num_results_per_query=3
            )
            all_sources.extend(exa_sources)
            logger.info(f"Collected {len(exa_sources)} sources from Exa")
        except Exception as e:
            logger.error(f"Error collecting from Exa: {e}")

        # Сбор из Habr
        try:
            habr_sources = await self.habr_parser.parse_articles_by_tags(
                tags=habr_tags,
                max_articles_per_tag=3,
                days_back=7
            )
            all_sources.extend(habr_sources)
            logger.info(f"Collected {len(habr_sources)} sources from Habr")
        except Exception as e:
            logger.error(f"Error collecting from Habr: {e}")

        logger.info(f"Total sources collected: {len(all_sources)}")
        return all_sources

    async def generate_and_publish_post(
        self,
        sources: List[Dict[str, Any]],
        publish: bool = True
    ) -> Dict[str, Any]:
        """
        Генерация и публикация поста

        Args:
            sources: Список источников
            publish: Публиковать ли сразу (False - только сгенерировать)

        Returns:
            Информация о созданном посте
        """
        if not sources:
            logger.warning("No sources provided for post generation")
            return {'success': False, 'error': 'No sources'}

        # Генерация поста
        try:
            post_data = await self.content_generator.generate_post(sources)
            logger.info("Post generated successfully")

            if publish:
                # Публикация в Telegram
                result = await self.telegram_publisher.publish_post(
                    content=post_data['content'],
                    tags=post_data['tags']
                )

                if result['success']:
                    logger.info(f"Post published. Message ID: {result['message_id']}")
                    return {
                        'success': True,
                        'post': post_data,
                        'telegram': result
                    }
                else:
                    logger.error(f"Failed to publish: {result['error']}")
                    return {
                        'success': False,
                        'post': post_data,
                        'error': result['error']
                    }
            else:
                # Только генерация, без публикации
                return {
                    'success': True,
                    'post': post_data,
                    'published': False
                }

        except Exception as e:
            logger.error(f"Error in post generation/publication: {e}")
            return {'success': False, 'error': str(e)}

    async def run_once(self, publish: bool = True):
        """
        Однократный запуск пайплайна

        Args:
            publish: Публиковать ли пост
        """
        logger.info("=== Starting Content Pipeline ===")

        # Сбор источников
        sources = await self.collect_sources()

        if not sources:
            logger.warning("No sources collected, aborting")
            return

        # Генерация и публикация
        result = await self.generate_and_publish_post(sources, publish=publish)

        if result['success']:
            logger.info("Pipeline completed successfully")
            print("\n" + "=" * 50)
            print("GENERATED POST:")
            print("=" * 50)
            print(result['post']['content'])
            print("\nTAGS:", ' '.join(result['post']['tags']))

            if result.get('published', True):
                print(f"\n✅ Published to Telegram! Message ID: {result['telegram']['message_id']}")
            else:
                print("\n📝 Post generated but not published")
        else:
            logger.error(f"Pipeline failed: {result.get('error')}")

        # Cleanup
        await self.habr_parser.close()

    async def close(self):
        """Закрытие ресурсов"""
        await self.habr_parser.close()


async def main():
    """Главная функция"""
    pipeline = ContentPipeline()

    try:
        # Запуск пайплайна (publish=False для тестирования без публикации)
        await pipeline.run_once(publish=True)
    finally:
        await pipeline.close()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     Telegram AI Content Agent                             ║
    ║     Powered by Claude Sonnet 4.5                          ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    asyncio.run(main())
