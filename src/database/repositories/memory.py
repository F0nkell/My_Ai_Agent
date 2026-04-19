"""
Репозиторий для системы памяти (3 уровня).
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import InvestmentMemory


class MemoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        memory_type: str,
        content: dict,
        asset_id: uuid.UUID = None,
        category: str = None,
        valid_until: datetime = None,
    ) -> InvestmentMemory:
        """Сохранить запись в память."""
        # Деактивируем предыдущую версию (если есть)
        if asset_id and category:
            await self.session.execute(
                update(InvestmentMemory)
                .where(
                    InvestmentMemory.memory_type == memory_type,
                    InvestmentMemory.asset_id == asset_id,
                    InvestmentMemory.category == category,
                    InvestmentMemory.is_active.is_(True),
                )
                .values(is_active=False, valid_until=datetime.utcnow())
            )

        memory = InvestmentMemory(
            memory_type=memory_type,
            asset_id=asset_id,
            category=category,
            content=content,
            valid_until=valid_until,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get_permanent(self) -> list[InvestmentMemory]:
        """Получить все постоянные правила и предпочтения."""
        result = await self.session.execute(
            select(InvestmentMemory)
            .where(
                InvestmentMemory.memory_type == "permanent",
                InvestmentMemory.is_active.is_(True),
            )
            .order_by(InvestmentMemory.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_thesis(
        self, asset_id: uuid.UUID = None
    ) -> list[InvestmentMemory]:
        """Получить текущие тезисы (по активу или все)."""
        query = select(InvestmentMemory).where(
            InvestmentMemory.memory_type == "thesis",
            InvestmentMemory.is_active.is_(True),
        )
        if asset_id:
            query = query.where(InvestmentMemory.asset_id == asset_id)
        result = await self.session.execute(
            query.order_by(InvestmentMemory.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_recent_context(self, days: int = 7) -> list[InvestmentMemory]:
        """Получить недавний контекст (последние N дней)."""
        since = datetime.utcnow() - timedelta(days=days)
        result = await self.session.execute(
            select(InvestmentMemory)
            .where(
                InvestmentMemory.memory_type == "recent",
                InvestmentMemory.is_active.is_(True),
                InvestmentMemory.created_at >= since,
            )
            .order_by(InvestmentMemory.created_at.desc())
        )
        return list(result.scalars().all())

    async def build_context_for_agent(
        self,
        asset_id: uuid.UUID = None,
        recent_days: int = 7,
    ) -> dict:
        """Собрать контекст памяти для агента (НЕ всю историю!)."""
        permanent = await self.get_permanent()
        thesis = await self.get_thesis(asset_id)
        recent = await self.get_recent_context(recent_days)

        return {
            "permanent_rules": [m.content for m in permanent],
            "thesis": [m.content for m in thesis],
            "recent_context": [m.content for m in recent[:10]],  # Максимум 10
        }
