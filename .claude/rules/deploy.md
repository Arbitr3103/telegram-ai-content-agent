---
paths: "docker-compose.yml, Dockerfile, *.sh"
---

# Deploy Rules

Деплой на VPS и Docker.

## Локальный запуск

```bash
# 1. Виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# 2. Зависимости
pip install -r requirements.txt

# 3. PostgreSQL
docker-compose up -d postgres

# 4. Миграции
alembic upgrade head

# 5. Запуск
python -m app.main
```

## Docker Compose

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql://telegram_agent:password@postgres:5432/telegram_ai_agent
    env_file:
      - .env
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: telegram_agent
      POSTGRES_PASSWORD: tg_agent_secure_2026
      POSTGRES_DB: telegram_ai_agent
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "app.main"]
```

## VPS Деплой

### Сервер

- **IP:** 87.228.113.203
- **User:** vladimir
- **Path:** `/home/vladimir/telegram-ai-content-agent`

### Требования

- Ubuntu 22.04+
- Python 3.11+
- (Опционально) Docker + Docker Compose

### Установка

```bash
# SSH на сервер
ssh vladimir@87.228.113.203

# Проект
cd /home/vladimir/telegram-ai-content-agent
git pull origin main

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Конфиг
cp .env.example .env
nano .env  # Заполнить ключи

# Запуск scheduler как сервис
sudo systemctl enable telegram-content-scheduler
sudo systemctl start telegram-content-scheduler
```

## Proxy (ZenRows)

Для Claude API из РФ нужен proxy:

```env
PROXY_URL=http://mpMTX73mfbhf:atforfjydSHk@superproxy.zenrows.com:1337
```

**Важно:** Proxy работает только для исходящих запросов к api.anthropic.com.

## Мониторинг

```bash
# Логи приложения
docker-compose logs -f app

# Логи PostgreSQL
docker-compose logs -f postgres

# Статус
docker-compose ps

# Перезапуск
docker-compose restart app
```

## Scheduler (APScheduler)

### app/scheduler/tasks.py

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Парсинг: 8:00 и 20:00
scheduler.add_job(collect_sources, 'cron', hour='8,20')

# Генерация: Пн, Ср, Пт в 10:00
scheduler.add_job(generate_post, 'cron', day_of_week='mon,wed,fri', hour=10)

# Публикация: через час после генерации
scheduler.add_job(publish_post, 'cron', day_of_week='mon,wed,fri', hour=11)

scheduler.start()
```

## Автозапуск (systemd)

### Scheduler сервис (основной)

```ini
# /etc/systemd/system/telegram-content-scheduler.service
[Unit]
Description=Telegram AI Content Scheduler
After=network.target

[Service]
Type=simple
User=vladimir
WorkingDirectory=/home/vladimir/telegram-ai-content-agent
ExecStart=/home/vladimir/telegram-ai-content-agent/venv/bin/python -m app.scheduler.content_scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-content-scheduler
sudo systemctl start telegram-content-scheduler
sudo systemctl status telegram-content-scheduler
journalctl -u telegram-content-scheduler -f
```

### Docker сервис (альтернатива)

```ini
# /etc/systemd/system/telegram-ai-agent.service
[Unit]
Description=Telegram AI Content Agent (Docker)
After=docker.service

[Service]
Type=simple
WorkingDirectory=/home/vladimir/telegram-ai-content-agent
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always

[Install]
WantedBy=multi-user.target
```

## Backup

```bash
# Backup PostgreSQL
docker exec telegram-ai-agent-postgres pg_dump -U telegram_agent telegram_ai_agent > backup.sql

# Restore
cat backup.sql | docker exec -i telegram-ai-agent-postgres psql -U telegram_agent telegram_ai_agent
```

## Стоимость

| Компонент | Цена/мес |
|-----------|----------|
| VPS (2 CPU, 4GB) | ~500₽ |
| Claude API | $20-40 |
| ZenRows Proxy | $49 (10K запросов) |
| **Итого** | ~5000-7000₽ |
