"""
Обработчик калькулятора экономии времени
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
    CALC_RESULT_TEMPLATE, WELCOME_MESSAGE
)
from app.client_bot.keyboards.menus import (
    get_calc_hours_keyboard, get_calc_rate_keyboard,
    get_calc_result_keyboard, get_main_menu_keyboard
)

logger = logging.getLogger(__name__)

CALC_HOURS, CALC_RATE, CALC_RATE_CUSTOM = range(3)


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
    """Обработка выбора ставки и вывод результата"""
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

    result = calculate_savings(context.user_data["calc"])

    context.user_data["calc"]["result"] = result
    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["calculator_done"] = True
    context.user_data["bot_activity"]["calculated_savings"] = result["total_savings"]

    await query.edit_message_text(
        result["message"],
        reply_markup=get_calc_result_keyboard()
    )

    return ConversationHandler.END


async def calc_rate_custom_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кастомной ставки и вывод результата"""
    try:
        rate = int(update.message.text.strip().replace(" ", "").replace("₽", ""))
        context.user_data["calc"]["rate"] = rate
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите число. Например: 1500"
        )
        return CALC_RATE_CUSTOM

    result = calculate_savings(context.user_data["calc"])

    context.user_data["calc"]["result"] = result
    if "bot_activity" not in context.user_data:
        context.user_data["bot_activity"] = {}
    context.user_data["bot_activity"]["calculator_done"] = True
    context.user_data["bot_activity"]["calculated_savings"] = result["total_savings"]

    await update.message.reply_text(
        result["message"],
        reply_markup=get_calc_result_keyboard()
    )

    return ConversationHandler.END


def calculate_savings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Расчёт экономии времени при автоматизации"""
    hours = data.get("hours", 10)
    rate = data.get("rate", 1000)

    # Стоимость ручной работы в месяц
    manual_work_cost = hours * rate * 4

    # Типичные задачи для автоматизации
    tasks_text = """Типичные задачи для автоматизации:
• Выгрузка заказов и остатков
• Обновление цен и наличия
• Формирование отчётов
• Сверка данных с учётными системами"""

    # Периодичность
    frequency_text = "При ежедневной работе — ещё больше экономии."

    message = CALC_RESULT_TEMPLATE.format(
        hours_per_week=hours,
        hourly_rate=rate,
        manual_work_cost=manual_work_cost,
        tasks_text=tasks_text,
        frequency_text=frequency_text,
        total_loss=manual_work_cost
    )

    return {
        "message": message,
        "total_savings": manual_work_cost,
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
        },
        fallbacks=[
            CallbackQueryHandler(calc_cancel, pattern="^menu$"),
        ],
        per_message=False,
    )
