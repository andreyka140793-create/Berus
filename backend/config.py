"""Конфиг Берусь!"""
from __future__ import annotations
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    webapp_url: str = os.getenv("WEBAPP_URL", "").rstrip("/")
    admin_ids: list[int]
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./berus.db")
    bot_username: str = os.getenv("BOT_USERNAME", "berus_bot")

    def __init__(self) -> None:
        raw = os.getenv("ADMIN_TELEGRAM_ID", "")
        ids: list[int] = []
        for part in raw.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        self.admin_ids = ids


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Стартовые справочники (потом — в БД/админке)
CITIES = [
    {"slug": "moscow", "name": "Москва"},
    {"slug": "spb", "name": "Санкт-Петербург"},
    {"slug": "kazan", "name": "Казань"},
    {"slug": "ekb", "name": "Екатеринбург"},
]

CATEGORIES = [
    {"slug": "cleaning", "name": "Клининг"},
    {"slug": "handyman", "name": "Мастер на час"},
    {"slug": "tutor", "name": "Репетитор"},
    {"slug": "beauty", "name": "Красота"},
    {"slug": "courier", "name": "Курьер / помощь"},
    {"slug": "repair", "name": "Мелкий ремонт"},
    {"slug": "photo", "name": "Фото / видео"},
    {"slug": "it", "name": "IT / компьютер"},
]
