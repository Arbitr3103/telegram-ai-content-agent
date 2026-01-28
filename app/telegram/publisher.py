"""
Telegram Publisher для публикации постов в канал
"""
import logging
from typing import Optional, Dict, Any

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.config import settings

logger = logging.getLogger(__name__)


class TelegramPublisher:
    """Класс для публикации постов в Telegram канал"""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None
    ):
        """
        Инициализация Publisher

        Args:
            bot_token: Telegram Bot Token
            channel_id: ID канала для публикации
        """
        self.bot_token = bot_token or settings.telegram_bot_token
        self.channel_id = channel_id or settings.telegram_channel_id

        self.bot = Bot(token=self.bot_token)
        logger.info(f"TelegramPublisher initialized for channel: {self.channel_id}")

    async def publish_post(
        self,
        content: str,
        disable_web_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Публикация поста в Telegram канал

        Args:
            content: Текст поста
            disable_web_preview: Отключить preview ссылок

        Returns:
            Информация об отправленном сообщении
        """
        # Форматирование текста
        message_text = self._format_message(content)

        try:
            # Отправка сообщения
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=message_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=disable_web_preview
            )

            logger.info(f"Post published successfully. Message ID: {message.message_id}")

            return {
                'success': True,
                'message_id': message.message_id,
                'chat_id': message.chat.id,
                'date': message.date
            }

        except TelegramError as e:
            logger.error(f"Error publishing post: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _format_message(self, content: str) -> str:
        """
        Форматирование сообщения для Telegram

        Args:
            content: Контент поста

        Returns:
            Отформатированный текст
        """
        return content.strip()

    async def edit_post(
        self,
        message_id: int,
        new_content: str
    ) -> Dict[str, Any]:
        """
        Редактирование опубликованного поста

        Args:
            message_id: ID сообщения для редактирования
            new_content: Новый контент

        Returns:
            Результат редактирования
        """
        message_text = self._format_message(new_content)

        try:
            await self.bot.edit_message_text(
                chat_id=self.channel_id,
                message_id=message_id,
                text=message_text,
                parse_mode=ParseMode.HTML
            )

            logger.info(f"Post {message_id} edited successfully")
            return {'success': True, 'message_id': message_id}

        except TelegramError as e:
            logger.error(f"Error editing post {message_id}: {e}")
            return {'success': False, 'error': str(e)}

    async def delete_post(self, message_id: int) -> bool:
        """
        Удаление поста

        Args:
            message_id: ID сообщения

        Returns:
            True если успешно удалено
        """
        try:
            await self.bot.delete_message(
                chat_id=self.channel_id,
                message_id=message_id
            )
            logger.info(f"Post {message_id} deleted successfully")
            return True

        except TelegramError as e:
            logger.error(f"Error deleting post {message_id}: {e}")
            return False

    async def get_chat_info(self) -> Dict[str, Any]:
        """Получить информацию о канале"""
        try:
            chat = await self.bot.get_chat(chat_id=self.channel_id)
            return {
                'id': chat.id,
                'title': chat.title,
                'type': chat.type,
                'username': chat.username
            }
        except TelegramError as e:
            logger.error(f"Error getting chat info: {e}")
            return {}


# Вспомогательная функция

async def publish_to_telegram(
    content: str,
    bot_token: Optional[str] = None,
    channel_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Удобная функция для публикации поста

    Args:
        content: Текст поста
        bot_token: Telegram Bot Token (опционально)
        channel_id: ID канала (опционально)

    Returns:
        Результат публикации
    """
    publisher = TelegramPublisher(bot_token=bot_token, channel_id=channel_id)
    return await publisher.publish_post(content)


if __name__ == "__main__":
    import asyncio

    async def main():
        # Пример публикации
        test_content = """🚨 Тестовый пост от AI Content Agent

Это автоматически сгенерированный пост для проверки системы.

Если вы видите это сообщение — всё работает! ✅
        """

        publisher = TelegramPublisher()

        # Получить информацию о канале
        info = await publisher.get_chat_info()
        print(f"Channel info: {info}")

        # Опубликовать пост
        result = await publisher.publish_post(content=test_content)
        print(f"Publish result: {result}")

    asyncio.run(main())
