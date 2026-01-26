"""
Главный модуль клиентского бота
"""
import logging

from telegram.ext import Application

from app.config import settings
from app.client_bot.handlers.start import get_start_handlers
from app.client_bot.handlers.calculator import get_calculator_handler
from app.client_bot.handlers.faq import get_faq_handler, get_faq_direct_handlers
from app.client_bot.handlers.audit import get_audit_handler
from app.client_bot.handlers.application import get_application_handler
from app.client_bot.handlers.contact import get_contact_handler

logger = logging.getLogger(__name__)


def create_client_bot_application() -> Application:
    """
    Создать и настроить приложение клиентского бота

    Returns:
        Настроенное приложение Telegram бота
    """
    token = settings.telegram_client_bot_token

    if not token:
        raise ValueError("TELEGRAM_CLIENT_BOT_TOKEN не задан в .env")

    application = Application.builder().token(token).build()

    # ConversationHandlers (порядок важен!)
    application.add_handler(get_calculator_handler())
    application.add_handler(get_faq_handler())
    application.add_handler(get_audit_handler())
    application.add_handler(get_application_handler())
    application.add_handler(get_contact_handler())

    # Простые handlers
    for handler in get_start_handlers():
        application.add_handler(handler)

    for handler in get_faq_direct_handlers():
        application.add_handler(handler)

    logger.info("Client bot application created")

    return application


async def run_client_bot() -> None:
    """Запустить клиентского бота"""
    application = create_client_bot_application()

    logger.info("Starting client bot...")

    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)

    logger.info("Client bot is running")

    import asyncio
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(run_client_bot())
