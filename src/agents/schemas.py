"""
Agentic Investment OS — JSON схемы агентов (Pydantic)
Строгая типизация ВСЕХ выходов агентов. Без free-text.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# Chief Planner — Выход
# ============================================================
class PlannerFocusAsset(BaseModel):
    symbol: str = Field(description="Тикер актива")
    priority: int = Field(ge=1, le=10, description="Приоритет 1-10")
    reason: str = Field(description="Причина фокуса")


class ChiefPlannerOutput(BaseModel):
    """Выход Chief Planner — динамический план ПЕРЕД анализом."""
    focus_assets: list[PlannerFocusAsset] = Field(
        description="Активы в фокусе на этот прогон"
    )
    news_filters: dict = Field(
        default_factory=dict,
        description="Фильтры для новостей: ключевые слова, категории"
    )
    market_conditions: list[str] = Field(
        default_factory=list,
        description="Рыночные условия для отслеживания"
    )
    ignored_noise: list[str] = Field(
        default_factory=list,
        description="Темы/ключевые слова-шум для игнорирования"
    )
    macro_focus: list[str] = Field(
        default_factory=list,
        description="Макроэкономические факторы в фокусе"
    )
    risk_alerts: list[str] = Field(
        default_factory=list,
        description="Предупреждения о рисках"
    )
    summary: str = Field(description="Краткое резюме плана")


# ============================================================
# News Analyst — Выход
# ============================================================
class NewsAnalysisItem(BaseModel):
    title: str
    source: str
    sentiment: str = Field(description="positive/negative/neutral")
    impact_level: str = Field(description="critical/significant/moderate/minor")
    affected_assets: list[str] = Field(default_factory=list)
    key_takeaway: str
    event_type: str


class NewsAnalystOutput(BaseModel):
    """Выход News Analyst — анализ отфильтрованных новостей."""
    overall_sentiment: str = Field(description="bullish/bearish/neutral")
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    key_events: list[NewsAnalysisItem] = Field(default_factory=list)
    macro_outlook: str = Field(description="Макроэкономический прогноз")
    sector_highlights: dict = Field(
        default_factory=dict,
        description="Ключевые моменты по секторам"
    )
    risk_factors: list[str] = Field(default_factory=list)
    summary: str


# ============================================================
# Market Analyst — Выход
# ============================================================
class AssetTechnicalAnalysis(BaseModel):
    symbol: str
    current_price: float
    trend: str = Field(description="strong_uptrend/uptrend/sideways/downtrend/strong_downtrend")
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    rsi_reading: Optional[str] = Field(default=None, description="overbought/neutral/oversold")
    macd_signal: Optional[str] = Field(default=None, description="bullish/bearish")
    volume_assessment: str = Field(description="high/normal/low")
    key_observation: str


class MarketAnalystOutput(BaseModel):
    """Выход Market Analyst — анализ цен и индикаторов."""
    market_regime: str = Field(
        description="bull_market/bear_market/consolidation/correction"
    )
    overall_score: float = Field(ge=-1.0, le=1.0)
    asset_analyses: list[AssetTechnicalAnalysis] = Field(default_factory=list)
    correlations: list[str] = Field(
        default_factory=list,
        description="Замеченные корреляции между активами"
    )
    key_levels: dict = Field(
        default_factory=dict,
        description="Ключевые уровни поддержки/сопротивления"
    )
    summary: str


# ============================================================
# Thesis/Risk Analyst — Выход
# ============================================================
class ThesisUpdate(BaseModel):
    symbol: str
    current_thesis: str
    thesis_status: str = Field(description="intact/weakening/strengthening/broken")
    key_risks: list[str] = Field(default_factory=list)
    catalysts: list[str] = Field(default_factory=list)
    confidence_change: float = Field(
        ge=-1.0, le=1.0,
        description="Изменение уверенности в тезисе"
    )


class ThesisAnalystOutput(BaseModel):
    """Выход Thesis/Risk Analyst — отслеживание тезисов и рисков."""
    thesis_updates: list[ThesisUpdate] = Field(default_factory=list)
    portfolio_risks: list[str] = Field(default_factory=list)
    risk_score: float = Field(
        ge=0.0, le=1.0,
        description="Общий уровень риска портфеля 0-1"
    )
    hedging_suggestions: list[str] = Field(default_factory=list)
    strategy_alignment: str = Field(
        description="Насколько текущая ситуация соответствует стратегии 'Русский Спринт'"
    )
    summary: str


# ============================================================
# Chief Investor — Выход (финальное решение)
# ============================================================
class AssetRecommendation(BaseModel):
    symbol: str
    action: str = Field(description="buy/sell/hold/accumulate/reduce")
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = Field(ge=1, le=10)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    time_horizon: str = Field(description="Временной горизонт: days/weeks/months")
    reasoning: str
    risks: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(
        default_factory=list,
        description="Условия для пересмотра решения"
    )


class ChiefInvestorOutput(BaseModel):
    """Выход Chief Investor — финальное решение."""
    market_assessment: str = Field(description="Общая оценка рынка")
    portfolio_health: str = Field(description="strong/moderate/weak")
    recommendations: list[AssetRecommendation] = Field(default_factory=list)
    capital_allocation: dict = Field(
        default_factory=dict,
        description="Предлагаемое распределение капитала"
    )
    next_actions: list[str] = Field(
        default_factory=list,
        description="Конкретные шаги для инвестора"
    )
    key_dates: list[str] = Field(
        default_factory=list,
        description="Важные даты впереди (отчёты, дивиденды, решения ЦБ)"
    )
    risk_warning: str = Field(
        description="Главное предупреждение о рисках"
    )
    summary: str
