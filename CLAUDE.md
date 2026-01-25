# Telegram AI Content Agent

Автономная система генерации контента для Telegram-канала @smart_analytics_mp (маркетплейсы Ozon/Wildberries).

## Критичные правила

- **Proxy обязателен** — Claude API заблокирован в РФ, используй `settings.proxy_url`
- **Посты без меток** — никаких "ПОСТ:", "ТЕГИ:", "---" в выводе
- **Русские маркетплейсы** — Ozon, Wildberries, Яндекс.Маркет, не SerpAPI/Google
- **Async везде** — все I/O операции через async/await

## Команды

```bash
python -m app.main              # Запуск пайплайна (publish=True/False в коде)
python test_pipeline.py         # Тест Exa + Claude без публикации
python test_publish.py          # Тест с публикацией
docker-compose up -d postgres   # БД
alembic upgrade head            # Миграции
```

## Архитектура

| Модуль | Путь | Назначение |
|--------|------|------------|
| Content Generator | `app/agents/content_generator.py` | Claude API + proxy |
| Exa Searcher | `app/parsers/exa_searcher.py` | Поиск источников |
| Habr Parser | `app/parsers/habr_parser.py` | Парсинг Habr |
| Publisher | `app/telegram/publisher.py` | Публикация в канал |
| Prompts | `app/utils/prompts.py` | Промпты для Claude |
| Config | `app/config.py` | Pydantic Settings |

## Конфигурация (.env)

```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-haiku-20240307
PROXY_URL=http://user:pass@proxy:port
EXA_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHANNEL_ID=@smart_analytics_mp
DATABASE_URL=postgresql://...
```

## Пайплайн

```
Exa API → источники → Claude (proxy) → пост → Telegram
```

1. `ExaSearcher.search_all_sources()` — сбор новостей
2. `ContentGenerator.generate_post()` — генерация через Claude
3. `TelegramPublisher.publish_post()` — публикация

## Стиль постов

- 300-600 символов
- Экспертный тон без воды
- 1-3 эмодзи
- Хештеги в конце (#ozon #wildberries)
- Вопрос к аудитории

## Модульная документация

| Файл | Содержание |
|------|------------|
| `.claude/rules/ai-generation.md` | Claude API, промпты, proxy |
| `.claude/rules/parsers.md` | Exa API, Habr parser |
| `.claude/rules/database.md` | PostgreSQL, SQLAlchemy, Alembic |
| `.claude/rules/telegram.md` | Telegram Bot API, публикация |
| `.claude/rules/deploy.md` | Docker, VPS, деплой |

## Tech Stack

Python 3.11+, Claude API (Anthropic), Exa API, PostgreSQL, SQLAlchemy, python-telegram-bot, httpx, Pydantic
