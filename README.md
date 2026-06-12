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
- **Mobile Web App**: Responsive web interface accessible from any phone

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

### Mobile Web App (Access from Phone)

Run the web server on your computer:

```bash
python web_app.py
```

Then access from your phone:

1. **Same WiFi Network**: Open your phone's browser and go to `http://<your-computer-ip>:5000`
   - Find your computer's IP: `ipconfig` (Windows) or `ifconfig`/`ip addr` (Mac/Linux)
   - Example: `http://192.168.1.100:5000`

2. **Add to Home Screen** (optional):
   - iOS: Tap Share → "Add to Home Screen"
   - Android: Tap menu → "Add to Home Screen"

3. **Cloud Deployment** (access from anywhere):
   ```bash
   # Using ngrok for quick public URL
   ngrok http 5000

   # Or deploy to a cloud service like Railway, Render, or Heroku
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

---

# U-Haul Space Optimizer

A space optimizer that finds the **smallest U-Haul trailer** that fits all of
your furniture. It models each piece in 3D, packs them with a bin-packing
heuristic, and checks volume, interior dimensions, door clearance, and weight
limits for every trailer in the catalog.

## How it works

For each trailer (smallest to largest), it verifies:

1. **Weight** — total payload is under the trailer's max load.
2. **Dimensions** — every item physically fits the interior in some rotation.
3. **Door clearance** — every item fits through the door opening, straight-on
   or tilted diagonally (how a 54"-wide mattress really enters a 48" door).
4. **Volume** — the furniture's total volume doesn't exceed the trailer.
5. **3D packing** — a greedy "maximal empty spaces" packer actually arranges
   all the pieces inside, respecting `keep_upright` and `stackable` flags.

The first trailer that passes all checks is the recommendation.

> Packing in 3D is NP-hard, so this is a heuristic estimate. A successful pack
> means "this should fit with careful loading." Confirm exact trailer specs and
> weight limits at [uhaul.com](https://www.uhaul.com) and measure tight pieces.

## Quick start (web app)

One command — it installs Flask if needed, picks a free port, and opens your
browser:

```bash
./start_uhaul.sh          # macOS / Linux
start_uhaul.bat           # Windows (double-click works too)
python launch_uhaul.py    # any platform
```

The terminal also prints a `http://<your-ip>:<port>` URL you can open on your
phone over the same WiFi. Useful flags: `--port N`, `--no-browser`.

The web UI gives you:

- **Quick presets** — Dorm room, Studio, and 1-Bedroom starting points
- A **categorized, searchable furniture catalog** — tap a card to add it
- **Custom items** with dimensions, weight, upright/no-stack flags
- An animated recommendation card with a capacity gauge
- An **interactive isometric load plan** — drag the slider to step through the
  exact loading order the packer computed, item by item
- A per-trailer breakdown explaining *why* each trailer does or doesn't fit
- Your load is saved in the browser, so it survives a refresh

## CLI usage

```bash
# Pick items from the built-in catalog (slug[:quantity])
python uhaul.py queen_mattress sofa dresser dining_chair:4 box_large:8

# Restrict to enclosed (weatherproof) trailers
python uhaul.py refrigerator washer dryer --enclosed-only

# Add a custom item:  "Name=LengthxWidthxHeight:weight:quantity"  (inches/lbs)
python uhaul.py "Antique hutch=44x20x72:150" sofa coffee_table

# Load a full inventory from JSON
python uhaul.py --file inventory.json

# Browse what's available
python uhaul.py --list-furniture
python uhaul.py --list-trailers
```

`inventory.json` can be a list of catalog references and/or custom items:

```json
[
  { "slug": "queen_mattress", "quantity": 1 },
  { "slug": "sofa", "quantity": 1 },
  { "name": "Tool chest", "length": 40, "width": 22, "height": 38,
    "weight": 120, "quantity": 1, "keep_upright": true, "stackable": false }
]
```

## As a module

```python
from uhaul_optimizer import find_minimum_trailer, get_catalog_item, FurnitureItem

items = [
    get_catalog_item("queen_mattress"),
    get_catalog_item("sofa"),
    FurnitureItem("Tool chest", 40, 22, 38, weight=120, keep_upright=True),
]

rec = find_minimum_trailer(items)
if rec.recommended:
    print(f"Use a {rec.recommended.trailer.name} "
          f"(~{rec.recommended.utilization*100:.0f}% full)")
else:
    print("No single trailer fits — consider a moving truck.")
```

## Item flags

- `keep_upright` — the piece may only rotate about the vertical axis (dressers,
  washers, TVs). Tall pieces like refrigerators and bookshelves are taller than
  every trailer ceiling, so they're modeled to travel on their side or back; in
  a truck, always move appliances upright.
- `stackable` — whether other items may be placed on top. Glass tabletops and
  TVs are flagged non-stackable so the space above them stays clear.

## Tests

```bash
python tests/test_optimizer.py   # packing engine + trailer evaluation
python tests/test_web.py         # web API
```

## Disclaimer

Trailer dimensions are approximate published values and vary by model year.
This tool is for planning estimates only — always verify the exact trailer,
its interior dimensions, and its load rating before you reserve and load.

## License

MIT License
