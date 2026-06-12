#!/usr/bin/env bash
# Double-clickable / one-command launcher for the U-Haul Space Optimizer.
set -e
cd "$(dirname "$0")"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || { echo "Python 3 is required — install it from python.org"; exit 1; }

exec "$PY" launch_uhaul.py "$@"
