"""
Agentic Investment OS — Форматирование сообщений для Telegram
"""

def format_recommendations(run_summary: dict, recommendations: list[dict]) -> str:
    """Форматирует рекомендации Chief Investor для Telegram."""
    if not recommendations:
        return "Никаких новых рекомендаций не сгенерировано."

    market_eval = run_summary.get("market_assessment", "Нет данных")
    health = run_summary.get("portfolio_health", "Нет данных")
    
    text = f"📊 *Agentic Investment OS — Отчёт*\n"
    text += f"Рынок: _{market_eval}_\n"
    text += f"Здоровье портфеля: _{health}_\n\n"
    
    # Сначала buy
    buys = [r for r in recommendations if r["action"].lower() == "buy"]
    if buys:
        text += "🟢 *Рекомендации к ПОКУПКЕ:*\n"
        for r in buys:
            text += _format_single_rec(r)
            
    # Потом hold/accumulate
    holds = [r for r in recommendations if r["action"].lower() in ["hold", "accumulate"]]
    if holds:
         text += "🟡 *Рекомендации УДЕРЖИВАТЬ/НАКАПЛИВАТЬ:*\n"
         for r in holds:
            text += _format_single_rec(r)

    # Потом sell/reduce
    sells = [r for r in recommendations if r["action"].lower() in ["sell", "reduce"]]
    if sells:
         text += "🔴 *Рекомендации ПРОДАВАТЬ/СОКРАЩАТЬ:*\n"
         for r in sells:
            text += _format_single_rec(r)
            
    text += f"\n💡 _Резюме_: {run_summary.get('summary', '')}"
    return text

def _format_single_rec(rec: dict) -> str:
    conf = rec.get('confidence', 0.0) * 100
    emoji = "🔥" if conf >= 80 else "👍" if conf >= 60 else "🤔"
    
    res = f"• *{rec['symbol']}* {emoji} (Уверенность: {conf:.0f}%)\n"
    res += f"  ✏️ {rec['reasoning']}\n"
    if rec.get('target_price'):
        res += f"  🎯 Цель: {rec['target_price']}₽\n"
    if rec.get('stop_loss'):
        res += f"  🛑 Стоп: {rec['stop_loss']}₽\n"
    res += "\n"
    return res

def format_portfolio_status(portfolio: dict) -> str:
    """Форматирует текущий статус портфеля."""
    value = portfolio.get('total_value_rub', 0)
    core = portfolio.get('core_assets', [])
    hold = portfolio.get('hold_assets', [])
    
    text = f"💼 *Ваш портфель — Стратегия '{portfolio.get('strategy', '')}'*\n"
    text += f"Ориентировочная стоимость: *{value:,.2f} ₽*\n\n"
    
    text += "🛡️ *Великая Четвёрка (Core):*\n"
    for a in core:
         text += f"• {a['name']} ({a['symbol']}): {a['shares']} шт. (ср. {a['avg_price']}₽)\n"
         
    text += "\n📦 *Остальные (Hold):*\n"
    for a in hold:
         text += f"• {a['name']} ({a['symbol']}): {a['shares']} шт. (ср. {a['avg_price']}₽)\n"

    text += "\n📝 _Правило снайпера: копим кэш, бьём крупно по хорошим ценам._"
    return text
