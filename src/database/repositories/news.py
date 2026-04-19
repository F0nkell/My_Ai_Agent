"""
Репозиторий для работы с новостями.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import NewsItem


class NewsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def compute_hash(title: str, source: str) -> str:
        """Вычислить хеш для дедупликации."""
        raw = f"{title.strip().lower()}|{source.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def exists_by_hash(self, content_hash: str) -> bool:
        """Проверить существует ли новость (дедупликация)."""
        result = await self.session.execute(
            select(func.count()).where(NewsItem.content_hash == content_hash)
        )
        return result.scalar() > 0

    async def create(
        self,
        title: str,
        source: str,
        content: str = None,
        summary: str = None,
        url: str = None,
        importance_score: float = 0.0,
        sentiment_score: float = None,
        entities: dict = None,
        asset_symbols: list = None,
        category: str = None,
        published_at: datetime = None,
    ) -> Optional[NewsItem]:
        """Создать новость (с проверкой дупликатов)."""
        content_hash = self.compute_hash(title, source)

        if await self.exists_by_hash(content_hash):
            return None  # Дупликат

        news = NewsItem(
            title=title,
            content=content,
            summary=summary,
            source=source,
            url=url,
            content_hash=content_hash,
            importance_score=importance_score,
            sentiment_score=sentiment_score,
            entities=entities or {},
            asset_symbols=asset_symbols or [],
            category=category,
            published_at=published_at or datetime.utcnow(),
        )
        self.session.add(news)
        await self.session.flush()
        return news

    async def get_recent(
        self,
        days: int = 7,
        limit: int = 50,
        min_importance: float = 0.0,
        symbols: list[str] = None,
    ) -> list[NewsItem]:
        """Получить недавние новости с фильтрацией."""
        since = datetime.utcnow() - timedelta(days=days)
        query = (
            select(NewsItem)
            .where(
                NewsItem.published_at >= since,
                NewsItem.importance_score >= min_importance,
            )
            .order_by(NewsItem.importance_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        # Фильтрация по символам (если указаны)
        if symbols:
            filtered = []
            for item in items:
                if item.asset_symbols:
                    if any(s in item.asset_symbols for s in symbols):
                        filtered.append(item)
                else:
                    filtered.append(item)  # Общие новости тоже включаем
            return filtered
        return items

    async def get_unprocessed(self, limit: int = 100) -> list[NewsItem]:
        """Получить необработанные новости."""
        result = await self.session.execute(
            select(NewsItem)
            .where(NewsItem.processed.is_(False))
            .order_by(NewsItem.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processed(self, news_id) -> None:
        """Отметить новость как обработанную."""
        result = await self.session.execute(
            select(NewsItem).where(NewsItem.id == news_id)
        )
        news = result.scalar_one_or_none()
        if news:
            news.processed = True
            await self.session.flush()
