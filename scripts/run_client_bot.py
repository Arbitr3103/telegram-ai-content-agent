#!/usr/bin/env python3
"""
Скрипт запуска клиентского бота
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.client_bot.bot import run_client_bot


def main():
    """Точка входа"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/client_bot.log")
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Client Bot...")

    try:
        asyncio.run(run_client_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise


if __name__ == "__main__":
    main()
