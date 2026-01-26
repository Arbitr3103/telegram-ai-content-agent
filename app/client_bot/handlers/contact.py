"""
Обработчик кнопки "Связаться с человеком"
"""
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import CONTACT_REQUEST, CONTACT_WITH_MESSAGE, WELCOME_MESSAGE
from app.client_bot.keyboards.menus import get_contact_keyboard, get_main_menu_keyboard
from app.client_bot.services.lead_notifier import LeadNotifier

logger = logging.getLogger(__name__)

CONTACT_MESSAGE = 0


async def contact_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало запроса на связь"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(CONTACT_WITH_MESSAGE)

    return CONTACT_MESSAGE


async def contact_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка сообщения для передачи"""
    message = update.message.text.strip()
    user = update.effective_user

    notifier = LeadNotifier(context.bot)
    await notifier.notify_contact_request(
        username=user.username,
        first_name=user.first_name,
        message=message
    )

    logger.info(f"Contact request from @{user.username}: {message[:50]}...")

    await update.message.reply_text(
        CONTACT_REQUEST,
        reply_markup=get_contact_keyboard()
    )

    return ConversationHandler.END


async def contact_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_contact_handler() -> ConversationHandler:
    """Получить ConversationHandler для связи"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(contact_start, pattern="^contact$"),
        ],
        states={
            CONTACT_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, contact_message_handler),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(contact_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
