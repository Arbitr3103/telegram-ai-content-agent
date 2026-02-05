"""
Модуль промптов для генерации контента.

Структура:
- system.py: SYSTEM_PROMPT, CONTENT_BIBLE, REALISTIC_NUMBERS_GUIDE
- examples.py: EXAMPLE_POSTS (эталонные посты для каждого типа)
- post_types.py: POST_TYPE_PROMPTS (промпты для каждого типа)
"""

from .system import (
    SYSTEM_PROMPT,
    CONTENT_BIBLE,
    REALISTIC_NUMBERS_GUIDE,
    AUTHOR_EXPERIENCE_EXAMPLES,
)

from .examples import EXAMPLE_POSTS

from .post_types import POST_TYPE_PROMPTS

# Основной промпт генерации (собирается динамически в content_generator.py)
CONTENT_GENERATION_PROMPT = """
{system_prompt}

{realistic_numbers_guide}

{author_experience_examples}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИСТОЧНИКИ (используй как основу для фактов):
{sources}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{post_type_prompt}

{topic_instruction}

{cta_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ ФИНАЛЬНЫЕ ТРЕБОВАНИЯ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Пиши ТОЛЬКО готовый пост — без "ПОСТ:", "ТЕГИ:", "---", "Заголовок:"
2. Начинай СРАЗУ с эмодзи и заголовка
3. Заканчивай вопросом к аудитории + 👇 + хештеги
4. Минимум 2 конкретные цифры (%, ₽, часы)
5. Используй разделитель ━━━━━━━━━━ перед практической частью
6. НЕ отклоняйся от темы ни на слово!
"""

# Промпт для оценки релевантности источников
RELEVANCE_EVALUATION_PROMPT = """Оцени релевантность этого источника для аудитории специалистов по автоматизации и селлеров маркетплейсов.

ИСТОЧНИК:
Заголовок: {title}
Контент: {content_preview}

КРИТЕРИИ:
1. Актуальность для e-commerce (0-1)
2. Техническая ценность (0-1)
3. Практическая применимость (0-1)

ОТВЕТ В JSON:
{{"relevance_score": 0.0-1.0, "reason": "объяснение", "is_relevant": true/false}}
"""

__all__ = [
    # Системные промпты
    "SYSTEM_PROMPT",
    "CONTENT_BIBLE",
    "REALISTIC_NUMBERS_GUIDE",
    "AUTHOR_EXPERIENCE_EXAMPLES",
    # Эталонные примеры
    "EXAMPLE_POSTS",
    # Промпты по типам
    "POST_TYPE_PROMPTS",
    # Основные промпты
    "CONTENT_GENERATION_PROMPT",
    "RELEVANCE_EVALUATION_PROMPT",
]
