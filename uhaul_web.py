"""Optional Flask web server for the U-Haul space optimizer.

The primary interface is the desktop app (``desktop_app.py``). This thin server
is kept for headless/remote use and shares all of its logic with the desktop
app via ``uhaul_optimizer.serialization``.
"""

import os

from flask import Flask, render_template, request, jsonify

from uhaul_optimizer.lovesac import lovesac_components_payload
from uhaul_optimizer.scraper import fetch_listing
from uhaul_optimizer.serialization import catalog_payload, optimize_payload

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    return render_template(
        "uhaul.html",
        catalog=catalog_payload(),
        lovesac=lovesac_components_payload(),
    )


@app.route("/api/optimize", methods=["POST"])
def optimize():
    data = request.get_json(silent=True) or {}
    try:
        result = optimize_payload(data.get("items", []), bool(data.get("enclosed_only", False)))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except (KeyError, TypeError) as e:
        return jsonify({"error": f"Bad item data: {e}"}), 400
    return jsonify(result)


@app.route("/api/fetch_url", methods=["POST"])
def fetch_url():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(fetch_listing(data.get("url", "")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Couldn't reach or read that page."}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
