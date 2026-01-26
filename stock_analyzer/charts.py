"""Chart visualization module for stock analysis."""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional


def create_candlestick_chart(
    df: pd.DataFrame,
    symbol: str,
    show_volume: bool = True,
    show_ma: bool = True,
    show_bb: bool = True,
    save_path: Optional[str] = None,
    figsize: tuple = (14, 10)
) -> None:
    """
    Create a candlestick chart with optional overlays.

    Args:
        df: DataFrame with OHLCV data and indicators
        symbol: Stock symbol for title
        show_volume: Whether to show volume subplot
        show_ma: Whether to show moving averages
        show_bb: Whether to show Bollinger Bands
        save_path: Path to save the chart (if None, displays interactively)
        figsize: Figure size tuple
    """
    # Prepare data for mplfinance
    plot_df = df.copy()
    plot_df.index = pd.DatetimeIndex(plot_df.index)

    # Rename columns to match mplfinance expectations
    plot_df = plot_df.rename(columns={
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume"
    })

    # Build additional plots
    add_plots = []

    if show_ma:
        if "sma_20" in df.columns:
            add_plots.append(mpf.make_addplot(df["sma_20"], color="blue", width=1, label="SMA 20"))
        if "sma_50" in df.columns:
            add_plots.append(mpf.make_addplot(df["sma_50"], color="orange", width=1, label="SMA 50"))
        if "sma_200" in df.columns:
            add_plots.append(mpf.make_addplot(df["sma_200"], color="red", width=1.5, label="SMA 200"))

    if show_bb:
        if all(col in df.columns for col in ["bb_upper", "bb_lower"]):
            add_plots.append(mpf.make_addplot(df["bb_upper"], color="gray", linestyle="--", width=0.8))
            add_plots.append(mpf.make_addplot(df["bb_lower"], color="gray", linestyle="--", width=0.8))

    # Style configuration
    mc = mpf.make_marketcolors(
        up="green",
        down="red",
        edge="inherit",
        wick="inherit",
        volume="in"
    )
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle="-", gridcolor="lightgray")

    # Create the chart
    kwargs = {
        "type": "candle",
        "style": style,
        "title": f"{symbol} Stock Chart",
        "ylabel": "Price ($)",
        "volume": show_volume,
        "figsize": figsize,
        "tight_layout": True,
    }

    if add_plots:
        kwargs["addplot"] = add_plots

    if save_path:
        kwargs["savefig"] = save_path

    mpf.plot(plot_df, **kwargs)

    if not save_path:
        plt.show()


def create_indicator_chart(
    df: pd.DataFrame,
    symbol: str,
    save_path: Optional[str] = None,
    figsize: tuple = (14, 12)
) -> None:
    """
    Create a multi-panel chart showing price and indicators.

    Args:
        df: DataFrame with OHLCV data and indicators
        symbol: Stock symbol for title
        save_path: Path to save the chart
        figsize: Figure size tuple
    """
    fig, axes = plt.subplots(4, 1, figsize=figsize, gridspec_kw={"height_ratios": [3, 1, 1, 1]})
    fig.suptitle(f"{symbol} Technical Analysis", fontsize=14, fontweight="bold")

    # Price chart with moving averages
    ax1 = axes[0]
    ax1.plot(df.index, df["close"], label="Close", color="black", linewidth=1.5)

    if "sma_20" in df.columns:
        ax1.plot(df.index, df["sma_20"], label="SMA 20", color="blue", linewidth=1)
    if "sma_50" in df.columns:
        ax1.plot(df.index, df["sma_50"], label="SMA 50", color="orange", linewidth=1)
    if "sma_200" in df.columns:
        ax1.plot(df.index, df["sma_200"], label="SMA 200", color="red", linewidth=1)

    if all(col in df.columns for col in ["bb_upper", "bb_lower"]):
        ax1.fill_between(df.index, df["bb_upper"], df["bb_lower"], alpha=0.2, color="gray")

    ax1.set_ylabel("Price ($)")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # RSI
    ax2 = axes[1]
    if "rsi" in df.columns:
        ax2.plot(df.index, df["rsi"], color="purple", linewidth=1)
        ax2.axhline(y=70, color="red", linestyle="--", linewidth=0.8)
        ax2.axhline(y=30, color="green", linestyle="--", linewidth=0.8)
        ax2.fill_between(df.index, 70, 100, alpha=0.2, color="red")
        ax2.fill_between(df.index, 0, 30, alpha=0.2, color="green")
        ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI")
    ax2.grid(True, alpha=0.3)

    # MACD
    ax3 = axes[2]
    if all(col in df.columns for col in ["macd", "macd_signal", "macd_histogram"]):
        ax3.plot(df.index, df["macd"], label="MACD", color="blue", linewidth=1)
        ax3.plot(df.index, df["macd_signal"], label="Signal", color="orange", linewidth=1)

        colors = ["green" if val >= 0 else "red" for val in df["macd_histogram"]]
        ax3.bar(df.index, df["macd_histogram"], color=colors, alpha=0.5, width=0.8)

        ax3.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        ax3.legend(loc="upper left")
    ax3.set_ylabel("MACD")
    ax3.grid(True, alpha=0.3)

    # Stochastic
    ax4 = axes[3]
    if all(col in df.columns for col in ["stoch_k", "stoch_d"]):
        ax4.plot(df.index, df["stoch_k"], label="%K", color="blue", linewidth=1)
        ax4.plot(df.index, df["stoch_d"], label="%D", color="orange", linewidth=1)
        ax4.axhline(y=80, color="red", linestyle="--", linewidth=0.8)
        ax4.axhline(y=20, color="green", linestyle="--", linewidth=0.8)
        ax4.fill_between(df.index, 80, 100, alpha=0.2, color="red")
        ax4.fill_between(df.index, 0, 20, alpha=0.2, color="green")
        ax4.set_ylim(0, 100)
        ax4.legend(loc="upper left")
    ax4.set_ylabel("Stochastic")
    ax4.set_xlabel("Date")
    ax4.grid(True, alpha=0.3)

    # Format x-axis
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {save_path}")
    else:
        plt.show()

    plt.close()


def create_comparison_chart(
    data_dict: dict[str, pd.DataFrame],
    normalize: bool = True,
    save_path: Optional[str] = None,
    figsize: tuple = (12, 6)
) -> None:
    """
    Create a comparison chart for multiple stocks.

    Args:
        data_dict: Dictionary mapping symbols to DataFrames
        normalize: Whether to normalize prices to percentage change
        save_path: Path to save the chart
        figsize: Figure size tuple
    """
    fig, ax = plt.subplots(figsize=figsize)

    for symbol, df in data_dict.items():
        if normalize:
            # Normalize to percentage change from first value
            values = (df["close"] / df["close"].iloc[0] - 1) * 100
            ylabel = "Change (%)"
        else:
            values = df["close"]
            ylabel = "Price ($)"

        ax.plot(df.index, values, label=symbol, linewidth=1.5)

    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.set_title("Stock Comparison")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))

    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {save_path}")
    else:
        plt.show()

    plt.close()


def print_analysis_summary(
    df: pd.DataFrame,
    signals: list,
    recommendation: tuple,
    symbol: str
) -> str:
    """
    Generate a text summary of the analysis.

    Returns:
        Formatted summary string
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price_change = latest["close"] - prev["close"]
    price_change_pct = (price_change / prev["close"]) * 100

    lines = [
        "=" * 60,
        f" STOCK ANALYSIS: {symbol}",
        "=" * 60,
        "",
        f"Current Price: ${latest['close']:.2f}",
        f"Daily Change: ${price_change:+.2f} ({price_change_pct:+.2f}%)",
        f"Volume: {latest['volume']:,.0f}",
        "",
        "-" * 40,
        " TECHNICAL INDICATORS",
        "-" * 40,
    ]

    if "rsi" in df.columns and not pd.isna(latest["rsi"]):
        rsi = latest["rsi"]
        rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
        lines.append(f"RSI (14): {rsi:.1f} [{rsi_status}]")

    if "macd" in df.columns and not pd.isna(latest["macd"]):
        macd_status = "Bullish" if latest["macd"] > latest["macd_signal"] else "Bearish"
        lines.append(f"MACD: {latest['macd']:.3f} [{macd_status}]")

    if "sma_50" in df.columns and "sma_200" in df.columns:
        trend = "Bullish" if latest["sma_50"] > latest["sma_200"] else "Bearish"
        lines.append(f"Trend (50/200 SMA): {trend}")

    if "stoch_k" in df.columns and not pd.isna(latest["stoch_k"]):
        stoch_status = "Oversold" if latest["stoch_k"] < 20 else "Overbought" if latest["stoch_k"] > 80 else "Neutral"
        lines.append(f"Stochastic %K: {latest['stoch_k']:.1f} [{stoch_status}]")

    if "atr" in df.columns and not pd.isna(latest["atr"]):
        lines.append(f"ATR (14): ${latest['atr']:.2f}")

    lines.extend([
        "",
        "-" * 40,
        " SIGNALS",
        "-" * 40,
    ])

    if signals:
        for signal in signals:
            lines.append(f"  [{signal.type.value}] {signal.indicator}: {signal.reason}")
    else:
        lines.append("  No active signals")

    rec, confidence = recommendation
    lines.extend([
        "",
        "-" * 40,
        " OVERALL RECOMMENDATION",
        "-" * 40,
        f"  {rec.value} (Confidence: {confidence*100:.0f}%)",
        "",
        "=" * 60,
    ])

    return "\n".join(lines)
