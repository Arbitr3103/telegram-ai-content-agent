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
from app.utils.prompts import (
    SYSTEM_PROMPT,
    CONTENT_GENERATION_PROMPT,
    RELEVANCE_EVALUATION_PROMPT,
    AUTHOR_EXPERIENCE_EXAMPLES,
    REALISTIC_NUMBERS_GUIDE,
    POST_TYPE_PROMPTS,
)

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
            # httpx 0.28+ использует proxy=, более ранние версии - proxies=
            try:
                http_client = httpx.Client(proxy=proxy_url, timeout=60.0)
            except TypeError:
                http_client = httpx.Client(proxies=proxy_url, timeout=60.0)
        else:
            http_client = httpx.Client(timeout=60.0)

        self.client = Anthropic(
            api_key=self.api_key,
            http_client=http_client
        )

        logger.info(f"ContentGenerator initialized with model: {self.model}")

    async def generate_post(
        self,
        sources: List[Dict[str, Any]],
        post_type_instruction: str = "",
        add_cta: bool = False,
        cta_text: str = "",
        add_personal_experience: bool = False
    ) -> Dict[str, Any]:
        """
        Генерация поста на основе источников

        Args:
            sources: Список источников информации
            post_type_instruction: Инструкция для типа поста
            add_cta: Нужно ли добавлять CTA-блок
            cta_text: Текст CTA-блока
            add_personal_experience: Нужно ли добавлять личный опыт

        Returns:
            Словарь с контентом поста
        """
        logger.info(f"Generating post from {len(sources)} sources")

        # Подготовка текста источников
        sources_text = self._prepare_sources_text(sources)

        # Личный опыт - условная инструкция и примеры
        if add_personal_experience:
            author_experience_examples = AUTHOR_EXPERIENCE_EXAMPLES
        else:
            author_experience_examples = ""  # НЕ показываем примеры

        # CTA-инструкция для промпта
        if add_cta and cta_text:
            cta_instruction = f"""
ОБЯЗАТЕЛЬНО ДОБАВЬ CTA-БЛОК В КОНЦЕ ПОСТА:
После основного текста добавь пустую строку, затем разделитель и CTA:

━━━━━━━━━━
{cta_text}

ВАЖНО: CTA-блок ОБЯЗАТЕЛЕН! Не пропускай его!
"""
        else:
            cta_instruction = "БЕЗ CTA-БЛОКА в конце поста."

        # Формируем промпт с полной структурой
        prompt = CONTENT_GENERATION_PROMPT.format(
            system_prompt=SYSTEM_PROMPT,
            author_experience_examples=author_experience_examples,
            realistic_numbers_guide=REALISTIC_NUMBERS_GUIDE,
            sources=sources_text,
            post_type_prompt=post_type_instruction,
            cta_instruction=cta_instruction
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

            # Извлекаем теги из текста (хештеги)
            tags = re.findall(r'#(\w+)', cleaned_text)
            if not tags:
                # Генерируем теги из ключевых слов если их нет в посте
                tags = ['маркетплейсы', 'аналитика', 'автоматизация']

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

        # Убираем вступительные фразы Claude (в начале текста)
        text = re.sub(
            r"^(Вот что я написал|Вот пост|Готово|Конечно|Хорошо).{0,100}?:\s*\n+",
            "",
            text,
            flags=re.IGNORECASE
        )

        # Очистка пустых строк
        text = text.strip()
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text

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

    asyncio.run(main())
