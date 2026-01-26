"""
AI-ответчик для FAQ (Claude API)
"""
import logging
from typing import Optional

import httpx
from anthropic import Anthropic

from app.config import settings
from app.client_bot.texts.messages import (
    FAQ_COST, FAQ_TIMELINE, FAQ_MARKETPLACES,
    FAQ_TECHNICAL, FAQ_FREE_TRIAL, FAQ_OFF_TOPIC
)

logger = logging.getLogger(__name__)

# База знаний для AI
FAQ_KNOWLEDGE_BASE = f"""
Ты — помощник сервиса "Умная аналитика для маркетплейсов".
Владимир — специалист по аналитике и автоматизации для Ozon, Wildberries, Яндекс.Маркет.

ИНФОРМАЦИЯ ОБ УСЛУГАХ:

Стоимость:
{FAQ_COST}

Сроки:
{FAQ_TIMELINE}

Маркетплейсы:
{FAQ_MARKETPLACES}

Техническая реализация:
{FAQ_TECHNICAL}

Бесплатный тест:
{FAQ_FREE_TRIAL}

ПРАВИЛА ОТВЕТОВ:
- Отвечай кратко и по делу (2-4 предложения)
- Используй "вы" (формальный стиль)
- Если вопрос не про маркетплейсы/аналитику — вежливо откажись
- Не придумывай информацию, которой нет в базе знаний
- В конце можешь предложить оставить заявку для детального обсуждения
"""


class AIResponder:
    """AI-ответчик на вопросы пользователей"""

    def __init__(self):
        """Инициализация с proxy для Claude API"""
        proxy_url = settings.proxy_url
        if proxy_url:
            http_client = httpx.Client(proxy=proxy_url, timeout=60.0)
        else:
            http_client = httpx.Client(timeout=60.0)

        self.client = Anthropic(
            api_key=settings.anthropic_api_key,
            http_client=http_client
        )
        self.model = settings.claude_model

    async def answer_question(self, question: str) -> str:
        """
        Ответить на вопрос пользователя

        Args:
            question: Вопрос пользователя

        Returns:
            Ответ на вопрос
        """
        if self._is_off_topic(question):
            return FAQ_OFF_TOPIC

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                system=FAQ_KNOWLEDGE_BASE,
                messages=[
                    {"role": "user", "content": question}
                ]
            )

            answer = response.content[0].text.strip()
            logger.info(f"AI answered question: {question[:50]}...")

            return answer

        except Exception as e:
            logger.error(f"AI error: {e}")
            return "К сожалению, не смог обработать ваш вопрос. Попробуйте переформулировать или оставьте заявку."

    def _is_off_topic(self, question: str) -> bool:
        """Проверка на офф-топик"""
        off_topic_keywords = [
            "погода", "новости", "политика", "спорт",
            "рецепт", "фильм", "музыка", "игра",
            "знакомств", "отношени", "шутк", "анекдот"
        ]

        question_lower = question.lower()
        return any(kw in question_lower for kw in off_topic_keywords)


_ai_responder: Optional[AIResponder] = None


def get_ai_responder() -> AIResponder:
    """Получить экземпляр AI-ответчика"""
    global _ai_responder
    if _ai_responder is None:
        _ai_responder = AIResponder()
    return _ai_responder
