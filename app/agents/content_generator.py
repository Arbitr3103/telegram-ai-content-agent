"""
AI Content Agent для генерации постов через Claude API
"""
import re
import json
import logging
from typing import List, Dict, Any, Optional

import httpx
from anthropic import Anthropic

from app.config import settings
from app.utils.prompts import CONTENT_GENERATION_PROMPT, RELEVANCE_EVALUATION_PROMPT

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Генератор контента с использованием Claude API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация Content Generator

        Args:
            api_key: API ключ Anthropic (если None, берётся из настроек)
            model: Модель Claude (если None, берётся из настроек)
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.claude_model

        # Настройка HTTP клиента с proxy
        proxy_url = settings.proxy_url
        if proxy_url:
            logger.info(f"Using proxy: {proxy_url.split('@')[-1]}")
            http_client = httpx.Client(proxy=proxy_url, timeout=60.0)
        else:
            http_client = httpx.Client(timeout=60.0)

        self.client = Anthropic(
            api_key=self.api_key,
            http_client=http_client
        )

        logger.info(f"ContentGenerator initialized with model: {self.model}")

    async def generate_post(self, sources: List[Dict[str, Any]], post_type_instruction: str = "") -> Dict[str, Any]:
        """
        Генерация поста на основе источников

        Args:
            sources: Список источников информации

        Returns:
            Словарь с контентом поста
        """
        logger.info(f"Generating post from {len(sources)} sources")

        # Подготовка текста источников
        sources_text = self._prepare_sources_text(sources)

        # Формируем промпт
        prompt = CONTENT_GENERATION_PROMPT.format(
            sources=sources_text,
            post_type_instruction=post_type_instruction
        )

        try:
            # Генерация через Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=settings.claude_max_tokens,
                temperature=settings.claude_temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            raw_text = response.content[0].text
            logger.info("Post generated successfully")

            # Очистка поста от служебных меток
            cleaned_text = self._clean_post(raw_text)

            # Извлечение тегов
            tags = self._extract_tags(cleaned_text)

            return {
                'content': cleaned_text,
                'tags': tags,
                'sources': [{'name': s.get('title', ''), 'url': s.get('url', '')} for s in sources[:3]],
                'metadata': {
                    'raw_output': raw_text,
                    'model': self.model,
                    'sources_count': len(sources)
                }
            }

        except Exception as e:
            logger.error(f"Error generating post: {e}")
            raise

    def _prepare_sources_text(self, sources: List[Dict[str, Any]]) -> str:
        """Подготовка текста источников для промпта"""
        parts = []

        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Без заголовка')
            content = source.get('content', '')[:500]
            url = source.get('url', '')
            source_type = source.get('source_type', 'web')

            parts.append(
                f"{i}. [{source_type}] {title}\n"
                f"   URL: {url}\n"
                f"   Контент: {content}...\n"
            )

        return "\n".join(parts)

    def _clean_post(self, text: str) -> str:
        """Очистка поста от служебных меток"""
        # Убираем разделители ---
        text = re.sub(r"^-+\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*-+$", "", text, flags=re.MULTILINE)

        # Убираем служебные метки в начале строк
        text = re.sub(
            r"^(ПОСТ|POST|КОНТЕНТ|CONTENT|ТЕГИ|TAGS|ИСТОЧНИКИ|SOURCES|ХЕШТЕГИ):\s*",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE
        )

        # Очистка пустых строк
        text = text.strip()
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

    def _extract_tags(self, text: str) -> List[str]:
        """Извлечение хештегов из текста"""
        tags = re.findall(r'#(\w+)', text)
        return tags

    async def evaluate_relevance(
        self,
        title: str,
        content: str,
        min_score: float = 0.7
    ) -> Dict[str, Any]:
        """
        Оценка релевантности источника

        Args:
            title: Заголовок источника
            content: Контент источника
            min_score: Минимальная оценка для релевантности

        Returns:
            Словарь с оценкой релевантности
        """
        content_preview = content[:500] if len(content) > 500 else content

        prompt = RELEVANCE_EVALUATION_PROMPT.format(
            title=title,
            content_preview=content_preview
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            result_text = response.content[0].text

            # Парсинг JSON ответа
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                evaluation = json.loads(json_match.group(0))
                return evaluation
            else:
                logger.warning("Could not parse relevance evaluation, returning default")
                return {
                    'relevance_score': 0.5,
                    'reason': 'Could not parse response',
                    'is_relevant': False
                }

        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            return {
                'relevance_score': 0.0,
                'reason': f'Error: {str(e)}',
                'is_relevant': False
            }


# Вспомогательная функция

async def generate_post_from_sources(
    sources: List[Dict[str, Any]],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Удобная функция для генерации поста

    Args:
        sources: Список источников
        api_key: API ключ (опционально)

    Returns:
        Сгенерированный пост
    """
    generator = ContentGenerator(api_key=api_key)
    return await generator.generate_post(sources)


if __name__ == "__main__":
    import asyncio

    async def main():
        # Пример источников
        example_sources = [
            {
                'title': 'Ozon обновил API до версии 3.0',
                'content': 'Новая версия API Ozon включает улучшенную производительность...',
                'url': 'https://docs.ozon.ru/api/v3',
                'source_type': 'news'
            },
            {
                'title': 'ETL лучшие практики для e-commerce',
                'content': 'Оптимизация ETL пайплайнов для обработки данных маркетплейсов...',
                'url': 'https://habr.com/ru/articles/123456',
                'source_type': 'habr'
            }
        ]

        generator = ContentGenerator()
        post = await generator.generate_post(example_sources)

        print("GENERATED POST:")
        print(post['content'])
        print("\nTAGS:", ' '.join(['#' + t for t in post['tags']]))

    asyncio.run(main())
