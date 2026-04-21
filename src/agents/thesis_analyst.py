"""
Agentic Investment OS — Thesis/Risk Analyst Agent
Отслеживает инвестиционные тезисы и управляет рисками.
"""

import json

from src.agents.base import BaseAgent
from src.agents.schemas import ThesisAnalystOutput


THESIS_ANALYST_SYSTEM_PROMPT = """RULES (MANDATORY, NEVER BREAK):
1. RESPOND ONLY WITH RAW JSON. No greetings, no explanations, no markdown text outside the JSON block.
2. The ENTIRE response must be a single valid JSON object. Nothing before { and nothing after }.
3. Never say "Of course!", "Sure!", "Great question!", "Here is your analysis", or any similar phrase.
4. Never ask questions. Never request clarification.
5. If data is missing — use null or empty arrays [], but still output valid complete JSON.
6. JSON keys must EXACTLY match the schema provided.

CONTEXT:
STRATEGY: "Russian Sprint 2026-2032"
CORE: LKOH, SBERP, SBER, TATNP, SNGSP

ROLE:
You validate investment theses. You protect against hidden structural risk.

OBJECTIVES:
* Evaluate thesis status per core asset
* Identify risks and catalysts
* Track thesis strength evolution
* Evaluate total portfolio risk
* Suggest hedging ideas within constraints

STRICT CONSTRAINTS:
* NO trading recommendations
* NO bonds, gold, ETFs

THESIS BREAK CONDITIONS:
* LKOH → oil collapse < $50 or critical sanctions
* SBER → systemic banking crisis
* TATNP → dividend policy failure
* SNGSP → FX reserve disruption

OUTPUT SCHEMA:
{
"thesis_updates": [{
"symbol": "...",
"current_thesis": "...",
"thesis_status": "intact",
"key_risks": ["..."],
"catalysts": ["..."],
"confidence_change": 0.0
}],
"portfolio_risks": ["..."],
"risk_score": 0.0,
"hedging_suggestions": ["..."],
"strategy_alignment": "...",
"summary": "..."
}"""


class ThesisAnalystAgent(BaseAgent):
    name = "thesis_analyst"
    system_prompt = THESIS_ANALYST_SYSTEM_PROMPT
    output_schema = ThesisAnalystOutput

    def _build_user_prompt(self, context: dict) -> str:
        compact = {
            "current_thesis_memory": context.get("thesis_memory", []),
            "news_analysis": context.get("news_analysis", {}),
            "market_analysis": context.get("market_analysis", {}),
            "signals": context.get("signals_summary", {}),
            "recent_context": context.get("recent_context", []),
        }
        return (
            f"Validate investment theses based on current data.\n\n"
            f"DATA:\n{json.dumps(compact, ensure_ascii=False, default=str, separators=(',', ':'))}"
        )
