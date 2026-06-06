#!/usr/bin/env python3
"""
U-Haul Space Optimizer - Entry point script.

Find the smallest U-Haul trailer that fits all of your furniture.

Usage:
    python uhaul.py queen_mattress sofa dresser      # from the catalog
    python uhaul.py dining_chair:4 box_large:10      # with quantities
    python uhaul.py --file inventory.json            # from a JSON file
    python uhaul.py --list-furniture                 # see available items
"""

from uhaul_optimizer.cli import main

if __name__ == "__main__":
    main()
