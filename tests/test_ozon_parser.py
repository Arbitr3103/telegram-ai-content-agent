"""
Тесты парсера Ozon
"""
import pytest
from app.client_bot.services.ozon_parser import extract_seller_id, format_audit_result


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


class TestFormatAuditResult:
    """Тесты форматирования результата аудита"""

    def test_formats_full_data(self):
        """Форматирует полные данные"""
        seller_data = {
            "seller_id": "test-shop-123",
            "name": "Тестовый магазин",
            "rating": 4.8,
            "products_count": 150,
        }
        result = format_audit_result(seller_data)

        assert "Тестовый магазин" in result
        assert "4.8" in result
        assert "150" in result

    def test_handles_missing_data(self):
        """Обрабатывает отсутствующие данные"""
        seller_data = {
            "seller_id": "test-123",
            "name": "Магазин",
        }
        result = format_audit_result(seller_data)

        assert "Магазин" in result
        assert "Мини-аудит" in result
