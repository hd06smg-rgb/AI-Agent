import pandas as pd
from core.exchange import OKXExchange
from config.settings import TIMEFRAME, CANDLE_LIMIT
from utils.logger import logger


class DataFetcher:
    """Fetch and prepare market data as pandas DataFrames."""

    def __init__(self, exchange: OKXExchange):
        self.exchange = exchange

    def get_candles(self, symbol: str, timeframe: str = None, limit: int = None) -> pd.DataFrame:
        """
        Fetch OHLCV data and return as DataFrame.
        Columns: timestamp, open, high, low, close, volume
        """
        tf = timeframe or TIMEFRAME
        lim = limit or CANDLE_LIMIT

        ohlcv = self.exchange.fetch_ohlcv(symbol, tf, lim)

        if not ohlcv:
            logger.warning(f"No candle data for {symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        return df
