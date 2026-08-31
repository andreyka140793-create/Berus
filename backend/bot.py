"""Telegram bot instance."""
import logging
from aiogram import Bot, Dispatcher
from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
dp = Dispatcher()


def get_bot() -> Bot | None:
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set")
        return None
    return Bot(token=settings.telegram_bot_token)
