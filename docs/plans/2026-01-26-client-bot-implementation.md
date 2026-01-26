# Client Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Создать Telegram-бота для лид-генерации с мини-аудитом Ozon, калькулятором упущенной выгоды, FAQ с AI и формой заявки.

**Architecture:** Отдельный бот с ConversationHandler для FSM-диалогов. Интеграция в существующий проект telegram-ai-agent. Новые модели User, Lead, Conversation в PostgreSQL. Парсинг Ozon через httpx + BeautifulSoup.

**Tech Stack:** python-telegram-bot 20.7, SQLAlchemy 2.0, Claude API (через существующий proxy), httpx, BeautifulSoup4, pytest-asyncio.

---

## Task 1: Конфигурация и настройки

**Files:**
- Modify: `app/config.py`
- Modify: `.env.example`

**Step 1: Добавить настройки клиентского бота в config.py**

```python
# В класс Settings добавить после telegram_admin_id:

    # Client Bot
    telegram_client_bot_token: str | None = None

    # Rate limits
    audit_daily_limit: int = 2
    messages_per_minute_limit: int = 20
```

**Step 2: Обновить .env.example**

Добавить в конец файла:

```
# Client Bot
TELEGRAM_CLIENT_BOT_TOKEN=your_client_bot_token_here
```

**Step 3: Проверить что приложение запускается**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && python -c "from app.config import settings; print(settings.telegram_client_bot_token)"`
Expected: `None` (пока токен не задан)

**Step 4: Commit**

```bash
git add app/config.py .env.example
git commit -m "feat: добавлена конфигурация клиентского бота"
```

---

## Task 2: Модели базы данных

**Files:**
- Create: `app/database/client_models.py`
- Create: `alembic/versions/xxxx_add_client_bot_tables.py`

**Step 1: Создать модели User, Lead, Conversation**

Create file `app/database/client_models.py`:

```python
"""
Модели БД для клиентского бота
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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
```

**Step 2: Создать миграцию Alembic**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && alembic revision --autogenerate -m "add client bot tables"`

**Step 3: Применить миграцию**

Run: `alembic upgrade head`
Expected: Таблицы bot_users, leads, conversations созданы

**Step 4: Commit**

```bash
git add app/database/client_models.py alembic/versions/
git commit -m "feat: добавлены модели БД для клиентского бота"
```

---

## Task 3: CRUD операции для клиентского бота

**Files:**
- Create: `app/database/client_crud.py`
- Create: `tests/test_client_crud.py`

**Step 1: Написать тест для get_or_create_user**

Create file `tests/test_client_crud.py`:

```python
"""
Тесты CRUD операций клиентского бота
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.database.client_crud import get_or_create_user, create_lead, can_do_audit


class TestGetOrCreateUser:
    """Тесты получения/создания пользователя"""

    def test_creates_new_user(self):
        """Создаёт нового пользователя если не существует"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user = get_or_create_user(
            db=mock_db,
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_returns_existing_user(self):
        """Возвращает существующего пользователя"""
        mock_db = MagicMock()
        existing_user = MagicMock()
        existing_user.telegram_id = 123456789
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user = get_or_create_user(
            db=mock_db,
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )

        assert user == existing_user
        mock_db.add.assert_not_called()


class TestCanDoAudit:
    """Тесты проверки лимита аудитов"""

    def test_allows_first_audit(self):
        """Разрешает первый аудит"""
        mock_user = MagicMock()
        mock_user.audits_today = 0
        mock_user.audits_reset_date = None

        result = can_do_audit(mock_user, limit=2)

        assert result is True

    def test_denies_over_limit(self):
        """Запрещает при превышении лимита"""
        mock_user = MagicMock()
        mock_user.audits_today = 2
        mock_user.audits_reset_date = datetime.now(timezone.utc)

        result = can_do_audit(mock_user, limit=2)

        assert result is False

    def test_resets_on_new_day(self):
        """Сбрасывает счётчик на следующий день"""
        mock_user = MagicMock()
        mock_user.audits_today = 2
        mock_user.audits_reset_date = datetime(2026, 1, 25, tzinfo=timezone.utc)

        with patch('app.database.client_crud.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 1, 26, 12, 0, tzinfo=timezone.utc)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            result = can_do_audit(mock_user, limit=2)

        assert result is True
```

**Step 2: Запустить тест — должен упасть**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && python -m pytest tests/test_client_crud.py -v`
Expected: FAIL (модуль не найден)

**Step 3: Реализовать CRUD**

Create file `app/database/client_crud.py`:

```python
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
    Получить или создать пользователя

    Args:
        db: Сессия БД
        telegram_id: Telegram ID пользователя
        username: Username в Telegram
        first_name: Имя пользователя

    Returns:
        Объект пользователя
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
    Проверить, может ли пользователь сделать аудит

    Args:
        user: Объект пользователя
        limit: Лимит аудитов в день

    Returns:
        True если аудит разрешён
    """
    now = datetime.now(timezone.utc)

    # Сброс счётчика на новый день
    if user.audits_reset_date is None or user.audits_reset_date.date() < now.date():
        user.audits_today = 0
        user.audits_reset_date = now
        return True

    return user.audits_today < limit


def increment_audit_count(db: Session, user: BotUser) -> None:
    """Увеличить счётчик аудитов"""
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
    Создать заявку

    Args:
        db: Сессия БД
        user_id: ID пользователя в БД
        name: Имя клиента
        task: Описание задачи
        budget: Бюджет
        contact_method: Способ связи
        sku_count: Количество SKU
        urgency: Срочность
        marketplaces: Список маркетплейсов
        bot_activity: Активность в боте

    Returns:
        Созданная заявка
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
    """Получить все заявки пользователя"""
    return db.query(Lead).filter(Lead.user_id == user_id).order_by(Lead.created_at.desc()).all()


def update_lead_status(db: Session, lead_id: int, status: str) -> Optional[Lead]:
    """Обновить статус заявки"""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if lead:
        lead.status = status
        db.commit()
        db.refresh(lead)
    return lead
```

**Step 4: Запустить тесты — должны пройти**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && python -m pytest tests/test_client_crud.py -v`
Expected: PASSED

**Step 5: Commit**

```bash
git add app/database/client_crud.py tests/test_client_crud.py
git commit -m "feat: добавлены CRUD операции для клиентского бота"
```

---

## Task 4: Тексты и клавиатуры бота

**Files:**
- Create: `app/client_bot/texts/messages.py`
- Create: `app/client_bot/keyboards/menus.py`

**Step 1: Создать файл с текстами**

Create directories and file `app/client_bot/__init__.py`, `app/client_bot/texts/__init__.py`, `app/client_bot/keyboards/__init__.py` (empty `__init__.py` files).

Create file `app/client_bot/texts/messages.py`:

```python
"""
Тексты сообщений клиентского бота
"""

# Главное меню
WELCOME_MESSAGE = """Здравствуйте! Я помощник сервиса "Умная аналитика для маркетплейсов".

Чем могу помочь?"""

# Аудит
AUDIT_REQUEST_LINK = """📊 Мини-аудит магазина на Ozon

Пришлите ссылку на ваш магазин в формате:
`ozon.ru/seller/название-12345`

Я проанализирую:
• Общую статистику магазина
• Сравню цены 1-2 товаров с конкурентами
• Дам рекомендации по улучшению"""

AUDIT_INVALID_LINK = """Не могу распознать ссылку. Пришлите ссылку на магазин в формате:
`ozon.ru/seller/название-12345`

Или попробуйте скопировать ссылку из адресной строки браузера."""

AUDIT_PARSING_ERROR = """К сожалению, не удалось получить данные магазина. Возможные причины:
• Магазин временно недоступен
• Ozon ограничил доступ

Попробуйте через 5 минут или оставьте заявку — проведу аудит вручную."""

AUDIT_LIMIT_REACHED = """Вы использовали 2 бесплатных аудита сегодня.
Следующий будет доступен завтра.

Хотите полный анализ всех SKU с мониторингом конкурентов?"""

# Калькулятор упущенной выгоды
CALC_HOURS_QUESTION = """💸 Калькулятор упущенной выгоды

Сколько часов в неделю вы тратите на аналитику и отчёты вручную?"""

CALC_HOURLY_RATE_QUESTION = """Сколько стоит час вашей работы (или менеджера)?"""

CALC_PRICING_ERRORS_QUESTION = """Бывали ли ошибки в ценообразовании за последние 3 месяца?"""

CALC_COMPETITOR_CHECK_QUESTION = """Как часто проверяете цены конкурентов?"""

CALC_RESULT_TEMPLATE = """💸 Расчёт упущенной выгоды

Ручная работа:
{hours_per_week} часов/нед × {hourly_rate} ₽ × 4 недели = {manual_work_cost:,} ₽/мес

Ошибки в ценах:
{pricing_errors_text}

Упущенные продажи (без мониторинга конкурентов):
{competitor_text}

━━━━━━━━━━━━━━━━━━━━━━

📉 Вы теряете от {total_loss:,} ₽/мес
   на ручной работе и отсутствии автоматизации

Автоматизация окупится за 2-3 недели."""

# FAQ
FAQ_MENU = """❓ Частые вопросы

Выберите интересующий вопрос или напишите свой — я постараюсь ответить."""

FAQ_COST = """💰 Стоимость услуг

Стоимость зависит от количества SKU и нужного функционала:
• Базовая аналитика — от 15 000 ₽/мес
• Автоматизация под ключ — от 50 000 ₽ единоразово

Точную стоимость рассчитаю после понимания вашей задачи."""

FAQ_TIMELINE = """⏱ Сроки внедрения

• Подключение аналитики — 2-3 дня
• Кастомная автоматизация — от 1 до 4 недель в зависимости от сложности
• Интеграции с API маркетплейсов — 3-5 дней"""

FAQ_MARKETPLACES = """🛒 Маркетплейсы

Работаю с Ozon, Wildberries и Яндекс.Маркет.

Возможна интеграция нескольких маркетплейсов в единый дашборд для удобного сравнения показателей."""

FAQ_TECHNICAL = """⚙️ Техническая реализация

Программист с вашей стороны не нужен.

Вы предоставляете API-ключи маркетплейса, я настраиваю автоматический сбор данных и отчёты.

Всё работает в облаке — вам нужен только браузер."""

FAQ_FREE_TRIAL = """🎁 Бесплатный тест

Да, делаю бесплатный аудит текущей аналитики и показываю, какие метрики вы упускаете.

Занимает 30 минут созвона."""

FAQ_CUSTOM_QUESTION = """Напишите ваш вопрос, и я постараюсь на него ответить."""

FAQ_AI_FALLBACK = """К сожалению, не смог найти ответ на ваш вопрос.

Оставьте заявку — отвечу лично в течение 24 часов."""

FAQ_OFF_TOPIC = """Я специализируюсь на аналитике для маркетплейсов (Ozon, Wildberries, Яндекс.Маркет).

По этому вопросу лучше обратиться в другое место.

Чем могу помочь по маркетплейсам?"""

# Заявка
APPLICATION_SKU_QUESTION = """📝 Оставить заявку

Для начала несколько вопросов, чтобы лучше понять вашу задачу.

Сколько у вас товаров (SKU)?"""

APPLICATION_URGENCY_QUESTION = """Когда планируете внедрение?"""

APPLICATION_MARKETPLACES_QUESTION = """С какими маркетплейсами работаете?

Можно выбрать несколько."""

APPLICATION_NAME_QUESTION = """Отлично! Теперь контактные данные.

Как к вам обращаться?"""

APPLICATION_TASK_QUESTION = """Опишите вашу задачу — что хотите автоматизировать или какую проблему решить?"""

APPLICATION_BUDGET_QUESTION = """Какой бюджет планируете на автоматизацию?"""

APPLICATION_CONTACT_METHOD_QUESTION = """Как удобнее связаться?"""

APPLICATION_SUCCESS = """✅ Заявка отправлена!

Свяжусь с вами в течение 24 часов в рабочие дни.

Пока можете изучить другие возможности бота."""

# Связаться с человеком
CONTACT_REQUEST = """👤 Связаться с человеком

Ваш запрос передан. Владимир свяжется с вами в течение 24 часов в рабочие дни.

Пока ждёте, можете:"""

CONTACT_WITH_MESSAGE = """Опишите вкратце ваш вопрос — передам вместе с запросом на связь."""

# Уведомления администратору
ADMIN_NEW_LEAD = """🔔 Новая заявка

👤 Имя: {name}
📱 Контакт: @{username}
💬 Способ связи: {contact_method}

━━━━━━━━━━━━━━━━━━━━━━

📋 Квалификация:
• SKU: {sku_count}
• Срочность: {urgency}
• Маркетплейсы: {marketplaces}

💰 Бюджет: {budget}

━━━━━━━━━━━━━━━━━━━━━━

📝 Задача:
{task}

━━━━━━━━━━━━━━━━━━━━━━

📊 Активность в боте:
{bot_activity}"""

ADMIN_CONTACT_REQUEST = """👤 Запрос на связь

От: @{username} ({first_name})
Сообщение: {message}"""
```

**Step 2: Создать клавиатуры**

Create file `app/client_bot/keyboards/menus.py`:

```python
"""
Клавиатуры клиентского бота
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📊 Аудит магазина на Ozon", callback_data="audit")],
        [InlineKeyboardButton("💸 Калькулятор упущенной выгоды", callback_data="calculator")],
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("👤 Связаться с человеком", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню"""
    keyboard = [[InlineKeyboardButton("🏠 В меню", callback_data="menu")]]
    return InlineKeyboardMarkup(keyboard)


def get_audit_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после аудита"""
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_audit_limit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при превышении лимита аудитов"""
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Калькулятор
def get_calc_hours_keyboard() -> InlineKeyboardMarkup:
    """Выбор часов в неделю"""
    keyboard = [
        [
            InlineKeyboardButton("2-3 часа", callback_data="calc_hours_3"),
            InlineKeyboardButton("5-10 часов", callback_data="calc_hours_10"),
            InlineKeyboardButton(">10 часов", callback_data="calc_hours_15"),
        ],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_rate_keyboard() -> InlineKeyboardMarkup:
    """Выбор стоимости часа"""
    keyboard = [
        [
            InlineKeyboardButton("500 ₽", callback_data="calc_rate_500"),
            InlineKeyboardButton("1000 ₽", callback_data="calc_rate_1000"),
            InlineKeyboardButton("2000 ₽", callback_data="calc_rate_2000"),
        ],
        [InlineKeyboardButton("Другая", callback_data="calc_rate_custom")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_errors_keyboard() -> InlineKeyboardMarkup:
    """Выбор ошибок в ценах"""
    keyboard = [
        [InlineKeyboardButton("Да, теряли деньги", callback_data="calc_errors_big")],
        [InlineKeyboardButton("Да, мелкие", callback_data="calc_errors_small")],
        [InlineKeyboardButton("Нет", callback_data="calc_errors_no")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_competitor_keyboard() -> InlineKeyboardMarkup:
    """Выбор частоты проверки конкурентов"""
    keyboard = [
        [InlineKeyboardButton("Каждый день", callback_data="calc_comp_daily")],
        [InlineKeyboardButton("Раз в неделю", callback_data="calc_comp_weekly")],
        [InlineKeyboardButton("Редко/никогда", callback_data="calc_comp_rarely")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после калькулятора"""
    keyboard = [
        [InlineKeyboardButton("📝 Обсудить автоматизацию", callback_data="application")],
        [InlineKeyboardButton("🔄 Пересчитать", callback_data="calculator")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# FAQ
def get_faq_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню FAQ"""
    keyboard = [
        [InlineKeyboardButton("💰 Сколько стоят услуги?", callback_data="faq_cost")],
        [InlineKeyboardButton("⏱ Сколько времени займёт внедрение?", callback_data="faq_timeline")],
        [InlineKeyboardButton("🛒 С какими маркетплейсами работаете?", callback_data="faq_marketplaces")],
        [InlineKeyboardButton("⚙️ Как это технически работает?", callback_data="faq_technical")],
        [InlineKeyboardButton("🎁 Можно попробовать бесплатно?", callback_data="faq_trial")],
        [InlineKeyboardButton("✍️ Задать свой вопрос", callback_data="faq_custom")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_faq_answer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после ответа на FAQ"""
    keyboard = [
        [InlineKeyboardButton("❓ Другой вопрос", callback_data="faq")],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Заявка
def get_sku_keyboard() -> InlineKeyboardMarkup:
    """Выбор количества SKU"""
    keyboard = [
        [
            InlineKeyboardButton("< 50", callback_data="app_sku_lt50"),
            InlineKeyboardButton("50-200", callback_data="app_sku_50_200"),
        ],
        [
            InlineKeyboardButton("200-500", callback_data="app_sku_200_500"),
            InlineKeyboardButton("> 500", callback_data="app_sku_gt500"),
        ],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_urgency_keyboard() -> InlineKeyboardMarkup:
    """Выбор срочности"""
    keyboard = [
        [InlineKeyboardButton("Нужно сейчас", callback_data="app_urgency_now")],
        [InlineKeyboardButton("В ближайший месяц", callback_data="app_urgency_month")],
        [InlineKeyboardButton("Просто смотрю", callback_data="app_urgency_looking")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_marketplaces_keyboard(selected: list = None) -> InlineKeyboardMarkup:
    """Выбор маркетплейсов (мультивыбор)"""
    selected = selected or []

    def mark(name: str) -> str:
        return f"✓ {name}" if name in selected else name

    keyboard = [
        [
            InlineKeyboardButton(mark("Ozon"), callback_data="app_mp_ozon"),
            InlineKeyboardButton(mark("Wildberries"), callback_data="app_mp_wb"),
        ],
        [InlineKeyboardButton(mark("Яндекс.Маркет"), callback_data="app_mp_yandex")],
        [InlineKeyboardButton("✅ Готово", callback_data="app_mp_done")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_budget_keyboard() -> InlineKeyboardMarkup:
    """Выбор бюджета"""
    keyboard = [
        [
            InlineKeyboardButton("до 30 тыс", callback_data="app_budget_lt30"),
            InlineKeyboardButton("30-50 тыс", callback_data="app_budget_30_50"),
        ],
        [
            InlineKeyboardButton("50-100 тыс", callback_data="app_budget_50_100"),
            InlineKeyboardButton("> 100 тыс", callback_data="app_budget_gt100"),
        ],
        [InlineKeyboardButton("Не определён", callback_data="app_budget_unknown")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_contact_method_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа связи"""
    keyboard = [
        [
            InlineKeyboardButton("Telegram", callback_data="app_contact_telegram"),
            InlineKeyboardButton("WhatsApp", callback_data="app_contact_whatsapp"),
        ],
        [InlineKeyboardButton("Звонок", callback_data="app_contact_call")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Связаться
def get_contact_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после запроса на связь"""
    keyboard = [
        [InlineKeyboardButton("📊 Пройти аудит магазина", callback_data="audit")],
        [InlineKeyboardButton("💸 Рассчитать упущенную выгоду", callback_data="calculator")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)
```

**Step 3: Commit**

```bash
git add app/client_bot/
git commit -m "feat: добавлены тексты и клавиатуры клиентского бота"
```

---

## Task 5: Парсер Ozon

**Files:**
- Create: `app/client_bot/services/ozon_parser.py`
- Create: `tests/test_ozon_parser.py`

**Step 1: Написать тест для парсера**

Create file `tests/test_ozon_parser.py`:

```python
"""
Тесты парсера Ozon
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.client_bot.services.ozon_parser import (
    extract_seller_id,
    parse_ozon_seller,
    OzonParseError
)


class TestExtractSellerId:
    """Тесты извлечения ID продавца из ссылки"""

    def test_extracts_from_full_url(self):
        """Извлекает ID из полной ссылки"""
        url = "https://www.ozon.ru/seller/wildberries-store-123456/"
        assert extract_seller_id(url) == "wildberries-store-123456"

    def test_extracts_from_short_url(self):
        """Извлекает ID из короткой ссылки"""
        url = "ozon.ru/seller/test-shop-789"
        assert extract_seller_id(url) == "test-shop-789"

    def test_extracts_numeric_id(self):
        """Извлекает числовой ID"""
        url = "https://ozon.ru/seller/123456"
        assert extract_seller_id(url) == "123456"

    def test_returns_none_for_invalid_url(self):
        """Возвращает None для невалидной ссылки"""
        url = "https://google.com/search?q=ozon"
        assert extract_seller_id(url) is None

    def test_returns_none_for_product_url(self):
        """Возвращает None для ссылки на товар"""
        url = "https://ozon.ru/product/iphone-123456"
        assert extract_seller_id(url) is None


class TestParseOzonSeller:
    """Тесты парсинга магазина"""

    @pytest.mark.asyncio
    async def test_parses_seller_data(self):
        """Парсит данные продавца"""
        mock_html = """
        <div data-widget="webSeller">
            <span>Рейтинг продавца: 4.8</span>
            <span>150 товаров</span>
        </div>
        """

        with patch('app.client_bot.services.ozon_parser.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await parse_ozon_seller("test-seller-123")

            assert result is not None
            assert "seller_id" in result
```

**Step 2: Запустить тест — должен упасть**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && python -m pytest tests/test_ozon_parser.py -v`
Expected: FAIL (модуль не найден)

**Step 3: Реализовать парсер**

Create directory `app/client_bot/services/` with `__init__.py`.

Create file `app/client_bot/services/ozon_parser.py`:

```python
"""
Парсер магазинов Ozon
"""
import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class OzonParseError(Exception):
    """Ошибка парсинга Ozon"""
    pass


@dataclass
class SellerData:
    """Данные о продавце"""
    seller_id: str
    name: str
    rating: Optional[float] = None
    products_count: Optional[int] = None
    reviews_info: Optional[str] = None


@dataclass
class ProductComparison:
    """Сравнение товара с конкурентами"""
    name: str
    seller_price: float
    best_price: float
    difference_percent: float
    recommendation: str


def extract_seller_id(url: str) -> Optional[str]:
    """
    Извлечь ID продавца из ссылки Ozon

    Args:
        url: Ссылка на магазин

    Returns:
        ID продавца или None
    """
    # Паттерны для ссылок на продавца
    patterns = [
        r'ozon\.ru/seller/([a-zA-Z0-9_-]+)',
        r'ozon\.ru/brand/([a-zA-Z0-9_-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            seller_id = match.group(1).rstrip('/')
            return seller_id

    return None


async def parse_ozon_seller(seller_id: str) -> Dict[str, Any]:
    """
    Парсинг данных о продавце Ozon

    Args:
        seller_id: ID продавца

    Returns:
        Данные о продавце

    Raises:
        OzonParseError: при ошибке парсинга
    """
    url = f"https://www.ozon.ru/seller/{seller_id}/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                raise OzonParseError(f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, 'lxml')

            # Извлекаем данные
            result = {
                "seller_id": seller_id,
                "url": url,
                "name": _extract_seller_name(soup),
                "rating": _extract_seller_rating(soup),
                "products_count": _extract_products_count(soup),
                "products": await _get_sample_products(client, seller_id, headers),
            }

            return result

    except httpx.TimeoutException:
        raise OzonParseError("Timeout при запросе к Ozon")
    except httpx.RequestError as e:
        raise OzonParseError(f"Ошибка запроса: {e}")
    except Exception as e:
        logger.error(f"Ошибка парсинга Ozon: {e}")
        raise OzonParseError(f"Ошибка парсинга: {e}")


def _extract_seller_name(soup: BeautifulSoup) -> str:
    """Извлечь название продавца"""
    # Пробуем разные селекторы
    selectors = [
        'h1',
        '[data-widget="webSeller"] h1',
        '.seller-info__title',
    ]

    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)

    return "Неизвестный продавец"


def _extract_seller_rating(soup: BeautifulSoup) -> Optional[float]:
    """Извлечь рейтинг продавца"""
    # Ищем рейтинг в тексте
    rating_pattern = r'(\d[.,]\d)\s*(?:из\s*5|★|звёзд)'

    text = soup.get_text()
    match = re.search(rating_pattern, text)

    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except ValueError:
            pass

    return None


def _extract_products_count(soup: BeautifulSoup) -> Optional[int]:
    """Извлечь количество товаров"""
    # Ищем паттерн "N товаров"
    count_pattern = r'(\d+)\s*товар'

    text = soup.get_text()
    match = re.search(count_pattern, text)

    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return None


async def _get_sample_products(
    client: httpx.AsyncClient,
    seller_id: str,
    headers: dict
) -> List[Dict[str, Any]]:
    """Получить примеры товаров для сравнения"""
    # Упрощённая реализация — возвращаем заглушку
    # В реальной версии нужно парсить каталог продавца
    return []


async def compare_with_competitors(
    product_name: str,
    seller_price: float
) -> Optional[ProductComparison]:
    """
    Сравнить цену товара с конкурентами

    Args:
        product_name: Название товара
        seller_price: Цена продавца

    Returns:
        Результат сравнения
    """
    # Упрощённая реализация — поиск аналогичных товаров
    # В реальной версии нужно искать по названию товара
    # и сравнивать цены
    return None


def format_audit_result(seller_data: Dict[str, Any]) -> str:
    """
    Форматировать результат аудита для отправки пользователю

    Args:
        seller_data: Данные о продавце

    Returns:
        Отформатированный текст
    """
    name = seller_data.get("name", "Неизвестный продавец")
    rating = seller_data.get("rating")
    products_count = seller_data.get("products_count")

    lines = [
        "📊 Мини-аудит магазина на Ozon",
        "",
        f"Магазин: \"{name}\"",
    ]

    if rating:
        lines.append(f"⭐ Рейтинг продавца: {rating}")

    if products_count:
        lines.append(f"📦 Товаров: {products_count} SKU")

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "💡 Рекомендации:",
        "• Настройте автоматический мониторинг цен конкурентов",
        "• Следите за рейтингом и отзывами ежедневно",
        "• Автоматизируйте отчётность для экономии времени",
        "",
        "Хотите настроить автоматический мониторинг?",
    ])

    return "\n".join(lines)
```

**Step 4: Запустить тесты — должны пройти**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && python -m pytest tests/test_ozon_parser.py -v`
Expected: PASSED

**Step 5: Commit**

```bash
git add app/client_bot/services/ tests/test_ozon_parser.py
git commit -m "feat: добавлен парсер магазинов Ozon"
```

---

## Task 6: AI-ответчик для FAQ

**Files:**
- Create: `app/client_bot/services/ai_responder.py`

**Step 1: Создать сервис AI-ответов**

Create file `app/client_bot/services/ai_responder.py`:

```python
"""
AI-ответчик для FAQ (Claude API)
"""
import logging
from typing import Optional

import httpx
from anthropic import Anthropic

from app.config import settings
from app.client_bot.texts.messages import (
    FAQ_COST, FAQ_TIMELINE, FAQ_MARKETPLACES,
    FAQ_TECHNICAL, FAQ_FREE_TRIAL, FAQ_OFF_TOPIC
)

logger = logging.getLogger(__name__)

# База знаний для AI
FAQ_KNOWLEDGE_BASE = f"""
Ты — помощник сервиса "Умная аналитика для маркетплейсов".
Владимир — специалист по аналитике и автоматизации для Ozon, Wildberries, Яндекс.Маркет.

ИНФОРМАЦИЯ ОБ УСЛУГАХ:

Стоимость:
{FAQ_COST}

Сроки:
{FAQ_TIMELINE}

Маркетплейсы:
{FAQ_MARKETPLACES}

Техническая реализация:
{FAQ_TECHNICAL}

Бесплатный тест:
{FAQ_FREE_TRIAL}

ПРАВИЛА ОТВЕТОВ:
- Отвечай кратко и по делу (2-4 предложения)
- Используй "вы" (формальный стиль)
- Если вопрос не про маркетплейсы/аналитику — вежливо откажись
- Не придумывай информацию, которой нет в базе знаний
- В конце можешь предложить оставить заявку для детального обсуждения
"""


class AIResponder:
    """AI-ответчик на вопросы пользователей"""

    def __init__(self):
        """Инициализация с proxy для Claude API"""
        proxy_url = settings.proxy_url
        if proxy_url:
            http_client = httpx.Client(proxy=proxy_url, timeout=60.0)
        else:
            http_client = httpx.Client(timeout=60.0)

        self.client = Anthropic(
            api_key=settings.anthropic_api_key,
            http_client=http_client
        )
        self.model = settings.claude_model

    async def answer_question(self, question: str) -> str:
        """
        Ответить на вопрос пользователя

        Args:
            question: Вопрос пользователя

        Returns:
            Ответ на вопрос
        """
        # Проверка на офф-топик (простая эвристика)
        if self._is_off_topic(question):
            return FAQ_OFF_TOPIC

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                system=FAQ_KNOWLEDGE_BASE,
                messages=[
                    {"role": "user", "content": question}
                ]
            )

            answer = response.content[0].text.strip()
            logger.info(f"AI answered question: {question[:50]}...")

            return answer

        except Exception as e:
            logger.error(f"AI error: {e}")
            return "К сожалению, не смог обработать ваш вопрос. Попробуйте переформулировать или оставьте заявку."

    def _is_off_topic(self, question: str) -> bool:
        """Проверка на офф-топик"""
        off_topic_keywords = [
            "погода", "новости", "политика", "спорт",
            "рецепт", "фильм", "музыка", "игра",
            "знакомств", "отношени", "шутк", "анекдот"
        ]

        question_lower = question.lower()
        return any(kw in question_lower for kw in off_topic_keywords)


# Синглтон для переиспользования
_ai_responder: Optional[AIResponder] = None


def get_ai_responder() -> AIResponder:
    """Получить экземпляр AI-ответчика"""
    global _ai_responder
    if _ai_responder is None:
        _ai_responder = AIResponder()
    return _ai_responder
```

**Step 2: Commit**

```bash
git add app/client_bot/services/ai_responder.py
git commit -m "feat: добавлен AI-ответчик для FAQ"
```

---

## Task 7: Сервис уведомлений администратора

**Files:**
- Create: `app/client_bot/services/lead_notifier.py`

**Step 1: Создать сервис уведомлений**

Create file `app/client_bot/services/lead_notifier.py`:

```python
"""
Сервис уведомлений администратора о заявках
"""
import logging
from typing import Optional, Dict, Any

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.config import settings
from app.client_bot.texts.messages import ADMIN_NEW_LEAD, ADMIN_CONTACT_REQUEST

logger = logging.getLogger(__name__)


class LeadNotifier:
    """Уведомления администратора о новых заявках"""

    def __init__(self, bot: Bot):
        """
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.admin_id = settings.telegram_admin_id

    async def notify_new_lead(
        self,
        name: str,
        username: str,
        contact_method: str,
        sku_count: str,
        urgency: str,
        marketplaces: list,
        budget: str,
        task: str,
        bot_activity: Dict[str, Any]
    ) -> bool:
        """
        Уведомить о новой заявке

        Returns:
            True если уведомление отправлено
        """
        # Форматируем активность в боте
        activity_lines = []
        if bot_activity.get("audit_done"):
            activity_lines.append("• Прошёл аудит магазина: Да")
        if bot_activity.get("calculator_done"):
            loss = bot_activity.get("calculated_loss", 0)
            activity_lines.append(f"• Калькулятор: Да (потери ~{loss:,} ₽/мес)")
        if bot_activity.get("faq_count", 0) > 0:
            activity_lines.append(f"• Вопросов в FAQ: {bot_activity['faq_count']}")

        activity_text = "\n".join(activity_lines) if activity_lines else "• Минимальная"

        message = ADMIN_NEW_LEAD.format(
            name=name or "Не указано",
            username=username or "Не указан",
            contact_method=contact_method or "Не указан",
            sku_count=sku_count or "Не указано",
            urgency=urgency or "Не указана",
            marketplaces=", ".join(marketplaces) if marketplaces else "Не указаны",
            budget=budget or "Не указан",
            task=task or "Не указана",
            bot_activity=activity_text
        )

        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Lead notification sent for @{username}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send lead notification: {e}")
            return False

    async def notify_contact_request(
        self,
        username: str,
        first_name: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Уведомить о запросе на связь

        Returns:
            True если уведомление отправлено
        """
        text = ADMIN_CONTACT_REQUEST.format(
            username=username or "Не указан",
            first_name=first_name or "Пользователь",
            message=message or "Без сообщения"
        )

        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=text
            )
            logger.info(f"Contact request notification sent for @{username}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send contact notification: {e}")
            return False
```

**Step 2: Commit**

```bash
git add app/client_bot/services/lead_notifier.py
git commit -m "feat: добавлен сервис уведомлений администратора"
```

---

## Task 8: Обработчик /start и главное меню

**Files:**
- Create: `app/client_bot/handlers/start.py`

**Step 1: Создать обработчик start**

Create directory `app/client_bot/handlers/` with `__init__.py`.

Create file `app/client_bot/handlers/start.py`:

```python
"""
Обработчик команды /start и главного меню
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.client_bot.texts.messages import WELCOME_MESSAGE
from app.client_bot.keyboards.menus import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"User {user.id} (@{user.username}) started the bot")

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки возврата в меню"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )


def get_start_handlers() -> list:
    """Получить обработчики для регистрации"""
    return [
        CommandHandler("start", start_handler),
        CallbackQueryHandler(menu_callback_handler, pattern="^menu$"),
    ]
```

**Step 2: Commit**

```bash
git add app/client_bot/handlers/
git commit -m "feat: добавлен обработчик /start и главное меню"
```

---

## Task 9: Обработчик калькулятора упущенной выгоды

**Files:**
- Create: `app/client_bot/handlers/calculator.py`

**Step 1: Создать обработчик калькулятора**

Create file `app/client_bot/handlers/calculator.py`:

```python
"""
Обработчик калькулятора упущенной выгоды
"""
import logging
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import (
    CALC_HOURS_QUESTION, CALC_HOURLY_RATE_QUESTION,
    CALC_PRICING_ERRORS_QUESTION, CALC_COMPETITOR_CHECK_QUESTION,
    CALC_RESULT_TEMPLATE
)
from app.client_bot.keyboards.menus import (
    get_calc_hours_keyboard, get_calc_rate_keyboard,
    get_calc_errors_keyboard, get_calc_competitor_keyboard,
    get_calc_result_keyboard, get_main_menu_keyboard
)

logger = logging.getLogger(__name__)

# Состояния калькулятора
CALC_HOURS, CALC_RATE, CALC_RATE_CUSTOM, CALC_ERRORS, CALC_COMPETITOR = range(5)


async def calculator_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало калькулятора"""
    query = update.callback_query
    await query.answer()

    # Очищаем предыдущие данные
    context.user_data["calc"] = {}

    await query.edit_message_text(
        CALC_HOURS_QUESTION,
        reply_markup=get_calc_hours_keyboard()
    )

    return CALC_HOURS


async def calc_hours_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора часов"""
    query = update.callback_query
    await query.answer()

    # Парсим значение из callback_data
    hours_map = {
        "calc_hours_3": 3,
        "calc_hours_10": 10,
        "calc_hours_15": 15,
    }

    hours = hours_map.get(query.data, 10)
    context.user_data["calc"]["hours"] = hours

    await query.edit_message_text(
        CALC_HOURLY_RATE_QUESTION,
        reply_markup=get_calc_rate_keyboard()
    )

    return CALC_RATE


async def calc_rate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора ставки"""
    query = update.callback_query
    await query.answer()

    if query.data == "calc_rate_custom":
        await query.edit_message_text(
            "Введите стоимость вашего часа работы (число в рублях):"
        )
        return CALC_RATE_CUSTOM

    rate_map = {
        "calc_rate_500": 500,
        "calc_rate_1000": 1000,
        "calc_rate_2000": 2000,
    }

    rate = rate_map.get(query.data, 1000)
    context.user_data["calc"]["rate"] = rate

    await query.edit_message_text(
        CALC_PRICING_ERRORS_QUESTION,
        reply_markup=get_calc_errors_keyboard()
    )

    return CALC_ERRORS


async def calc_rate_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кастомной ставки"""
    try:
        rate = int(update.message.text.strip().replace(" ", "").replace("₽", ""))
        context.user_data["calc"]["rate"] = rate
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число. Например: 1500"
        )
        return CALC_RATE_CUSTOM

    await update.message.reply_text(
        CALC_PRICING_ERRORS_QUESTION,
        reply_markup=get_calc_errors_keyboard()
    )

    return CALC_ERRORS


async def calc_errors_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора ошибок в ценах"""
    query = update.callback_query
    await query.answer()

    errors_map = {
        "calc_errors_big": "big",
        "calc_errors_small": "small",
        "calc_errors_no": "no",
    }

    errors = errors_map.get(query.data, "small")
    context.user_data["calc"]["errors"] = errors

    await query.edit_message_text(
        CALC_COMPETITOR_CHECK_QUESTION,
        reply_markup=get_calc_competitor_keyboard()
    )

    return CALC_COMPETITOR


async def calc_competitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора частоты проверки конкурентов и вывод результата"""
    query = update.callback_query
    await query.answer()

    competitor_map = {
        "calc_comp_daily": "daily",
        "calc_comp_weekly": "weekly",
        "calc_comp_rarely": "rarely",
    }

    competitor = competitor_map.get(query.data, "weekly")
    context.user_data["calc"]["competitor"] = competitor

    # Расчёт
    result = calculate_losses(context.user_data["calc"])

    # Сохраняем для статистики
    context.user_data["calc"]["result"] = result
    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["calculator_done"] = True
    context.user_data["bot_activity"]["calculated_loss"] = result["total_loss"]

    await query.edit_message_text(
        result["message"],
        reply_markup=get_calc_result_keyboard()
    )

    return ConversationHandler.END


def calculate_losses(data: Dict[str, Any]) -> Dict[str, Any]:
    """Расчёт упущенной выгоды"""
    hours = data.get("hours", 10)
    rate = data.get("rate", 1000)
    errors = data.get("errors", "small")
    competitor = data.get("competitor", "weekly")

    # Ручная работа
    manual_work_cost = hours * rate * 4

    # Ошибки в ценах
    errors_map = {
        "big": (25000, "Средняя потеря при серьёзных ошибках = 25 000 ₽/мес*"),
        "small": (10000, "Средняя потеря при мелких ошибках = 10 000 ₽/мес*"),
        "no": (0, "Отлично, что ошибок нет!"),
    }
    errors_cost, errors_text = errors_map.get(errors, (10000, ""))

    # Упущенные продажи
    competitor_map = {
        "daily": (0, "Вы следите за рынком — отлично!"),
        "weekly": (15000, "~3-5% упущенных продаж из-за неоптимальных цен"),
        "rarely": (30000, "~5-10% оборота теряется при редкой проверке цен"),
    }
    competitor_cost, competitor_text = competitor_map.get(competitor, (15000, ""))

    total_loss = manual_work_cost + errors_cost + competitor_cost

    message = CALC_RESULT_TEMPLATE.format(
        hours_per_week=hours,
        hourly_rate=rate,
        manual_work_cost=manual_work_cost,
        pricing_errors_text=errors_text,
        competitor_text=competitor_text,
        total_loss=total_loss
    )

    return {
        "message": message,
        "total_loss": total_loss,
        "manual_work_cost": manual_work_cost,
        "errors_cost": errors_cost,
        "competitor_cost": competitor_cost,
    }


async def calc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена калькулятора"""
    query = update.callback_query
    await query.answer()

    from app.client_bot.texts.messages import WELCOME_MESSAGE

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_calculator_handler() -> ConversationHandler:
    """Получить ConversationHandler для калькулятора"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(calculator_start, pattern="^calculator$"),
        ],
        states={
            CALC_HOURS: [
                CallbackQueryHandler(calc_hours_handler, pattern="^calc_hours_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
            CALC_RATE: [
                CallbackQueryHandler(calc_rate_handler, pattern="^calc_rate_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
            CALC_RATE_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, calc_rate_custom_handler),
            ],
            CALC_ERRORS: [
                CallbackQueryHandler(calc_errors_handler, pattern="^calc_errors_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
            CALC_COMPETITOR: [
                CallbackQueryHandler(calc_competitor_handler, pattern="^calc_comp_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(calc_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
```

**Step 2: Commit**

```bash
git add app/client_bot/handlers/calculator.py
git commit -m "feat: добавлен калькулятор упущенной выгоды"
```

---

## Task 10: Обработчик FAQ

**Files:**
- Create: `app/client_bot/handlers/faq.py`

**Step 1: Создать обработчик FAQ**

Create file `app/client_bot/handlers/faq.py`:

```python
"""
Обработчик FAQ
"""
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import (
    FAQ_MENU, FAQ_COST, FAQ_TIMELINE, FAQ_MARKETPLACES,
    FAQ_TECHNICAL, FAQ_FREE_TRIAL, FAQ_CUSTOM_QUESTION
)
from app.client_bot.keyboards.menus import (
    get_faq_menu_keyboard, get_faq_answer_keyboard, get_main_menu_keyboard
)
from app.client_bot.services.ai_responder import get_ai_responder

logger = logging.getLogger(__name__)

# Состояния
FAQ_CUSTOM_INPUT = 0


async def faq_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать меню FAQ"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        FAQ_MENU,
        reply_markup=get_faq_menu_keyboard()
    )

    return ConversationHandler.END


async def faq_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ответ на вопрос из FAQ"""
    query = update.callback_query
    await query.answer()

    # Маппинг вопросов к ответам
    answers = {
        "faq_cost": FAQ_COST,
        "faq_timeline": FAQ_TIMELINE,
        "faq_marketplaces": FAQ_MARKETPLACES,
        "faq_technical": FAQ_TECHNICAL,
        "faq_trial": FAQ_FREE_TRIAL,
    }

    answer = answers.get(query.data, "Извините, ответ не найден.")

    # Считаем вопросы для статистики
    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["faq_count"] = \
        context.user_data["bot_activity"].get("faq_count", 0) + 1

    await query.edit_message_text(
        answer,
        reply_markup=get_faq_answer_keyboard()
    )

    return ConversationHandler.END


async def faq_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало ввода своего вопроса"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(FAQ_CUSTOM_QUESTION)

    return FAQ_CUSTOM_INPUT


async def faq_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка своего вопроса через AI"""
    question = update.message.text.strip()

    # Считаем вопросы
    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["faq_count"] = \
        context.user_data["bot_activity"].get("faq_count", 0) + 1

    # Отправляем "печатает..."
    await update.message.chat.send_action("typing")

    # Получаем ответ от AI
    ai_responder = get_ai_responder()
    answer = await ai_responder.answer_question(question)

    await update.message.reply_text(
        answer,
        reply_markup=get_faq_answer_keyboard()
    )

    return ConversationHandler.END


async def faq_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена FAQ"""
    query = update.callback_query
    await query.answer()

    from app.client_bot.texts.messages import WELCOME_MESSAGE

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_faq_handler() -> ConversationHandler:
    """Получить ConversationHandler для FAQ"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(faq_menu_handler, pattern="^faq$"),
        ],
        states={
            FAQ_CUSTOM_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, faq_custom_handler),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(faq_cancel, pattern="^menu$"),
            CallbackQueryHandler(faq_answer_handler, pattern="^faq_(cost|timeline|marketplaces|technical|trial)$"),
            CallbackQueryHandler(faq_custom_start, pattern="^faq_custom$"),
        ],
        per_message=False,
    )


def get_faq_direct_handlers() -> list:
    """Дополнительные обработчики для прямых callback"""
    return [
        CallbackQueryHandler(faq_answer_handler, pattern="^faq_(cost|timeline|marketplaces|technical|trial)$"),
    ]
```

**Step 2: Commit**

```bash
git add app/client_bot/handlers/faq.py
git commit -m "feat: добавлен обработчик FAQ с AI-ответами"
```

---

## Task 11: Обработчик аудита Ozon

**Files:**
- Create: `app/client_bot/handlers/audit.py`

**Step 1: Создать обработчик аудита**

Create file `app/client_bot/handlers/audit.py`:

```python
"""
Обработчик мини-аудита магазина Ozon
"""
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.config import settings
from app.client_bot.texts.messages import (
    AUDIT_REQUEST_LINK, AUDIT_INVALID_LINK,
    AUDIT_PARSING_ERROR, AUDIT_LIMIT_REACHED
)
from app.client_bot.keyboards.menus import (
    get_back_to_menu_keyboard, get_audit_result_keyboard,
    get_audit_limit_keyboard, get_main_menu_keyboard
)
from app.client_bot.services.ozon_parser import (
    extract_seller_id, parse_ozon_seller,
    format_audit_result, OzonParseError
)

logger = logging.getLogger(__name__)

# Состояния
AUDIT_WAITING_LINK = 0


async def audit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало аудита — запрос ссылки"""
    query = update.callback_query
    await query.answer()

    # Проверяем лимит (упрощённо — через user_data)
    audits_today = context.user_data.get("audits_today", 0)
    limit = settings.audit_daily_limit

    if audits_today >= limit:
        await query.edit_message_text(
            AUDIT_LIMIT_REACHED,
            reply_markup=get_audit_limit_keyboard()
        )
        return ConversationHandler.END

    await query.edit_message_text(
        AUDIT_REQUEST_LINK,
        reply_markup=get_back_to_menu_keyboard()
    )

    return AUDIT_WAITING_LINK


async def audit_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ссылки на магазин"""
    link = update.message.text.strip()

    # Извлекаем ID продавца
    seller_id = extract_seller_id(link)

    if not seller_id:
        await update.message.reply_text(
            AUDIT_INVALID_LINK,
            reply_markup=get_back_to_menu_keyboard()
        )
        return AUDIT_WAITING_LINK

    # Отправляем "печатает..."
    await update.message.chat.send_action("typing")

    try:
        # Парсим магазин
        seller_data = await parse_ozon_seller(seller_id)

        # Форматируем результат
        result_text = format_audit_result(seller_data)

        # Увеличиваем счётчик аудитов
        context.user_data["audits_today"] = context.user_data.get("audits_today", 0) + 1

        # Сохраняем для статистики
        if "bot_activity" not in context.user_data:
            context.user_data["bot_activity"] = {}
        context.user_data["bot_activity"]["audit_done"] = True

        await update.message.reply_text(
            result_text,
            reply_markup=get_audit_result_keyboard()
        )

        logger.info(f"Audit completed for seller: {seller_id}")

    except OzonParseError as e:
        logger.error(f"Ozon parse error: {e}")
        await update.message.reply_text(
            AUDIT_PARSING_ERROR,
            reply_markup=get_audit_result_keyboard()
        )

    return ConversationHandler.END


async def audit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена аудита"""
    query = update.callback_query
    await query.answer()

    from app.client_bot.texts.messages import WELCOME_MESSAGE

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_audit_handler() -> ConversationHandler:
    """Получить ConversationHandler для аудита"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(audit_start, pattern="^audit$"),
        ],
        states={
            AUDIT_WAITING_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, audit_link_handler),
                CallbackQueryHandler(audit_cancel, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(audit_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
```

**Step 2: Commit**

```bash
git add app/client_bot/handlers/audit.py
git commit -m "feat: добавлен обработчик аудита магазина Ozon"
```

---

## Task 12: Обработчик заявки

**Files:**
- Create: `app/client_bot/handlers/application.py`

**Step 1: Создать обработчик заявки**

Create file `app/client_bot/handlers/application.py`:

```python
"""
Обработчик формы заявки
"""
import logging
from typing import List

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import (
    APPLICATION_SKU_QUESTION, APPLICATION_URGENCY_QUESTION,
    APPLICATION_MARKETPLACES_QUESTION, APPLICATION_NAME_QUESTION,
    APPLICATION_TASK_QUESTION, APPLICATION_BUDGET_QUESTION,
    APPLICATION_CONTACT_METHOD_QUESTION, APPLICATION_SUCCESS
)
from app.client_bot.keyboards.menus import (
    get_sku_keyboard, get_urgency_keyboard, get_marketplaces_keyboard,
    get_budget_keyboard, get_contact_method_keyboard, get_main_menu_keyboard
)

logger = logging.getLogger(__name__)

# Состояния
(APP_SKU, APP_URGENCY, APP_MARKETPLACES,
 APP_NAME, APP_TASK, APP_BUDGET, APP_CONTACT) = range(7)


async def application_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало заявки — вопрос о SKU"""
    query = update.callback_query
    await query.answer()

    # Очищаем предыдущие данные
    context.user_data["application"] = {
        "marketplaces": []
    }

    await query.edit_message_text(
        APPLICATION_SKU_QUESTION,
        reply_markup=get_sku_keyboard()
    )

    return APP_SKU


async def app_sku_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора SKU"""
    query = update.callback_query
    await query.answer()

    sku_map = {
        "app_sku_lt50": "< 50",
        "app_sku_50_200": "50-200",
        "app_sku_200_500": "200-500",
        "app_sku_gt500": "> 500",
    }

    context.user_data["application"]["sku_count"] = sku_map.get(query.data, "Не указано")

    await query.edit_message_text(
        APPLICATION_URGENCY_QUESTION,
        reply_markup=get_urgency_keyboard()
    )

    return APP_URGENCY


async def app_urgency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора срочности"""
    query = update.callback_query
    await query.answer()

    urgency_map = {
        "app_urgency_now": "Нужно сейчас",
        "app_urgency_month": "В ближайший месяц",
        "app_urgency_looking": "Просто смотрю",
    }

    context.user_data["application"]["urgency"] = urgency_map.get(query.data, "Не указано")

    await query.edit_message_text(
        APPLICATION_MARKETPLACES_QUESTION,
        reply_markup=get_marketplaces_keyboard()
    )

    return APP_MARKETPLACES


async def app_marketplaces_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора маркетплейсов (мультивыбор)"""
    query = update.callback_query
    await query.answer()

    mp_map = {
        "app_mp_ozon": "Ozon",
        "app_mp_wb": "Wildberries",
        "app_mp_yandex": "Яндекс.Маркет",
    }

    if query.data == "app_mp_done":
        # Переходим к следующему вопросу
        await query.edit_message_text(
            APPLICATION_NAME_QUESTION
        )
        return APP_NAME

    # Переключаем выбор маркетплейса
    mp = mp_map.get(query.data)
    if mp:
        selected: List[str] = context.user_data["application"].get("marketplaces", [])
        if mp in selected:
            selected.remove(mp)
        else:
            selected.append(mp)
        context.user_data["application"]["marketplaces"] = selected

    await query.edit_message_text(
        APPLICATION_MARKETPLACES_QUESTION,
        reply_markup=get_marketplaces_keyboard(
            context.user_data["application"]["marketplaces"]
        )
    )

    return APP_MARKETPLACES


async def app_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка имени"""
    name = update.message.text.strip()
    context.user_data["application"]["name"] = name

    await update.message.reply_text(APPLICATION_TASK_QUESTION)

    return APP_TASK


async def app_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка описания задачи"""
    task = update.message.text.strip()
    context.user_data["application"]["task"] = task

    await update.message.reply_text(
        APPLICATION_BUDGET_QUESTION,
        reply_markup=get_budget_keyboard()
    )

    return APP_BUDGET


async def app_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора бюджета"""
    query = update.callback_query
    await query.answer()

    budget_map = {
        "app_budget_lt30": "до 30 тыс",
        "app_budget_30_50": "30-50 тыс",
        "app_budget_50_100": "50-100 тыс",
        "app_budget_gt100": "> 100 тыс",
        "app_budget_unknown": "Не определён",
    }

    context.user_data["application"]["budget"] = budget_map.get(query.data, "Не указан")

    await query.edit_message_text(
        APPLICATION_CONTACT_METHOD_QUESTION,
        reply_markup=get_contact_method_keyboard()
    )

    return APP_CONTACT


async def app_contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка способа связи и отправка заявки"""
    query = update.callback_query
    await query.answer()

    contact_map = {
        "app_contact_telegram": "Telegram",
        "app_contact_whatsapp": "WhatsApp",
        "app_contact_call": "Звонок",
    }

    context.user_data["application"]["contact_method"] = contact_map.get(query.data, "Telegram")

    # Получаем данные пользователя
    user = update.effective_user
    app_data = context.user_data["application"]
    bot_activity = context.user_data.get("bot_activity", {})

    # Отправляем уведомление администратору
    from app.client_bot.services.lead_notifier import LeadNotifier
    notifier = LeadNotifier(context.bot)

    await notifier.notify_new_lead(
        name=app_data.get("name"),
        username=user.username,
        contact_method=app_data.get("contact_method"),
        sku_count=app_data.get("sku_count"),
        urgency=app_data.get("urgency"),
        marketplaces=app_data.get("marketplaces", []),
        budget=app_data.get("budget"),
        task=app_data.get("task"),
        bot_activity=bot_activity
    )

    logger.info(f"New lead from @{user.username}: {app_data}")

    await query.edit_message_text(
        APPLICATION_SUCCESS,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


async def app_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена заявки"""
    query = update.callback_query
    await query.answer()

    from app.client_bot.texts.messages import WELCOME_MESSAGE

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_application_handler() -> ConversationHandler:
    """Получить ConversationHandler для заявки"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(application_start, pattern="^application$"),
        ],
        states={
            APP_SKU: [
                CallbackQueryHandler(app_sku_handler, pattern="^app_sku_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_URGENCY: [
                CallbackQueryHandler(app_urgency_handler, pattern="^app_urgency_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_MARKETPLACES: [
                CallbackQueryHandler(app_marketplaces_handler, pattern="^app_mp_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, app_name_handler),
            ],
            APP_TASK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, app_task_handler),
            ],
            APP_BUDGET: [
                CallbackQueryHandler(app_budget_handler, pattern="^app_budget_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_CONTACT: [
                CallbackQueryHandler(app_contact_handler, pattern="^app_contact_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(app_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
```

**Step 2: Commit**

```bash
git add app/client_bot/handlers/application.py
git commit -m "feat: добавлен обработчик формы заявки"
```

---

## Task 13: Обработчик "Связаться с человеком"

**Files:**
- Create: `app/client_bot/handlers/contact.py`

**Step 1: Создать обработчик**

Create file `app/client_bot/handlers/contact.py`:

```python
"""
Обработчик кнопки "Связаться с человеком"
"""
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import CONTACT_REQUEST, CONTACT_WITH_MESSAGE
from app.client_bot.keyboards.menus import get_contact_keyboard, get_main_menu_keyboard
from app.client_bot.services.lead_notifier import LeadNotifier

logger = logging.getLogger(__name__)

# Состояния
CONTACT_MESSAGE = 0


async def contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало запроса на связь"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(CONTACT_WITH_MESSAGE)

    return CONTACT_MESSAGE


async def contact_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка сообщения для передачи"""
    message = update.message.text.strip()
    user = update.effective_user

    # Отправляем уведомление администратору
    notifier = LeadNotifier(context.bot)
    await notifier.notify_contact_request(
        username=user.username,
        first_name=user.first_name,
        message=message
    )

    logger.info(f"Contact request from @{user.username}: {message[:50]}...")

    await update.message.reply_text(
        CONTACT_REQUEST,
        reply_markup=get_contact_keyboard()
    )

    return ConversationHandler.END


async def contact_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена"""
    query = update.callback_query
    await query.answer()

    from app.client_bot.texts.messages import WELCOME_MESSAGE

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_contact_handler() -> ConversationHandler:
    """Получить ConversationHandler для связи"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(contact_start, pattern="^contact$"),
        ],
        states={
            CONTACT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, contact_message_handler),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(contact_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
```

**Step 2: Commit**

```bash
git add app/client_bot/handlers/contact.py
git commit -m "feat: добавлен обработчик связи с человеком"
```

---

## Task 14: Главный модуль бота

**Files:**
- Create: `app/client_bot/bot.py`

**Step 1: Создать главный модуль**

Create file `app/client_bot/bot.py`:

```python
"""
Главный модуль клиентского бота
"""
import logging

from telegram.ext import Application

from app.config import settings
from app.client_bot.handlers.start import get_start_handlers
from app.client_bot.handlers.calculator import get_calculator_handler
from app.client_bot.handlers.faq import get_faq_handler, get_faq_direct_handlers
from app.client_bot.handlers.audit import get_audit_handler
from app.client_bot.handlers.application import get_application_handler
from app.client_bot.handlers.contact import get_contact_handler

logger = logging.getLogger(__name__)


def create_client_bot_application() -> Application:
    """
    Создать и настроить приложение клиентского бота

    Returns:
        Настроенное приложение Telegram бота
    """
    token = settings.telegram_client_bot_token

    if not token:
        raise ValueError("TELEGRAM_CLIENT_BOT_TOKEN не задан в .env")

    # Создаём приложение
    application = Application.builder().token(token).build()

    # Добавляем обработчики
    # Порядок важен! ConversationHandler должны быть до простых handlers

    # ConversationHandlers
    application.add_handler(get_calculator_handler())
    application.add_handler(get_faq_handler())
    application.add_handler(get_audit_handler())
    application.add_handler(get_application_handler())
    application.add_handler(get_contact_handler())

    # Простые handlers
    for handler in get_start_handlers():
        application.add_handler(handler)

    for handler in get_faq_direct_handlers():
        application.add_handler(handler)

    logger.info("Client bot application created")

    return application


async def run_client_bot() -> None:
    """Запустить клиентского бота"""
    application = create_client_bot_application()

    logger.info("Starting client bot...")

    # Запускаем polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    logger.info("Client bot is running")

    # Держим бота запущенным
    import asyncio
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(run_client_bot())
```

**Step 2: Commit**

```bash
git add app/client_bot/bot.py
git commit -m "feat: добавлен главный модуль клиентского бота"
```

---

## Task 15: Интеграционный тест

**Files:**
- Create: `tests/test_client_bot_integration.py`

**Step 1: Создать интеграционный тест**

Create file `tests/test_client_bot_integration.py`:

```python
"""
Интеграционные тесты клиентского бота
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat, CallbackQuery


@pytest.fixture
def mock_update():
    """Создать мок Update"""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 123456789
    update.effective_user.username = "test_user"
    update.effective_user.first_name = "Test"
    return update


@pytest.fixture
def mock_context():
    """Создать мок Context"""
    context = MagicMock()
    context.user_data = {}
    context.bot = AsyncMock()
    return context


class TestStartHandler:
    """Тесты обработчика /start"""

    @pytest.mark.asyncio
    async def test_start_sends_welcome_message(self, mock_update, mock_context):
        """Проверяет что /start отправляет приветственное сообщение"""
        from app.client_bot.handlers.start import start_handler

        mock_update.message = AsyncMock()
        mock_update.message.reply_text = AsyncMock()

        await start_handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Здравствуйте" in call_args[0][0]


class TestCalculator:
    """Тесты калькулятора"""

    def test_calculate_losses(self):
        """Проверяет расчёт упущенной выгоды"""
        from app.client_bot.handlers.calculator import calculate_losses

        data = {
            "hours": 10,
            "rate": 1000,
            "errors": "big",
            "competitor": "rarely",
        }

        result = calculate_losses(data)

        assert result["manual_work_cost"] == 40000  # 10 * 1000 * 4
        assert result["errors_cost"] == 25000
        assert result["competitor_cost"] == 30000
        assert result["total_loss"] == 95000


class TestOzonParser:
    """Тесты парсера Ozon"""

    def test_extract_seller_id_from_url(self):
        """Проверяет извлечение ID продавца из URL"""
        from app.client_bot.services.ozon_parser import extract_seller_id

        url = "https://www.ozon.ru/seller/test-shop-123456/"
        seller_id = extract_seller_id(url)

        assert seller_id == "test-shop-123456"

    def test_extract_seller_id_invalid_url(self):
        """Проверяет что невалидный URL возвращает None"""
        from app.client_bot.services.ozon_parser import extract_seller_id

        url = "https://google.com/search"
        seller_id = extract_seller_id(url)

        assert seller_id is None
```

**Step 2: Запустить тесты**

Run: `cd /Users/vladimirbragin/projects/telegram-ai-agent && python -m pytest tests/test_client_bot_integration.py -v`
Expected: PASSED

**Step 3: Commit**

```bash
git add tests/test_client_bot_integration.py
git commit -m "test: добавлены интеграционные тесты клиентского бота"
```

---

## Task 16: Скрипт запуска и документация

**Files:**
- Create: `scripts/run_client_bot.py`
- Modify: `CLAUDE.md` (add client bot section)

**Step 1: Создать скрипт запуска**

Create file `scripts/run_client_bot.py`:

```python
#!/usr/bin/env python3
"""
Скрипт запуска клиентского бота
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.client_bot.bot import run_client_bot


def main():
    """Точка входа"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/client_bot.log")
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Client Bot...")

    try:
        asyncio.run(run_client_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    main()
```

**Step 2: Добавить информацию в CLAUDE.md**

Add to CLAUDE.md after "## Команды" section:

```markdown
## Client Bot (лид-генерация)

Отдельный бот для работы с клиентами.

**Запуск:**
```bash
python scripts/run_client_bot.py
```

**Функции:**
- Мини-аудит магазина Ozon (2 аудита/день)
- Калькулятор упущенной выгоды
- FAQ с AI-ответами (Claude)
- Форма заявки с квалификацией
- Пересылка заявок администратору

**Модули:** `app/client_bot/`
```

**Step 3: Commit**

```bash
git add scripts/run_client_bot.py CLAUDE.md
git commit -m "docs: добавлен скрипт запуска и документация клиентского бота"
```

---

## Checklist

После выполнения всех задач:

- [ ] Task 1: Конфигурация
- [ ] Task 2: Модели БД
- [ ] Task 3: CRUD операции
- [ ] Task 4: Тексты и клавиатуры
- [ ] Task 5: Парсер Ozon
- [ ] Task 6: AI-ответчик
- [ ] Task 7: Уведомления администратора
- [ ] Task 8: Обработчик /start
- [ ] Task 9: Калькулятор
- [ ] Task 10: FAQ
- [ ] Task 11: Аудит Ozon
- [ ] Task 12: Форма заявки
- [ ] Task 13: Связаться с человеком
- [ ] Task 14: Главный модуль бота
- [ ] Task 15: Интеграционные тесты
- [ ] Task 16: Скрипт запуска

**Финальная проверка:**
```bash
# Запустить все тесты
python -m pytest tests/ -v

# Проверить что бот создаётся без ошибок
python -c "from app.client_bot.bot import create_client_bot_application; print('OK')"
```
