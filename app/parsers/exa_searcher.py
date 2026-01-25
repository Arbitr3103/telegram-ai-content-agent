"""
Exa API парсер для поиска актуальной информации
Использует MCP сервер exa-mcp-server через Claude Code
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ExaSearcher:
    """Класс для поиска информации через Exa API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация Exa Searcher

        Args:
            api_key: API ключ Exa (опционально, если используется MCP сервер)
        """
        self.api_key = api_key

    async def search_latest_news(
        self,
        query: str,
        num_results: int = 10,
        context_max_characters: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Поиск последних новостей по запросу

        Args:
            query: Поисковый запрос
            num_results: Количество результатов
            context_max_characters: Максимальное количество символов контекста

        Returns:
            Список найденных источников
        """
        logger.info(f"Searching for news: {query}")

        # NOTE: В production версии здесь будет прямой вызов Exa API
        # Сейчас возвращаем заглушку для тестирования структуры

        results = []

        # Пример структуры результата
        # В реальности это будет вызов mcp__plugin_exa-mcp-server_exa__web_search_exa
        example_result = {
            'title': f"Пример новости по запросу: {query}",
            'url': 'https://example.com',
            'content': 'Пример контента новости...',
            'published_at': datetime.utcnow(),
            'source_type': 'exa',
            'relevance_score': 0.95,
            'metadata': {
                'search_query': query,
                'search_type': 'news'
            }
        }

        results.append(example_result)

        logger.info(f"Found {len(results)} news items")
        return results

    async def search_technical_content(
        self,
        query: str,
        num_results: int = 5,
        context_max_characters: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Поиск технического контента (статьи, документация)

        Args:
            query: Поисковый запрос
            num_results: Количество результатов
            context_max_characters: Максимальное количество символов контекста

        Returns:
            Список найденных источников
        """
        logger.info(f"Searching for technical content: {query}")

        results = []

        example_result = {
            'title': f"Техническая статья: {query}",
            'url': 'https://habr.com/example',
            'content': 'Техническое содержание статьи...',
            'published_at': datetime.utcnow(),
            'source_type': 'exa',
            'relevance_score': 0.88,
            'metadata': {
                'search_query': query,
                'search_type': 'technical'
            }
        }

        results.append(example_result)

        logger.info(f"Found {len(results)} technical articles")
        return results

    async def get_code_context(
        self,
        query: str,
        tokens_num: int = 5000
    ) -> Dict[str, Any]:
        """
        Получение контекста кода для программирования

        Args:
            query: Запрос для поиска кода
            tokens_num: Количество токенов контекста (1000-50000)

        Returns:
            Контекст кода
        """
        logger.info(f"Getting code context: {query}")

        # NOTE: В production это будет вызов mcp__plugin_exa-mcp-server_exa__get_code_context_exa

        result = {
            'title': f"Code context: {query}",
            'content': f"# Example code context for {query}\n\n```python\n# Code example\n```",
            'source_type': 'exa_code',
            'relevance_score': 0.92,
            'metadata': {
                'search_query': query,
                'tokens_num': tokens_num
            }
        }

        logger.info("Code context retrieved")
        return result

    async def search_company_info(
        self,
        company_name: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Исследование компаний (для поиска информации об Ozon, Wildberries и т.д.)

        Args:
            company_name: Название компании
            num_results: Количество результатов

        Returns:
            Список найденной информации о компании
        """
        logger.info(f"Researching company: {company_name}")

        # NOTE: В production это будет вызов mcp__plugin_exa-mcp-server_exa__company_research_exa

        results = []

        example_result = {
            'title': f"Информация о компании {company_name}",
            'url': f'https://example.com/{company_name}',
            'content': f'Исследование компании {company_name}...',
            'published_at': datetime.utcnow(),
            'source_type': 'exa_company',
            'relevance_score': 0.90,
            'metadata': {
                'company_name': company_name,
                'search_type': 'company_research'
            }
        }

        results.append(example_result)

        logger.info(f"Found {len(results)} company insights")
        return results

    async def search_all_sources(
        self,
        queries: List[str],
        num_results_per_query: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Комплексный поиск по нескольким запросам

        Args:
            queries: Список поисковых запросов
            num_results_per_query: Количество результатов на запрос

        Returns:
            Агрегированный список всех найденных источников
        """
        all_results = []

        for query in queries:
            # Параллельный поиск новостей и технического контента
            news = await self.search_latest_news(query, num_results_per_query)
            technical = await self.search_technical_content(query, num_results_per_query // 2)

            all_results.extend(news)
            all_results.extend(technical)

        # Дедупликация по URL
        seen_urls = set()
        unique_results = []

        for result in all_results:
            url = result.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        logger.info(f"Total unique sources found: {len(unique_results)}")
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


# Примеры использования

if __name__ == "__main__":
    # Пример использования
    async def main():
        searcher = ExaSearcher()

        # Поиск новостей
        news = await searcher.search_latest_news("Ozon API updates 2026")
        print(f"Found {len(news)} news items")

        # Поиск технического контента
        tech = await searcher.search_technical_content("ETL pipeline for e-commerce")
        print(f"Found {len(tech)} technical articles")

        # Получение контекста кода
        code = await searcher.get_code_context("Python asyncio best practices")
        print(f"Code context: {code['title']}")

        # Исследование компании
        company = await searcher.search_company_info("Wildberries")
        print(f"Found {len(company)} company insights")

    asyncio.run(main())
