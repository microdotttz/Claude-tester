"""Tests for the desktop app layer (the parts that don't need a GUI)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# desktop_app must import without pywebview installed (it's loaded lazily).
import desktop_app
from desktop_app import Api, render_html


def test_render_html_bakes_catalog_and_bridge():
    html = render_html()
    assert "<!DOCTYPE html>" in html
    # Catalog injected as JSON, not the raw Jinja expression.
    assert "{{ catalog" not in html
    assert "queen_mattress" in html
    # The page knows how to talk to the desktop bridge.
    assert "window.pywebview" in html
    assert "planCanvas" in html  # load-plan diagram present


def test_api_optimize_returns_recommendation_with_placements():
    api = Api()
    d = api.optimize({"items": [
        {"slug": "full_mattress", "quantity": 1},
        {"slug": "box_large", "quantity": 4},
    ]})
    assert "error" not in d
    assert d["fits_any"]
    rec = d["recommended"]
    assert len(rec["placements"]) == 5
    c = rec["container"]
    for p in rec["placements"]:
        assert 0 <= p["x"] and p["x"] + p["l"] <= c["length"] + 1e-6
        assert 0 <= p["y"] and p["y"] + p["w"] <= c["width"] + 1e-6
        assert 0 <= p["z"] and p["z"] + p["h"] <= c["height"] + 1e-6


def test_api_optimize_custom_item_with_flags():
    api = Api()
    d = api.optimize({"items": [
        {"name": "Glass case", "length": 30, "width": 20, "height": 40,
         "weight": 80, "quantity": 1, "keep_upright": True, "stackable": False},
    ]})
    assert d.get("fits_any")


def test_api_optimize_errors_are_returned_not_raised():
    api = Api()
    assert api.optimize({"items": []}) == {"error": "Add at least one item."}
    assert api.optimize({}) == {"error": "Add at least one item."}
    bad = api.optimize({"items": [{"name": "broken"}]})  # missing dimensions
    assert "error" in bad


def test_api_optimize_enclosed_only():
    api = Api()
    d = api.optimize({"items": [{"slug": "box_medium", "quantity": 2}], "enclosed_only": True})
    assert d["fits_any"]
    assert d["recommended"]["enclosed"]


def test_main_is_callable_without_gui():
    # We can't open a window here, but main() should exist and the lazy
    # pywebview import must not have happened at module load.
    assert callable(desktop_app.main)
    assert "webview" not in dir(desktop_app) or desktop_app.__dict__.get("webview") is None


if __name__ == "__main__":
    import traceback

    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failures += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(funcs) - failures}/{len(funcs)} passed")
    sys.exit(1 if failures else 0)
