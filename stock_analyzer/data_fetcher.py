"""Stock data fetching module using yfinance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


def fetch_stock_data(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch historical stock data from Yahoo Finance.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
        period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')
        interval: Data interval ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo')
        start_date: Start date in 'YYYY-MM-DD' format (overrides period)
        end_date: End date in 'YYYY-MM-DD' format

    Returns:
        DataFrame with OHLCV data
    """
    ticker = yf.Ticker(symbol)

    if start_date and end_date:
        df = ticker.history(start=start_date, end=end_date, interval=interval)
    elif start_date:
        df = ticker.history(start=start_date, interval=interval)
    else:
        df = ticker.history(period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No data found for symbol: {symbol}")

    # Clean up column names
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]

    return df


def get_stock_info(symbol: str) -> dict:
    """
    Get basic information about a stock.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with stock information
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info

    return {
        "symbol": symbol.upper(),
        "name": info.get("longName", "N/A"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": info.get("marketCap", "N/A"),
        "pe_ratio": info.get("trailingPE", "N/A"),
        "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
        "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
        "avg_volume": info.get("averageVolume", "N/A"),
        "current_price": info.get("currentPrice", info.get("regularMarketPrice", "N/A")),
    }


def fetch_multiple_stocks(symbols: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """
    Fetch data for multiple stocks.

    Args:
        symbols: List of stock ticker symbols
        period: Data period

    Returns:
        Dictionary mapping symbols to their DataFrames
    """
    data = {}
    for symbol in symbols:
        try:
            data[symbol] = fetch_stock_data(symbol, period=period)
        except Exception as e:
            print(f"Warning: Could not fetch data for {symbol}: {e}")

    return data
