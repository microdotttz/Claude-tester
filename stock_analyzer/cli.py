"""Command-line interface for the stock analyzer."""

import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .data_fetcher import fetch_stock_data, get_stock_info
from .indicators import add_all_indicators
from .signals import generate_signals, calculate_overall_recommendation, get_support_resistance, SignalType
from .charts import create_candlestick_chart, create_indicator_chart, print_analysis_summary


console = Console()


def display_stock_info(info: dict) -> None:
    """Display stock information in a formatted table."""
    table = Table(title=f"Stock Information: {info['symbol']}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    for key, value in info.items():
        if key == "symbol":
            continue
        formatted_key = key.replace("_", " ").title()
        if isinstance(value, (int, float)) and key in ["market_cap", "avg_volume"]:
            value = f"{value:,.0f}"
        elif isinstance(value, float):
            value = f"{value:.2f}"
        table.add_row(formatted_key, str(value))

    console.print(table)


def display_signals(signals: list, recommendation: tuple) -> None:
    """Display trading signals in a formatted panel."""
    rec, confidence = recommendation

    # Color based on recommendation
    colors = {
        SignalType.STRONG_BUY: "bold green",
        SignalType.BUY: "green",
        SignalType.HOLD: "yellow",
        SignalType.SELL: "red",
        SignalType.STRONG_SELL: "bold red",
    }

    rec_text = Text()
    rec_text.append(f"\n{rec.value}", style=colors.get(rec, "white"))
    rec_text.append(f" (Confidence: {confidence*100:.0f}%)\n")

    console.print(Panel(rec_text, title="Overall Recommendation", border_style=colors.get(rec, "white")))

    if signals:
        table = Table(title="Active Signals")
        table.add_column("Type", style="cyan")
        table.add_column("Indicator", style="magenta")
        table.add_column("Reason", style="white")
        table.add_column("Strength", style="yellow")

        for signal in signals:
            signal_color = colors.get(signal.type, "white")
            table.add_row(
                Text(signal.type.value, style=signal_color),
                signal.indicator,
                signal.reason,
                f"{signal.strength*100:.0f}%"
            )

        console.print(table)
    else:
        console.print("[yellow]No active trading signals[/yellow]")


def display_indicators(df) -> None:
    """Display current indicator values."""
    latest = df.iloc[-1]

    table = Table(title="Current Indicator Values")
    table.add_column("Indicator", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Status", style="yellow")

    # RSI
    if "rsi" in df.columns:
        rsi = latest["rsi"]
        status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
        color = "green" if rsi < 30 else "red" if rsi > 70 else "yellow"
        table.add_row("RSI (14)", f"{rsi:.1f}", Text(status, style=color))

    # MACD
    if "macd" in df.columns:
        macd = latest["macd"]
        signal = latest["macd_signal"]
        status = "Bullish" if macd > signal else "Bearish"
        color = "green" if macd > signal else "red"
        table.add_row("MACD", f"{macd:.3f}", Text(status, style=color))

    # Stochastic
    if "stoch_k" in df.columns:
        k = latest["stoch_k"]
        status = "Oversold" if k < 20 else "Overbought" if k > 80 else "Neutral"
        color = "green" if k < 20 else "red" if k > 80 else "yellow"
        table.add_row("Stochastic %K", f"{k:.1f}", Text(status, style=color))

    # Bollinger Band position
    if all(col in df.columns for col in ["close", "bb_upper", "bb_lower"]):
        close = latest["close"]
        bb_pos = (close - latest["bb_lower"]) / (latest["bb_upper"] - latest["bb_lower"]) * 100
        status = "Near Lower" if bb_pos < 20 else "Near Upper" if bb_pos > 80 else "Middle"
        color = "green" if bb_pos < 20 else "red" if bb_pos > 80 else "yellow"
        table.add_row("BB Position", f"{bb_pos:.1f}%", Text(status, style=color))

    # Moving Average Trend
    if all(col in df.columns for col in ["sma_50", "sma_200"]):
        trend = "Bullish" if latest["sma_50"] > latest["sma_200"] else "Bearish"
        color = "green" if trend == "Bullish" else "red"
        table.add_row("Trend (50/200)", "-", Text(trend, style=color))

    console.print(table)


def display_support_resistance(df, supports: list, resistances: list) -> None:
    """Display support and resistance levels."""
    current_price = df["close"].iloc[-1]

    table = Table(title="Support & Resistance Levels")
    table.add_column("Type", style="cyan")
    table.add_column("Price", style="green")
    table.add_column("Distance", style="yellow")

    # Filter to relevant levels
    relevant_supports = [s for s in supports if s < current_price][-3:]
    relevant_resistances = [r for r in resistances if r > current_price][:3]

    for r in reversed(relevant_resistances):
        dist = ((r - current_price) / current_price) * 100
        table.add_row("Resistance", f"${r:.2f}", f"+{dist:.1f}%")

    table.add_row("[bold]Current Price[/bold]", f"[bold]${current_price:.2f}[/bold]", "-")

    for s in reversed(relevant_supports):
        dist = ((current_price - s) / current_price) * 100
        table.add_row("Support", f"${s:.2f}", f"-{dist:.1f}%")

    console.print(table)


def analyze_stock(symbol: str, period: str = "1y", show_chart: bool = False, save_chart: str = None) -> None:
    """Run complete analysis on a stock."""
    console.print(f"\n[bold blue]Analyzing {symbol.upper()}...[/bold blue]\n")

    try:
        # Fetch data
        with console.status("Fetching stock data..."):
            df = fetch_stock_data(symbol, period=period)
            info = get_stock_info(symbol)

        # Add indicators
        with console.status("Calculating indicators..."):
            df = add_all_indicators(df)

        # Generate signals
        signals = generate_signals(df)
        recommendation = calculate_overall_recommendation(signals)

        # Get support/resistance
        supports, resistances = get_support_resistance(df)

        # Display results
        display_stock_info(info)
        console.print()

        display_indicators(df)
        console.print()

        display_signals(signals, recommendation)
        console.print()

        display_support_resistance(df, supports, resistances)

        # Show/save chart
        if show_chart or save_chart:
            console.print("\n[bold]Generating chart...[/bold]")
            create_indicator_chart(df, symbol.upper(), save_path=save_chart)

    except Exception as e:
        console.print(f"[bold red]Error analyzing {symbol}: {e}[/bold red]")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Stock Chart Analyzer - Technical analysis tool for market timing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s AAPL                    Analyze Apple stock
  %(prog)s GOOGL --period 6mo      Analyze Google with 6 months of data
  %(prog)s TSLA --chart            Analyze Tesla and show chart
  %(prog)s MSFT --save chart.png   Analyze Microsoft and save chart

Disclaimer:
  This tool is for educational purposes only. Past performance does not
  guarantee future results. Always do your own research before investing.
        """
    )

    parser.add_argument("symbol", help="Stock ticker symbol (e.g., AAPL, GOOGL)")
    parser.add_argument(
        "--period", "-p",
        default="1y",
        choices=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        help="Historical data period (default: 1y)"
    )
    parser.add_argument(
        "--chart", "-c",
        action="store_true",
        help="Display interactive chart"
    )
    parser.add_argument(
        "--save", "-s",
        metavar="PATH",
        help="Save chart to file (e.g., chart.png)"
    )
    parser.add_argument(
        "--info", "-i",
        action="store_true",
        help="Show only basic stock information"
    )

    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold blue]Stock Chart Analyzer[/bold blue]\n"
        "[dim]Technical Analysis for Market Timing[/dim]",
        border_style="blue"
    ))

    if args.info:
        try:
            info = get_stock_info(args.symbol)
            display_stock_info(info)
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")
            sys.exit(1)
    else:
        analyze_stock(
            args.symbol,
            period=args.period,
            show_chart=args.chart,
            save_chart=args.save
        )


if __name__ == "__main__":
    main()
