"""
Скрипт для публикации и закрепления навигационного поста
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot
from telegram.constants import ParseMode
from app.config import settings


PINNED_POST_CONTENT = """👋 Привет! Я Владимир — специалист по аналитике и автоматизации для маркетплейсов.

📊 <b>Чем занимаюсь:</b>
• Сбор данных через API (Ozon, Wildberries, Яндекс.Маркет)
• Автоматические отчёты и дашборды
• ETL-пайплайны для e-commerce
• Интеграции с 1С, Google Sheets, Looker Studio

💼 <b>Кейс:</b>
Селлер с 3000+ SKU тратил 6 часов в день на отчёты.
→ Настроил автоматический сбор данных + дашборд.
→ Теперь отчёты готовы к 9:00 без участия человека.
→ Экономия: 120+ часов в месяц.

🎯 <b>Что найдёте в канале:</b>
• Новости API маркетплейсов
• Лайфхаки по автоматизации
• Разборы реальных кейсов
• Инструменты для селлеров

📩 <b>Нужна консультация?</b>
Пишите: @Bragin_Arbitr"""


async def publish_and_pin():
    """Публикация и закрепление поста"""
    bot = Bot(token=settings.telegram_bot_token)

    print(f"📤 Публикация в канал {settings.telegram_channel_id}...")

    # Публикуем пост
    message = await bot.send_message(
        chat_id=settings.telegram_channel_id,
        text=PINNED_POST_CONTENT,
        parse_mode=ParseMode.HTML
    )

    print(f"✅ Опубликовано! Message ID: {message.message_id}")

    # Закрепляем
    try:
        await bot.pin_chat_message(
            chat_id=settings.telegram_channel_id,
            message_id=message.message_id,
            disable_notification=True
        )
        print(f"📌 Пост закреплён!")
    except Exception as e:
        print(f"⚠️ Не удалось закрепить (возможно нет прав): {e}")

    return message.message_id


if __name__ == "__main__":
    message_id = asyncio.run(publish_and_pin())
    print(f"\n✅ Готово! Закреплённый пост: Message ID {message_id}")
