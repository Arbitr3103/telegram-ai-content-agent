---
paths: "app/database/**/*.py, alembic/**/*.py"
---

# Database Rules

PostgreSQL + SQLAlchemy + Alembic.

## Подключение

```python
# app/config.py
DATABASE_URL=postgresql://telegram_agent:password@localhost:5432/telegram_ai_agent
```

## Модели (app/database/models.py)

### Source (источник)

```python
class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    content = Column(Text)
    source_type = Column(String(50))  # 'exa_news', 'habr', 'telegram'
    relevance_score = Column(Float, default=0.5)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Post (пост)

```python
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    tags = Column(ARRAY(String))
    status = Column(String(20), default='draft')  # draft, scheduled, published
    telegram_message_id = Column(Integer)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### PostStats (статистика)

```python
class PostStats(Base):
    __tablename__ = "post_stats"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    views = Column(Integer, default=0)
    forwards = Column(Integer, default=0)
    reactions = Column(Integer, default=0)
    collected_at = Column(DateTime, default=datetime.utcnow)
```

## CRUD (app/database/crud.py)

```python
from sqlalchemy.orm import Session
from app.database.models import Source, Post

def create_source(db: Session, source_data: dict) -> Source:
    source = Source(**source_data)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source

def get_sources_by_type(db: Session, source_type: str, limit: int = 10):
    return db.query(Source).filter(
        Source.source_type == source_type
    ).order_by(Source.created_at.desc()).limit(limit).all()

def source_exists(db: Session, url: str) -> bool:
    return db.query(Source).filter(Source.url == url).first() is not None
```

## Alembic миграции

```bash
# Создать миграцию
alembic revision --autogenerate -m "Add post_stats table"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1

# История
alembic history
```

### alembic/env.py

```python
from app.database.models import Base
from app.config import settings

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

## Docker PostgreSQL

```bash
# Запуск
docker-compose up -d postgres

# Проверка
docker-compose ps

# Логи
docker-compose logs postgres

# Подключение
docker exec -it telegram-ai-agent-postgres psql -U telegram_agent -d telegram_ai_agent
```

## docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: telegram_agent
      POSTGRES_PASSWORD: tg_agent_secure_2026
      POSTGRES_DB: telegram_ai_agent
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Timezone

Всегда используй UTC:

```python
from datetime import datetime, timezone

# Правильно
created_at = datetime.now(timezone.utc)

# Неправильно (naive datetime)
created_at = datetime.now()
```
