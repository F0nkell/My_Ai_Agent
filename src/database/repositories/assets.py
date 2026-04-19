"""
Репозиторий для работы с активами и вотчлистом.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Asset, WatchlistItem


class AssetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_symbol(self, symbol: str) -> Optional[Asset]:
        """Получить актив по тикету."""
        result = await self.session.execute(
            select(Asset).where(Asset.symbol == symbol)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Asset]:
        """Получить все активы."""
        result = await self.session.execute(select(Asset))
        return list(result.scalars().all())

    async def create(
        self,
        symbol: str,
        name: str,
        asset_type: str,
        sector: str = None,
        exchange: str = "MOEX",
        metadata_json: dict = None,
    ) -> Asset:
        """Создать новый актив."""
        asset = Asset(
            symbol=symbol,
            name=name,
            asset_type=asset_type,
            sector=sector,
            exchange=exchange,
            metadata_json=metadata_json or {},
        )
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def upsert(
        self,
        symbol: str,
        name: str,
        asset_type: str,
        sector: str = None,
        exchange: str = "MOEX",
    ) -> Asset:
        """Создать или обновить актив."""
        existing = await self.get_by_symbol(symbol)
        if existing:
            existing.name = name
            existing.asset_type = asset_type
            existing.sector = sector or existing.sector
            existing.exchange = exchange
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            return existing
        return await self.create(symbol, name, asset_type, sector, exchange)

    # --- Watchlist ---

    async def get_watchlist(self, active_only: bool = True) -> list[WatchlistItem]:
        """Получить вотчлист."""
        query = select(WatchlistItem).join(Asset)
        if active_only:
            query = query.where(WatchlistItem.active.is_(True))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_watchlist_with_assets(self, active_only: bool = True) -> list[dict]:
        """Получить вотчлист с информацией об активах."""
        query = select(WatchlistItem, Asset).join(Asset)
        if active_only:
            query = query.where(WatchlistItem.active.is_(True))
        result = await self.session.execute(query)
        items = []
        for wi, asset in result.all():
            items.append({
                "watchlist_item": wi,
                "asset": asset,
            })
        return items

    async def add_to_watchlist(
        self,
        asset_id: uuid.UUID,
        priority: str = "core",
        shares_owned: int = 0,
        avg_buy_price: float = None,
        user_notes: dict = None,
    ) -> WatchlistItem:
        """Добавить актив в вотчлист."""
        item = WatchlistItem(
            asset_id=asset_id,
            priority=priority,
            shares_owned=shares_owned,
            avg_buy_price=avg_buy_price,
            user_notes=user_notes or {},
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_core_symbols(self) -> list[str]:
        """Получить тикеры core-активов."""
        result = await self.session.execute(
            select(Asset.symbol)
            .join(WatchlistItem)
            .where(
                WatchlistItem.active.is_(True),
                WatchlistItem.priority == "core",
            )
        )
        return [row[0] for row in result.all()]
