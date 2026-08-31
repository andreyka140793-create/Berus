"""Проверка Telegram WebApp initData (упрощённо для MVP)."""
from __future__ import annotations
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl
from config import get_settings


def validate_init_data(init_data: str, max_age_sec: int = 86400) -> dict | None:
    """Возвращает user dict или None. Для локальной отладки: init_data=dev:<telegram_id>."""
    if not init_data:
        return None
    if init_data.startswith("dev:"):
        try:
            tid = int(init_data.split(":", 1)[1])
            return {"id": tid, "username": "dev", "first_name": "Dev"}
        except ValueError:
            return None

    token = get_settings().telegram_bot_token
    if not token:
        return None

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        return None

    auth_date = int(parsed.get("auth_date", "0") or 0)
    if auth_date and time.time() - auth_date > max_age_sec:
        return None

    user_raw = parsed.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        return None
