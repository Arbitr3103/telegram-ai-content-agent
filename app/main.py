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
from app.utils.post_types import get_next_post_type, mark_post_published, get_rotation_status, can_publish

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
            # Общие новости маркетплейсов
            "Ozon селлер новости обновления 2025",
            "Wildberries продавцы изменения комиссии",
            "Яндекс Маркет продавцы новости",

            # Официальные API документации (проверка обновлений)
            "site:docs.ozon.ru API новости обновления seller",
            "site:openapi.wildberries.ru изменения API",
            "site:yandex.ru/dev/market API изменения",

            # Performance API и аналитика
            "Ozon Performance API реклама обновления",
            "Wildberries API статистика продвижение",
            "Яндекс Маркет аналитика API отчёты",

            # Кейсы и практика
            "автоматизация Ozon Wildberries кейс результаты"
        ]

        # Теги для Habr
        habr_tags = ['etl', 'ozon', 'wildberries', 'e-commerce', 'маркетплейсы']

        # Сбор из Exa (общие новости)
        try:
            exa_sources = await self.exa_searcher.search_all_sources(
                queries=exa_queries,
                num_results_per_query=2
            )
            all_sources.extend(exa_sources)
            logger.info(f"Collected {len(exa_sources)} sources from Exa")
        except Exception as e:
            logger.error(f"Error collecting from Exa: {e}")

        # Сбор из официальных API документаций (приоритетный источник)
        try:
            api_docs = await self.exa_searcher.search_api_documentation(num_results=2)
            # Добавляем в начало списка как приоритетные
            all_sources = api_docs + all_sources
            logger.info(f"Collected {len(api_docs)} sources from API docs")
        except Exception as e:
            logger.error(f"Error collecting API docs: {e}")

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

        # Определяем тип поста по ротации "3 кита"
        post_type_key, post_type_config = get_next_post_type()
        logger.info(f"Post type: {post_type_config['name']}")

        # Генерация поста с учётом типа
        try:
            post_data = await self.content_generator.generate_post(
                sources,
                post_type_instruction=post_type_config['prompt_addition'],
                add_cta=post_type_config.get('add_cta', False),
                cta_text=post_type_config.get('cta', '')
            )
            logger.info("Post generated successfully")

            if publish:
                # Публикация в Telegram
                result = await self.telegram_publisher.publish_post(
                    content=post_data['content'],
                    tags=post_data['tags']
                )

                if result['success']:
                    logger.info(f"Post published. Message ID: {result['message_id']}")
                    # Отмечаем тип поста как опубликованный для ротации
                    mark_post_published(post_type_key)
                    return {
                        'success': True,
                        'post': post_data,
                        'post_type': post_type_config['name'],
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

    async def run_once(self, publish: bool = True, force: bool = False):
        """
        Однократный запуск пайплайна

        Args:
            publish: Публиковать ли пост
            force: Игнорировать проверку интервала (для тестов)
        """
        logger.info("=== Starting Content Pipeline ===")

        # Проверка интервала между постами (защита от дублей)
        if publish and not force:
            can_pub, reason = can_publish()
            if not can_pub:
                logger.warning(f"Publication blocked: {reason}")
                print(f"\n⚠️ {reason}")
                return

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
