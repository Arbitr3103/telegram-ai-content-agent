"""
Обработчик формы заявки
"""
import logging
from typing import List

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import (
    APPLICATION_SKU_QUESTION, APPLICATION_URGENCY_QUESTION,
    APPLICATION_MARKETPLACES_QUESTION, APPLICATION_NAME_QUESTION,
    APPLICATION_TASK_QUESTION, APPLICATION_BUDGET_QUESTION,
    APPLICATION_CONTACT_METHOD_QUESTION, APPLICATION_SUCCESS, WELCOME_MESSAGE
)
from app.client_bot.keyboards.menus import (
    get_sku_keyboard, get_urgency_keyboard, get_marketplaces_keyboard,
    get_budget_keyboard, get_contact_method_keyboard, get_main_menu_keyboard
)

logger = logging.getLogger(__name__)

(APP_SKU, APP_URGENCY, APP_MARKETPLACES,
 APP_NAME, APP_TASK, APP_BUDGET, APP_CONTACT) = range(7)


async def application_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало заявки — вопрос о SKU"""
    query = update.callback_query
    await query.answer()

    context.user_data["application"] = {
        "marketplaces": []
    }

    await query.edit_message_text(
        APPLICATION_SKU_QUESTION,
        reply_markup=get_sku_keyboard()
    )

    return APP_SKU


async def app_sku_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора SKU"""
    query = update.callback_query
    await query.answer()

    sku_map = {
        "app_sku_lt50": "< 50",
        "app_sku_50_200": "50-200",
        "app_sku_200_500": "200-500",
        "app_sku_gt500": "> 500",
    }

    context.user_data["application"]["sku_count"] = sku_map.get(query.data, "Не указано")

    await query.edit_message_text(
        APPLICATION_URGENCY_QUESTION,
        reply_markup=get_urgency_keyboard()
    )

    return APP_URGENCY


async def app_urgency_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора срочности"""
    query = update.callback_query
    await query.answer()

    urgency_map = {
        "app_urgency_now": "Нужно сейчас",
        "app_urgency_month": "В ближайший месяц",
        "app_urgency_looking": "Просто смотрю",
    }

    context.user_data["application"]["urgency"] = urgency_map.get(query.data, "Не указано")

    await query.edit_message_text(
        APPLICATION_MARKETPLACES_QUESTION,
        reply_markup=get_marketplaces_keyboard()
    )

    return APP_MARKETPLACES


async def app_marketplaces_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора маркетплейсов (мультивыбор)"""
    query = update.callback_query
    await query.answer()

    mp_map = {
        "app_mp_ozon": "Ozon",
        "app_mp_wb": "Wildberries",
        "app_mp_yandex": "Яндекс.Маркет",
    }

    if query.data == "app_mp_done":
        await query.edit_message_text(
            APPLICATION_NAME_QUESTION
        )
        return APP_NAME

    mp = mp_map.get(query.data)
    if mp:
        selected: List[str] = context.user_data["application"].get("marketplaces", [])
        if mp in selected:
            selected.remove(mp)
        else:
            selected.append(mp)
        context.user_data["application"]["marketplaces"] = selected

    await query.edit_message_text(
        APPLICATION_MARKETPLACES_QUESTION,
        reply_markup=get_marketplaces_keyboard(
            context.user_data["application"]["marketplaces"]
        )
    )

    return APP_MARKETPLACES


async def app_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка имени"""
    name = update.message.text.strip()
    context.user_data["application"]["name"] = name

    await update.message.reply_text(APPLICATION_TASK_QUESTION)

    return APP_TASK


async def app_task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка описания задачи"""
    task = update.message.text.strip()
    context.user_data["application"]["task"] = task

    await update.message.reply_text(
        APPLICATION_BUDGET_QUESTION,
        reply_markup=get_budget_keyboard()
    )

    return APP_BUDGET


async def app_budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора бюджета"""
    query = update.callback_query
    await query.answer()

    budget_map = {
        "app_budget_lt30": "до 30 тыс",
        "app_budget_30_50": "30-50 тыс",
        "app_budget_50_100": "50-100 тыс",
        "app_budget_gt100": "> 100 тыс",
        "app_budget_unknown": "Не определён",
    }

    context.user_data["application"]["budget"] = budget_map.get(query.data, "Не указан")

    await query.edit_message_text(
        APPLICATION_CONTACT_METHOD_QUESTION,
        reply_markup=get_contact_method_keyboard()
    )

    return APP_CONTACT


async def app_contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка способа связи и отправка заявки"""
    query = update.callback_query
    await query.answer()

    contact_map = {
        "app_contact_telegram": "Telegram",
        "app_contact_whatsapp": "WhatsApp",
        "app_contact_call": "Звонок",
    }

    context.user_data["application"]["contact_method"] = contact_map.get(query.data, "Telegram")

    user = update.effective_user
    app_data = context.user_data["application"]
    bot_activity = context.user_data.get("bot_activity", {})

    from app.client_bot.services.lead_notifier import LeadNotifier
    notifier = LeadNotifier(context.bot)

    await notifier.notify_new_lead(
        name=app_data.get("name"),
        username=user.username,
        contact_method=app_data.get("contact_method"),
        sku_count=app_data.get("sku_count"),
        urgency=app_data.get("urgency"),
        marketplaces=app_data.get("marketplaces", []),
        budget=app_data.get("budget"),
        task=app_data.get("task"),
        bot_activity=bot_activity
    )

    logger.info(f"New lead from @{user.username}: {app_data}")

    await query.edit_message_text(
        APPLICATION_SUCCESS,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


async def app_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена заявки"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_application_handler() -> ConversationHandler:
    """Получить ConversationHandler для заявки"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(application_start, pattern="^application$"),
        ],
        states={
            APP_SKU: [
                CallbackQueryHandler(app_sku_handler, pattern="^app_sku_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_URGENCY: [
                CallbackQueryHandler(app_urgency_handler, pattern="^app_urgency_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_MARKETPLACES: [
                CallbackQueryHandler(app_marketplaces_handler, pattern="^app_mp_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, app_name_handler),
            ],
            APP_TASK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, app_task_handler),
            ],
            APP_BUDGET: [
                CallbackQueryHandler(app_budget_handler, pattern="^app_budget_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
            APP_CONTACT: [
                CallbackQueryHandler(app_contact_handler, pattern="^app_contact_"),
                CallbackQueryHandler(app_cancel, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(app_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
