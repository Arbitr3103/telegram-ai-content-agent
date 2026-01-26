"""
Обработчик FAQ
"""
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import (
    FAQ_MENU, FAQ_COST, FAQ_TIMELINE, FAQ_MARKETPLACES,
    FAQ_TECHNICAL, FAQ_WHAT_CAN, FAQ_CUSTOM_QUESTION, WELCOME_MESSAGE
)
from app.client_bot.keyboards.menus import (
    get_faq_menu_keyboard, get_faq_answer_keyboard, get_main_menu_keyboard
)
from app.client_bot.services.ai_responder import get_ai_responder

logger = logging.getLogger(__name__)

FAQ_CUSTOM_INPUT = 0


async def faq_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать меню FAQ"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        FAQ_MENU,
        reply_markup=get_faq_menu_keyboard()
    )

    return ConversationHandler.END


async def faq_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ответ на вопрос из FAQ"""
    query = update.callback_query
    await query.answer()

    answers = {
        "faq_what_can": FAQ_WHAT_CAN,
        "faq_cost": FAQ_COST,
        "faq_timeline": FAQ_TIMELINE,
        "faq_marketplaces": FAQ_MARKETPLACES,
        "faq_technical": FAQ_TECHNICAL,
    }

    answer = answers.get(query.data, "Извините, ответ не найден.")

    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["faq_count"] = \
        context.user_data["bot_activity"].get("faq_count", 0) + 1

    await query.edit_message_text(
        answer,
        reply_markup=get_faq_answer_keyboard()
    )

    return ConversationHandler.END


async def faq_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало ввода своего вопроса"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(FAQ_CUSTOM_QUESTION)

    return FAQ_CUSTOM_INPUT


async def faq_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка своего вопроса через AI"""
    question = update.message.text.strip()

    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["faq_count"] = \
        context.user_data["bot_activity"].get("faq_count", 0) + 1

    await update.message.chat.send_action("typing")

    ai_responder = get_ai_responder()
    answer = await ai_responder.answer_question(question)

    await update.message.reply_text(
        answer,
        reply_markup=get_faq_answer_keyboard()
    )

    return ConversationHandler.END


async def faq_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена FAQ"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_faq_handler() -> ConversationHandler:
    """Получить ConversationHandler для FAQ"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(faq_menu_handler, pattern="^faq$"),
        ],
        states={
            FAQ_CUSTOM_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, faq_custom_handler),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(faq_cancel, pattern="^menu$"),
            CallbackQueryHandler(faq_answer_handler, pattern="^faq_(what_can|cost|timeline|marketplaces|technical)$"),
            CallbackQueryHandler(faq_custom_start, pattern="^faq_custom$"),
        ],
        per_message=False,
    )


def get_faq_direct_handlers() -> list:
    """Дополнительные обработчики для прямых callback"""
    return [
        CallbackQueryHandler(faq_answer_handler, pattern="^faq_(what_can|cost|timeline|marketplaces|technical)$"),
    ]
