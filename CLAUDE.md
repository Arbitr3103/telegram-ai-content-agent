# Telegram AI Content Agent

Автономная система генерации контента для @smart_analytics_mp (Ozon/Wildberries/Яндекс.Маркет).

**Модель:** Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)

## Критичные правила

- **Proxy обязателен** — Claude API заблокирован в РФ, `settings.proxy_url`
- **Посты без меток** — никаких "ПОСТ:", "ТЕГИ:", "---", "Заголовок:"
- **Только русские маркетплейсы** — Ozon, WB, Яндекс.Маркет
- **Async везде** — все I/O через async/await
- **Позиционирование как разработчик** — не пользователь чужих сервисов

## Контент-план

Посты берутся из `data/content_plan.yaml`. Если на сегодня есть запись — используется тема и тип из плана, иначе fallback на ротацию.

```yaml
# data/content_plan.yaml
posts:
  - date: "2026-02-05"
    type: case
    topic: "Тема поста"
    keywords: [ключевые, слова]
```

**Типы постов:** useful, case, interactive, checklist, tools, mistake, lifehack, expert_opinion

## Расписание публикаций

| День | Время | Источник |
|------|-------|----------|
| Вторник | 09:00-12:00 (рандом) | content_plan.yaml или ротация |
| Четверг | 09:00-12:00 (рандом) | content_plan.yaml или ротация |

**Fallback ротация:** Полезная польза → Полезная польза → Кейс → Интерактив

**Ротация личного опыта:** 1 из 4 постов (каждый 4-й: позиции 4, 8, 12, 16...)

**Ротация CTA:** 2 из 3 постов (пропускается каждый 3-й)

**Защита от дублей:** Минимум 6 часов между постами (`can_publish()`)

## Команды

```bash
python -m app.main                           # Запуск пайплайна
python -m app.scheduler.content_scheduler    # Запуск планировщика
python test_publish.py                       # Тест публикации (показывает флаги)
python test_rotation_clean.py                # Тест ротации на 16 постах
systemctl status telegram-content-scheduler  # Статус на сервере
```

## Архитектура

| Модуль | Путь |
|--------|------|
| Content Generator | `app/agents/content_generator.py` |
| Content Plan | `app/utils/content_plan.py` |
| Scheduler | `app/scheduler/content_scheduler.py` |
| Post Types | `app/utils/post_types.py` |
| Exa Searcher | `app/parsers/exa_searcher.py` |
| Publisher | `app/telegram/publisher.py` |
| Admin Bot | `app/telegram/admin_bot.py` |
| Prompts | `app/utils/prompts.py` |

## Админ-бот

| Команда | Действие |
|---------|----------|
| `/preview` | Превью следующего поста |
| `/approve [id]` | Одобрить пост |
| `/reject [id] [причина]` | Отклонить пост |
| `/stats` | Статистика постов |

**Уведомления:** Админы получают уведомления при генерации и публикации постов.

## Ключевые функции

| Функция | Назначение |
|---------|------------|
| `should_add_cta()` | Определяет нужен ли CTA (2 из 3 постов) |
| `should_add_personal_experience()` | Определяет нужен ли личный опыт (1 из 4 постов) |
| `get_next_post_type()` | Возвращает тип поста + флаги (CTA, личный опыт) |
| `send_poll()` | Отправить опрос в канал (2-10 вариантов) |

## Мониторинг API

Автоматически отслеживаются:
- `docs.ozon.ru` — Seller API, Performance API
- `openapi.wildberries.ru` — API изменения
- `yandex.ru/dev/market` — Partner API

## Сервер

- **VPS:** 87.228.113.203
- **Сервис:** `telegram-content-scheduler.service`
- **Состояние ротации:** `data/post_rotation.json`
- **SSH ключ:** `~/.ssh/telegram_agent_deploy` (read+write)

## Модульная документация

| Файл | Содержание |
|------|------------|
| `.claude/rules/ai-generation.md` | Claude API, промпты, proxy, ротация личного опыта |
| `.claude/rules/parsers.md` | Exa API, Habr parser |
| `.claude/rules/scheduler.md` | Расписание, ротация постов |
| `.claude/rules/database.md` | PostgreSQL, Alembic |
| `.claude/rules/telegram.md` | Telegram Bot API |
| `.claude/rules/deploy.md` | Docker, VPS, systemd |

## Tech Stack

Python 3.11+, Claude API, Exa API, APScheduler, PostgreSQL, python-telegram-bot, httpx
