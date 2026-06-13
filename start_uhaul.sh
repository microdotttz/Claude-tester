#!/usr/bin/env bash
# One-command launcher for the U-Haul Space Optimizer desktop app.
set -e
cd "$(dirname "$0")"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || { echo "Python 3 is required — install it from python.org"; exit 1; }

exec "$PY" desktop_app.py "$@"
