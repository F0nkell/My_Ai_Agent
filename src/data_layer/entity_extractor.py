"""
Agentic Investment OS — Извлечение сущностей из текста
Без ML, на правилах (для минимизации зависимостей).
"""

import re
from typing import Optional

from loguru import logger


# Паттерны для извлечения
PATTERNS = {
    "cbr_rate": [
        r"ключев\w+ ставк\w+.*?(\d+[.,]?\d*)\s*%",
        r"ставк\w+ цб.*?(\d+[.,]?\d*)\s*%",
    ],
    "oil_price": [
        r"нефть.*?\$\s*(\d+[.,]?\d*)",
        r"brent.*?\$\s*(\d+[.,]?\d*)",
        r"нефть.*?(\d+[.,]?\d*)\s*доллар",
    ],
    "currency_rate": [
        r"доллар.*?(\d+[.,]?\d*)\s*рубл",
        r"курс.*?(\d+[.,]?\d*)\s*руб",
        r"usd.*?(\d+[.,]?\d*)\s*rub",
    ],
    "dividend": [
        r"дивиденд\w*.*?(\d+[.,]?\d*)\s*(?:руб|₽|р\.)",
        r"выплат\w*.*?(\d+[.,]?\d*)\s*(?:руб|₽|р\.)\s*на\s*акц",
    ],
    "percent_change": [
        r"(?:выросл|упал|снизил|повысил)\w*.*?на\s*(\d+[.,]?\d*)\s*%",
        r"[+-](\d+[.,]?\d*)\s*%",
    ],
}


class EntityExtractor:
    """Извлечение структурированных сущностей из текста."""

    def extract(self, text: str) -> dict:
        """Извлечь все сущности из текста."""
        if not text:
            return {}

        text_lower = text.lower()
        entities = {}

        for entity_type, patterns in PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    # Берём первое совпадение и конвертируем в float
                    try:
                        value = float(matches[0].replace(",", "."))
                        entities[entity_type] = value
                    except (ValueError, IndexError):
                        continue
                    break  # Достаточно одного совпадения

        # Определяем тип события
        entities["event_type"] = self._classify_event(text_lower)

        # Определяем тональность (базовая)
        entities["basic_sentiment"] = self._basic_sentiment(text_lower)

        return entities

    @staticmethod
    def _classify_event(text: str) -> str:
        """Классифицировать тип события."""
        events = {
            "rate_decision": ["ключевая ставка", "ставку", "цб решил", "цб снизил", "цб повысил"],
            "dividend": ["дивиденд", "выплат дивиденд"],
            "sanctions": ["санкци", "ограничени", "лицензи"],
            "earnings": ["прибыль", "выручк", "отчёт", "отчет", "финансов результат"],
            "macro": ["инфляц", "ввп", "безработиц"],
            "oil": ["нефть", "brent", "опек", "добыч"],
            "currency": ["рубль", "доллар", "валют", "курс"],
            "geopolitics": ["войн", "конфликт", "перегов", "мир"],
        }

        for event_type, keywords in events.items():
            if any(kw in text for kw in keywords):
                return event_type

        return "other"

    @staticmethod
    def _basic_sentiment(text: str) -> str:
        """Базовый анализ тональности на правилах."""
        positive = [
            "рост", "выросл", "повысил", "прибыль", "рекорд",
            "позитив", "оптими", "улучш", "успешн",
        ]
        negative = [
            "падени", "снижен", "упал", "убыт", "крах",
            "негатив", "пессими", "ухудш", "провал", "риск",
        ]

        pos_count = sum(1 for w in positive if w in text)
        neg_count = sum(1 for w in negative if w in text)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
