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

            result = {
                "seller_id": seller_id,
                "url": url,
                "name": _extract_seller_name(soup),
                "rating": _extract_seller_rating(soup),
                "products_count": _extract_products_count(soup),
                "products": [],
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
    count_pattern = r'(\d+)\s*товар'

    text = soup.get_text()
    match = re.search(count_pattern, text)

    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

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
