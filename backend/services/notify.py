"""Уведомления в Telegram."""
from __future__ import annotations
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from config import CITIES, CATEGORIES

logger = logging.getLogger(__name__)

_bot: Bot | None = None


def set_bot(bot: Bot | None) -> None:
    global _bot
    _bot = bot


def get_bot() -> Bot | None:
    return _bot


def _city_name(slug: str) -> str:
    for c in CITIES:
        if c["slug"] == slug:
            return c["name"]
    return slug


def _cat_name(slug: str) -> str:
    for c in CATEGORIES:
        if c["slug"] == slug:
            return c["name"]
    return slug


async def send_text(telegram_id: int, text: str) -> bool:
    bot = _bot
    if not bot:
        logger.warning("notify: bot not set")
        return False
    try:
        await bot.send_message(telegram_id, text)
        return True
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.info("notify fail %s: %s", telegram_id, e)
        return False
    except Exception as e:
        logger.warning("notify error %s: %s", telegram_id, e)
        return False


async def notify_new_order(order, performer_telegram_ids: list[int]) -> int:
    """Новая заявка → исполнителям того же города."""
    budget = f"\nБюджет: до {order.budget} ₽" if order.budget else ""
    text = (
        "🆕 Новая заявка в вашем городе\n\n"
        f"«{order.title}»\n"
        f"{_city_name(order.city_slug)} · {_cat_name(order.category_slug)}"
        f"{budget}\n\n"
        f"{order.description[:400]}\n\n"
        "Откройте Берусь! → Лента, чтобы откликнуться бесплатно."
    )
    ok = 0
    for tid in performer_telegram_ids:
        if await send_text(tid, text):
            ok += 1
    return ok


async def notify_new_bid(customer_telegram_id: int, order_title: str, performer_name: str, message: str, price: int | None) -> bool:
    """Новый отклик → заказчику."""
    price_line = f"\nЦена: {price} ₽" if price else ""
    text = (
        "💬 Новый отклик на вашу заявку\n\n"
        f"Заявка: «{order_title}»\n"
        f"От: {performer_name}"
        f"{price_line}\n\n"
        f"{message[:500]}\n\n"
        "Откройте Берусь! → Мои, чтобы посмотреть все отклики."
    )
    return await send_text(customer_telegram_id, text)
