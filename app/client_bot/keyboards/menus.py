"""
Клавиатуры клиентского бота
"""
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("💸 Калькулятор упущенной выгоды", callback_data="calculator")],
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("👤 Связаться с человеком", callback_data="contact")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню"""
    keyboard = [[InlineKeyboardButton("🏠 В меню", callback_data="menu")]]
    return InlineKeyboardMarkup(keyboard)


def get_audit_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после аудита"""
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_audit_limit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура при превышении лимита аудитов"""
    keyboard = [
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Калькулятор
def get_calc_hours_keyboard() -> InlineKeyboardMarkup:
    """Выбор часов в неделю"""
    keyboard = [
        [
            InlineKeyboardButton("2-3 часа", callback_data="calc_hours_3"),
            InlineKeyboardButton("5-10 часов", callback_data="calc_hours_10"),
            InlineKeyboardButton(">10 часов", callback_data="calc_hours_15"),
        ],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_rate_keyboard() -> InlineKeyboardMarkup:
    """Выбор стоимости часа"""
    keyboard = [
        [
            InlineKeyboardButton("500 ₽", callback_data="calc_rate_500"),
            InlineKeyboardButton("1000 ₽", callback_data="calc_rate_1000"),
            InlineKeyboardButton("2000 ₽", callback_data="calc_rate_2000"),
        ],
        [InlineKeyboardButton("Другая", callback_data="calc_rate_custom")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_errors_keyboard() -> InlineKeyboardMarkup:
    """Выбор ошибок в ценах"""
    keyboard = [
        [InlineKeyboardButton("Да, теряли деньги", callback_data="calc_errors_big")],
        [InlineKeyboardButton("Да, мелкие", callback_data="calc_errors_small")],
        [InlineKeyboardButton("Нет", callback_data="calc_errors_no")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_competitor_keyboard() -> InlineKeyboardMarkup:
    """Выбор частоты проверки конкурентов"""
    keyboard = [
        [InlineKeyboardButton("Каждый день", callback_data="calc_comp_daily")],
        [InlineKeyboardButton("Раз в неделю", callback_data="calc_comp_weekly")],
        [InlineKeyboardButton("Редко/никогда", callback_data="calc_comp_rarely")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_calc_result_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после калькулятора"""
    keyboard = [
        [InlineKeyboardButton("📝 Обсудить автоматизацию", callback_data="application")],
        [InlineKeyboardButton("🔄 Пересчитать", callback_data="calculator")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# FAQ
def get_faq_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню FAQ"""
    keyboard = [
        [InlineKeyboardButton("💰 Сколько стоят услуги?", callback_data="faq_cost")],
        [InlineKeyboardButton("⏱ Сколько времени займёт внедрение?", callback_data="faq_timeline")],
        [InlineKeyboardButton("🛒 С какими маркетплейсами работаете?", callback_data="faq_marketplaces")],
        [InlineKeyboardButton("⚙️ Как это технически работает?", callback_data="faq_technical")],
        [InlineKeyboardButton("🎁 Можно попробовать бесплатно?", callback_data="faq_trial")],
        [InlineKeyboardButton("✍️ Задать свой вопрос", callback_data="faq_custom")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_faq_answer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после ответа на FAQ"""
    keyboard = [
        [InlineKeyboardButton("❓ Другой вопрос", callback_data="faq")],
        [InlineKeyboardButton("📝 Оставить заявку", callback_data="application")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Заявка
def get_sku_keyboard() -> InlineKeyboardMarkup:
    """Выбор количества SKU"""
    keyboard = [
        [
            InlineKeyboardButton("< 50", callback_data="app_sku_lt50"),
            InlineKeyboardButton("50-200", callback_data="app_sku_50_200"),
        ],
        [
            InlineKeyboardButton("200-500", callback_data="app_sku_200_500"),
            InlineKeyboardButton("> 500", callback_data="app_sku_gt500"),
        ],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_urgency_keyboard() -> InlineKeyboardMarkup:
    """Выбор срочности"""
    keyboard = [
        [InlineKeyboardButton("Нужно сейчас", callback_data="app_urgency_now")],
        [InlineKeyboardButton("В ближайший месяц", callback_data="app_urgency_month")],
        [InlineKeyboardButton("Просто смотрю", callback_data="app_urgency_looking")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_marketplaces_keyboard(selected: List[str] = None) -> InlineKeyboardMarkup:
    """Выбор маркетплейсов (мультивыбор)"""
    selected = selected or []

    def mark(name: str) -> str:
        return f"✓ {name}" if name in selected else name

    keyboard = [
        [
            InlineKeyboardButton(mark("Ozon"), callback_data="app_mp_ozon"),
            InlineKeyboardButton(mark("Wildberries"), callback_data="app_mp_wb"),
        ],
        [InlineKeyboardButton(mark("Яндекс.Маркет"), callback_data="app_mp_yandex")],
        [InlineKeyboardButton("✅ Готово", callback_data="app_mp_done")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_budget_keyboard() -> InlineKeyboardMarkup:
    """Выбор бюджета"""
    keyboard = [
        [
            InlineKeyboardButton("до 30 тыс", callback_data="app_budget_lt30"),
            InlineKeyboardButton("30-50 тыс", callback_data="app_budget_30_50"),
        ],
        [
            InlineKeyboardButton("50-100 тыс", callback_data="app_budget_50_100"),
            InlineKeyboardButton("> 100 тыс", callback_data="app_budget_gt100"),
        ],
        [InlineKeyboardButton("Не определён", callback_data="app_budget_unknown")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_contact_method_keyboard() -> InlineKeyboardMarkup:
    """Выбор способа связи"""
    keyboard = [
        [
            InlineKeyboardButton("Telegram", callback_data="app_contact_telegram"),
            InlineKeyboardButton("WhatsApp", callback_data="app_contact_whatsapp"),
        ],
        [InlineKeyboardButton("Звонок", callback_data="app_contact_call")],
        [InlineKeyboardButton("🏠 В меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


# Связаться
def get_contact_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после запроса на связь"""
    keyboard = [
        [InlineKeyboardButton("💸 Рассчитать упущенную выгоду", callback_data="calculator")],
        [InlineKeyboardButton("❓ Частые вопросы", callback_data="faq")],
        [InlineKeyboardButton("🏠 Вернуться в меню", callback_data="menu")],
    ]
    return InlineKeyboardMarkup(keyboard)
