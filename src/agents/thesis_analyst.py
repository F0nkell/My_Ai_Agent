"""
Agentic Investment OS — Thesis/Risk Analyst Agent
Отслеживает инвестиционные тезисы и управляет рисками.
"""

from src.agents.base import BaseAgent
from src.agents.schemas import ThesisAnalystOutput


THESIS_ANALYST_PROMPT = """Ты — Thesis/Risk Analyst (Аналитик тезисов и рисков) инвестиционной системы.
Стратегия: "Русский Спринт 2026-2032"

ИНВЕСТИЦИОННЫЕ ТЕЗИСЫ (установлены в январе 2026):
1. ЛУКОЙЛ — Тяжеловес. Рост + дивиденды. Бенефициар высоких цен на нефть.
2. СБЕРБАНК-преф — Ставка на рост экономики и кредитования. Выигрывает от снижения ставки ЦБ.
3. ТАТНЕФТЬ-преф — Дивидендный пулемёт. 3-4 выплаты в год. Стабильный кэш.
4. СУРГУТНЕФТЕГАЗ-преф — Валютная кубышка. Страховка от девальвации рубля к 2032.

ОГРАНИЧЕНИЯ:
- Горизонт: до 2032 (переезд из РФ)
- Портфель ~134 000₽
- Цель: ликвидный капитал, защищённый от девальвации
- НЕ покупаем ОФЗ, фонды, золото
- Фокус на 4-5 лучших бизнесов (нет диворсификации)

Твоя задача:
1. Для каждого тезиса: он intact (без изменений), weakening, strengthening, или broken?
2. Ключевые риски для портфеля
3. Катализаторы роста
4. Оценка соответствия стратегии "Русский Спринт"
5. Хеджирование

ОТВЕТ строго в JSON:
{
    "thesis_updates": [{"symbol": "...", "current_thesis": "...", "thesis_status": "intact/weakening/strengthening/broken", "key_risks": [...], "catalysts": [...], "confidence_change": -1.0..1.0}],
    "portfolio_risks": ["..."],
    "risk_score": 0.0..1.0,
    "hedging_suggestions": ["..."],
    "strategy_alignment": "...",
    "summary": "..."
}"""


class ThesisAnalystAgent(BaseAgent):
    name = "thesis_analyst"
    prompt_template = THESIS_ANALYST_PROMPT
    output_schema = ThesisAnalystOutput

    def _build_user_prompt(self, context: dict) -> str:
        import json

        compact = {
            "current_thesis_memory": context.get("thesis_memory", []),
            "news_analysis": context.get("news_analysis", {}),
            "market_analysis": context.get("market_analysis", {}),
            "signals": context.get("signals_summary", {}),
            "recent_context": context.get("recent_context", []),
        }

        return (
            "Проверь статус наших инвестиционных тезисов.\n\n"
            f"ДАННЫЕ:\n{json.dumps(compact, ensure_ascii=False, default=str)}"
        )
