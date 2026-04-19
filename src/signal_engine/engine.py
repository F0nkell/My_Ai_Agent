"""
Agentic Investment OS — Главный движок сигналов
Оркестрация всех анализаторов, хранение результатов в БД.
"""

from loguru import logger

from src.signal_engine.sentiment import SentimentAnalyzer
from src.signal_engine.volatility import VolatilityAnalyzer
from src.signal_engine.volume import VolumeAnalyzer
from src.signal_engine.trend import TrendClassifier
from src.signal_engine.impact import EventImpactAnalyzer


class SignalEngine:
    """
    Главный движок сигналов.
    Вычисляет 5 типов сигналов для каждого актива:
    1. Sentiment (тональность новостей)
    2. Volatility (волатильность)
    3. Volume (аномалии объёма)
    4. Trend (классификация тренда)
    5. Event Impact (влияние событий)
    """

    def __init__(self):
        self.sentiment = SentimentAnalyzer()
        self.volatility = VolatilityAnalyzer()
        self.volume = VolumeAnalyzer()
        self.trend = TrendClassifier()
        self.impact = EventImpactAnalyzer()

    def compute_all_signals(
        self,
        symbol: str,
        sector: str,
        market_data: dict,
        news_items: list[dict] = None,
    ) -> dict:
        """
        Вычислить все 5 сигналов для актива.
        Это заменяет "ретрейнинг модели" — улучшаем данные, НЕ модель.
        """
        signals = {}
        close_price = market_data.get("price", market_data.get("close", 0))
        indicators = market_data.get("indicators", {})
        volume = market_data.get("volume", 0)

        # 1. Sentiment
        if news_items:
            texts = [f"{n.get('title', '')} {n.get('content', '')}" for n in news_items]
            sentiment_result = self.sentiment.analyze_batch(texts)
            signals["sentiment"] = {
                "value": sentiment_result["score"],
                "confidence": 0.6,
                "direction": sentiment_result["direction"],
                "details": sentiment_result,
            }
        else:
            signals["sentiment"] = {
                "value": 0.0,
                "confidence": 0.1,
                "direction": "neutral",
                "details": {"comment": "Нет новостей для анализа"},
            }

        # 2. Volatility
        vol_result = self.volatility.analyze(indicators, close_price)
        signals["volatility"] = {
            "value": vol_result["score"],
            "confidence": vol_result["confidence"],
            "direction": "bearish" if vol_result["score"] < -0.3 else "neutral",
            "details": vol_result,
        }

        # 3. Volume
        vol_anomaly = self.volume.analyze(indicators, volume)
        signals["volume_anomaly"] = {
            "value": vol_anomaly["score"],
            "confidence": vol_anomaly["confidence"],
            "direction": "bullish" if vol_anomaly["score"] > 0.3 else "neutral",
            "details": vol_anomaly,
        }

        # 4. Trend
        trend_result = self.trend.analyze(indicators, close_price)
        signals["trend"] = {
            "value": trend_result["score"],
            "confidence": trend_result["confidence"],
            "direction": "bullish" if trend_result["score"] > 0 else "bearish",
            "details": trend_result,
        }

        # 5. Event Impact
        if news_items:
            events_for_impact = []
            for n in news_items:
                entities = n.get("entities", {})
                events_for_impact.append({
                    "event_type": entities.get("event_type", "other"),
                    "sentiment_score": signals["sentiment"]["value"],
                    "importance_score": n.get("importance_score", 0.5),
                })

            impact_result = self.impact.analyze_batch_for_asset(
                events_for_impact, symbol, sector
            )
            signals["event_impact"] = {
                "value": impact_result["score"],
                "confidence": 0.5,
                "direction": impact_result["direction"],
                "details": impact_result,
            }
        else:
            signals["event_impact"] = {
                "value": 0.0,
                "confidence": 0.1,
                "direction": "neutral",
                "details": {"comment": "Нет событий для оценки"},
            }

        # Сводный score
        composite = self._compute_composite(signals)
        signals["composite"] = composite

        logger.info(
            f"📡 {symbol}: composite={composite['score']:.3f} "
            f"({composite['direction']}) | "
            f"sent={signals['sentiment']['value']:.2f} "
            f"trend={signals['trend']['value']:.2f} "
            f"vol={signals['volatility']['value']:.2f}"
        )

        return signals

    def _compute_composite(self, signals: dict) -> dict:
        """Вычислить композитный (сводный) скор."""
        # Веса для каждого типа сигнала (можно корректировать через Learning)
        weights = {
            "trend": 0.30,
            "sentiment": 0.25,
            "event_impact": 0.20,
            "volatility": 0.15,
            "volume_anomaly": 0.10,
        }

        total_score = 0.0
        total_confidence = 0.0

        for signal_type, weight in weights.items():
            if signal_type in signals:
                s = signals[signal_type]
                total_score += s["value"] * weight
                total_confidence += s["confidence"] * weight

        if total_score > 0.2:
            direction = "bullish"
        elif total_score < -0.2:
            direction = "bearish"
        else:
            direction = "neutral"

        return {
            "score": round(total_score, 4),
            "direction": direction,
            "confidence": round(total_confidence, 4),
            "weights": weights,
        }
