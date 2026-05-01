import pandas as pd
import numpy as np
from config.settings import (
    RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    SUPERTREND_PERIOD, SUPERTREND_MULTIPLIER
)


class TechnicalIndicators:
    """Calculate technical indicators: RSI, MACD, SuperTrend."""

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = None) -> pd.Series:
        """Calculate Relative Strength Index."""
        period = period or RSI_PERIOD
        close = df["close"]

        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = None, slow: int = None,
                       signal: int = None) -> tuple:
        """
        Calculate MACD.
        Returns: (macd_line, signal_line, histogram)
        """
        fast = fast or MACD_FAST
        slow = slow or MACD_SLOW
        signal = signal or MACD_SIGNAL

        close = df["close"]

        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_supertrend(df: pd.DataFrame, period: int = None,
                              multiplier: float = None) -> tuple:
        """
        Calculate SuperTrend indicator.
        Returns: (supertrend_values, direction)
        direction: 1 = bullish (price above supertrend), -1 = bearish
        """
        period = period or SUPERTREND_PERIOD
        multiplier = multiplier or SUPERTREND_MULTIPLIER

        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Calculate ATR
        hl = high - low
        hc = (high - close.shift(1)).abs()
        lc = (low - close.shift(1)).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        # Calculate basic bands
        hl2 = (high + low) / 2
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        # Initialize SuperTrend
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        supertrend.iloc[0] = upper_band.iloc[0]
        direction.iloc[0] = -1

        for i in range(1, len(df)):
            # Update lower band
            if lower_band.iloc[i] > lower_band.iloc[i - 1] or close.iloc[i - 1] < lower_band.iloc[i - 1]:
                pass  # Keep current lower band
            else:
                lower_band.iloc[i] = lower_band.iloc[i - 1]

            # Update upper band
            if upper_band.iloc[i] < upper_band.iloc[i - 1] or close.iloc[i - 1] > upper_band.iloc[i - 1]:
                pass  # Keep current upper band
            else:
                upper_band.iloc[i] = upper_band.iloc[i - 1]

            # Determine direction
            if supertrend.iloc[i - 1] == upper_band.iloc[i - 1]:
                if close.iloc[i] > upper_band.iloc[i]:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
            else:
                if close.iloc[i] < lower_band.iloc[i]:
                    supertrend.iloc[i] = upper_band.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = lower_band.iloc[i]
                    direction.iloc[i] = 1

        return supertrend, direction

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range for SL/TP."""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        hl = high - low
        hc = (high - close.shift(1)).abs()
        lc = (low - close.shift(1)).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def get_rsi_signal(rsi_value: float) -> int:
        """
        Get RSI signal.
        Returns: 1 (LONG), -1 (SHORT), 0 (NEUTRAL)
        """
        if rsi_value <= RSI_OVERSOLD:
            return 1   # Oversold → LONG signal
        elif rsi_value >= RSI_OVERBOUGHT:
            return -1  # Overbought → SHORT signal
        return 0

    @staticmethod
    def get_macd_signal(macd_line: pd.Series, signal_line: pd.Series) -> int:
        """
        Get MACD crossover signal.
        Returns: 1 (LONG), -1 (SHORT), 0 (NEUTRAL)
        """
        if len(macd_line) < 2:
            return 0

        # Current and previous values
        macd_curr = macd_line.iloc[-1]
        macd_prev = macd_line.iloc[-2]
        signal_curr = signal_line.iloc[-1]
        signal_prev = signal_line.iloc[-2]

        # Bullish crossover: MACD crosses above signal
        if macd_prev <= signal_prev and macd_curr > signal_curr:
            return 1
        # Bearish crossover: MACD crosses below signal
        elif macd_prev >= signal_prev and macd_curr < signal_curr:
            return -1

        # Continuation: MACD above signal = bullish momentum
        if macd_curr > signal_curr:
            return 1
        elif macd_curr < signal_curr:
            return -1

        return 0

    @staticmethod
    def get_supertrend_signal(direction: pd.Series) -> int:
        """
        Get SuperTrend signal.
        Returns: 1 (LONG/bullish), -1 (SHORT/bearish)
        """
        if len(direction) == 0:
            return 0
        return int(direction.iloc[-1])
