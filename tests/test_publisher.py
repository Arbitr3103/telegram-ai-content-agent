"""Tests for TelegramPublisher"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.telegram.publisher import TelegramPublisher


@pytest.fixture
def mock_bot():
    with patch('app.telegram.publisher.Bot') as mock:
        bot_instance = AsyncMock()
        mock.return_value = bot_instance
        yield bot_instance


@pytest.fixture
def publisher(mock_bot):
    with patch('app.telegram.publisher.settings') as mock_settings:
        mock_settings.telegram_bot_token = "test_token"
        mock_settings.telegram_channel_id = "@test_channel"
        return TelegramPublisher()


class TestSendPoll:
    @pytest.mark.asyncio
    async def test_send_poll_success(self, publisher, mock_bot):
        """Test successful poll sending"""
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_message.poll.id = "poll_123"
        mock_message.chat.id = "@test_channel"
        mock_bot.send_poll.return_value = mock_message

        result = await publisher.send_poll(
            question="Test question?",
            options=["Option 1", "Option 2", "Option 3"]
        )

        assert result['success'] is True
        assert result['message_id'] == 123
        assert result['poll_id'] == "poll_123"
        mock_bot.send_poll.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_poll_validates_min_options(self, publisher):
        """Test that poll requires at least 2 options"""
        result = await publisher.send_poll(
            question="Test?",
            options=["Only one"]
        )

        assert result['success'] is False
        assert 'at least 2' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_send_poll_validates_max_options(self, publisher):
        """Test that poll allows max 10 options"""
        result = await publisher.send_poll(
            question="Test?",
            options=[f"Option {i}" for i in range(11)]
        )

        assert result['success'] is False
        assert 'at most 10' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_send_poll_validates_question_length(self, publisher):
        """Test question length validation (max 300 chars)"""
        result = await publisher.send_poll(
            question="A" * 301,
            options=["Yes", "No"]
        )

        assert result['success'] is False
        assert '300' in result['error']

    @pytest.mark.asyncio
    async def test_send_poll_validates_option_length(self, publisher):
        """Test option length validation (max 100 chars)"""
        result = await publisher.send_poll(
            question="Test?",
            options=["Option 1", "A" * 101]
        )

        assert result['success'] is False
        assert '100' in result['error']
        assert 'Option 2' in result['error']

    @pytest.mark.asyncio
    async def test_send_poll_with_custom_params(self, publisher, mock_bot):
        """Test poll with custom parameters (anonymous, multiple answers)"""
        mock_message = MagicMock()
        mock_message.message_id = 456
        mock_message.poll.id = "poll_456"
        mock_message.chat.id = "@test_channel"
        mock_bot.send_poll.return_value = mock_message

        result = await publisher.send_poll(
            question="Multiple choice?",
            options=["A", "B", "C"],
            is_anonymous=False,
            allows_multiple_answers=True
        )

        assert result['success'] is True
        mock_bot.send_poll.assert_called_once_with(
            chat_id="@test_channel",
            question="Multiple choice?",
            options=["A", "B", "C"],
            is_anonymous=False,
            allows_multiple_answers=True
        )

    @pytest.mark.asyncio
    async def test_send_poll_handles_telegram_error(self, publisher, mock_bot):
        """Test error handling when Telegram API fails"""
        from telegram.error import TelegramError

        mock_bot.send_poll.side_effect = TelegramError("Network error")

        result = await publisher.send_poll(
            question="Test?",
            options=["Yes", "No"]
        )

        assert result['success'] is False
        assert 'error' in result
        assert 'Network error' in result['error']


class TestPublishPostWithPoll:
    @pytest.mark.asyncio
    async def test_publish_post_then_poll(self, publisher, mock_bot):
        """Test publishing post followed by poll"""
        mock_message = MagicMock()
        mock_message.message_id = 100
        mock_message.chat.id = -1001234567890
        mock_message.date = MagicMock()
        mock_bot.send_message.return_value = mock_message

        mock_poll_message = MagicMock()
        mock_poll_message.message_id = 101
        mock_poll_message.poll.id = "poll_456"
        mock_poll_message.chat.id = -1001234567890
        mock_bot.send_poll.return_value = mock_poll_message

        result = await publisher.publish_post_with_poll(
            content="Check out this post!",
            poll_question="What do you think?",
            poll_options=["Great", "Good", "Meh"]
        )

        assert result['success'] is True
        assert result['post_message_id'] == 100
        assert result['poll_message_id'] == 101
