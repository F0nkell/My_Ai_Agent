"""
Agentic Investment OS — API Dependencies
FastAPI Depends для инъекции зависимостей.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_factory
from src.database.repositories import (
    AssetRepository,
    NewsRepository,
    SignalRepository,
    AnalysisRepository,
    MemoryRepository,
)


async def get_session():
    """Генератор сессий БД для FastAPI."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_asset_repo(session: AsyncSession = None):
    """Инъекция AssetRepository."""
    async with async_session_factory() as session:
        yield AssetRepository(session)
        await session.commit()


async def get_analysis_repo(session: AsyncSession = None):
    """Инъекция AnalysisRepository."""
    async with async_session_factory() as session:
        yield AnalysisRepository(session)
        await session.commit()
