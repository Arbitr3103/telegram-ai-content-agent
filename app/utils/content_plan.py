"""
Модуль для работы с контент-планом.
Загружает план из YAML и предоставляет посты по датам.
"""
import yaml
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class PlannedPost:
    """Запланированный пост из контент-плана."""
    date: date
    type: str
    topic: str
    keywords: list[str]
    structure: Optional[str] = None
    tags: Optional[list[str]] = None
    include_poll: bool = False
    poll_question: Optional[str] = None
    poll_options: Optional[list[str]] = None
    facts: Optional[list[str]] = None


class ContentPlan:
    """Менеджер контент-плана."""

    def __init__(self, plan_path: Optional[Path] = None):
        if plan_path is None:
            plan_path = Path(__file__).parent.parent.parent / "data" / "content_plan.yaml"
        self.plan_path = plan_path
        self._posts: list[PlannedPost] = []
        self._load()

    def _load(self) -> None:
        """Загрузить план из YAML файла."""
        if not self.plan_path.exists():
            return

        with open(self.plan_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data or 'posts' not in data:
            return

        for post_data in data['posts']:
            post_date = post_data['date']
            if isinstance(post_date, str):
                post_date = datetime.strptime(post_date, '%Y-%m-%d').date()

            self._posts.append(PlannedPost(
                date=post_date,
                type=post_data['type'],
                topic=post_data['topic'],
                keywords=post_data.get('keywords', []),
                structure=post_data.get('structure'),
                tags=post_data.get('tags'),
                include_poll=post_data.get('include_poll', False),
                poll_question=post_data.get('poll_question'),
                poll_options=post_data.get('poll_options'),
                facts=post_data.get('facts'),
            ))

    def get_post_for_date(self, target_date: Optional[date] = None) -> Optional[PlannedPost]:
        """Получить пост для указанной даты."""
        if target_date is None:
            target_date = date.today()

        for post in self._posts:
            if post.date == target_date:
                return post
        return None

    def get_next_post(self, after_date: Optional[date] = None) -> Optional[PlannedPost]:
        """Получить следующий запланированный пост после указанной даты."""
        if after_date is None:
            after_date = date.today()

        future_posts = [p for p in self._posts if p.date > after_date]
        if not future_posts:
            return None

        return min(future_posts, key=lambda p: p.date)

    def get_all_posts(self) -> list[PlannedPost]:
        """Получить все посты из плана."""
        return self._posts.copy()

    def has_post_for_today(self) -> bool:
        """Проверить, есть ли пост на сегодня."""
        return self.get_post_for_date() is not None


# Глобальный экземпляр для удобства
_content_plan: Optional[ContentPlan] = None


def get_content_plan() -> ContentPlan:
    """Получить глобальный экземпляр контент-плана."""
    global _content_plan
    if _content_plan is None:
        _content_plan = ContentPlan()
    return _content_plan


def get_todays_post() -> Optional[PlannedPost]:
    """Shortcut: получить пост на сегодня."""
    return get_content_plan().get_post_for_date()
