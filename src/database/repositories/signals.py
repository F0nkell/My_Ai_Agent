"""
Репозиторий для работы с сигналами.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Signal


class SignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        asset_id: uuid.UUID,
        signal_type: str,
        value: float,
        confidence: float = 0.5,
        direction: str = None,
        weight: float = 1.0,
        metadata_json: dict = None,
    ) -> Signal:
        """Создать новый сигнал."""
        signal = Signal(
            asset_id=asset_id,
            signal_type=signal_type,
            value=value,
            confidence=confidence,
            direction=direction,
            weight=weight,
            metadata_json=metadata_json or {},
        )
        self.session.add(signal)
        await self.session.flush()
        return signal

    async def get_latest_by_asset(
        self,
        asset_id: uuid.UUID,
        signal_types: list[str] = None,
        limit: int = 20,
    ) -> list[Signal]:
        """Получить последние сигналы по активу."""
        query = (
            select(Signal)
            .where(Signal.asset_id == asset_id)
            .order_by(Signal.computed_at.desc())
            .limit(limit)
        )
        if signal_types:
            query = query.where(Signal.signal_type.in_(signal_types))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_aggregated_score(
        self,
        asset_id: uuid.UUID,
        hours: int = 24,
    ) -> dict:
        """Получить взвешенный агрегированный скор по активу."""
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await self.session.execute(
            select(Signal)
            .where(
                Signal.asset_id == asset_id,
                Signal.computed_at >= since,
            )
        )
        signals = list(result.scalars().all())

        if not signals:
            return {"score": 0.0, "direction": "neutral", "signals_count": 0}

        total_weight = sum(s.weight for s in signals)
        if total_weight == 0:
            return {"score": 0.0, "direction": "neutral", "signals_count": len(signals)}

        weighted_score = sum(s.value * s.weight for s in signals) / total_weight

        direction = "neutral"
        if weighted_score > 0.2:
            direction = "bullish"
        elif weighted_score < -0.2:
            direction = "bearish"

        return {
            "score": round(weighted_score, 4),
            "direction": direction,
            "signals_count": len(signals),
            "by_type": {
                s.signal_type: {"value": s.value, "confidence": s.confidence}
                for s in signals
            },
        }

    async def update_weight(
        self,
        signal_type: str,
        asset_id: uuid.UUID,
        new_weight: float,
    ) -> None:
        """Обновить вес сигнала (для Learning системы)."""
        await self.session.execute(
            update(Signal)
            .where(
                Signal.signal_type == signal_type,
                Signal.asset_id == asset_id,
            )
            .values(weight=new_weight)
        )
        await self.session.flush()
