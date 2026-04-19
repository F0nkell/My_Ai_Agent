"""
Agentic Investment OS — Сборщик рыночных данных
Источники: MOEX ISS API (бесплатный) + yfinance (fallback)
"""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
import aiohttp
from loguru import logger


# MOEX ISS API endpoints
MOEX_BASE_URL = "https://iss.moex.com/iss"

# Маппинг наших тикеров для yfinance (добавляем .ME для MOEX)
YFINANCE_SUFFIX = {
    "LKOH": "LKOH.ME",
    "SBER": "SBER.ME",
    "SBERP": "SBERP.ME",
    "TATNP": "TATNP.ME",
    "SNGSP": "SNGSP.ME",
    "GAZP": "GAZP.ME",
    "OZON": "OZON.ME",
    "MOEX": "MOEX.ME",
}


class MarketCollector:
    """Сборщик рыночных данных с MOEX и yfinance."""

    async def get_market_data(
        self,
        symbols: list[str],
        period_days: int = 30,
    ) -> dict[str, dict]:
        """
        Получить рыночные данные для списка тикеров.
        Сначала пробуем MOEX ISS, потом yfinance как fallback.
        """
        results = {}

        for symbol in symbols:
            try:
                # Попытка через MOEX ISS API
                data = await self._fetch_moex(symbol, period_days)

                if data is None or data.empty:
                    # Fallback на yfinance
                    data = self._fetch_yfinance(symbol, period_days)

                if data is not None and not data.empty:
                    # Вычисляем технические индикаторы
                    indicators = self._compute_indicators(data)
                    latest = data.iloc[-1]

                    results[symbol] = {
                        "open": float(latest.get("open", latest.get("Open", 0))),
                        "close": float(latest.get("close", latest.get("Close", 0))),
                        "high": float(latest.get("high", latest.get("High", 0))),
                        "low": float(latest.get("low", latest.get("Low", 0))),
                        "volume": int(latest.get("volume", latest.get("Volume", 0))),
                        "change_percent": self._calc_change(data),
                        "indicators": indicators,
                        "history": self._df_to_history(data),
                        "snapshot_date": datetime.utcnow().date().isoformat(),
                    }
                    logger.debug(f"📈 {symbol}: close={results[symbol]['close']}")
                else:
                    logger.warning(f"⚠️ Нет данных для {symbol}")

            except Exception as e:
                logger.error(f"❌ Ошибка получения данных {symbol}: {e}")

        logger.info(
            f"📊 Получены рыночные данные для {len(results)}/{len(symbols)} активов"
        )
        return results

    async def _fetch_moex(
        self, symbol: str, period_days: int
    ) -> Optional[pd.DataFrame]:
        """Получить данные через MOEX ISS API."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            url = (
                f"{MOEX_BASE_URL}/engines/stock/markets/shares/boards/TQBR/"
                f"securities/{symbol}/candles.json"
            )
            params = {
                "from": start_date.strftime("%Y-%m-%d"),
                "till": end_date.strftime("%Y-%m-%d"),
                "interval": 24,  # Дневные свечи
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()
                    candles = data.get("candles", {})
                    columns = candles.get("columns", [])
                    rows = candles.get("data", [])

                    if not rows:
                        return None

                    df = pd.DataFrame(rows, columns=columns)
                    df = df.rename(columns={
                        "open": "open",
                        "close": "close",
                        "high": "high",
                        "low": "low",
                        "volume": "volume",
                        "begin": "date",
                    })
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.set_index("date").sort_index()
                    return df

        except Exception as e:
            logger.debug(f"MOEX ISS недоступен для {symbol}: {e}")
            return None

    def _fetch_yfinance(
        self, symbol: str, period_days: int
    ) -> Optional[pd.DataFrame]:
        """Fallback: получить данные через yfinance."""
        try:
            yf_symbol = YFINANCE_SUFFIX.get(symbol, f"{symbol}.ME")
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=f"{period_days}d")

            if df.empty:
                return None

            df = df.rename(columns={
                "Open": "open",
                "Close": "close",
                "High": "high",
                "Low": "low",
                "Volume": "volume",
            })
            return df

        except Exception as e:
            logger.debug(f"yfinance недоступен для {symbol}: {e}")
            return None

    def _compute_indicators(self, df: pd.DataFrame) -> dict:
        """Вычислить технические индикаторы."""
        try:
            import ta

            close = df["close"] if "close" in df.columns else df["Close"]
            high = df["high"] if "high" in df.columns else df["High"]
            low = df["low"] if "low" in df.columns else df["Low"]
            volume = df["volume"] if "volume" in df.columns else df["Volume"]

            indicators = {}

            # SMA
            if len(close) >= 20:
                indicators["sma_20"] = round(float(close.rolling(20).mean().iloc[-1]), 2)
            if len(close) >= 50:
                indicators["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2)

            # EMA
            if len(close) >= 12:
                indicators["ema_12"] = round(float(close.ewm(span=12).mean().iloc[-1]), 2)
            if len(close) >= 26:
                indicators["ema_26"] = round(float(close.ewm(span=26).mean().iloc[-1]), 2)

            # RSI
            if len(close) >= 14:
                rsi = ta.momentum.RSIIndicator(close, window=14)
                rsi_val = rsi.rsi().iloc[-1]
                indicators["rsi_14"] = round(float(rsi_val), 2) if pd.notna(rsi_val) else None

            # MACD
            if len(close) >= 26:
                macd = ta.trend.MACD(close)
                macd_line = macd.macd().iloc[-1]
                macd_signal = macd.macd_signal().iloc[-1]
                indicators["macd"] = round(float(macd_line), 4) if pd.notna(macd_line) else None
                indicators["macd_signal"] = round(float(macd_signal), 4) if pd.notna(macd_signal) else None

            # Bollinger Bands
            if len(close) >= 20:
                bb = ta.volatility.BollingerBands(close, window=20)
                indicators["bb_upper"] = round(float(bb.bollinger_hband().iloc[-1]), 2)
                indicators["bb_lower"] = round(float(bb.bollinger_lband().iloc[-1]), 2)
                indicators["bb_middle"] = round(float(bb.bollinger_mavg().iloc[-1]), 2)

            # ATR (Average True Range)
            if len(close) >= 14:
                atr = ta.volatility.AverageTrueRange(high, low, close, window=14)
                atr_val = atr.average_true_range().iloc[-1]
                indicators["atr_14"] = round(float(atr_val), 2) if pd.notna(atr_val) else None

            # Объёмный индикатор
            if len(volume) >= 20:
                avg_vol = volume.rolling(20).mean().iloc[-1]
                curr_vol = volume.iloc[-1]
                indicators["volume_ratio"] = round(float(curr_vol / avg_vol), 2) if avg_vol > 0 else 1.0

            return indicators

        except Exception as e:
            logger.warning(f"Ошибка вычисления индикаторов: {e}")
            return {}

    @staticmethod
    def _calc_change(df: pd.DataFrame) -> float:
        """Вычислить процент изменения за период."""
        close = df["close"] if "close" in df.columns else df["Close"]
        if len(close) < 2:
            return 0.0
        first = close.iloc[0]
        last = close.iloc[-1]
        if first == 0:
            return 0.0
        return round(((last - first) / first) * 100, 2)

    @staticmethod
    def _df_to_history(df: pd.DataFrame, last_n: int = 5) -> list[dict]:
        """Конвертировать DataFrame в список (для JSON)."""
        result = []
        for idx, row in df.tail(last_n).iterrows():
            result.append({
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                "close": round(float(row.get("close", row.get("Close", 0))), 2),
                "volume": int(row.get("volume", row.get("Volume", 0))),
            })
        return result


class MacroCollector:
    """Сборщик макроэкономических данных."""

    async def get_macro_data(self) -> dict:
        """Получить основные макроэкономические показатели."""
        data = {}

        try:
            # Нефть Brent
            brent = yf.Ticker("BZ=F")
            hist = brent.history(period="5d")
            if not hist.empty:
                data["brent_oil"] = {
                    "price": round(float(hist["Close"].iloc[-1]), 2),
                    "change_5d": round(
                        float(
                            ((hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                             / hist["Close"].iloc[0]) * 100
                        ), 2
                    ),
                }
        except Exception as e:
            logger.warning(f"Ошибка получения цены нефти: {e}")

        try:
            # USD/RUB
            usdrub = yf.Ticker("USDRUB=X")
            hist = usdrub.history(period="5d")
            if not hist.empty:
                data["usd_rub"] = {
                    "rate": round(float(hist["Close"].iloc[-1]), 2),
                    "change_5d": round(
                        float(
                            ((hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                             / hist["Close"].iloc[0]) * 100
                        ), 2
                    ),
                }
        except Exception as e:
            logger.warning(f"Ошибка получения USD/RUB: {e}")

        try:
            # Индекс MOEX
            moex_idx = yf.Ticker("IMOEX.ME")
            hist = moex_idx.history(period="5d")
            if not hist.empty:
                data["moex_index"] = {
                    "value": round(float(hist["Close"].iloc[-1]), 2),
                    "change_5d": round(
                        float(
                            ((hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                             / hist["Close"].iloc[0]) * 100
                        ), 2
                    ),
                }
        except Exception as e:
            logger.warning(f"Ошибка получения индекса MOEX: {e}")

        logger.info(f"🌍 Макро данные: {list(data.keys())}")
        return data
