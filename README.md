# Stock Chart Analyzer

A Python-based technical analysis tool for analyzing stocks and generating trading signals.

## Features

- **Real-time Data**: Fetches live stock data from Yahoo Finance
- **Technical Indicators**:
  - Simple Moving Averages (SMA 20, 50, 200)
  - Exponential Moving Averages (EMA 12, 26)
  - Relative Strength Index (RSI)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - Stochastic Oscillator
  - Average True Range (ATR)
  - On-Balance Volume (OBV)
  - Volume Weighted Average Price (VWAP)
- **Signal Generation**: Automated buy/sell signals based on multiple indicators
- **Support/Resistance**: Automatic identification of key price levels
- **Visualization**: Candlestick charts with indicator overlays

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Analysis

```bash
# Analyze a stock
python analyze.py AAPL

# With a specific time period
python analyze.py GOOGL --period 6mo

# Show interactive chart
python analyze.py TSLA --chart

# Save chart to file
python analyze.py MSFT --save analysis.png

# Get basic stock info only
python analyze.py NVDA --info
```

### As a Module

```python
from stock_analyzer.data_fetcher import fetch_stock_data, get_stock_info
from stock_analyzer.indicators import add_all_indicators
from stock_analyzer.signals import generate_signals, calculate_overall_recommendation

# Fetch and analyze
df = fetch_stock_data("AAPL", period="1y")
df = add_all_indicators(df)

# Get signals
signals = generate_signals(df)
recommendation, confidence = calculate_overall_recommendation(signals)

print(f"Recommendation: {recommendation.value} ({confidence*100:.0f}% confidence)")
```

## Signal Interpretation

### RSI (Relative Strength Index)
- **< 30**: Oversold (potential buy)
- **> 70**: Overbought (potential sell)

### MACD
- **Bullish Crossover**: MACD crosses above signal line
- **Bearish Crossover**: MACD crosses below signal line

### Moving Averages
- **Golden Cross**: 50 SMA crosses above 200 SMA (strong bullish)
- **Death Cross**: 50 SMA crosses below 200 SMA (strong bearish)

### Bollinger Bands
- **Price at lower band**: Potential bounce (buy opportunity)
- **Price at upper band**: Potential pullback (sell opportunity)

## Disclaimer

**This tool is for educational and informational purposes only.**

- Past performance does not guarantee future results
- Technical analysis is not a perfect predictor of market movements
- Always conduct your own research before making investment decisions
- Consider consulting a licensed financial advisor
- Never invest more than you can afford to lose

The authors and contributors are not responsible for any financial losses incurred from using this tool.

## License

MIT License
