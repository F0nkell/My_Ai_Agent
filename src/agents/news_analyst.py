"""
Agentic Investment OS — News Analyst Agent
Анализирует ТОЛЬКО отфильтрованные по плану новости.
"""

from src.agents.base import BaseAgent
from src.agents.schemas import NewsAnalystOutput


NEWS_ANALYST_PROMPT = """Ты — News Analyst (Аналитик новостей) инвестиционной системы.
Стратегия: "Русский Спринт 2026-2032" — фокус на российские акции (нефтегаз + банки).

Твоя задача: Проанализировать ОТФИЛЬТРОВАННЫЕ новости и дать структурированную оценку:
1. Общий sentiment (бычий/медвежий/нейтральный)
2. Ключевые события и их влияние на портфель
3. Макроэкономический прогноз
4. Секторальные выводы
5. Факторы риска

ПРАВИЛА:
- НЕ придумывай новости — анализируй ТОЛЬКО предоставленные
- Оценивай каждую новость через призму нашего портфеля
- Особое внимание: ключевая ставка ЦБ (влияет на Сбер), нефть (Лукойл/Татнефть/Газпром), курс рубля (Сургутнефтегаз-преф)
- Бди: "шум" vs "сигнал" (как нас учил инвестор)
- Дивидендный сезон (май-июль) — критически важен

ОТВЕТ строго в JSON:
{
    "overall_sentiment": "bullish/bearish/neutral",
    "sentiment_score": -1.0..1.0,
    "key_events": [{"title": "...", "source": "...", "sentiment": "...", "impact_level": "...", "affected_assets": [...], "key_takeaway": "...", "event_type": "..."}],
    "macro_outlook": "...",
    "sector_highlights": {"oil_gas": "...", "finance": "..."},
    "risk_factors": ["..."],
    "summary": "..."
}"""


class NewsAnalystAgent(BaseAgent):
    name = "news_analyst"
    prompt_template = NEWS_ANALYST_PROMPT
    output_schema = NewsAnalystOutput

    def _build_user_prompt(self, context: dict) -> str:
        import json

        # Только отфильтрованные новости + план
        compact = {
            "plan_summary": context.get("plan_summary", ""),
            "focus_assets": context.get("focus_assets", []),
            "news": [
                {
                    "title": n.get("title", ""),
                    "content": n.get("content", "")[:500],  # Ограничиваем
                    "source": n.get("source", ""),
                    "category": n.get("category", ""),
                    "asset_symbols": n.get("asset_symbols", []),
                    "importance": n.get("importance_score", 0.5),
                }
                for n in context.get("news", [])[:15]  # Максимум 15 новостей
            ],
        }

        return (
            "Проанализируй следующие новости для нашего портфеля.\n\n"
            f"ДАННЫЕ:\n{json.dumps(compact, ensure_ascii=False, default=str)}"
        )
