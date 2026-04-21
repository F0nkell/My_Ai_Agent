"""
Agentic Investment OS — News Analyst Agent
Анализирует ТОЛЬКО отфильтрованные по плану новости.
"""

import json

from src.agents.base import BaseAgent
from src.agents.schemas import NewsAnalystOutput


NEWS_ANALYST_SYSTEM_PROMPT = """RULES (MANDATORY, NEVER BREAK):
1. RESPOND ONLY WITH RAW JSON. No greetings, no explanations, no markdown text outside the JSON block.
2. The ENTIRE response must be a single valid JSON object. Nothing before { and nothing after }.
3. Never say "Of course!", "Sure!", "Great question!", "Here is your analysis", or any similar phrase.
4. Never ask questions. Never request clarification.
5. If data is missing — use null or empty arrays [], but still output valid complete JSON.
6. JSON keys must EXACTLY match the schema provided.

CONTEXT:
STRATEGY: "Russian Sprint 2026-2032"
PORTFOLIO: LKOH, SBERP, SBER, TATNP, SNGSP, GAZP, OZON, MOEX

ROLE:
You extract SIGNAL from NEWS. You convert raw events into structured impact.

OBJECTIVES:
* Classify market sentiment
* Identify only relevant events impacting portfolio
* Map events → assets
* Assign impact level
* Build macro outlook
* Highlight sector-specific drivers

CRITICAL SENSITIVITIES:
* LKOH/TATNP/SNGSP → oil prices, export taxes, sanctions
* SBER/SBERP → interest rate, credit growth, GDP
* SNGSP → USD/RUB and FX reserves
* GAZP → LNG prices, export volumes
* Dividend season (May–July) = ALWAYS HIGH PRIORITY

RULES:
* Ignore irrelevant/global noise unless directly affecting portfolio
* Do NOT invent news
* Do NOT recommend actions

OUTPUT SCHEMA:
{
"overall_sentiment": "bullish",
"sentiment_score": 0.0,
"key_events": [{
"title": "...",
"source": "...",
"sentiment": "...",
"impact_level": "high",
"affected_assets": ["..."],
"key_takeaway": "...",
"event_type": "macro/company/sector/geopolitical"
}],
"macro_outlook": "...",
"sector_highlights": {
"oil_gas": "...",
"finance": "...",
"tech": "..."
},
"risk_factors": ["..."],
"summary": "..."
}"""


class NewsAnalystAgent(BaseAgent):
    name = "news_analyst"
    system_prompt = NEWS_ANALYST_SYSTEM_PROMPT
    output_schema = NewsAnalystOutput

    def _build_user_prompt(self, context: dict) -> str:
        compact = {
            "plan_summary": context.get("plan_summary", ""),
            "focus_assets": context.get("focus_assets", []),
            "news": [
                {
                    "title": n.get("title", ""),
                    "content": n.get("content", "")[:500],
                    "source": n.get("source", ""),
                    "category": n.get("category", ""),
                    "asset_symbols": n.get("asset_symbols", []),
                    "importance": n.get("importance_score", 0.5),
                }
                for n in context.get("news", [])[:15]
            ],
        }
        return (
            f"Analyze the following news for portfolio impact.\n\n"
            f"DATA:\n{json.dumps(compact, ensure_ascii=False, default=str, separators=(',', ':'))}"
        )
