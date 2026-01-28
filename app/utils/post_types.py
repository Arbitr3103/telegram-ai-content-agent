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


# Типы постов
POST_TYPES = {
    "useful": {
        "name": "Полезная польза",
        "description": "Разбор API, фишки автоматизации, как сэкономить",
        "frequency": 2,  # 2 раза в цикле
        "cta": "💡 Хотите настроить такую же интеграцию? Пишите → https://t.me/smart_analytics_mp_bot",
        "prompt_addition": """
ТИП ПОСТА: ПОЛЕЗНАЯ ПОЛЬЗА (практический гайд)

Напиши пост с конкретной пользой:
- Разбор нового API или метода
- Фишка в работе с данными
- Как сэкономить время/деньги
- Лайфхак автоматизации

Формат: Проблема → Решение → Как применить
"""
    },
    "case": {
        "name": "Кейс/Доказательство",
        "description": "Реальный результат с цифрами",
        "frequency": 1,  # 1 раз в цикле
        "cta": "📊 Рассчитать вашу экономию → https://t.me/smart_analytics_mp_bot",
        "prompt_addition": """
ТИП ПОСТА: КЕЙС (доказательство экспертизы)

Напиши пост-кейс с результатами:
- Опиши задачу клиента (можно обобщённо)
- Что сделали (автоматизация, интеграция, дашборд)
- Результат в цифрах: сэкономили X часов, увеличили Y%
- Вывод: почему это важно для других

Формат: Было → Сделали → Стало (с цифрами!)
"""
    },
    "interactive": {
        "name": "Интерактив/Мнение",
        "description": "Твоё мнение или вопрос аудитории",
        "frequency": 1,  # 1 раз в цикле
        "cta": "💬 Обсудить в боте → https://t.me/smart_analytics_mp_bot",
        "prompt_addition": """
ТИП ПОСТА: ИНТЕРАКТИВ (вовлечение аудитории)

Напиши пост с твоим мнением или вопросом:
- Твой взгляд на новость/изменение маркетплейса
- Спорное мнение (но обоснованное)
- Вопрос к аудитории в конце
- Призыв поделиться опытом

Формат: Новость/Факт → Твоё мнение → Вопрос аудитории
"""
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
