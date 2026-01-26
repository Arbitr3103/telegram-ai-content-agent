"""
Интеграционные тесты клиентского бота
"""
import pytest
from unittest.mock import MagicMock, AsyncMock


class TestStartHandler:
    """Тесты обработчика /start"""

    @pytest.mark.asyncio
    async def test_start_sends_welcome_message(self):
        """Проверяет что /start отправляет приветственное сообщение"""
        from app.client_bot.handlers.start import start_handler

        mock_update = MagicMock()
        mock_update.effective_user = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.effective_user.username = "test"
        mock_update.message = AsyncMock()
        mock_update.message.reply_text = AsyncMock()

        mock_context = MagicMock()

        await start_handler(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Здравствуйте" in call_args[0][0]


class TestCalculator:
    """Тесты калькулятора"""

    def test_calculate_savings(self):
        """Проверяет расчёт экономии времени"""
        from app.client_bot.handlers.calculator import calculate_savings

        data = {
            "hours": 10,
            "rate": 1000,
        }

        result = calculate_savings(data)

        # 10 часов × 1000 ₽ × 4 недели = 40000 ₽/мес
        assert result["total_savings"] == 40000
        assert "message" in result


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
