"""
Обработчик команды /start и главного меню
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from app.client_bot.texts.messages import WELCOME_MESSAGE
from app.client_bot.keyboards.menus import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"User {user.id} (@{user.username}) started the bot")

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )


async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки возврата в меню"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )


def get_start_handlers() -> list:
    """Получить обработчики для регистрации"""
    return [
        CommandHandler("start", start_handler),
        CallbackQueryHandler(menu_callback_handler, pattern="^menu$"),
    ]
