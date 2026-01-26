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

        assert result["manual_work_cost"] == 40000
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
