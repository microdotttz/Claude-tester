"""Signal generator for buy/sell recommendations based on technical analysis."""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalType(Enum):
    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG SELL"


@dataclass
class Signal:
    """Represents a trading signal."""
    type: SignalType
    indicator: str
    reason: str
    strength: float  # 0.0 to 1.0


def check_rsi_signal(rsi: float) -> Optional[Signal]:
    """Generate signal based on RSI."""
    if pd.isna(rsi):
        return None

    if rsi < 20:
        return Signal(SignalType.STRONG_BUY, "RSI", f"Extremely oversold (RSI: {rsi:.1f})", 0.9)
    elif rsi < 30:
        return Signal(SignalType.BUY, "RSI", f"Oversold (RSI: {rsi:.1f})", 0.7)
    elif rsi > 80:
        return Signal(SignalType.STRONG_SELL, "RSI", f"Extremely overbought (RSI: {rsi:.1f})", 0.9)
    elif rsi > 70:
        return Signal(SignalType.SELL, "RSI", f"Overbought (RSI: {rsi:.1f})", 0.7)

    return None


def check_macd_signal(macd: float, signal: float, prev_macd: float, prev_signal: float) -> Optional[Signal]:
    """Generate signal based on MACD crossover."""
    if any(pd.isna([macd, signal, prev_macd, prev_signal])):
        return None

    # Bullish crossover
    if prev_macd <= prev_signal and macd > signal:
        strength = min(abs(macd - signal) / abs(signal) if signal != 0 else 0.5, 1.0)
        return Signal(SignalType.BUY, "MACD", "Bullish crossover - MACD crossed above signal line", strength)

    # Bearish crossover
    if prev_macd >= prev_signal and macd < signal:
        strength = min(abs(macd - signal) / abs(signal) if signal != 0 else 0.5, 1.0)
        return Signal(SignalType.SELL, "MACD", "Bearish crossover - MACD crossed below signal line", strength)

    return None


def check_moving_average_signal(
    close: float,
    sma_20: float,
    sma_50: float,
    sma_200: float,
    prev_close: float,
    prev_sma_20: float,
    prev_sma_50: float
) -> Optional[Signal]:
    """Generate signals based on moving average crossovers."""
    if any(pd.isna([close, sma_20, sma_50, sma_200])):
        return None

    # Golden Cross (50 SMA crosses above 200 SMA) - Strong bullish
    if not pd.isna(prev_sma_50) and prev_sma_50 <= sma_200 and sma_50 > sma_200:
        return Signal(SignalType.STRONG_BUY, "MA", "Golden Cross - 50 SMA crossed above 200 SMA", 0.9)

    # Death Cross (50 SMA crosses below 200 SMA) - Strong bearish
    if not pd.isna(prev_sma_50) and prev_sma_50 >= sma_200 and sma_50 < sma_200:
        return Signal(SignalType.STRONG_SELL, "MA", "Death Cross - 50 SMA crossed below 200 SMA", 0.9)

    # Price crosses above 20 SMA
    if not pd.isna(prev_close) and prev_close <= prev_sma_20 and close > sma_20:
        return Signal(SignalType.BUY, "MA", "Price crossed above 20 SMA", 0.6)

    # Price crosses below 20 SMA
    if not pd.isna(prev_close) and prev_close >= prev_sma_20 and close < sma_20:
        return Signal(SignalType.SELL, "MA", "Price crossed below 20 SMA", 0.6)

    return None


def check_bollinger_signal(
    close: float,
    bb_upper: float,
    bb_lower: float,
    bb_middle: float
) -> Optional[Signal]:
    """Generate signals based on Bollinger Bands."""
    if any(pd.isna([close, bb_upper, bb_lower, bb_middle])):
        return None

    band_width = bb_upper - bb_lower
    position = (close - bb_lower) / band_width if band_width > 0 else 0.5

    if position <= 0.05:  # At or below lower band
        return Signal(SignalType.BUY, "BB", f"Price at lower Bollinger Band (potential bounce)", 0.7)
    elif position >= 0.95:  # At or above upper band
        return Signal(SignalType.SELL, "BB", f"Price at upper Bollinger Band (potential pullback)", 0.7)

    return None


def check_stochastic_signal(
    k: float,
    d: float,
    prev_k: float,
    prev_d: float
) -> Optional[Signal]:
    """Generate signals based on Stochastic Oscillator."""
    if any(pd.isna([k, d, prev_k, prev_d])):
        return None

    # Oversold with bullish crossover
    if k < 20 and prev_k <= prev_d and k > d:
        return Signal(SignalType.BUY, "Stoch", "Oversold with bullish %K/%D crossover", 0.75)

    # Overbought with bearish crossover
    if k > 80 and prev_k >= prev_d and k < d:
        return Signal(SignalType.SELL, "Stoch", "Overbought with bearish %K/%D crossover", 0.75)

    return None


def check_volume_signal(volume: float, avg_volume: float, close: float, prev_close: float) -> Optional[Signal]:
    """Generate signals based on volume analysis."""
    if any(pd.isna([volume, avg_volume, close, prev_close])) or avg_volume == 0:
        return None

    volume_ratio = volume / avg_volume

    # High volume breakout
    if volume_ratio > 2.0 and close > prev_close:
        return Signal(SignalType.BUY, "Volume", f"High volume breakout ({volume_ratio:.1f}x avg volume)", 0.65)

    # High volume breakdown
    if volume_ratio > 2.0 and close < prev_close:
        return Signal(SignalType.SELL, "Volume", f"High volume breakdown ({volume_ratio:.1f}x avg volume)", 0.65)

    return None


def generate_signals(df: pd.DataFrame) -> list[Signal]:
    """
    Generate all trading signals from the latest data point.

    Args:
        df: DataFrame with all technical indicators

    Returns:
        List of active signals
    """
    if len(df) < 2:
        return []

    signals = []
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Calculate average volume
    avg_volume = df["volume"].rolling(window=20).mean().iloc[-1]

    # Check all indicators
    signal_checks = [
        check_rsi_signal(latest.get("rsi")),
        check_macd_signal(
            latest.get("macd"),
            latest.get("macd_signal"),
            prev.get("macd"),
            prev.get("macd_signal")
        ),
        check_moving_average_signal(
            latest.get("close"),
            latest.get("sma_20"),
            latest.get("sma_50"),
            latest.get("sma_200"),
            prev.get("close"),
            prev.get("sma_20"),
            prev.get("sma_50")
        ),
        check_bollinger_signal(
            latest.get("close"),
            latest.get("bb_upper"),
            latest.get("bb_lower"),
            latest.get("bb_middle")
        ),
        check_stochastic_signal(
            latest.get("stoch_k"),
            latest.get("stoch_d"),
            prev.get("stoch_k"),
            prev.get("stoch_d")
        ),
        check_volume_signal(
            latest.get("volume"),
            avg_volume,
            latest.get("close"),
            prev.get("close")
        ),
    ]

    signals = [s for s in signal_checks if s is not None]

    return signals


def calculate_overall_recommendation(signals: list[Signal]) -> tuple[SignalType, float]:
    """
    Calculate overall recommendation based on all signals.

    Returns:
        Tuple of (recommendation, confidence score)
    """
    if not signals:
        return SignalType.HOLD, 0.5

    # Weight signals by strength
    score = 0.0
    total_weight = 0.0

    signal_values = {
        SignalType.STRONG_BUY: 2.0,
        SignalType.BUY: 1.0,
        SignalType.HOLD: 0.0,
        SignalType.SELL: -1.0,
        SignalType.STRONG_SELL: -2.0,
    }

    for signal in signals:
        weight = signal.strength
        score += signal_values[signal.type] * weight
        total_weight += weight

    if total_weight > 0:
        avg_score = score / total_weight
    else:
        avg_score = 0.0

    # Convert score to recommendation
    if avg_score >= 1.5:
        recommendation = SignalType.STRONG_BUY
    elif avg_score >= 0.5:
        recommendation = SignalType.BUY
    elif avg_score <= -1.5:
        recommendation = SignalType.STRONG_SELL
    elif avg_score <= -0.5:
        recommendation = SignalType.SELL
    else:
        recommendation = SignalType.HOLD

    # Calculate confidence (how aligned are the signals)
    confidence = min(abs(avg_score) / 2.0, 1.0)

    return recommendation, confidence


def get_support_resistance(df: pd.DataFrame, lookback: int = 30) -> tuple[list[float], list[float]]:
    """
    Identify support and resistance levels.

    Returns:
        Tuple of (support_levels, resistance_levels)
    """
    recent = df.tail(lookback)

    # Find local minima for support
    lows = recent["low"].values
    supports = []
    for i in range(1, len(lows) - 1):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            supports.append(lows[i])

    # Find local maxima for resistance
    highs = recent["high"].values
    resistances = []
    for i in range(1, len(highs) - 1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            resistances.append(highs[i])

    # Cluster nearby levels
    def cluster_levels(levels: list[float], threshold: float = 0.02) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for level in levels[1:]:
            if (level - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        return [sum(c) / len(c) for c in clusters]

    current_price = df["close"].iloc[-1]
    threshold = current_price * 0.02

    return cluster_levels(supports), cluster_levels(resistances)
