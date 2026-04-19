"""
Agentic Investment OS — Анализ волатильности
Детекция спайков волатильности через ATR и Bollinger Bands.
"""

from loguru import logger


class VolatilityAnalyzer:
    """Анализ волатильности актива."""

    def analyze(self, indicators: dict, close_price: float) -> dict:
        """
        Анализ волатильности на основе индикаторов.
        Возвращает score от -1.0 (экстремальная волатильность) до +1.0 (спокойный рынок).
        """
        if not indicators or close_price <= 0:
            return {"score": 0.0, "level": "unknown", "confidence": 0.0}

        signals = []

        # 1. ATR как % от цены (нормализованная волатильность)
        atr = indicators.get("atr_14")
        if atr and close_price > 0:
            atr_pct = (atr / close_price) * 100
            if atr_pct > 5.0:
                signals.append(("atr_high", -0.8, "ATR > 5% — экстремальная волатильность"))
            elif atr_pct > 3.0:
                signals.append(("atr_elevated", -0.4, "ATR 3-5% — повышенная волатильность"))
            elif atr_pct > 1.5:
                signals.append(("atr_normal", 0.2, "ATR 1.5-3% — нормальная волатильность"))
            else:
                signals.append(("atr_low", 0.6, "ATR < 1.5% — низкая волатильность"))

        # 2. Bollinger Bands — позиция цены
        bb_upper = indicators.get("bb_upper")
        bb_lower = indicators.get("bb_lower")
        if bb_upper and bb_lower:
            bb_width = bb_upper - bb_lower
            if bb_width > 0:
                # Позиция внутри канала (0 = нижняя граница, 1 = верхняя)
                bb_position = (close_price - bb_lower) / bb_width

                if bb_position > 0.95:
                    signals.append(("bb_overbought", -0.6, "Цена у верхней Bollinger — перекупленность"))
                elif bb_position < 0.05:
                    signals.append(("bb_oversold", 0.5, "Цена у нижней Bollinger — перепроданность"))
                elif 0.3 < bb_position < 0.7:
                    signals.append(("bb_middle", 0.3, "Цена в середине канала"))

                # Ширина канала как % от цены
                bb_width_pct = (bb_width / close_price) * 100
                if bb_width_pct > 10:
                    signals.append(("bb_wide", -0.3, "Широкий BB канал — нестабильность"))

        # 3. Агрегация
        if not signals:
            return {"score": 0.0, "level": "unknown", "confidence": 0.0}

        avg_score = sum(s[1] for s in signals) / len(signals)

        if avg_score < -0.4:
            level = "extreme"
        elif avg_score < -0.1:
            level = "elevated"
        elif avg_score < 0.3:
            level = "normal"
        else:
            level = "low"

        return {
            "score": round(avg_score, 4),
            "level": level,
            "confidence": round(min(len(signals) * 0.3, 1.0), 2),
            "signals": [
                {"name": s[0], "value": s[1], "comment": s[2]}
                for s in signals
            ],
        }
