"""
Agentic Investment OS — Конфигурация
Все настройки загружаются из .env файла через Pydantic Settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Главный конфиг приложения."""

    # === Database ===
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="investor")
    postgres_password: str = Field(default="invest_os_2026")
    postgres_db: str = Field(default="investment_os")

    @property
    def database_url(self) -> str:
        """Синхронный URL для Alembic."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """Асинхронный URL для SQLAlchemy async."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # === Redis ===
    redis_url: str = Field(default="redis://localhost:6379/0")

    # === Telegram ===
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # === LLM ===
    llm_provider: str = Field(default="g4f")
    llm_model: str = Field(default="gpt-4o")
    llm_fallback_model: str = Field(default="gpt-4o-mini")

    # === Pipeline ===
    pipeline_interval_hours: int = Field(default=6)
    max_news_per_run: int = Field(default=50)
    analysis_depth_days: int = Field(default=7)

    # === Logging ===
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/investment_os.log")

    # === Watchlist по умолчанию (Русский Спринт 2026-2032) ===
    @property
    def default_watchlist(self) -> list[dict]:
        """Активы из портфеля пользователя Т-Инвестиции."""
        return [
            {
                "symbol": "LKOH",
                "name": "ЛУКОЙЛ",
                "asset_type": "stock",
                "sector": "oil_gas",
                "priority": "core",
                "shares": 4,
                "avg_price": 5365.5,
            },
            {
                "symbol": "SBERP",
                "name": "Сбер Банк - привилегированные",
                "asset_type": "stock",
                "sector": "finance",
                "priority": "core",
                "shares": 26,
                "avg_price": 324.3,
            },
            {
                "symbol": "SBER",
                "name": "Сбер Банк",
                "asset_type": "stock",
                "sector": "finance",
                "priority": "core",
                "shares": 13,
                "avg_price": 324.47,
            },
            {
                "symbol": "TATNP",
                "name": "Татнефть - привилегированные",
                "asset_type": "stock",
                "sector": "oil_gas",
                "priority": "core",
                "shares": 2,
                "avg_price": 577.6,
            },
            {
                "symbol": "SNGSP",
                "name": "Сургутнефтегаз - привилегированные",
                "asset_type": "stock",
                "sector": "oil_gas",
                "priority": "core",
                "shares": 180,
                "avg_price": 42.925,
            },
            {
                "symbol": "GAZP",
                "name": "Газпром",
                "asset_type": "stock",
                "sector": "oil_gas",
                "priority": "hold",
                "shares": 30,
                "avg_price": 125.69,
            },
            {
                "symbol": "OZON",
                "name": "Озон",
                "asset_type": "stock",
                "sector": "tech",
                "priority": "hold",
                "shares": 1,
                "avg_price": 4365.5,
            },
            {
                "symbol": "MOEX",
                "name": "ПАО Московская Биржа",
                "asset_type": "stock",
                "sector": "finance",
                "priority": "hold",
                "shares": 10,
                "avg_price": 172.02,
            },
        ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Синглтон для настроек."""
    return Settings()
