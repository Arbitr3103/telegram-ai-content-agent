"""
Обработчик мини-аудита магазина Ozon
"""
import logging

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.config import settings
from app.client_bot.texts.messages import (
    AUDIT_REQUEST_LINK, AUDIT_INVALID_LINK,
    AUDIT_PARSING_ERROR, AUDIT_LIMIT_REACHED, WELCOME_MESSAGE
)
from app.client_bot.keyboards.menus import (
    get_back_to_menu_keyboard, get_audit_result_keyboard,
    get_audit_limit_keyboard, get_main_menu_keyboard
)
from app.client_bot.services.ozon_parser import (
    extract_seller_id, parse_ozon_seller,
    format_audit_result, OzonParseError
)

logger = logging.getLogger(__name__)

AUDIT_WAITING_LINK = 0


async def audit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало аудита — запрос ссылки"""
    query = update.callback_query
    await query.answer()

    audits_today = context.user_data.get("audits_today", 0)
    limit = settings.audit_daily_limit

    if audits_today >= limit:
        await query.edit_message_text(
            AUDIT_LIMIT_REACHED,
            reply_markup=get_audit_limit_keyboard()
        )
        return ConversationHandler.END

    await query.edit_message_text(
        AUDIT_REQUEST_LINK,
        reply_markup=get_back_to_menu_keyboard()
    )

    return AUDIT_WAITING_LINK


async def audit_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ссылки на магазин"""
    link = update.message.text.strip()

    seller_id = extract_seller_id(link)

    if not seller_id:
        await update.message.reply_text(
            AUDIT_INVALID_LINK,
            reply_markup=get_back_to_menu_keyboard()
        )
        return AUDIT_WAITING_LINK

    await update.message.chat.send_action("typing")

    try:
        seller_data = await parse_ozon_seller(seller_id)

        result_text = format_audit_result(seller_data)

        context.user_data["audits_today"] = context.user_data.get("audits_today", 0) + 1

        if "bot_activity" not in context.user_data:
            context.user_data["bot_activity"] = {}
        context.user_data["bot_activity"]["audit_done"] = True

        await update.message.reply_text(
            result_text,
            reply_markup=get_audit_result_keyboard()
        )

        logger.info(f"Audit completed for seller: {seller_id}")

    except OzonParseError as e:
        logger.error(f"Ozon parse error: {e}")
        await update.message.reply_text(
            AUDIT_PARSING_ERROR,
            reply_markup=get_audit_result_keyboard()
        )

    return ConversationHandler.END


async def audit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена аудита"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_audit_handler() -> ConversationHandler:
    """Получить ConversationHandler для аудита"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(audit_start, pattern="^audit$"),
        ],
        states={
            AUDIT_WAITING_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, audit_link_handler),
                CallbackQueryHandler(audit_cancel, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(audit_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
