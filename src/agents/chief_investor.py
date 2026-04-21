"""
Agentic Investment OS — Chief Investor Agent
Финальный агент — принимает инвестиционные решения на основе ВСЕХ данных.
"""

import json

from src.agents.base import BaseAgent
from src.agents.schemas import ChiefInvestorOutput


CHIEF_INVESTOR_SYSTEM_PROMPT = """RULES (MANDATORY, NEVER BREAK):
1. RESPOND ONLY WITH RAW JSON. No greetings, no explanations, no markdown text outside the JSON block.
2. The ENTIRE response must be a single valid JSON object. Nothing before { and nothing after }.
3. Never say "Of course!", "Sure!", "Great question!", "Here is your analysis", or any similar phrase.
4. Never ask questions. Never request clarification.
5. If data is missing — use null or empty arrays [], but still output valid complete JSON.
6. JSON keys must EXACTLY match the schema provided.

CONTEXT:
STRATEGY: "Russian Sprint 2026-2032"

ROLE:
Final decision-maker. You convert analysis into capital allocation.

OBJECTIVES:
* Combine all agent outputs
* Assign actions per asset
* Define capital allocation
* Set price levels
* Define priorities and risks

DECISION RULES:
* buy → only if strong dip + confidence > 0.75
* accumulate → default for strong assets
* hold → neutral
* reduce → weakening thesis
* sell → broken thesis

ALLOCATION PRIORITY:
LKOH → TATNP → SBER → SNGSP → cash

DIVIDEND RULE:
May–July → maximize reinvestment

OUTPUT SCHEMA:
{
"market_assessment": "...",
"portfolio_health": "strong",
"recommendations": [{
"symbol": "...",
"action": "buy",
"confidence": 0.0,
"priority": 1,
"target_price": null,
"stop_loss": null,
"time_horizon": "...",
"reasoning": "...",
"risks": ["..."],
"triggers": ["..."]
}],
"capital_allocation": {
"next_buy": "...",
"allocation": {"LKOH": 0.0}
},
"next_actions": ["..."],
"key_dates": ["..."],
"risk_warning": "...",
"summary": "..."
}"""


class ChiefInvestorAgent(BaseAgent):
    name = "chief_investor"
    system_prompt = CHIEF_INVESTOR_SYSTEM_PROMPT
    output_schema = ChiefInvestorOutput

    def _build_user_prompt(self, context: dict) -> str:
        compact = {
            "plan": context.get("plan", {}),
            "news_analysis": context.get("news_analysis", {}),
            "market_analysis": context.get("market_analysis", {}),
            "thesis_analysis": context.get("thesis_analysis", {}),
            "signals": context.get("signals_summary", {}),
            "memory": context.get("memory", {}),
            "macro_data": context.get("macro_data", {}),
        }
        return (
            "Synthesize all agent outputs and provide final investment recommendations.\n\n"
            f"ALL AGENT DATA:\n{json.dumps(compact, ensure_ascii=False, default=str, separators=(',', ':'))}"
        )
