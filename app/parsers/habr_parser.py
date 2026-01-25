"""
Habr парсер для получения технических статей
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HabrParser:
    """Парсер статей с Habr.com"""

    BASE_URL = "https://habr.com"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    def __init__(self):
        self.client = httpx.AsyncClient(headers=self.HEADERS, timeout=30.0)

    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()

    async def parse_articles_by_tags(
        self,
        tags: List[str],
        max_articles_per_tag: int = 10,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Парсинг статей по тегам

        Args:
            tags: Список тегов для поиска
            max_articles_per_tag: Максимальное количество статей на тег
            days_back: Сколько дней назад искать статьи

        Returns:
            Список найденных статей
        """
        all_articles = []
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        for tag in tags:
            logger.info(f"Parsing Habr tag: {tag}")

            try:
                articles = await self._parse_tag_page(tag, max_articles_per_tag)

                # Фильтрация по дате
                recent_articles = [
                    article for article in articles
                    if article.get('published_at') and article['published_at'] >= cutoff_date
                ]

                logger.info(f"Found {len(recent_articles)} recent articles for tag '{tag}'")
                all_articles.extend(recent_articles)

            except Exception as e:
                logger.error(f"Error parsing tag '{tag}': {e}")

            # Небольшая задержка между запросами
            await asyncio.sleep(1)

        # Дедупликация по URL
        seen_urls = set()
        unique_articles = []

        for article in all_articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        logger.info(f"Total unique Habr articles: {len(unique_articles)}")
        return unique_articles

    async def _parse_tag_page(
        self,
        tag: str,
        max_articles: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Парсинг страницы тега

        Args:
            tag: Тег для поиска
            max_articles: Максимальное количество статей

        Returns:
            Список статей
        """
        url = f"{self.BASE_URL}/ru/search/?q={tag}&target_type=posts&order=date"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []

        # NOTE: Здесь упрощённый парсинг, реальная структура Habr может отличаться
        # В production версии нужно будет обновить селекторы

        article_blocks = soup.select('article.tm-articles-list__item')[:max_articles]

        for block in article_blocks:
            try:
                article = self._parse_article_block(block, tag)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Error parsing article block: {e}")

        return articles

    def _parse_article_block(
        self,
        block: BeautifulSoup,
        tag: str
    ) -> Dict[str, Any]:
        """
        Парсинг блока статьи

        Args:
            block: BeautifulSoup элемент статьи
            tag: Тег, по которому нашли статью

        Returns:
            Словарь с данными статьи
        """
        # Заголовок и ссылка
        title_elem = block.select_one('h2.tm-title a')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        relative_url = title_elem.get('href', '')
        url = f"{self.BASE_URL}{relative_url}" if relative_url.startswith('/') else relative_url

        # Краткое описание
        description_elem = block.select_one('.tm-article-snippet__lead')
        description = description_elem.get_text(strip=True) if description_elem else ""

        # Дата публикации
        date_elem = block.select_one('time')
        published_at = None

        if date_elem and date_elem.get('datetime'):
            try:
                published_at = datetime.fromisoformat(date_elem['datetime'].replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Error parsing date: {e}")

        # Контент (первые 500 символов описания)
        content = f"{title}\n\n{description}"

        article = {
            'title': title,
            'content': content[:1000],  # Ограничиваем размер
            'url': url,
            'published_at': published_at or datetime.utcnow(),
            'source_type': 'habr',
            'relevance_score': None,  # Будет вычислена AI агентом
            'metadata': {
                'tag': tag,
                'description': description
            }
        }

        return article


# Вспомогательные функции

async def fetch_habr_articles(
    tags: List[str] = None,
    max_articles_per_tag: int = 10,
    days_back: int = 7
) -> List[Dict[str, Any]]:
    """
    Удобная функция для получения статей с Habr

    Args:
        tags: Список тегов (по умолчанию: etl, ozon, wildberries, e-commerce)
        max_articles_per_tag: Максимальное количество статей на тег
        days_back: Сколько дней назад искать

    Returns:
        Список найденных статей
    """
    if tags is None:
        tags = ['etl', 'ozon api', 'wildberries', 'e-commerce', 'маркетплейсы']

    parser = HabrParser()

    try:
        articles = await parser.parse_articles_by_tags(
            tags=tags,
            max_articles_per_tag=max_articles_per_tag,
            days_back=days_back
        )
        return articles
    finally:
        await parser.close()


# Примеры использования

if __name__ == "__main__":
    async def main():
        articles = await fetch_habr_articles(
            tags=['etl', 'ozon', 'маркетплейсы'],
            max_articles_per_tag=5,
            days_back=7
        )

        print(f"Found {len(articles)} articles:")
        for article in articles[:3]:
            print(f"- {article['title']}")
            print(f"  URL: {article['url']}")
            print(f"  Date: {article['published_at']}")
            print()

    asyncio.run(main())
