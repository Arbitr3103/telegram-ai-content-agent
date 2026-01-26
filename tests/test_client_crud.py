"""
Тесты CRUD операций клиентского бота
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.database.client_crud import (
    get_or_create_user,
    create_lead,
    can_do_audit,
    increment_audit_count,
    get_user_leads,
    update_lead_status,
    get_or_create_conversation,
    update_conversation_messages,
)


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
        existing_user.username = "old_username"
        existing_user.first_name = "OldName"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user = get_or_create_user(
            db=mock_db,
            telegram_id=123456789,
            username="test_user",
            first_name="Test"
        )

        assert user == existing_user
        mock_db.add.assert_not_called()

    def test_updates_username_for_existing_user(self):
        """Обновляет username для существующего пользователя"""
        mock_db = MagicMock()
        existing_user = MagicMock()
        existing_user.telegram_id = 123456789
        existing_user.username = "old_username"
        existing_user.first_name = "Test"
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user = get_or_create_user(
            db=mock_db,
            telegram_id=123456789,
            username="new_username",
            first_name="Test"
        )

        assert user.username == "new_username"
        mock_db.commit.assert_called_once()


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

    def test_allows_after_day_reset(self):
        """Разрешает после сброса дня"""
        mock_user = MagicMock()
        mock_user.audits_today = 2
        # Дата сброса была вчера
        mock_user.audits_reset_date = datetime.now(timezone.utc) - timedelta(days=1)

        result = can_do_audit(mock_user, limit=2)

        assert result is True
        # Счётчик должен сброситься
        assert mock_user.audits_today == 0

    def test_allows_when_under_limit(self):
        """Разрешает когда не достигнут лимит"""
        mock_user = MagicMock()
        mock_user.audits_today = 1
        mock_user.audits_reset_date = datetime.now(timezone.utc)

        result = can_do_audit(mock_user, limit=2)

        assert result is True


class TestIncrementAuditCount:
    """Тесты увеличения счётчика аудитов"""

    def test_increments_count(self):
        """Увеличивает счётчик на 1"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.audits_today = 0

        increment_audit_count(mock_db, mock_user)

        assert mock_user.audits_today == 1
        mock_db.commit.assert_called_once()

    def test_updates_reset_date(self):
        """Обновляет дату сброса"""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.audits_today = 1
        mock_user.audits_reset_date = None

        increment_audit_count(mock_db, mock_user)

        assert mock_user.audits_reset_date is not None


class TestCreateLead:
    """Тесты создания заявки"""

    def test_creates_lead_with_all_fields(self):
        """Создаёт заявку со всеми полями"""
        mock_db = MagicMock()

        lead = create_lead(
            db=mock_db,
            user_id=1,
            name="Иван Иванов",
            task="Нужна аналитика продаж",
            budget="50000-100000",
            contact_method="telegram",
            sku_count="100-500",
            urgency="urgent",
            marketplaces=["ozon", "wildberries"],
            bot_activity={"sessions": 3, "last_action": "audit"}
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_creates_lead_with_minimal_fields(self):
        """Создаёт заявку с минимальными полями"""
        mock_db = MagicMock()

        lead = create_lead(
            db=mock_db,
            user_id=1
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()


class TestGetUserLeads:
    """Тесты получения заявок пользователя"""

    def test_returns_user_leads(self):
        """Возвращает заявки пользователя"""
        mock_db = MagicMock()
        mock_leads = [MagicMock(), MagicMock()]
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_leads

        leads = get_user_leads(mock_db, user_id=1)

        assert leads == mock_leads

    def test_returns_empty_list_for_new_user(self):
        """Возвращает пустой список для нового пользователя"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        leads = get_user_leads(mock_db, user_id=999)

        assert leads == []


class TestUpdateLeadStatus:
    """Тесты обновления статуса заявки"""

    def test_updates_existing_lead(self):
        """Обновляет статус существующей заявки"""
        mock_db = MagicMock()
        mock_lead = MagicMock()
        mock_lead.status = "new"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_lead

        lead = update_lead_status(mock_db, lead_id=1, status="contacted")

        assert lead.status == "contacted"
        mock_db.commit.assert_called_once()

    def test_returns_none_for_nonexistent_lead(self):
        """Возвращает None для несуществующей заявки"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        lead = update_lead_status(mock_db, lead_id=999, status="contacted")

        assert lead is None
        mock_db.commit.assert_not_called()


class TestGetOrCreateConversation:
    """Тесты получения/создания диалога"""

    def test_creates_new_conversation(self):
        """Создаёт новый диалог если не существует"""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        conversation = get_or_create_conversation(mock_db, user_id=1)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_returns_existing_conversation(self):
        """Возвращает существующий диалог"""
        mock_db = MagicMock()
        existing_conv = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_conv

        conversation = get_or_create_conversation(mock_db, user_id=1)

        assert conversation == existing_conv
        mock_db.add.assert_not_called()


class TestUpdateConversationMessages:
    """Тесты обновления сообщений диалога"""

    def test_updates_messages(self):
        """Обновляет сообщения в диалоге"""
        mock_db = MagicMock()
        mock_conv = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conv

        new_messages = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Здравствуйте!"}
        ]

        conversation = update_conversation_messages(
            mock_db,
            conversation_id=1,
            messages=new_messages
        )

        assert conversation.messages == new_messages
        mock_db.commit.assert_called_once()

    def test_updates_context(self):
        """Обновляет контекст диалога"""
        mock_db = MagicMock()
        mock_conv = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_conv

        conversation = update_conversation_messages(
            mock_db,
            conversation_id=1,
            messages=[],
            context="Пользователь интересуется аналитикой"
        )

        assert conversation.context == "Пользователь интересуется аналитикой"
