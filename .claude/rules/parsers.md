---
paths: "app/parsers/**/*.py"
---

# Parsers Rules

Правила работы с парсерами источников (Exa API, Habr).

## Exa API (app/parsers/exa_searcher.py)

### Конфигурация

```python
class ExaSearcher:
    BASE_URL = "https://api.exa.ai"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.exa_api_key
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
```

### Поисковые запросы

**Правильные запросы** (русские маркетплейсы):
```python
exa_queries = [
    "Ozon селлер новости обновления 2025",
    "Wildberries продавцы изменения комиссии",
    "Яндекс Маркет API изменения",
    "аналитика продаж Ozon Wildberries кейс"
]
```

**Неправильные запросы** (приведут к нерелевантным результатам):
```python
# НЕ ИСПОЛЬЗУЙ:
"API updates 2026"           # Слишком общий
"marketplace analytics"       # Вернёт Google/Amazon
"ETL pipeline e-commerce"    # Слишком технический
```

### API вызов

```python
async def search_latest_news(self, query: str, num_results: int = 5, days_back: int = 7):
    start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

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
                "contents": {"text": {"maxCharacters": 1500}}
            }
        )
```

### Структура результата

```python
{
    'title': 'Заголовок статьи',
    'url': 'https://real-url.com/article',  # Реальный URL!
    'content': 'Текст статьи...',
    'published_at': '2025-01-20T...',
    'source_type': 'exa_news',
    'relevance_score': 0.85
}
```

## Habr Parser (app/parsers/habr_parser.py)

### Известные проблемы

**Ошибка datetime:**
```
Error parsing tag 'ozon': can't compare offset-naive and offset-aware datetimes
```

**Причина:** Сравнение `datetime.now()` с timezone-aware датами из Habr.

**Решение:**
```python
from datetime import datetime, timezone

# Вместо:
if article_date > datetime.now() - timedelta(days=7):

# Используй:
if article_date > datetime.now(timezone.utc) - timedelta(days=7):
```

### Теги для парсинга

```python
habr_tags = ['etl', 'ozon', 'wildberries', 'e-commerce', 'маркетплейсы']
```

## Дедупликация

Всегда дедуплицируй результаты по URL:

```python
seen_urls = set()
unique_results = []

for result in all_results:
    url = result.get('url', '')
    if url and url not in seen_urls:
        seen_urls.add(url)
        unique_results.append(result)
```

## Параллельный поиск

```python
async def search_all_sources(self, queries: List[str]):
    tasks = [self.search_latest_news(q) for q in queries]
    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    for results in results_lists:
        if isinstance(results, list):
            all_results.extend(results)
    return all_results
```

## Fallback

Если Exa не вернул результаты, Habr может быть backup:

```python
sources = await exa_searcher.search_all_sources(queries)
if len(sources) < 3:
    habr_sources = await habr_parser.parse_articles_by_tags(tags)
    sources.extend(habr_sources)
```
