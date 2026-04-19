"""
Agentic Investment OS — Thesis Memory
Тезисы по каждому активу. Обновляются агентом Thesis Analyst.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.database.repositories.memory import MemoryRepository


class ThesisMemoryManager:
    """Управление тезисами по активам."""

    DEFAULT_THESES = {
        "LKOH": {
            "thesis": "Тяжеловес. Рост + дивиденды. Бенефициар высоких цен на нефть.",
            "status": "intact",
            "established": "2026-01",
            "key_metrics": ["oil_price", "dividends", "buyback"],
            "avg_price": 5365.5,
        },
        "SBERP": {
            "thesis": "Ставка на рост экономики и кредитования. Выигрывает от снижения ставки ЦБ.",
            "status": "intact",
            "established": "2026-01",
            "key_metrics": ["cbr_rate", "credit_growth", "net_profit"],
            "avg_price": 324.3,
        },
        "SBER": {
            "thesis": "Крупнейший банк РФ. Те же драйверы что и Сбер-преф.",
            "status": "intact",
            "established": "2026-01",
            "key_metrics": ["cbr_rate", "net_profit"],
            "avg_price": 324.47,
        },
        "TATNP": {
            "thesis": "Дивидендный пулемёт. 3-4 выплаты в год. Стабильный кэш.",
            "status": "intact",
            "established": "2026-02",
            "key_metrics": ["dividends", "oil_price", "payout_ratio"],
            "avg_price": 577.6,
        },
        "SNGSP": {
            "thesis": "Валютная кубышка. Страховка от девальвации рубля к 2032.",
            "status": "intact",
            "established": "2026-01",
            "key_metrics": ["usd_rub", "cash_reserves", "dividends"],
            "avg_price": 42.925,
        },
        "GAZP": {
            "thesis": "Hold. Ждём восстановления экспорта газа в Европу/Азию.",
            "status": "weakening",
            "established": "2026-01",
            "key_metrics": ["gas_price", "exports", "geopolitics"],
            "avg_price": 125.69,
        },
        "OZON": {
            "thesis": "Hold. Ставка на рост e-commerce в РФ.",
            "status": "intact",
            "established": "2026-01",
            "key_metrics": ["gmv", "revenue_growth", "profitability"],
            "avg_price": 4365.5,
        },
        "MOEX": {
            "thesis": "Hold. Инфраструктурный бенефициар роста рынка.",
            "status": "intact",
            "established": "2026-01",
            "key_metrics": ["trading_volumes", "new_accounts", "fees"],
            "avg_price": 172.02,
        },
    }

    def __init__(self, repo: MemoryRepository = None):
        self.repo = repo

    async def get_all_theses(self) -> dict:
        """Получить все текущие тезисы."""
        if self.repo:
            db_theses = await self.repo.get_thesis()
            if db_theses:
                return {m.content.get("symbol", ""): m.content for m in db_theses}

        return self.DEFAULT_THESES

    async def get_thesis(self, symbol: str) -> dict:
        """Получить тезис по конкретному активу."""
        all_theses = await self.get_all_theses()
        return all_theses.get(symbol, {})

    async def update_thesis(
        self,
        symbol: str,
        status: str,
        updates: dict = None,
        asset_id: uuid.UUID = None,
    ) -> None:
        """Обновить тезис (вызывается Thesis Analyst)."""
        current = await self.get_thesis(symbol)
        if not current:
            current = {"thesis": "Unknown", "status": "unknown"}

        current["status"] = status
        current["last_updated"] = datetime.utcnow().isoformat()
        current["symbol"] = symbol
        if updates:
            current.update(updates)

        if self.repo:
            await self.repo.save(
                memory_type="thesis",
                content=current,
                asset_id=asset_id,
                category=f"thesis_{symbol}",
            )
            logger.info(f"📝 Тезис {symbol} обновлён: status={status}")

    def get_theses_compact(self) -> str:
        """Компактная версия тезисов для промпта."""
        lines = []
        for symbol, thesis in self.DEFAULT_THESES.items():
            lines.append(
                f"- {symbol}: {thesis['thesis']} [status: {thesis['status']}]"
            )
        return "\n".join(lines)
