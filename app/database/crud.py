"""
CRUD операции для работы с базой данных
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from .models import Source, Post, Schedule, PostStats


# === Source CRUD ===

def store_source(
    db: Session,
    source_type: str,
    title: str,
    content: str,
    url: Optional[str] = None,
    published_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None,
    relevance_score: Optional[float] = None,
) -> Source:
    """Сохранить источник в БД"""
    if url:
        existing = db.query(Source).filter(Source.url == url).first()
        if existing:
            return existing

    source = Source(
        source_type=source_type,
        title=title,
        content=content,
        url=url,
        published_at=published_at,
        metadata=metadata or {},
        relevance_score=relevance_score,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_unused_sources(db: Session, limit: int = 10, min_relevance: float = 0.7) -> List[Source]:
    """Получить неиспользованные источники"""
    return db.query(Source).filter(
        and_(Source.used == False, Source.relevance_score >= min_relevance)
    ).order_by(desc(Source.published_at)).limit(limit).all()


# === Post CRUD ===

def create_post(
    db: Session,
    content: str,
    tags: List[str],
    sources: List[Dict[str, str]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Post:
    """Создать новый пост"""
    post = Post(content=content, tags=tags, sources=sources, metadata=metadata or {}, status='draft')
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def update_post_status(
    db: Session, post_id: int, status: str, telegram_message_id: Optional[int] = None
) -> Optional[Post]:
    """Обновить статус поста"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return None

    post.status = status
    if status == 'published':
        post.published_at = datetime.utcnow()
    if telegram_message_id:
        post.telegram_message_id = telegram_message_id

    db.commit()
    db.refresh(post)
    return post


# === Schedule CRUD ===

def schedule_post(db: Session, post_id: int, scheduled_for: datetime) -> Schedule:
    """Запланировать публикацию поста"""
    update_post_status(db, post_id, 'scheduled')
    schedule = Schedule(post_id=post_id, scheduled_for=scheduled_for)
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def get_pending_schedules(db: Session) -> List[Schedule]:
    """Получить ожидающие публикации"""
    now = datetime.utcnow()
    return db.query(Schedule).filter(
        and_(Schedule.published == False, Schedule.scheduled_for <= now)
    ).all()


# === PostStats CRUD ===

def update_post_stats(
    db: Session, post_id: int, views: int, reactions: int = 0, forwards: int = 0
) -> PostStats:
    """Обновить статистику поста"""
    stats = db.query(PostStats).filter(PostStats.post_id == post_id).first()

    if not stats:
        stats = PostStats(post_id=post_id)
        db.add(stats)

    stats.views = views
    stats.reactions = reactions
    stats.forwards = forwards
    stats.fetched_at = datetime.utcnow()

    db.commit()
    db.refresh(stats)
    return stats
