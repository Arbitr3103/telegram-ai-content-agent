---
paths: "app/telegram/**/*.py"
---

# Telegram Rules

Правила работы с Telegram Bot API.

## Конфигурация

```env
TELEGRAM_BOT_TOKEN=8345028030:AAH4Pq0oTEtIto9_sLMW0sswGhKeRtLEkus
TELEGRAM_CHANNEL_ID=@smart_analytics_mp
TELEGRAM_ADMIN_ID=123456789
```

**Channel ID форматы:**
- Username: `@smart_analytics_mp` (рекомендуется)
- Numeric: `-1001234567890` (для приватных каналов)

## Publisher (app/telegram/publisher.py)

```python
from telegram import Bot
from telegram.constants import ParseMode

class TelegramPublisher:
    def __init__(self, bot_token: str = None, channel_id: str = None):
        self.bot_token = bot_token or settings.telegram_bot_token
        self.channel_id = channel_id or settings.telegram_channel_id
        self.bot = Bot(token=self.bot_token)

    async def publish_post(self, content: str, tags: list = None) -> dict:
        message = await self.bot.send_message(
            chat_id=self.channel_id,
            text=content,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
        return {
            'success': True,
            'message_id': message.message_id
        }
```

## Форматирование

### Markdown (ParseMode.MARKDOWN)

```python
text = """
**Заголовок жирным**

Обычный текст с _курсивом_.

`код inline`

[Ссылка](https://example.com)

#хештег #ещёхештег
"""
```

**Важно:** Экранируй спецсимволы: `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`

### HTML (ParseMode.HTML)

```python
text = """
<b>Заголовок жирным</b>

Обычный текст с <i>курсивом</i>.

<code>код inline</code>

<a href="https://example.com">Ссылка</a>
"""
```

## Ошибки

### Chat not found

```python
# Ошибка: Chat not found
# Причины:
# 1. Неверный TELEGRAM_CHANNEL_ID
# 2. Бот не добавлен в канал
# 3. Бот не админ канала
```

**Решение:**
1. Добавь бота в канал как администратора
2. Дай права: публикация, редактирование, удаление
3. Используй @username вместо numeric ID

### Message too long

```python
# Telegram limit: 4096 символов
if len(content) > 4096:
    content = content[:4090] + "..."
```

## Admin Bot (app/telegram/admin_bot.py)

Команды для админа:

| Команда | Действие |
|---------|----------|
| `/preview` | Показать следующий пост |
| `/publish_now` | Опубликовать немедленно |
| `/skip` | Пропустить пост |
| `/stats` | Статистика постов |
| `/sources` | Список источников |

```python
from telegram.ext import Application, CommandHandler

async def preview_handler(update, context):
    # Генерируем пост без публикации
    post = await generator.generate_post(sources)
    await update.message.reply_text(post['content'])

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("preview", preview_handler))
```

## Тестирование

```python
# test_publish.py
async def main():
    publisher = TelegramPublisher()

    # Проверить канал
    info = await publisher.get_chat_info()
    print(f"Channel: {info['title']}")

    # Опубликовать
    result = await publisher.publish_post("Тестовый пост")
    print(f"Message ID: {result['message_id']}")
```

## Rate Limits

- 30 сообщений/сек в группу
- 1 сообщение/сек в канал (рекомендуется)
- Bulk: не более 30 сообщений в минуту

```python
import asyncio

async def publish_batch(posts):
    for post in posts:
        await publisher.publish_post(post)
        await asyncio.sleep(2)  # 2 сек между постами
```
