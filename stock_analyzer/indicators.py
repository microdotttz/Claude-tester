"""Technical indicators for stock analysis."""

import pandas as pd
import numpy as np
from typing import Tuple


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI).

    RSI measures momentum and identifies overbought/oversold conditions.
    - RSI > 70: Overbought (potential sell signal)
    - RSI < 30: Oversold (potential buy signal)
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    data: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Returns:
        Tuple of (MACD line, Signal line, Histogram)

    Signals:
    - MACD crosses above signal line: Bullish
    - MACD crosses below signal line: Bearish
    """
    ema_fast = calculate_ema(data, fast_period)
    ema_slow = calculate_ema(data, slow_period)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    data: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Returns:
        Tuple of (Upper band, Middle band (SMA), Lower band)

    Signals:
    - Price near upper band: Potentially overbought
    - Price near lower band: Potentially oversold
    - Band squeeze: Low volatility, potential breakout coming
    """
    middle_band = calculate_sma(data, period)
    std = data.rolling(window=period).std()

    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    return upper_band, middle_band, lower_band


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Stochastic Oscillator.

    Returns:
        Tuple of (%K, %D)

    Signals:
    - %K > 80: Overbought
    - %K < 20: Oversold
    - %K crosses above %D: Bullish
    - %K crosses below %D: Bearish
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d = k.rolling(window=d_period).mean()

    return k, d


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range (ATR).

    ATR measures volatility. Higher ATR = more volatile.
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    return atr


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Calculate On-Balance Volume (OBV).

    OBV uses volume flow to predict price changes.
    Rising OBV suggests buying pressure.
    """
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]

    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]

    return obv


def calculate_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).

    VWAP is used as a trading benchmark.
    - Price above VWAP: Bullish
    - Price below VWAP: Bearish
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()

    return vwap


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicators to the DataFrame.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        DataFrame with all indicators added
    """
    df = df.copy()

    # Moving Averages
    df["sma_20"] = calculate_sma(df["close"], 20)
    df["sma_50"] = calculate_sma(df["close"], 50)
    df["sma_200"] = calculate_sma(df["close"], 200)
    df["ema_12"] = calculate_ema(df["close"], 12)
    df["ema_26"] = calculate_ema(df["close"], 26)

    # RSI
    df["rsi"] = calculate_rsi(df["close"])

    # MACD
    df["macd"], df["macd_signal"], df["macd_histogram"] = calculate_macd(df["close"])

    # Bollinger Bands
    df["bb_upper"], df["bb_middle"], df["bb_lower"] = calculate_bollinger_bands(df["close"])

    # Stochastic
    df["stoch_k"], df["stoch_d"] = calculate_stochastic(df["high"], df["low"], df["close"])

    # ATR
    df["atr"] = calculate_atr(df["high"], df["low"], df["close"])

    # OBV
    df["obv"] = calculate_obv(df["close"], df["volume"])

    # VWAP
    df["vwap"] = calculate_vwap(df["high"], df["low"], df["close"], df["volume"])

    return df
