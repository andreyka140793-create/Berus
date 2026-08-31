"""Точка входа: FastAPI + aiogram polling."""
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import init_db
from api import router as api_router
from bot import get_bot, dp
from handlers.start import router as start_router
from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("berus")

ROOT = Path(__file__).resolve().parent
MINIAPP = ROOT.parent / "miniapp"


async def run_bot() -> None:
    bot = get_bot()
    if not bot:
        logger.warning("Bot disabled — no token")
        return
    dp.include_router(start_router)
    await dp.start_polling(bot)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(run_bot())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Берусь!", lifespan=lifespan)
app.include_router(api_router)

if MINIAPP.exists():
    app.mount("/assets", StaticFiles(directory=str(MINIAPP)), name="assets")

    @app.get("/app")
    async def miniapp_index():
        return FileResponse(MINIAPP / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "service": "berus"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
