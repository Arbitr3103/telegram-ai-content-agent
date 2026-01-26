"""
Модели БД для клиентского бота
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для моделей клиентского бота"""
    pass


class BotUser(Base):
    """Пользователь клиентского бота"""
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Лимиты и статистика
    audits_today: Mapped[int] = mapped_column(Integer, default=0)
    audits_reset_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Активность
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="user")
    conversations: Mapped[List["Conversation"]] = relationship("Conversation", back_populates="user")


class Lead(Base):
    """Заявка от клиента"""
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("bot_users.id"), nullable=False)

    # Контактные данные
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Квалификация
    sku_count: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    marketplaces: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)

    # Заявка
    task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Статус
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, contacted, closed

    # Метаданные
    bot_activity: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["BotUser"] = relationship("BotUser", back_populates="leads")


class Conversation(Base):
    """История диалога с пользователем"""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("bot_users.id"), nullable=False)

    messages: Mapped[Optional[dict]] = mapped_column(JSON, default=list)
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["BotUser"] = relationship("BotUser", back_populates="conversations")
