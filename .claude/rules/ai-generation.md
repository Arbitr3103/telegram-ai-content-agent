---
paths: "app/agents/**/*.py, app/utils/prompts.py"
---

# AI Generation Rules

Правила работы с Claude API и генерацией контента.

## Proxy Configuration

Claude API заблокирован в РФ. Всегда используй proxy:

```python
from app.config import settings
import httpx
from anthropic import Anthropic

proxy_url = settings.proxy_url
if proxy_url:
    http_client = httpx.Client(proxy=proxy_url, timeout=60.0)
else:
    http_client = httpx.Client(timeout=60.0)

client = Anthropic(api_key=settings.anthropic_api_key, http_client=http_client)
```

**Важно:** В httpx 0.28+ используй `proxy=`, не `proxies=`.

## Content Generator Pattern

```python
# app/agents/content_generator.py
class ContentGenerator:
    def __init__(self):
        # Всегда инициализируй client с proxy
        self.client = Anthropic(api_key=..., http_client=http_client)

    async def generate_post(self, sources: List[Dict]) -> Dict:
        # 1. Подготовь источники
        sources_text = self._prepare_sources_text(sources)

        # 2. Сформируй промпт
        prompt = CONTENT_GENERATION_PROMPT.format(sources=sources_text)

        # 3. Вызови Claude (синхронно, но в async контексте)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # 4. Очисти от служебных меток
        cleaned = self._clean_post(response.content[0].text)

        return {'content': cleaned, 'tags': self._extract_tags(cleaned)}
```

## Промпты (app/utils/prompts.py)

### Структура промпта

```python
CONTENT_GENERATION_PROMPT = """
Ты — Владимир, практикующий специалист по аналитике для маркетплейсов.

ТВОЙ СТИЛЬ:
- Пишешь от первого лица как практик
- Добавляешь личный опыт или мнение (ОБЯЗАТЕЛЬНО!)
- Используешь разговорные обороты: "честно говоря", "кстати"

ИСТОЧНИКИ:
{sources}

{post_type_instruction}

ВАЖНО:
- НЕ пиши "ПОСТ:", "ТЕГИ:", "---"
- ОБЯЗАТЕЛЬНО добавь личный комментарий
- Хештеги в конце
- 400-700 символов
"""
```

### Типы постов (post_type_instruction)

| Тип | Формат |
|-----|--------|
| Полезная польза | Проблема → Решение → Как применить |
| Кейс | Было → Сделали → Стало (с цифрами!) |
| Интерактив | Новость → Твоё мнение → Вопрос аудитории |

### Запрещённые паттерны в выводе

| Паттерн | Почему плохо |
|---------|--------------|
| `ПОСТ:` | Выглядит как бот |
| `ТЕГИ:` | Выглядит как бот |
| `---` | Разделители не нужны |
| `ИСТОЧНИКИ:` | Не для конечного поста |
| `example.com` | Фейковые URL |

## Очистка вывода

```python
def _clean_post(self, text: str) -> str:
    import re
    # Убираем разделители
    text = re.sub(r"^-+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*-+$", "", text, flags=re.MULTILINE)

    # Убираем метки
    text = re.sub(
        r"^(ПОСТ|POST|КОНТЕНТ|CONTENT|ТЕГИ|TAGS|ИСТОЧНИКИ|SOURCES):\s*",
        "", text, flags=re.MULTILINE | re.IGNORECASE
    )

    return text.strip()
```

## Модели

| Модель | Использование |
|--------|---------------|
| `claude-3-haiku-20240307` | Production (быстро, дёшево) |
| `claude-3-5-sonnet-20241022` | Если нужно качество |
| `claude-sonnet-4-5-20250929` | Новейшая (проверь доступность) |

## Обработка ошибок

```python
try:
    response = self.client.messages.create(...)
except anthropic.APIError as e:
    if "403" in str(e):
        logger.error("Proxy не работает или API заблокирован")
    raise
```

## Тестирование

```bash
# Тест генерации без публикации
python test_pipeline.py
```
