"""
Тестовый скрипт для проверки улучшенного пайплайна
"""
import asyncio
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.parsers.exa_searcher import ExaSearcher
from app.agents.content_generator import ContentGenerator


async def test_exa_api():
    """Тест Exa API"""
    print("\n" + "="*50)
    print("🔍 ТЕСТ EXA API")
    print("="*50)

    searcher = ExaSearcher()

    if not settings.exa_api_key:
        print("❌ EXA_API_KEY не установлен")
        return []

    print(f"API Key: {settings.exa_api_key[:10]}...")

    # Поиск новостей
    news = await searcher.search_latest_news(
        "Ozon Wildberries маркетплейс аналитика",
        num_results=3,
        days_back=14
    )

    if news:
        print(f"\n✅ Найдено {len(news)} источников:")
        for i, item in enumerate(news, 1):
            print(f"\n{i}. {item['title'][:70]}...")
            print(f"   URL: {item['url'][:60]}...")
            print(f"   Контент: {item['content'][:100]}...")
    else:
        print("❌ Источники не найдены")

    return news


async def test_content_generation(sources):
    """Тест генерации контента"""
    print("\n" + "="*50)
    print("✍️ ТЕСТ ГЕНЕРАЦИИ КОНТЕНТА")
    print("="*50)

    if not sources:
        print("⚠️ Нет источников, использую тестовые")
        sources = [
            {
                'title': 'Ozon обновил API до версии 3.0',
                'content': 'Новая версия API Ozon включает улучшенную производительность, новые эндпоинты для работы с товарами и автоматическое управление рекламой.',
                'url': 'https://docs.ozon.ru/api/v3',
                'source_type': 'news'
            }
        ]

    print(f"Модель: {settings.claude_model}")
    print(f"Proxy: {'настроен' if settings.proxy_url else 'не настроен'}")

    generator = ContentGenerator()

    try:
        post = await generator.generate_post(sources)

        print("\n" + "-"*40)
        print("📝 СГЕНЕРИРОВАННЫЙ ПОСТ:")
        print("-"*40)
        print(post['content'])
        print("\n" + "-"*40)
        print(f"Теги: {' '.join(['#' + t for t in post['tags']])}")
        print(f"Источников использовано: {len(post['sources'])}")

        return post

    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        return None


async def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     Тест улучшенного пайплайна                            ║
    ║     Exa API + Claude с proxy                              ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Проверка конфигурации
    print("📋 Конфигурация:")
    print(f"   ANTHROPIC_API_KEY: {'✅' if settings.anthropic_api_key else '❌'}")
    print(f"   EXA_API_KEY: {'✅' if settings.exa_api_key else '❌'}")
    print(f"   PROXY_URL: {'✅' if settings.proxy_url else '❌'}")
    print(f"   TELEGRAM_BOT_TOKEN: {'✅' if settings.telegram_bot_token else '❌'}")

    # Тест Exa API
    sources = await test_exa_api()

    # Тест генерации контента
    post = await test_content_generation(sources)

    print("\n" + "="*50)
    if post:
        print("✅ ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("Система готова к публикации.")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
        print("Проверьте логи выше.")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
