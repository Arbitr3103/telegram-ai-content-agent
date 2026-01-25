FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Создание директории для логов
RUN mkdir -p /app/logs

# Запуск приложения
CMD ["python", "-m", "app.main"]
