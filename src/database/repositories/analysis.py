"""
Репозиторий для analysis_runs, agent_outputs, chief_recommendations, feedback.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    AnalysisRun, AgentOutput, ChiefRecommendation, Feedback
)


class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Analysis Runs ---

    async def create_run(
        self,
        trigger: str = "scheduled",
        prompt_version: str = "v1.0",
    ) -> AnalysisRun:
        """Создать новый прогон анализа."""
        run = AnalysisRun(
            status="pending",
            trigger=trigger,
            prompt_version=prompt_version,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def update_run_status(
        self,
        run_id: uuid.UUID,
        status: str,
        error_message: str = None,
        model_used: str = None,
        total_tokens: int = None,
    ) -> None:
        """Обновить статус прогона."""
        values = {"status": status}
        if status in ("completed", "failed"):
            values["completed_at"] = datetime.utcnow()
        if error_message:
            values["error_message"] = error_message
        if model_used:
            values["model_used"] = model_used
        if total_tokens:
            values["total_tokens_used"] = total_tokens

        await self.session.execute(
            update(AnalysisRun).where(AnalysisRun.id == run_id).values(**values)
        )
        await self.session.flush()

    async def set_plan(self, run_id: uuid.UUID, plan: dict) -> None:
        """Сохранить план от Chief Planner."""
        await self.session.execute(
            update(AnalysisRun).where(AnalysisRun.id == run_id).values(
                plan=plan, status="planning"
            )
        )
        await self.session.flush()

    async def get_run(self, run_id: uuid.UUID) -> Optional[AnalysisRun]:
        """Получить прогон по ID."""
        result = await self.session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def get_recent_runs(self, limit: int = 10) -> list[AnalysisRun]:
        """Получить последние прогоны."""
        result = await self.session.execute(
            select(AnalysisRun)
            .order_by(AnalysisRun.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # --- Agent Outputs ---

    async def save_agent_output(
        self,
        run_id: uuid.UUID,
        agent_name: str,
        output: dict,
        confidence: float = 0.5,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        model_used: str = None,
        prompt_hash: str = None,
    ) -> AgentOutput:
        """Сохранить выход агента."""
        agent_output = AgentOutput(
            run_id=run_id,
            agent_name=agent_name,
            output=output,
            confidence=confidence,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            model_used=model_used,
            prompt_hash=prompt_hash,
        )
        self.session.add(agent_output)
        await self.session.flush()
        return agent_output

    async def get_outputs_for_run(self, run_id: uuid.UUID) -> list[AgentOutput]:
        """Получить все выходы агентов для прогона."""
        result = await self.session.execute(
            select(AgentOutput).where(AgentOutput.run_id == run_id)
        )
        return list(result.scalars().all())

    # --- Chief Recommendations ---

    async def save_recommendation(
        self,
        run_id: uuid.UUID,
        asset_symbol: str,
        action: str,
        reasoning: dict,
        risks: dict = None,
        triggers: dict = None,
        confidence: float = 0.5,
        priority: int = 5,
        target_price: float = None,
        stop_loss: float = None,
        time_horizon: str = None,
    ) -> ChiefRecommendation:
        """Сохранить рекомендацию."""
        rec = ChiefRecommendation(
            run_id=run_id,
            asset_symbol=asset_symbol,
            action=action,
            reasoning=reasoning,
            risks=risks or {},
            triggers=triggers or {},
            confidence=confidence,
            priority=priority,
            target_price=target_price,
            stop_loss=stop_loss,
            time_horizon=time_horizon,
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def get_latest_recommendations(
        self, limit: int = 20
    ) -> list[ChiefRecommendation]:
        """Получить последние рекомендации."""
        result = await self.session.execute(
            select(ChiefRecommendation)
            .order_by(ChiefRecommendation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_sent_to_telegram(self, rec_id: uuid.UUID) -> None:
        """Отметить что рекомендация отправлена в Telegram."""
        await self.session.execute(
            update(ChiefRecommendation)
            .where(ChiefRecommendation.id == rec_id)
            .values(sent_to_telegram=True)
        )
        await self.session.flush()

    # --- Feedback ---

    async def save_feedback(
        self,
        recommendation_id: uuid.UUID,
        price_at_recommendation: float = None,
        price_at_evaluation: float = None,
        actual_return_percent: float = None,
        was_correct: bool = None,
        evaluation_period_days: int = 7,
        notes: dict = None,
    ) -> Feedback:
        """Сохранить обратную связь по рекомендации."""
        fb = Feedback(
            recommendation_id=recommendation_id,
            price_at_recommendation=price_at_recommendation,
            price_at_evaluation=price_at_evaluation,
            actual_return_percent=actual_return_percent,
            was_correct=was_correct,
            evaluation_period_days=evaluation_period_days,
            notes=notes or {},
        )
        self.session.add(fb)
        await self.session.flush()
        return fb
