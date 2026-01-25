# Telegram AI Content Agent

Автономная система генерации контента для @smart_analytics_mp (Ozon/Wildberries/Яндекс.Маркет).

## Критичные правила

- **Proxy обязателен** — Claude API заблокирован в РФ, `settings.proxy_url`
- **Посты без меток** — никаких "ПОСТ:", "ТЕГИ:", "---"
- **Только русские маркетплейсы** — Ozon, WB, Яндекс.Маркет
- **Async везде** — все I/O через async/await

## Расписание публикаций

| День | Время | Тип поста |
|------|-------|-----------|
| Вторник | 09:00-12:00 (рандом) | По ротации |
| Четверг | 09:00-12:00 (рандом) | По ротации |

**Ротация "3 кита":** Полезная польза → Полезная польза → Кейс → Интерактив

**Защита от дублей:** Минимум 6 часов между постами (`can_publish()`)

## Команды

```bash
python -m app.main                           # Запуск пайплайна
python -m app.scheduler.content_scheduler    # Запуск планировщика
python test_pipeline.py                      # Тест без публикации
systemctl status telegram-content-scheduler  # Статус на сервере
```

## Архитектура

| Модуль | Путь |
|--------|------|
| Content Generator | `app/agents/content_generator.py` |
| Scheduler | `app/scheduler/content_scheduler.py` |
| Post Types | `app/utils/post_types.py` |
| Exa Searcher | `app/parsers/exa_searcher.py` |
| Publisher | `app/telegram/publisher.py` |
| Prompts | `app/utils/prompts.py` |

## Мониторинг API

Автоматически отслеживаются:
- `docs.ozon.ru` — Seller API, Performance API
- `openapi.wildberries.ru` — API изменения
- `yandex.ru/dev/market` — Partner API

## Сервер

- **VPS:** 87.228.113.203
- **Сервис:** `telegram-content-scheduler.service`
- **Состояние ротации:** `data/post_rotation.json`

## Модульная документация

| Файл | Содержание |
|------|------------|
| `.claude/rules/ai-generation.md` | Claude API, промпты, proxy |
| `.claude/rules/parsers.md` | Exa API, Habr parser |
| `.claude/rules/scheduler.md` | Расписание, ротация постов |
| `.claude/rules/database.md` | PostgreSQL, Alembic |
| `.claude/rules/telegram.md` | Telegram Bot API |
| `.claude/rules/deploy.md` | Docker, VPS, systemd |

## Tech Stack

Python 3.11+, Claude API, Exa API, APScheduler, PostgreSQL, python-telegram-bot, httpx
