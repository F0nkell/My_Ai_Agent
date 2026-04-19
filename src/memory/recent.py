"""
Agentic Investment OS — Recent Context Memory
Контекст за последние 1-7 дней. НЕ отправляем всю историю в LLM.
"""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from src.database.repositories.memory import MemoryRepository


class RecentContextManager:
    """Управление недавним контекстом (последние 1-7 дней)."""

    def __init__(self, repo: MemoryRepository = None):
        self.repo = repo

    async def save_run_summary(self, run_summary: dict) -> None:
        """Сохранить краткое резюме прогона в recent memory."""
        if self.repo:
            await self.repo.save(
                memory_type="recent",
                content={
                    "type": "run_summary",
                    "timestamp": datetime.utcnow().isoformat(),
                    **run_summary,
                },
                valid_until=datetime.utcnow() + timedelta(days=7),
            )

    async def save_market_snapshot_summary(self, snapshot: dict) -> None:
        """Сохранить краткий снимок рыночных данных."""
        if self.repo:
            await self.repo.save(
                memory_type="recent",
                content={
                    "type": "market_snapshot",
                    "timestamp": datetime.utcnow().isoformat(),
                    **snapshot,
                },
                valid_until=datetime.utcnow() + timedelta(days=3),
            )

    async def save_key_event(self, event: dict) -> None:
        """Сохранить ключевое событие."""
        if self.repo:
            await self.repo.save(
                memory_type="recent",
                content={
                    "type": "key_event",
                    "timestamp": datetime.utcnow().isoformat(),
                    **event,
                },
                valid_until=datetime.utcnow() + timedelta(days=7),
            )

    async def get_recent_context(self, days: int = 7) -> list[dict]:
        """Получить контекст за последние N дней."""
        if self.repo:
            memories = await self.repo.get_recent_context(days)
            return [m.content for m in memories]
        return []

    async def build_context_window(self, days: int = 7) -> dict:
        """
        Построить окно контекста для агентов.
        Возвращает КОМПАКТНЫЙ контекст, а НЕ всю историю.
        """
        recent = await self.get_recent_context(days)

        # Группируем по типу
        run_summaries = [r for r in recent if r.get("type") == "run_summary"]
        market_snapshots = [r for r in recent if r.get("type") == "market_snapshot"]
        key_events = [r for r in recent if r.get("type") == "key_event"]

        return {
            "period_days": days,
            "last_runs": run_summaries[:3],  # Максимум 3 последних прогона
            "market_trend": market_snapshots[:2],  # Последние 2 снимка
            "key_events": key_events[:5],  # Максимум 5 событий
        }
