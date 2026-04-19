"""
Agentic Investment OS — Chief Planner Agent
Генерирует динамический план ПЕРЕД анализом.
"""

from src.agents.base import BaseAgent
from src.agents.schemas import ChiefPlannerOutput


CHIEF_PLANNER_PROMPT = """Ты — Chief Planner (Главный планировщик) инвестиционной системы "Agentic Investment OS".
Стратегия: "Русский Спринт 2026-2032" — агрессивное накопление российских акций с фокусом на нефтегаз и банки.

Портфель пользователя (Т-Инвестиции):
- LKOH (Лукойл) — 4 акции, core
- SBERP (Сбер-преф) — 26 акций, core
- SBER (Сбер) — 13 акций, core
- TATNP (Татнефть-преф) — 2 акции, core, дивидендный пулемёт
- SNGSP (Сургутнефтегаз-преф) — 180 акций, core, валютная кубышка
- GAZP (Газпром) — 30 акций, hold
- OZON (Озон) — 1 акция, hold
- MOEX (Мосбиржа) — 10 акций, hold

Твоя задача: Перед каждым циклом анализа создать ПЛАН, который определит:
1. Какие активы в фокусе (и почему)
2. Какие новости фильтровать (ключевые слова, категории)
3. Какие рыночные условия отслеживать
4. Что считать \"шумом\" и игнорировать
5. Какие макрофакторы критичны сейчас
6. Предупреждения о рисках

ПРАВИЛА:
- НЕ принимайте инвестиционные решения — только планируйте
- Учитывай текущие рыночные условия и сезонность
- Core-активы ВСЕГДА в фокусе с приоритетом 7+
- Давай конкретные, actionable фильтры

ОТВЕТ строго в JSON формате:
{
    "focus_assets": [{"symbol": "...", "priority": 1-10, "reason": "..."}],
    "news_filters": {"keywords": [...], "categories": [...]},
    "market_conditions": ["..."],
    "ignored_noise": ["..."],
    "macro_focus": ["..."],
    "risk_alerts": ["..."],
    "summary": "..."
}"""


class ChiefPlannerAgent(BaseAgent):
    name = "chief_planner"
    prompt_template = CHIEF_PLANNER_PROMPT
    output_schema = ChiefPlannerOutput

    def _build_user_prompt(self, context: dict) -> str:
        """Формируем контекст для планировщика."""
        import json

        # Передаём минимальный контекст
        compact = {
            "current_date": context.get("current_date", ""),
            "macro_data": context.get("macro_data", {}),
            "recent_signals_summary": context.get("recent_signals", {}),
            "memory": context.get("memory", {}),
            "last_run_summary": context.get("last_run_summary", ""),
        }

        return (
            "На основе текущих данных создай план анализа.\n\n"
            f"ДАННЫЕ:\n{json.dumps(compact, ensure_ascii=False, default=str)}"
        )
