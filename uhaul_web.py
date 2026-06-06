"""Flask web app for the U-Haul space optimizer (mobile-friendly)."""

from flask import Flask, render_template, request, jsonify

from uhaul_optimizer.furniture import FURNITURE_CATALOG, FurnitureItem, get_catalog_item
from uhaul_optimizer.optimizer import find_minimum_trailer
from uhaul_optimizer.trailers import UHAUL_TRAILERS

app = Flask(__name__, template_folder="templates")


@app.route("/")
def index():
    """Main page with the furniture catalog pre-loaded."""
    catalog = [
        {
            "slug": slug,
            "name": item.name,
            "length": item.length,
            "width": item.width,
            "height": item.height,
            "weight": item.weight,
            "volume": round(item.volume_cuft, 1),
            "keep_upright": item.keep_upright,
            "stackable": item.stackable,
        }
        for slug, item in FURNITURE_CATALOG.items()
    ]
    return render_template("uhaul.html", catalog=catalog)


def _items_from_payload(payload: list[dict]) -> list[FurnitureItem]:
    items: list[FurnitureItem] = []
    for obj in payload:
        qty = int(obj.get("quantity", 1))
        if qty <= 0:
            continue
        if obj.get("slug") in FURNITURE_CATALOG:
            items.append(get_catalog_item(obj["slug"], qty))
        else:
            items.append(FurnitureItem(
                name=str(obj.get("name", "Custom item")),
                length=float(obj["length"]),
                width=float(obj["width"]),
                height=float(obj["height"]),
                weight=float(obj.get("weight", 0) or 0),
                quantity=qty,
                keep_upright=bool(obj.get("keep_upright", False)),
                stackable=bool(obj.get("stackable", True)),
            ))
    return items


@app.route("/api/optimize", methods=["POST"])
def optimize():
    """Return the smallest trailer that fits the submitted inventory."""
    data = request.get_json(silent=True) or {}
    payload = data.get("items", [])
    enclosed_only = bool(data.get("enclosed_only", False))

    if not payload:
        return jsonify({"error": "Add at least one item."}), 400

    try:
        items = _items_from_payload(payload)
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"error": f"Bad item data: {e}"}), 400

    if not items:
        return jsonify({"error": "Add at least one item."}), 400

    rec = find_minimum_trailer(items, enclosed_only=enclosed_only)

    def fit_dict(ev):
        return {
            "trailer": ev.trailer.name,
            "fits": ev.fits,
            "enclosed": ev.trailer.enclosed,
            "volume_cuft": ev.trailer.volume_cuft,
            "max_load": ev.trailer.max_load,
            "utilization": round(ev.utilization * 100),
            "summary": ev.trailer.summary(),
            "note": ev.trailer.note,
            "blockers": ev.blockers,
        }

    return jsonify({
        "total_volume": round(rec.total_volume_cuft),
        "total_weight": round(rec.total_weight),
        "fits_any": rec.fits_any,
        "recommended": fit_dict(rec.recommended) if rec.recommended else None,
        "evaluations": [fit_dict(e) for e in rec.evaluations],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
