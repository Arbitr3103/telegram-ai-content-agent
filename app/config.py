"""
Конфигурация приложения
Загружает переменные окружения из .env файла
"""
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Anthropic API
    anthropic_api_key: str
    claude_model: str = "claude-3-haiku-20240307"
    claude_temperature: float = 0.7
    claude_max_tokens: int = 2000

    # Proxy для обхода гео-блокировок
    proxy_url: str | None = None

    # Telegram Bot
    telegram_bot_token: str
    telegram_channel_id: str
    telegram_admin_id: int

    # Telegram API для парсинга
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None

    # Database
    database_url: str

    # Exa API
    exa_api_key: str | None = None

    # Sentry
    sentry_dsn: str | None = None

    # Scheduler Settings
    parse_schedule_hours: str = "8,20"
    post_generation_days: str = "mon,wed,fri"
    post_generation_hour: int = 10
    publish_delay_minutes: int = 60

    # Content Settings
    min_relevance_score: float = 0.7
    max_post_length: int = 800
    min_post_length: int = 400

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    # Paths
    base_dir: Path = Path(__file__).parent.parent

    @property
    def parse_hours(self) -> List[int]:
        """Часы для парсинга источников"""
        return [int(h.strip()) for h in self.parse_schedule_hours.split(',')]

    @property
    def generation_days(self) -> List[str]:
        """Дни для генерации постов"""
        return [d.strip() for d in self.post_generation_days.split(',')]

    def ensure_directories(self):
        """Создать необходимые директории"""
        logs_dir = self.base_dir / "logs"
        logs_dir.mkdir(exist_ok=True)


# Глобальный экземпляр настроек
settings = Settings()
settings.ensure_directories()
