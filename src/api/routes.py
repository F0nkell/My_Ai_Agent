"""
Agentic Investment OS — REST API Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.database.repositories import AssetRepository, AnalysisRepository
from src.config import get_settings

router = APIRouter(tags=["Investment OS"])
settings = get_settings()


@router.get("/watchlist")
async def get_watchlist(session: AsyncSession = Depends(get_session)):
    """Получить текущий вотчлист."""
    repo = AssetRepository(session)
    items = await repo.get_watchlist_with_assets()
    return {
        "count": len(items),
        "items": [
            {
                "symbol": item["asset"].symbol,
                "name": item["asset"].name,
                "sector": item["asset"].sector,
                "priority": item["watchlist_item"].priority,
                "shares_owned": item["watchlist_item"].shares_owned,
                "avg_buy_price": item["watchlist_item"].avg_buy_price,
            }
            for item in items
        ],
    }


@router.get("/runs")
async def get_recent_runs(
    limit: int = 10,
    session: AsyncSession = Depends(get_session),
):
    """Получить последние прогоны анализа."""
    repo = AnalysisRepository(session)
    runs = await repo.get_recent_runs(limit)
    return {
        "count": len(runs),
        "runs": [
            {
                "id": str(run.id),
                "status": run.status,
                "trigger": run.trigger,
                "model_used": run.model_used,
                "tokens_used": run.total_tokens_used,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            }
            for run in runs
        ],
    }


@router.get("/recommendations")
async def get_recommendations(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    """Получить последние рекомендации."""
    repo = AnalysisRepository(session)
    recs = await repo.get_latest_recommendations(limit)
    return {
        "count": len(recs),
        "recommendations": [
            {
                "id": str(rec.id),
                "asset": rec.asset_symbol,
                "action": rec.action,
                "confidence": rec.confidence,
                "priority": rec.priority,
                "reasoning": rec.reasoning,
                "risks": rec.risks,
                "target_price": rec.target_price,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            }
            for rec in recs
        ],
    }


@router.post("/pipeline/run")
async def trigger_pipeline(session: AsyncSession = Depends(get_session)):
    """Ручной запуск пайплайна анализа."""
    repo = AnalysisRepository(session)
    run = await repo.create_run(trigger="manual")
    # TODO: Запуск Celery задачи
    return {
        "message": "Пайплайн запущен",
        "run_id": str(run.id),
        "status": run.status,
    }


@router.get("/portfolio")
async def get_portfolio():
    """Получить конфигурацию портфеля (из настроек)."""
    watchlist = settings.default_watchlist
    total_value = sum(
        a["shares"] * a["avg_price"] for a in watchlist
    )
    return {
        "total_value_rub": round(total_value, 2),
        "strategy": "Русский Спринт 2026-2032",
        "core_assets": [a for a in watchlist if a["priority"] == "core"],
        "hold_assets": [a for a in watchlist if a["priority"] == "hold"],
    }
