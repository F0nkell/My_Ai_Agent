"""
Agentic Investment OS — Celery & Tasks
Настройка очереди задач и периодических запусков.
"""

import asyncio
from celery import Celery
from celery.schedules import crontab
from loguru import logger

from src.config import get_settings
from src.database import async_session_factory
from src.pipeline.orchestrator import PipelineOrchestrator
from src.data_layer.news_collector import NewsCollector
from src.database.repositories.news import NewsRepository

settings = get_settings()

celery_app = Celery(
    "investment_os_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
)

# --- Периодические задачи ---
# Запуск сбора новостей каждый час
# Запуск пайплайна анализа каждые N часов
celery_app.conf.beat_schedule = {
    "collect-news-hourly": {
        "task": "src.pipeline.tasks.collect_news_task",
        "schedule": crontab(minute="0"),  # В начале каждого часа
    },
    "run-pipeline-periodic": {
        "task": "src.pipeline.tasks.run_pipeline_task",
        "schedule": crontab(minute="30", hour=f"*/{settings.pipeline_interval_hours}"),
    },
}

async def run_pipeline_async(run_id_str: str = None) -> None:
    """Асинхронная обертка для пайплайна."""
    import uuid
    from src.database.repositories.analysis import AnalysisRepository
    
    async with async_session_factory() as session:
        try:
            repo = AnalysisRepository(session)
            if run_id_str:
                run_id = uuid.UUID(run_id_str)
            else:
                run = await repo.create_run(trigger="scheduled")
                run_id = run.id
                await session.commit() # Сохраняем создание
                
            orchestrator = PipelineOrchestrator(session)
            await orchestrator.run(run_id)
            await session.commit()
        except Exception as e:
            logger.error(f"Task pipeline error: {e}")
            await session.rollback()

async def collect_news_async() -> None:
    """Асинхронная обертка для сбора новостей."""
    collector = NewsCollector()
    news = await collector.collect_all()
    
    async with async_session_factory() as session:
        repo = NewsRepository(session)
        count = 0
        for item in news:
            created = await repo.create(
                title=item["title"],
                source=item["source"],
                content=item["content"],
                category=item["category"],
                asset_symbols=item["asset_symbols"],
                importance_score=item["importance_score"],
                published_at=item["published_at"],
            )
            if created:
                 count += 1
        await session.commit()
        logger.info(f"Сохранено {count} новых новостей в БД")

@celery_app.task
def run_pipeline_task(run_id_str: str = None) -> None:
    """Task: Запуск главного пайплайна."""
    logger.info("Celery: начинаем анализ")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_pipeline_async(run_id_str))

@celery_app.task
def collect_news_task() -> None:
    """Task: Фоновый сбор новостей."""
    logger.info("Celery: сбор новостей")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(collect_news_async())
