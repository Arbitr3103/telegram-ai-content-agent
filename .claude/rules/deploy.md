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

### Требования

- Ubuntu 22.04+
- 2 CPU, 4GB RAM
- Docker + Docker Compose

### Установка

```bash
# SSH на сервер
ssh user@87.228.113.203

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Проект
git clone https://github.com/user/telegram-ai-agent.git
cd telegram-ai-agent

# Конфиг
cp .env.example .env
nano .env  # Заполнить ключи

# Запуск
docker-compose up -d
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

```ini
# /etc/systemd/system/telegram-ai-agent.service
[Unit]
Description=Telegram AI Content Agent
After=docker.service

[Service]
Type=simple
WorkingDirectory=/home/user/telegram-ai-agent
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable telegram-ai-agent
sudo systemctl start telegram-ai-agent
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
