"""Flask web application for mobile-friendly stock analysis."""

from flask import Flask, render_template, request, jsonify
from stock_analyzer.data_fetcher import fetch_stock_data, get_stock_info
from stock_analyzer.indicators import add_all_indicators
from stock_analyzer.signals import generate_signals, calculate_overall_recommendation, get_support_resistance
import pandas as pd
import json

app = Flask(__name__, template_folder="templates", static_folder="static")


def dataframe_to_chart_data(df: pd.DataFrame) -> dict:
    """Convert DataFrame to JSON-serializable chart data."""
    df = df.copy()
    df.index = df.index.strftime("%Y-%m-%d")

    return {
        "dates": df.index.tolist(),
        "ohlc": {
            "open": df["open"].round(2).tolist(),
            "high": df["high"].round(2).tolist(),
            "low": df["low"].round(2).tolist(),
            "close": df["close"].round(2).tolist(),
        },
        "volume": df["volume"].tolist(),
        "indicators": {
            "sma_20": df["sma_20"].round(2).fillna("null").tolist() if "sma_20" in df else [],
            "sma_50": df["sma_50"].round(2).fillna("null").tolist() if "sma_50" in df else [],
            "sma_200": df["sma_200"].round(2).fillna("null").tolist() if "sma_200" in df else [],
            "bb_upper": df["bb_upper"].round(2).fillna("null").tolist() if "bb_upper" in df else [],
            "bb_lower": df["bb_lower"].round(2).fillna("null").tolist() if "bb_lower" in df else [],
            "rsi": df["rsi"].round(2).fillna("null").tolist() if "rsi" in df else [],
            "macd": df["macd"].round(4).fillna("null").tolist() if "macd" in df else [],
            "macd_signal": df["macd_signal"].round(4).fillna("null").tolist() if "macd_signal" in df else [],
            "macd_histogram": df["macd_histogram"].round(4).fillna("null").tolist() if "macd_histogram" in df else [],
        }
    }


@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """API endpoint for stock analysis."""
    data = request.get_json()
    symbol = data.get("symbol", "").upper().strip()
    period = data.get("period", "6mo")

    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    try:
        # Fetch data
        df = fetch_stock_data(symbol, period=period)
        if df.empty:
            return jsonify({"error": f"No data found for {symbol}"}), 404

        # Add indicators
        df = add_all_indicators(df)

        # Generate signals
        signals = generate_signals(df)
        recommendation, confidence = calculate_overall_recommendation(signals)

        # Get support/resistance
        supports, resistances = get_support_resistance(df)

        # Get stock info
        info = get_stock_info(symbol)

        # Latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        price_change = latest["close"] - prev["close"]
        price_change_pct = (price_change / prev["close"]) * 100 if prev["close"] != 0 else 0

        response = {
            "symbol": symbol,
            "company_name": info.get("name", symbol),
            "current_price": round(latest["close"], 2),
            "price_change": round(price_change, 2),
            "price_change_pct": round(price_change_pct, 2),
            "volume": int(latest["volume"]),
            "market_cap": info.get("market_cap"),
            "pe_ratio": info.get("pe_ratio"),
            "dividend_yield": info.get("dividend_yield"),
            "week_52_high": info.get("52_week_high"),
            "week_52_low": info.get("52_week_low"),
            "indicators": {
                "rsi": round(latest["rsi"], 1) if pd.notna(latest.get("rsi")) else None,
                "macd": round(latest["macd"], 4) if pd.notna(latest.get("macd")) else None,
                "macd_signal": round(latest["macd_signal"], 4) if pd.notna(latest.get("macd_signal")) else None,
                "sma_20": round(latest["sma_20"], 2) if pd.notna(latest.get("sma_20")) else None,
                "sma_50": round(latest["sma_50"], 2) if pd.notna(latest.get("sma_50")) else None,
                "sma_200": round(latest["sma_200"], 2) if pd.notna(latest.get("sma_200")) else None,
                "stoch_k": round(latest["stoch_k"], 1) if pd.notna(latest.get("stoch_k")) else None,
                "atr": round(latest["atr"], 2) if pd.notna(latest.get("atr")) else None,
            },
            "signals": [
                {
                    "type": s.type.value,
                    "indicator": s.indicator,
                    "reason": s.reason,
                    "strength": round(s.strength, 2)
                }
                for s in signals
            ],
            "recommendation": {
                "action": recommendation.value,
                "confidence": round(confidence * 100)
            },
            "support_levels": [round(s, 2) for s in supports[:3]],
            "resistance_levels": [round(r, 2) for r in resistances[:3]],
            "chart_data": dataframe_to_chart_data(df.tail(120))  # Last 120 days for chart
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/search", methods=["GET"])
def search():
    """Search for stock symbols."""
    query = request.args.get("q", "").upper()

    # Common stocks for quick suggestions
    common_stocks = [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "GOOGL", "name": "Alphabet Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "AMZN", "name": "Amazon.com Inc."},
        {"symbol": "TSLA", "name": "Tesla Inc."},
        {"symbol": "META", "name": "Meta Platforms Inc."},
        {"symbol": "NVDA", "name": "NVIDIA Corporation"},
        {"symbol": "AMD", "name": "Advanced Micro Devices"},
        {"symbol": "NFLX", "name": "Netflix Inc."},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
        {"symbol": "V", "name": "Visa Inc."},
        {"symbol": "DIS", "name": "The Walt Disney Company"},
        {"symbol": "BA", "name": "Boeing Company"},
        {"symbol": "COIN", "name": "Coinbase Global Inc."},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF"},
        {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
    ]

    if not query:
        return jsonify(common_stocks[:8])

    matches = [s for s in common_stocks if query in s["symbol"] or query in s["name"].upper()]
    return jsonify(matches[:8])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
