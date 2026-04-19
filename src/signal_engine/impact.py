"""
Agentic Investment OS — Оценка влияния событий
Скоринг новостных событий по потенциальному влиянию на активы.
"""

from loguru import logger


# Веса типов событий для разных секторов
EVENT_IMPACT_MATRIX = {
    "rate_decision": {
        "finance": 0.9,   # Сбербанк — максимально чувствителен к ставке ЦБ
        "oil_gas": 0.3,
        "tech": 0.5,
        "default": 0.5,
    },
    "oil": {
        "oil_gas": 0.9,   # Лукойл, Татнефть, Газпром, Сургут
        "finance": 0.3,
        "tech": 0.1,
        "default": 0.3,
    },
    "sanctions": {
        "oil_gas": 0.8,
        "finance": 0.7,
        "tech": 0.6,
        "default": 0.7,
    },
    "currency": {
        "oil_gas": 0.7,   # Сургутнефтегаз-преф — максимально чувствителен
        "finance": 0.5,
        "tech": 0.3,
        "default": 0.4,
    },
    "dividend": {
        "oil_gas": 0.8,
        "finance": 0.7,
        "tech": 0.3,
        "default": 0.5,
    },
    "earnings": {
        "oil_gas": 0.6,
        "finance": 0.7,
        "tech": 0.8,
        "default": 0.6,
    },
    "geopolitics": {
        "oil_gas": 0.6,
        "finance": 0.5,
        "tech": 0.3,
        "default": 0.5,
    },
    "macro": {
        "oil_gas": 0.4,
        "finance": 0.6,
        "tech": 0.4,
        "default": 0.4,
    },
}

# Специальные множители для конкретных тикеров
SYMBOL_MULTIPLIERS = {
    "SNGSP": {
        "currency": 1.5,  # Сургут-преф — валютная кубышка
    },
    "SBER": {
        "rate_decision": 1.3,  # Сбер — ставка на кредитование
    },
    "SBERP": {
        "rate_decision": 1.3,
    },
    "LKOH": {
        "oil": 1.3,
        "sanctions": 1.2,
    },
    "TATNP": {
        "dividend": 1.3,  # Дивидендный пулемёт
        "oil": 1.2,
    },
}


class EventImpactAnalyzer:
    """Оценка влияния событий на активы."""

    def analyze(
        self,
        event_type: str,
        sentiment_score: float,
        sector: str = None,
        symbol: str = None,
        importance_score: float = 0.5,
    ) -> dict:
        """
        Оценить влияние события на актив.
        Возвращает impact_score от -1.0 до +1.0.
        """
        # 1. Базовый вес по матрице событие→сектор
        sector_key = sector or "default"
        event_weights = EVENT_IMPACT_MATRIX.get(event_type, {})
        base_weight = event_weights.get(sector_key, event_weights.get("default", 0.3))

        # 2. Множитель для конкретного тикера
        multiplier = 1.0
        if symbol and symbol in SYMBOL_MULTIPLIERS:
            multiplier = SYMBOL_MULTIPLIERS[symbol].get(event_type, 1.0)

        # 3. Impact = sentiment × weight × multiplier × importance
        impact = sentiment_score * base_weight * multiplier * importance_score

        # 4. Определение уровня влияния
        abs_impact = abs(impact)
        if abs_impact > 0.6:
            level = "critical"
        elif abs_impact > 0.3:
            level = "significant"
        elif abs_impact > 0.1:
            level = "moderate"
        else:
            level = "minor"

        return {
            "score": round(impact, 4),
            "level": level,
            "direction": "positive" if impact > 0 else "negative" if impact < 0 else "neutral",
            "confidence": round(min(base_weight * multiplier, 1.0), 2),
            "details": {
                "event_type": event_type,
                "sector": sector_key,
                "base_weight": base_weight,
                "multiplier": multiplier,
                "sentiment": sentiment_score,
                "importance": importance_score,
            },
        }

    def analyze_batch_for_asset(
        self,
        events: list[dict],
        symbol: str,
        sector: str,
    ) -> dict:
        """Агрегированный анализ влияния пакета событий на один актив."""
        if not events:
            return {"score": 0.0, "direction": "neutral", "events_count": 0}

        impacts = []
        for event in events:
            impact = self.analyze(
                event_type=event.get("event_type", "other"),
                sentiment_score=event.get("sentiment_score", 0.0),
                sector=sector,
                symbol=symbol,
                importance_score=event.get("importance_score", 0.5),
            )
            impacts.append(impact)

        # Взвешенное среднее
        total_weight = sum(abs(i["score"]) for i in impacts)
        if total_weight == 0:
            avg_score = 0.0
        else:
            avg_score = sum(i["score"] for i in impacts) / len(impacts)

        return {
            "score": round(avg_score, 4),
            "direction": "positive" if avg_score > 0.1 else "negative" if avg_score < -0.1 else "neutral",
            "events_count": len(events),
            "critical_events": [i for i in impacts if i["level"] == "critical"],
        }
