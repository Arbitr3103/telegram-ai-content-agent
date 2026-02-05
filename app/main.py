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
from app.utils.post_types import get_next_post_type, get_post_type_from_plan, mark_post_published, get_rotation_status, can_publish
from app.utils.content_plan import get_content_plan, get_todays_post, PlannedPost

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

    async def collect_sources(
        self,
        keywords: List[str] = None,
        topic: str = None
    ) -> List[Dict[str, Any]]:
        """
        Сбор источников информации

        Args:
            keywords: Ключевые слова из контент-плана (опционально)
            topic: Тема поста из контент-плана (опционально)

        Returns:
            Список собранных источников
        """
        logger.info("Collecting sources...")

        all_sources = []

        # Если есть keywords из контент-плана - используем их для поиска
        if keywords:
            exa_queries = [
                f"{' '.join(keywords[:3])} маркетплейс селлер",
                f"{topic}" if topic else f"{keywords[0]} Ozon Wildberries"
            ]
            habr_tags = keywords[:3] + ['e-commerce']
            logger.info(f"Using content plan keywords: {keywords}")
        else:
            # Стандартные запросы
            exa_queries = [
                # Общие новости маркетплейсов
                "Ozon селлер новости обновления 2026",
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

        # Сбор из официальных API документаций (ТОЛЬКО если нет контент-плана!)
        if not keywords:
            try:
                api_docs = await self.exa_searcher.search_api_documentation(num_results=2)
                # Добавляем в начало списка как приоритетные
                all_sources = api_docs + all_sources
                logger.info(f"Collected {len(api_docs)} sources from API docs")
            except Exception as e:
                logger.error(f"Error collecting API docs: {e}")
        else:
            logger.info("Skipping API docs collection - using content plan keywords")

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
        publish: bool = True,
        planned_post: PlannedPost = None
    ) -> Dict[str, Any]:
        """
        Генерация и публикация поста

        Args:
            sources: Список источников
            publish: Публиковать ли сразу (False - только сгенерировать)
            planned_post: Пост из контент-плана (опционально)

        Returns:
            Информация о созданном посте
        """
        if not sources and not planned_post:
            logger.warning("No sources provided for post generation")
            return {'success': False, 'error': 'No sources'}

        # Если есть пост из контент-плана - используем его тип
        if planned_post:
            post_type_key, post_type_config = get_post_type_from_plan(planned_post.type)
            logger.info(f"Using content plan: {planned_post.topic}")
            logger.info(f"Post type from plan: {post_type_config['name']}")
        else:
            # Определяем тип поста по ротации "3 кита"
            post_type_key, post_type_config = get_next_post_type()
            logger.info(f"Post type: {post_type_config['name']}")

        # Генерация поста с учётом типа и контент-плана
        try:
            # Формируем ЖЁСТКУЮ инструкцию по теме из контент-плана
            topic_instruction = ""
            if planned_post:
                topic_instruction = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ КРИТИЧЕСКИ ВАЖНО — ТЕМА ПОСТА!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ТЕМА: {planned_post.topic}

🚫 ЗАПРЕЩЕНО:
• Писать про API, если тема НЕ про API
• Писать про "новые возможности", если тема про конкретный кейс
• Отклоняться от темы ни на слово
• Игнорировать структуру ниже

✅ ОБЯЗАТЕЛЬНО:
• Пост ТОЛЬКО на тему выше
• Использовать ключевые слова: {', '.join(planned_post.keywords)}
"""
                if planned_post.structure:
                    topic_instruction += f"""
СТРУКТУРА ПОСТА (следуй ей!):
{planned_post.structure}
"""
                if planned_post.facts:
                    topic_instruction += f"""
ИСПОЛЬЗУЙ ЭТИ ФАКТЫ: {', '.join(planned_post.facts)}
"""
                topic_instruction += """
Если в источниках нет информации по теме — придумай правдоподобный кейс с реалистичными цифрами.
НЕ ПЕРЕКЛЮЧАЙСЯ на другую тему! ПИШИ СТРОГО ПО ТЕМЕ!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            post_data = await self.content_generator.generate_post(
                sources,
                post_type_key=post_type_key,
                topic_instruction=topic_instruction,
                add_cta=post_type_config.get('add_cta', False),
                cta_text=post_type_config.get('cta', ''),
                add_personal_experience=post_type_config.get('add_personal_experience', False)
            )
            logger.info("Post generated successfully")

            # Notify admins about new post (if not auto-publishing)
            if not publish:
                try:
                    from app.telegram.admin_bot import notify_admins
                    await notify_admins(
                        f"<b>New post generated</b>\n\n"
                        f"Type: {post_type_config['name']}\n"
                        f"Length: {len(post_data['content'])} chars\n\n"
                        f"Use /preview in admin bot to review."
                    )
                except Exception as e:
                    logger.warning(f"Could not notify admins: {e}")

            if publish:
                # Check if this post should include a poll
                if planned_post and planned_post.include_poll and planned_post.poll_question:
                    result = await self.telegram_publisher.publish_post_with_poll(
                        content=post_data['content'],
                        poll_question=planned_post.poll_question,
                        poll_options=planned_post.poll_options or ["Да", "Нет"]
                    )
                    if result['success']:
                        logger.info(f"Post with poll published. Post ID: {result['post_message_id']}, Poll ID: {result['poll_message_id']}")
                        mark_post_published(post_type_key)

                        # Notify admins about published post
                        try:
                            from app.telegram.admin_bot import notify_admins
                            await notify_admins(
                                f"<b>Post published!</b>\n\n"
                                f"Type: {post_type_config['name']}\n"
                                f"Post ID: {result.get('post_message_id')}\n"
                                f"Poll ID: {result.get('poll_message_id')}\n"
                                f"Channel: {settings.telegram_channel_id}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not notify admins: {e}")

                        return {
                            'success': True,
                            'post': post_data,
                            'post_type': post_type_config['name'],
                            'telegram': result,
                            'has_poll': True
                        }
                    else:
                        logger.error(f"Failed to publish with poll: {result.get('error')}")
                        return {
                            'success': False,
                            'post': post_data,
                            'error': result.get('error')
                        }
                else:
                    # Regular post without poll
                    result = await self.telegram_publisher.publish_post(
                        content=post_data['content']
                    )

                    if result['success']:
                        logger.info(f"Post published. Message ID: {result['message_id']}")
                        # Отмечаем тип поста как опубликованный для ротации
                        mark_post_published(post_type_key)

                        # Notify admins about published post
                        try:
                            from app.telegram.admin_bot import notify_admins
                            await notify_admins(
                                f"<b>Post published!</b>\n\n"
                                f"Type: {post_type_config['name']}\n"
                                f"Message ID: {result.get('message_id')}\n"
                                f"Channel: {settings.telegram_channel_id}"
                            )
                        except Exception as e:
                            logger.warning(f"Could not notify admins: {e}")

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

        # Проверяем контент-план на сегодня
        planned_post = get_todays_post()
        if planned_post:
            logger.info(f"Found planned post for today: {planned_post.topic}")
            print(f"\n📅 Пост из контент-плана: {planned_post.topic}")
            print(f"   Тип: {planned_post.type}")

        # Сбор источников (с учётом keywords из плана)
        sources = await self.collect_sources(
            keywords=planned_post.keywords if planned_post else None,
            topic=planned_post.topic if planned_post else None
        )

        if not sources and not planned_post:
            logger.warning("No sources collected, aborting")
            return

        # Генерация и публикация
        result = await self.generate_and_publish_post(
            sources,
            publish=publish,
            planned_post=planned_post
        )

        if result['success']:
            logger.info("Pipeline completed successfully")
            print("\n" + "=" * 50)
            print("GENERATED POST:")
            print("=" * 50)
            print(result['post']['content'])

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
