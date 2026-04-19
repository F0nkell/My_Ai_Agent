"""
Agentic Investment OS — Аномалии объёма
Детекция необычных торговых объёмов.
"""

from loguru import logger


class VolumeAnalyzer:
    """Анализ аномалий торгового объёма."""

    def analyze(self, indicators: dict, volume: int) -> dict:
        """
        Анализ объёма торгов.
        volume_ratio > 2.0 → аномально высокий
        volume_ratio < 0.5 → аномально низкий
        """
        volume_ratio = indicators.get("volume_ratio", 1.0)

        if volume_ratio > 3.0:
            return {
                "score": 0.9,
                "level": "extreme_high",
                "confidence": 0.9,
                "volume_ratio": volume_ratio,
                "comment": f"Объём в {volume_ratio}x выше среднего — возможен крупный игрок или событие",
            }
        elif volume_ratio > 2.0:
            return {
                "score": 0.6,
                "level": "high",
                "confidence": 0.7,
                "volume_ratio": volume_ratio,
                "comment": f"Объём в {volume_ratio}x выше среднего — повышенный интерес",
            }
        elif volume_ratio > 1.3:
            return {
                "score": 0.3,
                "level": "above_average",
                "confidence": 0.5,
                "volume_ratio": volume_ratio,
                "comment": "Объём немного выше среднего",
            }
        elif volume_ratio < 0.3:
            return {
                "score": -0.5,
                "level": "very_low",
                "confidence": 0.6,
                "volume_ratio": volume_ratio,
                "comment": "Очень низкий объём — осторожность, низкая ликвидность",
            }
        elif volume_ratio < 0.5:
            return {
                "score": -0.3,
                "level": "low",
                "confidence": 0.5,
                "volume_ratio": volume_ratio,
                "comment": "Низкий объём торгов",
            }
        else:
            return {
                "score": 0.0,
                "level": "normal",
                "confidence": 0.3,
                "volume_ratio": volume_ratio,
                "comment": "Нормальный объём торгов",
            }
