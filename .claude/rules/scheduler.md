---
paths: "app/scheduler/**/*.py, app/utils/post_types.py"
---

# Scheduler Rules

Планировщик публикаций и ротация типов постов.

## Расписание

| День | Время | Как работает |
|------|-------|--------------|
| Вторник | 09:00-12:00 | Рандомное время в диапазоне |
| Четверг | 09:00-12:00 | Рандомное время в диапазоне |

Проверка в 00:05 каждого дня — если Вт/Чт, планируется пост.

## Ротация "3 кита" (app/utils/post_types.py)

```python
ROTATION_ORDER = ["useful", "useful", "case", "interactive"]
```

| Тип | Название | Описание |
|-----|----------|----------|
| `useful` | Полезная польза | Разбор API, лайфхак, как сэкономить |
| `case` | Кейс | Результат с цифрами, было/стало |
| `interactive` | Интерактив | Мнение + вопрос аудитории |

### Состояние ротации

Хранится в `data/post_rotation.json`:

```json
{
  "current_index": 2,
  "last_post_date": "2026-01-25T21:59:50",
  "history": [...]
}
```

### API

```python
from app.utils.post_types import get_next_post_type, mark_post_published, can_publish

# Получить следующий тип
post_type_key, post_type_config = get_next_post_type()
# post_type_config['prompt_addition'] — инструкция для Claude

# После публикации
mark_post_published(post_type_key)

# Проверка интервала (6 часов)
can_pub, reason = can_publish()
```

## Защита от дублей

Минимум 6 часов между постами:

```python
def can_publish() -> Tuple[bool, str]:
    state = get_state()
    last_post = state.get("last_post_date")
    if not last_post:
        return True, "OK"

    last_post_time = datetime.fromisoformat(last_post)
    min_interval = timedelta(hours=6)

    if datetime.now() - last_post_time < min_interval:
        hours_left = (min_interval - (datetime.now() - last_post_time)).total_seconds() / 3600
        return False, f"Подождите ещё {hours_left:.1f} часов"

    return True, "OK"
```

## ContentScheduler (app/scheduler/content_scheduler.py)

```python
class ContentScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        # Ежедневная проверка в 00:05
        self.scheduler.add_job(
            self._schedule_next_post,
            CronTrigger(hour=0, minute=5),
            id='daily_schedule_check'
        )

    async def _schedule_next_post(self):
        weekday = datetime.now().weekday()
        if weekday not in [1, 3]:  # Вт=1, Чт=3
            return

        hour, minute = get_random_publish_time()  # 09:00-12:00
        run_time = datetime.now().replace(hour=hour, minute=minute)

        self.scheduler.add_job(
            self._run_pipeline,
            'date',
            run_date=run_time,
            id=f'post_{datetime.now().strftime("%Y%m%d")}'
        )
```

## Запуск

### Локально

```bash
python -m app.scheduler.content_scheduler
```

### На сервере (systemd)

```bash
# Статус
systemctl status telegram-content-scheduler

# Логи
journalctl -u telegram-content-scheduler -f

# Перезапуск
systemctl restart telegram-content-scheduler
```

## Тестирование

```python
# Немедленная публикация (через 10 сек)
scheduler = ContentScheduler()
scheduler.start()
scheduler.schedule_now(delay_seconds=10)
```

## Статус

```python
scheduler.get_status()
# Показывает:
# - Запланированные задачи
# - Следующий тип поста
# - Позицию в цикле ротации
# - Время последнего поста
```
