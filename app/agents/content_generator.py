"""
AI Content Agent для генерации постов через Claude API
"""
import re
import json
import logging
from typing import List, Dict, Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

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

        self.llm = ChatAnthropic(
            model=self.model,
            api_key=self.api_key,
            temperature=settings.claude_temperature,
            max_tokens=settings.claude_max_tokens,
        )

        logger.info(f"ContentGenerator initialized with model: {self.model}")

    async def generate_post(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Генерация поста на основе источников

        Args:
            sources: Список источников информации

        Returns:
            Словарь с контентом поста
        """
        logger.info(f"Generating post from {len(sources)} sources")

        # Подготовка резюме источников
        sources_summary = self._prepare_sources_summary(sources)

        # Создание промпта
        prompt = PromptTemplate(
            input_variables=["sources_summary"],
            template=CONTENT_GENERATION_PROMPT
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        # Генерация
        try:
            result = await chain.arun(sources_summary=sources_summary)
            logger.info("Post generated successfully")

            # Парсинг ответа
            parsed = self._parse_generated_content(result)

            return {
                'content': parsed['post'],
                'tags': parsed['tags'],
                'sources': parsed['sources'],
                'metadata': {
                    'raw_output': result,
                    'model': self.model,
                    'sources_count': len(sources)
                }
            }

        except Exception as e:
            logger.error(f"Error generating post: {e}")
            raise

    def _prepare_sources_summary(self, sources: List[Dict[str, Any]]) -> str:
        """Подготовка резюме источников для промпта"""
        summary_parts = []

        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Без заголовка')
            content = source.get('content', '')[:500]  # Первые 500 символов
            url = source.get('url', 'N/A')
            source_type = source.get('source_type', 'unknown')

            summary_parts.append(
                f"{i}. [{source_type}] {title}\n"
                f"   URL: {url}\n"
                f"   Контент: {content}...\n"
            )

        return "\n".join(summary_parts)

    def _parse_generated_content(self, raw_text: str) -> Dict[str, Any]:
        """
        Парсинг сгенерированного контента

        Args:
            raw_text: Сырой текст от Claude

        Returns:
            Словарь с распарсенными данными
        """
        # Извлечение поста
        post_match = re.search(r'ПОСТ:\s*\n(.*?)\n\nТЕГИ:', raw_text, re.DOTALL)
        post_content = post_match.group(1).strip() if post_match else raw_text

        # Извлечение тегов
        tags_match = re.search(r'ТЕГИ:\s*(.+)', raw_text)
        tags_str = tags_match.group(1).strip() if tags_match else ""
        tags = [tag.strip() for tag in tags_str.split() if tag.startswith('#')]

        # Извлечение источников
        sources = []
        sources_section = re.search(r'ИСТОЧНИКИ:\s*\n(.*)', raw_text, re.DOTALL)
        if sources_section:
            sources_text = sources_section.group(1)
            # Парсинг списка источников
            source_lines = re.findall(r'-\s*\[(.+?)\]\s*\((.+?)\)', sources_text)
            sources = [{'name': name, 'url': url} for name, url in source_lines]

        return {
            'post': post_content,
            'tags': tags,
            'sources': sources
        }

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

        prompt = PromptTemplate(
            input_variables=["title", "content_preview"],
            template=RELEVANCE_EVALUATION_PROMPT
        )

        chain = LLMChain(llm=self.llm, prompt=prompt)

        try:
            result = await chain.arun(title=title, content_preview=content_preview)

            # Парсинг JSON ответа
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
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
                'url': 'https://example.com/ozon-api-v3',
                'source_type': 'news'
            },
            {
                'title': 'ETL лучшие практики для e-commerce',
                'content': 'Оптимизация ETL пайплайнов для обработки данных маркетплейсов...',
                'url': 'https://habr.com/etl-best-practices',
                'source_type': 'habr'
            }
        ]

        generator = ContentGenerator()
        post = await generator.generate_post(example_sources)

        print("GENERATED POST:")
        print(post['content'])
        print("\nTAGS:", ' '.join(post['tags']))
        print("\nSOURCES:")
        for source in post['sources']:
            print(f"- {source['name']}: {source['url']}")

    asyncio.run(main())
