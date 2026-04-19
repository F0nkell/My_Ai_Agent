"""
Agentic Investment OS — Препроцессор данных
Дедупликация, классификация, скоринг важности, фильтрация шума.
"""

import hashlib
import re
from datetime import datetime
from typing import Optional

from loguru import logger


class DataPreprocessor:
    """Предобработка данных перед отправкой агентам."""

    def __init__(self):
        self._seen_hashes: set[str] = set()

    def process_news_batch(
        self,
        raw_news: list[dict],
        plan_filters: dict = None,
    ) -> list[dict]:
        """
        Обработать пакет новостей:
        1. Дедупликация
        2. Фильтрация по плану Chief Planner
        3. Классификация
        4. Скоринг
        """
        processed = []

        for item in raw_news:
            # 1. Дедупликация
            content_hash = self._compute_hash(item.get("title", ""), item.get("source", ""))
            if content_hash in self._seen_hashes:
                continue
            self._seen_hashes.add(content_hash)

            # 2. Фильтрация по плану
            if plan_filters and not self._matches_plan(item, plan_filters):
                continue

            # 3. Классификация
            item["category"] = self._classify(item)

            # 4. Очистка текста
            item["content"] = self._clean_text(item.get("content", ""))
            item["title"] = self._clean_text(item.get("title", ""))

            # 5. Добавляем хеш
            item["content_hash"] = content_hash

            processed.append(item)

        logger.info(
            f"🔄 Препроцессор: {len(raw_news)} → {len(processed)} "
            f"(отфильтровано {len(raw_news) - len(processed)})"
        )
        return processed

    def prepare_market_data_for_agent(
        self,
        market_data: dict[str, dict],
        focus_symbols: list[str] = None,
    ) -> dict:
        """
        Подготовить рыночные данные для агента.
        Убираем лишние данные, оставляем только нужное.
        """
        if focus_symbols:
            filtered = {k: v for k, v in market_data.items() if k in focus_symbols}
        else:
            filtered = market_data

        # Компактный формат для минимизации токенов
        compact = {}
        for symbol, data in filtered.items():
            compact[symbol] = {
                "price": data.get("close", 0),
                "change_%": data.get("change_percent", 0),
                "volume_ratio": data.get("indicators", {}).get("volume_ratio", 1.0),
                "rsi": data.get("indicators", {}).get("rsi_14"),
                "macd": data.get("indicators", {}).get("macd"),
                "sma_20": data.get("indicators", {}).get("sma_20"),
                "sma_50": data.get("indicators", {}).get("sma_50"),
                "bb_upper": data.get("indicators", {}).get("bb_upper"),
                "bb_lower": data.get("indicators", {}).get("bb_lower"),
                "atr": data.get("indicators", {}).get("atr_14"),
            }

        return compact

    def _compute_hash(self, title: str, source: str) -> str:
        """SHA-256 хеш для дедупликации."""
        raw = f"{title.strip().lower()}|{source.strip().lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _matches_plan(self, item: dict, plan_filters: dict) -> bool:
        """Проверить соответствует ли новость плану Chief Planner."""
        # Фильтр по фокусным активам
        focus_assets = plan_filters.get("focus_assets", [])
        if focus_assets:
            item_symbols = item.get("asset_symbols", [])
            if item_symbols and not any(s in focus_assets for s in item_symbols):
                # Новость о конкретном неактивном тикере — пропускаем
                return False

        # Фильтр по шумовым словам
        ignored_noise = plan_filters.get("ignored_noise", [])
        if ignored_noise:
            title_lower = item.get("title", "").lower()
            if any(noise in title_lower for noise in ignored_noise):
                return False

        # Фильтр по минимальной важности
        min_importance = plan_filters.get("min_importance", 0.0)
        if item.get("importance_score", 0.0) < min_importance:
            return False

        return True

    def _classify(self, item: dict) -> str:
        """Классифицировать новость (macro, company, sector, noise)."""
        title = item.get("title", "").lower()
        content = item.get("content", "").lower()
        full = f"{title} {content}"

        # Компания
        if item.get("asset_symbols"):
            return "company"

        # Макро
        macro_kw = [
            "цб", "ключевая ставка", "инфляц", "ввп",
            "нефть", "brent", "рубль", "доллар", "санкци",
        ]
        if any(kw in full for kw in macro_kw):
            return "macro"

        # Сектор
        sector_kw = ["нефтегаз", "банковск", "технолог", "ритейл", "сектор"]
        if any(kw in full for kw in sector_kw):
            return "sector"

        return "general"

    @staticmethod
    def _clean_text(text: str) -> str:
        """Очистить текст от мусора."""
        if not text:
            return ""
        # Удаляем HTML теги
        text = re.sub(r"<[^>]+>", "", text)
        # Удаляем множественные пробелы
        text = re.sub(r"\s+", " ", text)
        # Удаляем спецсимволы
        text = text.strip()
        return text[:2000]  # Ограничиваем длину
