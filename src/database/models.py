"""
Agentic Investment OS — Модели базы данных
10 таблиц: assets, watchlist_items, news_items, market_snapshots,
signals, analysis_runs, agent_outputs, chief_recommendations,
investment_memory, feedback
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String, Text, Float, Integer, BigInteger, Boolean,
    DateTime, Date, ForeignKey, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base


# ============================================================
# 1. ASSETS — Активы (акции, облигации, крипта)
# ============================================================
class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)  # stock, bond, crypto
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    exchange: Mapped[str] = mapped_column(String(20), default="MOEX")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(back_populates="asset")
    market_snapshots: Mapped[list["MarketSnapshot"]] = relationship(back_populates="asset")
    signals: Mapped[list["Signal"]] = relationship(back_populates="asset")
    memories: Mapped[list["InvestmentMemory"]] = relationship(back_populates="asset")


# ============================================================
# 2. WATCHLIST_ITEMS — Вотчлист (отслеживаемые активы)
# ============================================================
class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="core"  # core, hold, watch
    )
    shares_owned: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    avg_buy_price: Mapped[Optional[float]] = mapped_column(Float)
    user_notes: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="watchlist_items")


# ============================================================
# 3. NEWS_ITEMS — Новости
# ============================================================
class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    content_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )  # SHA-256 для дедупликации
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    entities: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    asset_symbols: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    category: Mapped[Optional[str]] = mapped_column(String(50))  # macro, company, sector
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_news_published", "published_at"),
        Index("ix_news_importance", "importance_score"),
    )


# ============================================================
# 4. MARKET_SNAPSHOTS — Снимки рыночных данных
# ============================================================
class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    open_price: Mapped[Optional[float]] = mapped_column(Float)
    close_price: Mapped[Optional[float]] = mapped_column(Float)
    high: Mapped[Optional[float]] = mapped_column(Float)
    low: Mapped[Optional[float]] = mapped_column(Float)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    change_percent: Mapped[Optional[float]] = mapped_column(Float)
    indicators: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    # indicators: {sma_20, sma_50, ema_12, ema_26, rsi_14, macd, bollinger_upper, ...}
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="market_snapshots")

    __table_args__ = (
        Index("ix_snapshot_asset_date", "asset_id", "snapshot_date", unique=True),
    )


# ============================================================
# 5. SIGNALS — Вычисленные сигналы (заменяет ретрейнинг модели)
# ============================================================
class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    signal_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # sentiment, volatility, volume_anomaly, trend, event_impact
    value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    direction: Mapped[Optional[str]] = mapped_column(String(10))  # bullish, bearish, neutral
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # Корректируемый вес
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    asset: Mapped["Asset"] = relationship(back_populates="signals")

    __table_args__ = (
        Index("ix_signal_asset_type", "asset_id", "signal_type"),
        Index("ix_signal_computed", "computed_at"),
    )


# ============================================================
# 6. ANALYSIS_RUNS — Прогоны анализа
# ============================================================
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, planning, running, completed, failed
    plan: Mapped[Optional[dict]] = mapped_column(JSON)  # План от Chief Planner
    trigger: Mapped[str] = mapped_column(
        String(50), default="scheduled"
    )  # scheduled, manual, alert
    prompt_version: Mapped[str] = mapped_column(String(20), default="v1.0")
    model_used: Mapped[Optional[str]] = mapped_column(String(50))
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    agent_outputs: Mapped[list["AgentOutput"]] = relationship(back_populates="run")
    recommendations: Mapped[list["ChiefRecommendation"]] = relationship(back_populates="run")


# ============================================================
# 7. AGENT_OUTPUTS — Выходы агентов
# ============================================================
class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # chief_planner, news_analyst, market_analyst, thesis_analyst, chief_investor
    output: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    model_used: Mapped[Optional[str]] = mapped_column(String(50))
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    run: Mapped["AnalysisRun"] = relationship(back_populates="agent_outputs")

    __table_args__ = (
        Index("ix_agent_output_run", "run_id", "agent_name"),
    )


# ============================================================
# 8. CHIEF_RECOMMENDATIONS — Рекомендации Chief Investor
# ============================================================
class ChiefRecommendation(Base):
    __tablename__ = "chief_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    asset_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # buy, sell, hold, accumulate, reduce
    reasoning: Mapped[dict] = mapped_column(JSON, nullable=False)
    risks: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    triggers: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10
    target_price: Mapped[Optional[float]] = mapped_column(Float)
    stop_loss: Mapped[Optional[float]] = mapped_column(Float)
    time_horizon: Mapped[Optional[str]] = mapped_column(String(50))
    sent_to_telegram: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    run: Mapped["AnalysisRun"] = relationship(back_populates="recommendations")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="recommendation")


# ============================================================
# 9. INVESTMENT_MEMORY — Память (3 уровня)
# ============================================================
class InvestmentMemory(Base):
    __tablename__ = "investment_memory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True
    )
    memory_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # permanent, thesis, recent
    category: Mapped[Optional[str]] = mapped_column(String(50))
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    valid_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    asset: Mapped[Optional["Asset"]] = relationship(back_populates="memories")

    __table_args__ = (
        Index("ix_memory_type_asset", "memory_type", "asset_id"),
        Index("ix_memory_active", "is_active"),
    )


# ============================================================
# 10. FEEDBACK — Обратная связь (рекомендация vs результат)
# ============================================================
class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chief_recommendations.id"), nullable=False
    )
    price_at_recommendation: Mapped[Optional[float]] = mapped_column(Float)
    price_at_evaluation: Mapped[Optional[float]] = mapped_column(Float)
    actual_return_percent: Mapped[Optional[float]] = mapped_column(Float)
    was_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    evaluation_period_days: Mapped[int] = mapped_column(Integer, default=7)
    notes: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    recommendation: Mapped["ChiefRecommendation"] = relationship(back_populates="feedback")


# ============================================================
# 11. WEB_CHAT_SESSIONS — ChatGPT Plus чаты агентов
# ============================================================
class WebChatSession(Base):
    """
    Хранит URL конкретного чата ChatGPT Plus для каждого агента.
    Системный промпт агента отправляется один раз при создании чата,
    далее бот пишет в этот чат только данные (user prompt).
    """
    __tablename__ = "web_chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    # URL вида https://chatgpt.com/c/<uuid>
    chat_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_web_chat_sessions_agent", "agent_name"),
    )
