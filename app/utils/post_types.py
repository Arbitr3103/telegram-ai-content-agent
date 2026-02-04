"""
Типы постов и ротация по формуле "3 кита"
"""
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Tuple

# Путь к файлу состояния ротации
STATE_FILE = Path(__file__).parent.parent.parent / "data" / "post_rotation.json"


# Пул CTA-текстов (выбирается рандомно)
CTA_POOL = [
    "💡 Нужна настройка? Оставьте заявку → https://t.me/smart_analytics_mp_bot",
    "📊 Хотите такие же результаты? Оставьте заявку → https://t.me/smart_analytics_mp_bot",
    "💬 Есть вопросы? Напишите в бот → https://t.me/smart_analytics_mp_bot",
    "📲 Оставить заявку → https://t.me/smart_analytics_mp_bot"
]

# Импорт промптов
from app.utils.prompts import (
    POST_TYPE_PROMPTS,
    CASE_PROMPT,
    USEFUL_PROMPT,
    LIFEHACK_PROMPT,
    EXPERT_OPINION_PROMPT,
    TOOLS_PROMPT,
    MISTAKE_PROMPT,
    CHECKLIST_PROMPT,
    INTERACTIVE_PROMPT,
)

# Типы постов (8 типов)
POST_TYPES = {
    "useful": {
        "name": "Полезная польза",
        "description": "Обучающий контент: метрики, способы, фишки",
        "frequency": 2,
        "prompt_addition": USEFUL_PROMPT
    },
    "case": {
        "name": "Кейс/Доказательство",
        "description": "Реальный результат с цифрами ДО/ПОСЛЕ",
        "frequency": 1,
        "prompt_addition": CASE_PROMPT
    },
    "interactive": {
        "name": "Интерактив/Мнение",
        "description": "Спорное мнение + вопрос к аудитории",
        "frequency": 1,
        "prompt_addition": INTERACTIVE_PROMPT
    },
    "checklist": {
        "name": "Чек-лист",
        "description": "7 задач для месяца/события",
        "frequency": 1,
        "prompt_addition": CHECKLIST_PROMPT
    },
    "tools": {
        "name": "Обзор инструментов",
        "description": "Топ-3 инструмента с плюсами/минусами",
        "frequency": 1,
        "prompt_addition": TOOLS_PROMPT
    },
    "mistake": {
        "name": "История ошибки",
        "description": "Storytelling с драматургией и уроком",
        "frequency": 1,
        "prompt_addition": MISTAKE_PROMPT
    },
    "lifehack": {
        "name": "Лайфхак",
        "description": "Пошаговая инструкция (бесплатно/быстро)",
        "frequency": 1,
        "prompt_addition": LIFEHACK_PROMPT
    },
    "expert_opinion": {
        "name": "Экспертное мнение",
        "description": "Анализ изменений + прогноз + 3 действия",
        "frequency": 1,
        "prompt_addition": EXPERT_OPINION_PROMPT
    }
}

# Порядок ротации: полезно, полезно, кейс, интерактив
ROTATION_ORDER = ["useful", "useful", "case", "interactive"]


def get_state() -> dict:
    """Получить текущее состояние ротации"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)

    return {"current_index": 0, "last_post_date": None, "history": []}


def save_state(state: dict):
    """Сохранить состояние ротации"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def can_publish() -> Tuple[bool, str]:
    """
    Проверить, можно ли публиковать (защита от дублей)
    Минимум 6 часов между постами

    Returns:
        (can_publish, reason)
    """
    state = get_state()
    last_post = state.get("last_post_date")

    if not last_post:
        return True, "OK"

    from datetime import datetime, timedelta

    last_post_time = datetime.fromisoformat(last_post)
    min_interval = timedelta(hours=6)

    if datetime.now() - last_post_time < min_interval:
        time_left = min_interval - (datetime.now() - last_post_time)
        hours_left = time_left.total_seconds() / 3600
        return False, f"Слишком рано. Подождите ещё {hours_left:.1f} часов"

    return True, "OK"


def should_add_cta() -> bool:
    """
    Определить, нужно ли добавлять CTA в этот пост
    Добавляем в 2 постах из 3 (пропускаем каждый третий)

    Returns:
        True если нужно добавить CTA
    """
    state = get_state()
    # Считаем общее количество опубликованных постов
    total_posts = len(state.get("history", []))

    # Добавляем CTA во все посты КРОМЕ каждого третьего
    # total_posts + 1 потому что мы планируем СЛЕДУЮЩИЙ пост
    position = (total_posts % 3) + 1
    return position != 3


def should_add_personal_experience() -> bool:
    """
    Определить, нужно ли добавлять личный опыт в этот пост
    Добавляем в 1 посте из 4 (каждый 4-й пост)

    Returns:
        True если нужно добавить личный опыт
    """
    state = get_state()
    # Считаем общее количество опубликованных постов
    total_posts = len(state.get("history", []))

    # Добавляем личный опыт в каждый 4-й пост (позиции 4, 8, 12, 16...)
    # total_posts + 1 потому что мы планируем СЛЕДУЮЩИЙ пост
    position = (total_posts % 4) + 1
    return position == 4


def get_next_post_type() -> Tuple[str, dict]:
    """
    Получить следующий тип поста по ротации

    Returns:
        (post_type_key, post_type_config)
    """
    state = get_state()
    current_index = state.get("current_index", 0)

    # Получаем тип поста из ротации
    post_type_key = ROTATION_ORDER[current_index % len(ROTATION_ORDER)]
    post_type_config = POST_TYPES[post_type_key].copy()

    # Добавляем флаг, нужно ли CTA
    post_type_config["add_cta"] = should_add_cta()

    # Выбираем случайный CTA из пула
    if post_type_config["add_cta"]:
        post_type_config["cta"] = random.choice(CTA_POOL)
    else:
        post_type_config["cta"] = ""

    # Добавляем флаг, нужно ли добавлять личный опыт
    post_type_config["add_personal_experience"] = should_add_personal_experience()

    return post_type_key, post_type_config


def get_post_type_from_plan(post_type_key: str) -> Tuple[str, dict]:
    """
    Получить конфиг типа поста из контент-плана.

    Args:
        post_type_key: ключ типа поста (useful, case, checklist, etc.)

    Returns:
        (post_type_key, post_type_config)
    """
    if post_type_key not in POST_TYPES:
        # Fallback на useful если тип неизвестен
        post_type_key = "useful"

    post_type_config = POST_TYPES[post_type_key].copy()

    # Добавляем флаг, нужно ли CTA
    post_type_config["add_cta"] = should_add_cta()

    # Выбираем случайный CTA из пула
    if post_type_config["add_cta"]:
        post_type_config["cta"] = random.choice(CTA_POOL)
    else:
        post_type_config["cta"] = ""

    return post_type_key, post_type_config


def mark_post_published(post_type_key: str):
    """Отметить пост как опубликованный и перейти к следующему типу"""
    state = get_state()

    # Обновляем индекс
    state["current_index"] = (state.get("current_index", 0) + 1) % len(ROTATION_ORDER)
    state["last_post_date"] = datetime.now().isoformat()

    # Добавляем в историю
    if "history" not in state:
        state["history"] = []
    state["history"].append({
        "type": post_type_key,
        "date": datetime.now().isoformat()
    })
    # Храним только последние 20 записей
    state["history"] = state["history"][-20:]

    save_state(state)


def get_random_publish_time() -> Tuple[int, int]:
    """
    Получить случайное время публикации между 09:00 и 12:00

    Returns:
        (hour, minute)
    """
    hour = random.randint(9, 11)
    minute = random.randint(0, 59)
    return hour, minute


def get_rotation_status() -> str:
    """Получить текстовый статус ротации"""
    state = get_state()
    current_index = state.get("current_index", 0)
    next_type_key = ROTATION_ORDER[current_index % len(ROTATION_ORDER)]
    next_type = POST_TYPES[next_type_key]

    status = f"""📊 Статус ротации постов:

Следующий тип: {next_type['name']}
Позиция в цикле: {current_index % len(ROTATION_ORDER) + 1} из {len(ROTATION_ORDER)}

Цикл ротации:
1. Полезная польза
2. Полезная польза
3. Кейс
4. Интерактив

Последний пост: {state.get('last_post_date', 'нет данных')}
"""
    return status


if __name__ == "__main__":
    # Тест
    print("Текущий статус:")
    print(get_rotation_status())

    print("\nСледующие 6 постов:")
    for i in range(6):
        post_type_key, post_type = get_next_post_type()
        print(f"{i+1}. {post_type['name']}")
        mark_post_published(post_type_key)
