"""Клавиатуры бота Берусь!"""
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)
from config import get_settings


def main_kb(is_performer: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📱 Открыть Берусь!")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def webapp_kb() -> InlineKeyboardMarkup:
    url = get_settings().webapp_url
    if not url:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ WEBAPP_URL не задан", callback_data="noop")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=url))],
    ])
