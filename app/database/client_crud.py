"""
CRUD операции для клиентского бота
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.database.client_models import BotUser, Lead, Conversation


def get_or_create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None
) -> BotUser:
    """
    Получить или создать пользователя.

    Если пользователь существует — обновляет username/first_name и last_activity.
    Если не существует — создаёт нового.

    Args:
        db: Сессия SQLAlchemy
        telegram_id: Telegram ID пользователя
        username: Username в Telegram (опционально)
        first_name: Имя пользователя (опционально)

    Returns:
        BotUser: Объект пользователя
    """
    user = db.query(BotUser).filter(BotUser.telegram_id == telegram_id).first()

    if user is None:
        user = BotUser(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Обновляем данные если изменились
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        user.last_activity = datetime.now(timezone.utc)
        db.commit()

    return user


def can_do_audit(user: BotUser, limit: int = 2) -> bool:
    """
    Проверить, может ли пользователь сделать аудит.

    Лимит аудитов сбрасывается каждый день.

    Args:
        user: Объект пользователя
        limit: Максимум аудитов в день (по умолчанию 2)

    Returns:
        bool: True если можно делать аудит, False если лимит исчерпан
    """
    now = datetime.now(timezone.utc)

    # Сброс счётчика если прошёл день
    if user.audits_reset_date is None or user.audits_reset_date.date() < now.date():
        user.audits_today = 0
        user.audits_reset_date = now
        return True

    return user.audits_today < limit


def increment_audit_count(db: Session, user: BotUser) -> None:
    """
    Увеличить счётчик аудитов пользователя.

    Args:
        db: Сессия SQLAlchemy
        user: Объект пользователя
    """
    user.audits_today += 1
    user.audits_reset_date = datetime.now(timezone.utc)
    db.commit()


def create_lead(
    db: Session,
    user_id: int,
    name: Optional[str] = None,
    task: Optional[str] = None,
    budget: Optional[str] = None,
    contact_method: Optional[str] = None,
    sku_count: Optional[str] = None,
    urgency: Optional[str] = None,
    marketplaces: Optional[List[str]] = None,
    bot_activity: Optional[Dict[str, Any]] = None
) -> Lead:
    """
    Создать заявку (лид).

    Args:
        db: Сессия SQLAlchemy
        user_id: ID пользователя в БД
        name: Имя клиента
        task: Описание задачи
        budget: Бюджет
        contact_method: Способ связи
        sku_count: Количество SKU
        urgency: Срочность
        marketplaces: Список маркетплейсов
        bot_activity: Активность в боте (JSON)

    Returns:
        Lead: Созданная заявка
    """
    lead = Lead(
        user_id=user_id,
        name=name,
        task=task,
        budget=budget,
        contact_method=contact_method,
        sku_count=sku_count,
        urgency=urgency,
        marketplaces=marketplaces,
        bot_activity=bot_activity
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def get_user_leads(db: Session, user_id: int) -> List[Lead]:
    """
    Получить все заявки пользователя.

    Args:
        db: Сессия SQLAlchemy
        user_id: ID пользователя в БД

    Returns:
        List[Lead]: Список заявок, отсортированных по дате (новые первые)
    """
    return (
        db.query(Lead)
        .filter(Lead.user_id == user_id)
        .order_by(Lead.created_at.desc())
        .all()
    )


def update_lead_status(db: Session, lead_id: int, status: str) -> Optional[Lead]:
    """
    Обновить статус заявки.

    Args:
        db: Сессия SQLAlchemy
        lead_id: ID заявки
        status: Новый статус ('new', 'contacted', 'closed')

    Returns:
        Optional[Lead]: Обновлённая заявка или None если не найдена
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead:
        lead.status = status
        db.commit()
        db.refresh(lead)
    return lead


def get_or_create_conversation(db: Session, user_id: int) -> Conversation:
    """
    Получить или создать диалог пользователя.

    Args:
        db: Сессия SQLAlchemy
        user_id: ID пользователя в БД

    Returns:
        Conversation: Объект диалога
    """
    conversation = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .first()
    )

    if conversation is None:
        conversation = Conversation(
            user_id=user_id,
            messages=[]
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    return conversation


def update_conversation_messages(
    db: Session,
    conversation_id: int,
    messages: List[Dict[str, str]],
    context: Optional[str] = None
) -> Optional[Conversation]:
    """
    Обновить сообщения диалога.

    Args:
        db: Сессия SQLAlchemy
        conversation_id: ID диалога
        messages: Список сообщений [{"role": "user/assistant", "content": "..."}]
        context: Контекст диалога (опционально)

    Returns:
        Optional[Conversation]: Обновлённый диалог или None если не найден
    """
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )

    if conversation:
        conversation.messages = messages
        if context is not None:
            conversation.context = context
        db.commit()
        db.refresh(conversation)

    return conversation


def get_lead_by_id(db: Session, lead_id: int) -> Optional[Lead]:
    """
    Получить заявку по ID.

    Args:
        db: Сессия SQLAlchemy
        lead_id: ID заявки

    Returns:
        Optional[Lead]: Заявка или None если не найдена
    """
    return db.query(Lead).filter(Lead.id == lead_id).first()


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[BotUser]:
    """
    Получить пользователя по Telegram ID.

    Args:
        db: Сессия SQLAlchemy
        telegram_id: Telegram ID пользователя

    Returns:
        Optional[BotUser]: Пользователь или None если не найден
    """
    return db.query(BotUser).filter(BotUser.telegram_id == telegram_id).first()


def get_all_leads(
    db: Session,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Lead]:
    """
    Получить все заявки с фильтрацией по статусу.

    Args:
        db: Сессия SQLAlchemy
        status: Фильтр по статусу (опционально)
        limit: Максимум записей

    Returns:
        List[Lead]: Список заявок
    """
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)

    return query.order_by(Lead.created_at.desc()).limit(limit).all()
