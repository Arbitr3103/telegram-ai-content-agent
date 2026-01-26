"""
Обработчик калькулятора упущенной выгоды
"""
import logging
from typing import Dict, Any

from telegram import Update
from telegram.ext import (
    ContextTypes, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from app.client_bot.texts.messages import (
    CALC_HOURS_QUESTION, CALC_HOURLY_RATE_QUESTION,
    CALC_PRICING_ERRORS_QUESTION, CALC_COMPETITOR_CHECK_QUESTION,
    CALC_RESULT_TEMPLATE, WELCOME_MESSAGE
)
from app.client_bot.keyboards.menus import (
    get_calc_hours_keyboard, get_calc_rate_keyboard,
    get_calc_errors_keyboard, get_calc_competitor_keyboard,
    get_calc_result_keyboard, get_main_menu_keyboard
)

logger = logging.getLogger(__name__)

CALC_HOURS, CALC_RATE, CALC_RATE_CUSTOM, CALC_ERRORS, CALC_COMPETITOR = range(5)


async def calculator_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало калькулятора"""
    query = update.callback_query
    await query.answer()

    context.user_data["calc"] = {}

    await query.edit_message_text(
        CALC_HOURS_QUESTION,
        reply_markup=get_calc_hours_keyboard()
    )

    return CALC_HOURS


async def calc_hours_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора часов"""
    query = update.callback_query
    await query.answer()

    hours_map = {
        "calc_hours_3": 3,
        "calc_hours_10": 10,
        "calc_hours_15": 15,
    }

    hours = hours_map.get(query.data, 10)
    context.user_data["calc"]["hours"] = hours

    await query.edit_message_text(
        CALC_HOURLY_RATE_QUESTION,
        reply_markup=get_calc_rate_keyboard()
    )

    return CALC_RATE


async def calc_rate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора ставки"""
    query = update.callback_query
    await query.answer()

    if query.data == "calc_rate_custom":
        await query.edit_message_text(
            "Введите стоимость вашего часа работы (число в рублях):"
        )
        return CALC_RATE_CUSTOM

    rate_map = {
        "calc_rate_500": 500,
        "calc_rate_1000": 1000,
        "calc_rate_2000": 2000,
    }

    rate = rate_map.get(query.data, 1000)
    context.user_data["calc"]["rate"] = rate

    await query.edit_message_text(
        CALC_PRICING_ERRORS_QUESTION,
        reply_markup=get_calc_errors_keyboard()
    )

    return CALC_ERRORS


async def calc_rate_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кастомной ставки"""
    try:
        rate = int(update.message.text.strip().replace(" ", "").replace("₽", ""))
        context.user_data["calc"]["rate"] = rate
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число. Например: 1500"
        )
        return CALC_RATE_CUSTOM

    await update.message.reply_text(
        CALC_PRICING_ERRORS_QUESTION,
        reply_markup=get_calc_errors_keyboard()
    )

    return CALC_ERRORS


async def calc_errors_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора ошибок в ценах"""
    query = update.callback_query
    await query.answer()

    errors_map = {
        "calc_errors_big": "big",
        "calc_errors_small": "small",
        "calc_errors_no": "no",
    }

    errors = errors_map.get(query.data, "small")
    context.user_data["calc"]["errors"] = errors

    await query.edit_message_text(
        CALC_COMPETITOR_CHECK_QUESTION,
        reply_markup=get_calc_competitor_keyboard()
    )

    return CALC_COMPETITOR


async def calc_competitor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора частоты проверки конкурентов и вывод результата"""
    query = update.callback_query
    await query.answer()

    competitor_map = {
        "calc_comp_daily": "daily",
        "calc_comp_weekly": "weekly",
        "calc_comp_rarely": "rarely",
    }

    competitor = competitor_map.get(query.data, "weekly")
    context.user_data["calc"]["competitor"] = competitor

    result = calculate_losses(context.user_data["calc"])

    context.user_data["calc"]["result"] = result
    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["calculator_done"] = True
    context.user_data["bot_activity"]["calculated_loss"] = result["total_loss"]

    await query.edit_message_text(
        result["message"],
        reply_markup=get_calc_result_keyboard()
    )

    return ConversationHandler.END


def calculate_losses(data: Dict[str, Any]) -> Dict[str, Any]:
    """Расчёт упущенной выгоды"""
    hours = data.get("hours", 10)
    rate = data.get("rate", 1000)
    errors = data.get("errors", "small")
    competitor = data.get("competitor", "weekly")

    manual_work_cost = hours * rate * 4

    errors_map = {
        "big": (25000, "Средняя потеря при серьёзных ошибках = 25 000 ₽/мес*"),
        "small": (10000, "Средняя потеря при мелких ошибках = 10 000 ₽/мес*"),
        "no": (0, "Отлично, что ошибок нет!"),
    }
    errors_cost, errors_text = errors_map.get(errors, (10000, ""))

    competitor_map = {
        "daily": (0, "Вы следите за рынком — отлично!"),
        "weekly": (15000, "~3-5% упущенных продаж из-за неоптимальных цен"),
        "rarely": (30000, "~5-10% оборота теряется при редкой проверке цен"),
    }
    competitor_cost, competitor_text = competitor_map.get(competitor, (15000, ""))

    total_loss = manual_work_cost + errors_cost + competitor_cost

    message = CALC_RESULT_TEMPLATE.format(
        hours_per_week=hours,
        hourly_rate=rate,
        manual_work_cost=manual_work_cost,
        pricing_errors_text=errors_text,
        competitor_text=competitor_text,
        total_loss=total_loss
    )

    return {
        "message": message,
        "total_loss": total_loss,
        "manual_work_cost": manual_work_cost,
        "errors_cost": errors_cost,
        "competitor_cost": competitor_cost,
    }


async def calc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена калькулятора"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )

    return ConversationHandler.END


def get_calculator_handler() -> ConversationHandler:
    """Получить ConversationHandler для калькулятора"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(calculator_start, pattern="^calculator$"),
        ],
        states={
            CALC_HOURS: [
                CallbackQueryHandler(calc_hours_handler, pattern="^calc_hours_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
            CALC_RATE: [
                CallbackQueryHandler(calc_rate_handler, pattern="^calc_rate_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
            CALC_RATE_CUSTOM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, calc_rate_custom_handler),
            ],
            CALC_ERRORS: [
                CallbackQueryHandler(calc_errors_handler, pattern="^calc_errors_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
            CALC_COMPETITOR: [
                CallbackQueryHandler(calc_competitor_handler, pattern="^calc_comp_"),
                CallbackQueryHandler(calc_cancel, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(calc_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
