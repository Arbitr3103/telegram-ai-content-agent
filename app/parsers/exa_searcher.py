"""
Exa API парсер для поиска актуальной информации
Использует реальный Exa API для поиска новостей и технического контента
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ExaSearcher:
    """Класс для поиска информации через Exa API"""

    BASE_URL = "https://api.exa.ai"

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация Exa Searcher

        Args:
            api_key: API ключ Exa (если None, берётся из настроек)
        """
        self.api_key = api_key or settings.exa_api_key
        if not self.api_key:
            logger.warning("Exa API key not provided, searcher will return empty results")
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or ""
        }

    async def search_latest_news(
        self,
        query: str,
        num_results: int = 5,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Поиск последних новостей по запросу

        Args:
            query: Поисковый запрос
            num_results: Количество результатов
            days_back: За сколько дней искать

        Returns:
            Список найденных источников
        """
        if not self.api_key:
            logger.warning("Exa API key not set, returning empty results")
            return []

        logger.info(f"Exa: Searching news for '{query}'")

        # Дата начала поиска
        start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    json={
                        "query": query,
                        "numResults": num_results,
                        "startPublishedDate": start_date,
                        "useAutoprompt": True,
                        "type": "auto",
                        "contents": {
                            "text": {"maxCharacters": 1500}
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Exa API error: {response.status_code} - {response.text}")
                    return []

                data = response.json()
                results = []

                for item in data.get("results", []):
                    results.append({
                        'title': item.get('title', 'Без заголовка'),
                        'url': item.get('url', ''),
                        'content': item.get('text', '')[:1000],
                        'published_at': item.get('publishedDate'),
                        'source_type': 'exa_news',
                        'relevance_score': item.get('score', 0.5),
                        'metadata': {
                            'search_query': query,
                            'search_type': 'news',
                            'author': item.get('author', '')
                        }
                    })

                logger.info(f"Exa: Found {len(results)} news items for '{query}'")
                return results

        except Exception as e:
            logger.error(f"Exa search error: {e}")
            return []

    async def search_technical_content(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Поиск технического контента (статьи, документация)

        Args:
            query: Поисковый запрос
            num_results: Количество результатов

        Returns:
            Список найденных источников
        """
        if not self.api_key:
            return []

        logger.info(f"Exa: Searching technical content for '{query}'")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    json={
                        "query": query,
                        "numResults": num_results,
                        "useAutoprompt": True,
                        "type": "auto",
                        "contents": {
                            "text": {"maxCharacters": 2000}
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Exa API error: {response.status_code}")
                    return []

                data = response.json()
                results = []

                for item in data.get("results", []):
                    results.append({
                        'title': item.get('title', 'Без заголовка'),
                        'url': item.get('url', ''),
                        'content': item.get('text', '')[:1500],
                        'published_at': item.get('publishedDate'),
                        'source_type': 'exa_tech',
                        'relevance_score': item.get('score', 0.5),
                        'metadata': {
                            'search_query': query,
                            'search_type': 'technical'
                        }
                    })

                logger.info(f"Exa: Found {len(results)} technical articles")
                return results

        except Exception as e:
            logger.error(f"Exa technical search error: {e}")
            return []

    async def search_api_documentation(
        self,
        num_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Поиск обновлений в официальных API документациях маркетплейсов

        Returns:
            Список новостей из официальных API документаций
        """
        if not self.api_key:
            return []

        logger.info("Exa: Searching API documentation updates")

        # Официальные источники документации
        api_queries = [
            "site:docs.ozon.ru seller API news updates changelog",
            "site:openapi.wildberries.ru API changes updates",
            "site:yandex.ru/dev/market partner API updates",
            "Ozon Seller API Performance обновление 2025 2026",
            "Wildberries API статистика реклама новое",
        ]

        all_results = []

        for query in api_queries:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/search",
                        headers=self.headers,
                        json={
                            "query": query,
                            "numResults": num_results,
                            "useAutoprompt": True,
                            "type": "auto",
                            "contents": {
                                "text": {"maxCharacters": 2000}
                            }
                        }
                    )

                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("results", []):
                            all_results.append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'content': item.get('text', '')[:1500],
                                'published_at': item.get('publishedDate'),
                                'source_type': 'api_docs',
                                'relevance_score': item.get('score', 0.8),
                                'metadata': {
                                    'search_query': query,
                                    'search_type': 'api_documentation'
                                }
                            })

            except Exception as e:
                logger.error(f"Exa API docs search error for '{query}': {e}")

            await asyncio.sleep(0.3)  # Rate limit protection

        # Дедупликация
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        logger.info(f"Exa: Found {len(unique_results)} API documentation updates")
        return unique_results

    async def search_company_info(
        self,
        company_name: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Исследование компаний (Ozon, Wildberries и т.д.)

        Args:
            company_name: Название компании
            num_results: Количество результатов

        Returns:
            Список найденной информации о компании
        """
        if not self.api_key:
            return []

        logger.info(f"Exa: Researching company '{company_name}'")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/search",
                    headers=self.headers,
                    json={
                        "query": f"{company_name} новости аналитика обновления",
                        "numResults": num_results,
                        "useAutoprompt": True,
                        "type": "auto",
                        "contents": {
                            "text": {"maxCharacters": 1500}
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Exa API error: {response.status_code}")
                    return []

                data = response.json()
                results = []

                for item in data.get("results", []):
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('url', ''),
                        'content': item.get('text', '')[:1000],
                        'published_at': item.get('publishedDate'),
                        'source_type': 'exa_company',
                        'relevance_score': item.get('score', 0.5),
                        'metadata': {
                            'company_name': company_name,
                            'search_type': 'company_research'
                        }
                    })

                logger.info(f"Exa: Found {len(results)} company insights")
                return results

        except Exception as e:
            logger.error(f"Exa company research error: {e}")
            return []

    async def search_all_sources(
        self,
        queries: List[str],
        num_results_per_query: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Комплексный поиск по нескольким запросам

        Args:
            queries: Список поисковых запросов
            num_results_per_query: Количество результатов на запрос

        Returns:
            Агрегированный список всех найденных источников
        """
        if not self.api_key:
            logger.warning("Exa API key not set, returning empty results")
            return []

        all_results = []

        # Последовательный поиск с задержкой (rate limit: 5 req/sec)
        results_lists = []
        for query in queries:
            result = await self.search_latest_news(query, num_results_per_query)
            results_lists.append(result)
            await asyncio.sleep(0.3)  # 300ms между запросами

        for results in results_lists:
            if results:
                all_results.extend(results)

        # Дедупликация по URL
        seen_urls = set()
        unique_results = []

        for result in all_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        logger.info(f"Exa: Total unique sources found: {len(unique_results)}")
        return unique_results


# Вспомогательные функции

async def fetch_exa_sources(
    queries: List[str],
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Удобная функция для получения источников из Exa

    Args:
        queries: Список поисковых запросов
        api_key: API ключ Exa

    Returns:
        Список найденных источников
    """
    searcher = ExaSearcher(api_key=api_key)
    return await searcher.search_all_sources(queries)


if __name__ == "__main__":
    async def main():
        searcher = ExaSearcher()

        # Тест поиска новостей
        news = await searcher.search_latest_news("Ozon API маркетплейс", num_results=3)
        print(f"\nНайдено новостей: {len(news)}")
        for item in news:
            print(f"  - {item['title'][:60]}...")
            print(f"    URL: {item['url']}")

        # Тест исследования компании
        company = await searcher.search_company_info("Wildberries")
        print(f"\nИнформация о компании: {len(company)} результатов")

    asyncio.run(main())
