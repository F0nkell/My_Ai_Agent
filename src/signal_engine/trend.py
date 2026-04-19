"""
Agentic Investment OS — Классификация тренда
SMA/EMA кроссоверы, RSI зоны, MACD сигналы.
"""

from loguru import logger


class TrendClassifier:
    """Классификация тренда актива."""

    def analyze(self, indicators: dict, close_price: float) -> dict:
        """
        Классификация тренда.
        Возвращает score от -1.0 (сильный нисходящий) до +1.0 (сильный восходящий).
        """
        if not indicators or close_price <= 0:
            return {"score": 0.0, "trend": "unknown", "confidence": 0.0}

        signals = []

        # 1. Цена vs SMA
        sma_20 = indicators.get("sma_20")
        sma_50 = indicators.get("sma_50")

        if sma_20:
            if close_price > sma_20:
                signals.append(("price_above_sma20", 0.3, "Цена выше SMA-20"))
            else:
                signals.append(("price_below_sma20", -0.3, "Цена ниже SMA-20"))

        if sma_50:
            if close_price > sma_50:
                signals.append(("price_above_sma50", 0.3, "Цена выше SMA-50"))
            else:
                signals.append(("price_below_sma50", -0.3, "Цена ниже SMA-50"))

        # 2. Golden/Death Cross (SMA-20 vs SMA-50)
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                signals.append(("golden_cross", 0.5, "SMA-20 > SMA-50 — золотой крест"))
            else:
                signals.append(("death_cross", -0.5, "SMA-20 < SMA-50 — мёртвый крест"))

        # 3. RSI
        rsi = indicators.get("rsi_14")
        if rsi is not None:
            if rsi > 70:
                signals.append(("rsi_overbought", -0.4, f"RSI={rsi} — перекупленность"))
            elif rsi < 30:
                signals.append(("rsi_oversold", 0.4, f"RSI={rsi} — перепроданность (возможен отскок)"))
            elif 45 < rsi < 55:
                signals.append(("rsi_neutral", 0.0, f"RSI={rsi} — нейтральная зона"))
            elif rsi > 55:
                signals.append(("rsi_bullish", 0.2, f"RSI={rsi} — бычий импульс"))
            else:
                signals.append(("rsi_bearish", -0.2, f"RSI={rsi} — медвежий импульс"))

        # 4. MACD
        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                signals.append(("macd_bullish", 0.4, "MACD > Signal — бычий сигнал"))
            else:
                signals.append(("macd_bearish", -0.4, "MACD < Signal — медвежий сигнал"))

        # 5. EMA кроссовер
        ema_12 = indicators.get("ema_12")
        ema_26 = indicators.get("ema_26")
        if ema_12 and ema_26:
            if ema_12 > ema_26:
                signals.append(("ema_bullish", 0.3, "EMA-12 > EMA-26 — бычий тренд"))
            else:
                signals.append(("ema_bearish", -0.3, "EMA-12 < EMA-26 — медвежий тренд"))

        # Агрегация
        if not signals:
            return {"score": 0.0, "trend": "unknown", "confidence": 0.0}

        avg_score = sum(s[1] for s in signals) / len(signals)

        if avg_score > 0.3:
            trend = "strong_uptrend"
        elif avg_score > 0.1:
            trend = "uptrend"
        elif avg_score > -0.1:
            trend = "sideways"
        elif avg_score > -0.3:
            trend = "downtrend"
        else:
            trend = "strong_downtrend"

        return {
            "score": round(avg_score, 4),
            "trend": trend,
            "confidence": round(min(len(signals) * 0.15, 1.0), 2),
            "rsi": rsi,
            "signals": [
                {"name": s[0], "value": s[1], "comment": s[2]}
                for s in signals
            ],
        }
