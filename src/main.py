"""
Agentic Investment OS — FastAPI Application
Главная точка входа.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения."""
    logger.info("🚀 Agentic Investment OS запускается...")
    logger.info(f"📊 Вотчлист: {[a['symbol'] for a in settings.default_watchlist]}")
    yield
    logger.info("🛑 Agentic Investment OS останавливается...")


app = FastAPI(
    title="Agentic Investment OS",
    description=(
        "Многоагентная система принятия инвестиционных решений. "
        "Стратегия «Русский Спринт 2026-2032»."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def healthcheck():
    """Проверка здоровья сервиса."""
    return {
        "status": "ok",
        "service": "Agentic Investment OS",
        "version": "1.0.0",
    }


# Импорт роутов
from src.api.routes import router as api_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
