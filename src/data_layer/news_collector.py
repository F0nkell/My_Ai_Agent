"""
Agentic Investment OS — Сборщик новостей
Источники: RSS ленты (РБК, Investing.com, ТАСС, Interfax)
"""

import asyncio
from datetime import datetime
from typing import Optional

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from loguru import logger


# RSS ленты для российского финансового рынка
RSS_FEEDS = {
    "rbc_finance": {
        "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        "source": "РБК",
        "category": "general",
    },
    "rbc_economics": {
        "url": "https://rssexport.rbc.ru/rbcnews/news/20/full.rss",
        "source": "РБК Экономика",
        "category": "macro",
    },
    "investing_ru": {
        "url": "https://ru.investing.com/rss/news.rss",
        "source": "Investing.com",
        "category": "market",
    },
    "tass_economics": {
        "url": "https://tass.ru/rss/v2.xml",
        "source": "ТАСС",
        "category": "macro",
    },
    "interfax": {
        "url": "https://www.interfax.ru/rss.asp",
        "source": "Интерфакс",
        "category": "general",
    },
}

# Ключевые слова для фильтрации релевантных новостей
FINANCIAL_KEYWORDS = {
    # Общие финансовые
    "акции", "биржа", "дивиденд", "котировк", "инвестиц", "портфель",
    "облигаци", "фондов", "рынок", "капитал", "доходност",
    # Наши активы
    "лукойл", "сбербанк", "сбер", "татнефть", "сургутнефтегаз",
    "газпром", "озон", "ozon", "мосбиржа", "московская биржа",
    # Макро
    "цб", "центральный банк", "ключевая ставка", "инфляц",
    "нефть", "brent", "рубль", "доллар", "санкци",
    "ввп", "девальвац", "дефолт",
    # Секторы
    "нефтегаз", "банковск", "технолог", "ритейл",
}

# Маппинг ключевых слов -> тикеры
KEYWORD_TO_SYMBOL = {
    "лукойл": "LKOH",
    "lukoil": "LKOH",
    "сбербанк": "SBER",
    "сбер ": "SBER",
    "татнефть": "TATNP",
    "tatneft": "TATNP",
    "сургутнефтегаз": "SNGSP",
    "сургут": "SNGSP",
    "газпром": "GAZP",
    "gazprom": "GAZP",
    "озон": "OZON",
    "ozon": "OZON",
    "мосбиржа": "MOEX",
    "московская биржа": "MOEX",
}


class NewsCollector:
    """Сборщик новостей из RSS лент."""

    def __init__(self, feeds: dict = None):
        self.feeds = feeds or RSS_FEEDS

    async def collect_all(self, max_per_feed: int = 20) -> list[dict]:
        """Собрать новости из всех RSS лент."""
        all_news = []

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._fetch_feed(session, name, feed_config, max_per_feed)
                for name, feed_config in self.feeds.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"Ошибка сбора RSS: {result}")
                    continue
                all_news.extend(result)

        logger.info(f"📰 Собрано {len(all_news)} новостей из {len(self.feeds)} лент")
        return all_news

    async def _fetch_feed(
        self,
        session: aiohttp.ClientSession,
        feed_name: str,
        feed_config: dict,
        max_items: int,
    ) -> list[dict]:
        """Собрать новости из одной RSS ленты."""
        try:
            async with session.get(
                feed_config["url"],
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "InvestmentOS/1.0"},
            ) as response:
                if response.status != 200:
                    logger.warning(
                        f"RSS {feed_name}: HTTP {response.status}"
                    )
                    return []

                text = await response.text()
                feed = feedparser.parse(text)

                items = []
                for entry in feed.entries[:max_items]:
                    # Извлечение данных
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    content = ""
                    if hasattr(entry, "summary"):
                        content = BeautifulSoup(
                            entry.summary, "html.parser"
                        ).get_text(strip=True)
                    elif hasattr(entry, "description"):
                        content = BeautifulSoup(
                            entry.description, "html.parser"
                        ).get_text(strip=True)

                    # Дата публикации
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published_at = datetime(*entry.published_parsed[:6])
                        except Exception:
                            published_at = datetime.utcnow()

                    # Проверяем релевантность
                    full_text = f"{title} {content}".lower()
                    is_relevant = any(kw in full_text for kw in FINANCIAL_KEYWORDS)

                    if not is_relevant:
                        continue

                    # Извлекаем упомянутые тикеры
                    symbols = self._extract_symbols(full_text)

                    # Оценка важности (0-1)
                    importance = self._score_importance(title, content, symbols)

                    items.append({
                        "title": title,
                        "content": content[:2000],  # Ограничиваем длину
                        "source": feed_config["source"],
                        "url": entry.get("link", ""),
                        "category": feed_config["category"],
                        "published_at": published_at,
                        "asset_symbols": symbols,
                        "importance_score": importance,
                    })

                logger.debug(
                    f"RSS {feed_name}: {len(items)} релевантных из {len(feed.entries)}"
                )
                return items

        except Exception as e:
            logger.warning(f"Ошибка RSS {feed_name}: {e}")
            return []

    @staticmethod
    def _extract_symbols(text: str) -> list[str]:
        """Извлечь тикеры активов из текста."""
        symbols = set()
        for keyword, symbol in KEYWORD_TO_SYMBOL.items():
            if keyword in text:
                symbols.add(symbol)
        return list(symbols)

    @staticmethod
    def _score_importance(title: str, content: str, symbols: list) -> float:
        """Оценить важность новости (0.0 - 1.0)."""
        score = 0.3  # Базовый скор для финансовой новости

        full_text = f"{title} {content}".lower()

        # Упомянуты наши активы → +0.2
        if symbols:
            score += 0.2

        # Ключевые события → +0.1-0.3
        high_impact = [
            "ключевая ставка", "цб снизил", "цб повысил",
            "дивиденд", "санкци", "дефолт", "девальвац",
        ]
        for keyword in high_impact:
            if keyword in full_text:
                score += 0.15
                break

        # Макро → +0.1
        macro_keywords = ["инфляц", "ввп", "нефть brent", "рубль доллар"]
        for kw in macro_keywords:
            if kw in full_text:
                score += 0.1
                break

        return min(score, 1.0)
