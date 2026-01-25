"""
Тестовая публикация поста в Telegram канал
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.parsers.exa_searcher import ExaSearcher
from app.agents.content_generator import ContentGenerator
from app.telegram.publisher import TelegramPublisher


async def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     Тестовая публикация улучшенного поста                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # 1. Получаем реальные источники из Exa
    print("📡 Получение источников из Exa API...")
    searcher = ExaSearcher()
    sources = await searcher.search_latest_news(
        "Ozon Wildberries маркетплейс API автоматизация 2025 2026",
        num_results=5,
        days_back=14
    )

    if not sources:
        print("⚠️ Источники не найдены, используем резервные")
        sources = [
            {
                'title': 'Автоматизация аналитики маркетплейсов',
                'content': 'Современные инструменты позволяют автоматизировать сбор данных с Ozon и Wildberries, экономя время селлеров на рутинных задачах.',
                'url': 'https://sellermate.io',
                'source_type': 'news'
            }
        ]

    print(f"✅ Источников: {len(sources)}")

    # 2. Генерируем пост
    print("\n✍️ Генерация поста через Claude...")
    generator = ContentGenerator()
    post = await generator.generate_post(sources)

    print("\n" + "="*50)
    print("📝 ПОСТ ДЛЯ ПУБЛИКАЦИИ:")
    print("="*50)
    print(post['content'])
    print("="*50)

    # 3. Публикуем
    print(f"\n📤 Публикация в канал {settings.telegram_channel_id}...")

    publisher = TelegramPublisher()
    result = await publisher.publish_post(
        content=post['content'],
        tags=post['tags']
    )

    if result['success']:
        print(f"\n✅ ОПУБЛИКОВАНО!")
        print(f"Message ID: {result['message_id']}")
    else:
        print(f"\n❌ Ошибка публикации: {result.get('error')}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
