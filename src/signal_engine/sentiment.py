"""
Agentic Investment OS — Анализ тональности
VADER + правила для русскоязычного контента.
"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from loguru import logger


class SentimentAnalyzer:
    """Анализ тональности новостей."""

    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        # Русские финансовые модификаторы
        self._positive_words = {
            "рост", "прибыль", "дивиденд", "рекорд", "повысил",
            "выросли", "оптимизм", "улучшение", "превысил", "бычий",
            "покупка", "накопление", "снижение ставки", "восстановление",
        }
        self._negative_words = {
            "падение", "убыток", "санкции", "дефолт", "обвал",
            "снизились", "пессимизм", "ухудшение", "девальвация",
            "медвежий", "продажа", "повышение ставки", "инфляция",
        }
        self._amplifiers = {
            "резко", "сильно", "значительно", "рекордно", "максимально",
        }

    def analyze(self, text: str) -> dict:
        """
        Анализ тональности текста.
        Возвращает score от -1.0 (медвежий) до +1.0 (бычий).
        """
        if not text:
            return {"score": 0.0, "direction": "neutral", "confidence": 0.0}

        text_lower = text.lower()

        # 1. VADER (для английских элементов и общей структуры)
        vader_scores = self.vader.polarity_scores(text)
        vader_compound = vader_scores["compound"]

        # 2. Русский финансовый анализ
        ru_score = self._russian_score(text_lower)

        # 3. Комбинируем (70% русский, 30% VADER)
        final_score = ru_score * 0.7 + vader_compound * 0.3

        # Определяем направление
        if final_score > 0.15:
            direction = "bullish"
        elif final_score < -0.15:
            direction = "bearish"
        else:
            direction = "neutral"

        # Уверенность — чем дальше от нуля, тем выше
        confidence = min(abs(final_score) * 1.5, 1.0)

        return {
            "score": round(final_score, 4),
            "direction": direction,
            "confidence": round(confidence, 4),
            "vader_compound": round(vader_compound, 4),
            "russian_score": round(ru_score, 4),
        }

    def _russian_score(self, text: str) -> float:
        """Русскоязычный анализ тональности."""
        pos_count = sum(1 for w in self._positive_words if w in text)
        neg_count = sum(1 for w in self._negative_words if w in text)
        amp_count = sum(1 for w in self._amplifiers if w in text)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        raw_score = (pos_count - neg_count) / total

        # Усиление при наличии амплификаторов
        if amp_count > 0:
            raw_score *= (1 + amp_count * 0.2)

        return max(-1.0, min(1.0, raw_score))

    def analyze_batch(self, texts: list[str]) -> dict:
        """Анализ пакета текстов (агрегированный sentiment)."""
        if not texts:
            return {"score": 0.0, "direction": "neutral", "count": 0}

        scores = [self.analyze(t)["score"] for t in texts]
        avg_score = sum(scores) / len(scores)

        if avg_score > 0.15:
            direction = "bullish"
        elif avg_score < -0.15:
            direction = "bearish"
        else:
            direction = "neutral"

        return {
            "score": round(avg_score, 4),
            "direction": direction,
            "count": len(scores),
            "scores_distribution": {
                "positive": sum(1 for s in scores if s > 0.15),
                "neutral": sum(1 for s in scores if -0.15 <= s <= 0.15),
                "negative": sum(1 for s in scores if s < -0.15),
            },
        }
