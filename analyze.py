#!/usr/bin/env python3
"""
Stock Chart Analyzer - Entry point script.

Usage:
    python analyze.py AAPL           # Analyze Apple stock
    python analyze.py GOOGL -c       # Analyze Google with chart
    python analyze.py TSLA -p 6mo    # Tesla with 6 months of data
"""

from stock_analyzer.cli import main

if __name__ == "__main__":
    main()
