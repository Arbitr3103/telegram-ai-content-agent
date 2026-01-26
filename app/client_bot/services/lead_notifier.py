"""
Сервис уведомлений администратора о заявках
"""
import logging
from typing import Optional, Dict, Any

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.config import settings
from app.client_bot.texts.messages import ADMIN_NEW_LEAD, ADMIN_CONTACT_REQUEST

logger = logging.getLogger(__name__)


class LeadNotifier:
    """Уведомления администратора о новых заявках"""

    def __init__(self, bot: Bot):
        """
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self.admin_id = settings.telegram_admin_id

    async def notify_new_lead(
        self,
        name: str,
        username: str,
        contact_method: str,
        sku_count: str,
        urgency: str,
        marketplaces: list,
        budget: str,
        task: str,
        bot_activity: Dict[str, Any]
    ) -> bool:
        """
        Уведомить о новой заявке

        Returns:
            True если уведомление отправлено
        """
        activity_lines = []
        if bot_activity.get("audit_done"):
            activity_lines.append("• Прошёл аудит магазина: Да")
        if bot_activity.get("calculator_done"):
            loss = bot_activity.get("calculated_loss", 0)
            activity_lines.append(f"• Калькулятор: Да (потери ~{loss:,} ₽/мес)")
        if bot_activity.get("faq_count", 0) > 0:
            activity_lines.append(f"• Вопросов в FAQ: {bot_activity['faq_count']}")

        activity_text = "\n".join(activity_lines) if activity_lines else "• Минимальная"

        message = ADMIN_NEW_LEAD.format(
            name=name or "Не указано",
            username=username or "Не указан",
            contact_method=contact_method or "Не указан",
            sku_count=sku_count or "Не указано",
            urgency=urgency or "Не указана",
            marketplaces=", ".join(marketplaces) if marketplaces else "Не указаны",
            budget=budget or "Не указан",
            task=task or "Не указана",
            bot_activity=activity_text
        )

        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Lead notification sent for @{username}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send lead notification: {e}")
            return False

    async def notify_contact_request(
        self,
        username: str,
        first_name: str,
        message: Optional[str] = None
    ) -> bool:
        """
        Уведомить о запросе на связь

        Returns:
            True если уведомление отправлено
        """
        text = ADMIN_CONTACT_REQUEST.format(
            username=username or "Не указан",
            first_name=first_name or "Пользователь",
            message=message or "Без сообщения"
        )

        try:
            await self.bot.send_message(
                chat_id=self.admin_id,
                text=text
            )
            logger.info(f"Contact request notification sent for @{username}")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send contact notification: {e}")
            return False
