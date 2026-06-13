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
    assert "{{ lovesac" not in html
    assert "queen_mattress" in html
    # The page knows how to talk to the desktop bridge.
    assert "window.pywebview" in html
    assert "planCanvas" in html  # load-plan diagram present
    # New UI surfaces: collapsible groups, Lovesac configurator, URL fetch.
    assert "catGroups" in html and "catgroup" in html
    assert "Lovesac" in html and "lovesacRows" in html
    assert "fetch_url" in html and 'id="u_url"' in html


def test_fetch_url_bridge_rejects_bad_urls_without_network():
    api = Api()
    assert "error" in api.fetch_url("not-a-url")
    assert "error" in api.fetch_url("http://localhost/x")
    assert "error" in api.fetch_url("")


def test_fetch_url_bridge_parses_inline_via_scraper():
    # The bridge delegates to scraper.fetch_listing; patch its network call so we
    # exercise the bridge end-to-end without hitting the internet.
    import desktop_app
    sample = (
        '<html><head><title>Test Chair</title>'
        '<script type="application/ld+json">'
        '{"@type":"Product","name":"Test Chair",'
        '"width":24,"depth":24,"height":36}</script></head></html>'
    )
    from uhaul_optimizer import scraper
    orig = scraper.fetch_listing
    desktop_app.fetch_listing = lambda url: scraper.parse_listing(sample, url)
    try:
        d = Api().fetch_url("https://store.test/chair")
        assert d["ok"] and d["name"] == "Test Chair"
        assert d["width"] == 24 and d["height"] == 36
    finally:
        desktop_app.fetch_listing = orig


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


def test_api_optimize_exposes_balance_and_placement_weights():
    api = Api()
    d = api.optimize({"items": [
        {"slug": "refrigerator", "quantity": 1},
        {"slug": "box_large", "quantity": 4},
    ]})
    rec = d["recommended"]
    assert "front_weight_pct" in rec and rec["front_weight_pct"] is not None
    assert isinstance(rec["balance_advice"], str) and rec["balance_advice"]
    # Placements carry weight so the load plan can reason about balance.
    assert all("weight" in p for p in rec["placements"])
    assert any(p["weight"] > 0 for p in rec["placements"])


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


def test_render_marks_desktop_mode():
    assert "const DESKTOP = true" in render_html()


def test_render_has_new_items_and_editable_lovesac():
    html = render_html()
    # New catalog items are baked in.
    assert "kallax" in html and "litter_robot" in html
    # Lovesac measurements are editable and persisted; sizes can be reset.
    assert "ls-dim" in html and "lovesacDims" in html and "resetLovesac" in html
    # Categories default to collapsed for a fresh load.
    assert "? d.collapsed : CATEGORY_ORDER" in html


def test_state_persists_across_app_instances():
    import tempfile
    import desktop_app

    tmp = tempfile.mktemp(suffix=".json")
    os.environ["UHAUL_STATE_FILE"] = tmp
    try:
        # A fresh launch with no file yet sees an empty load.
        assert Api().load_state() == {}
        # Save a load, then a brand-new Api (simulating a relaunch) reads it back.
        payload = {"entries": [["sofa", {"qty": 2}]], "enclosed": True, "collapsed": ["Boxes"]}
        assert Api().save_state(payload) is True
        assert Api().load_state() == payload
        assert desktop_app.state_file().exists()
    finally:
        os.environ.pop("UHAUL_STATE_FILE", None)
        try:
            os.remove(tmp)
        except OSError:
            pass


def test_load_state_tolerates_a_corrupt_file():
    import tempfile

    tmp = tempfile.mktemp(suffix=".json")
    with open(tmp, "w") as f:
        f.write("{ this is not json")
    os.environ["UHAUL_STATE_FILE"] = tmp
    try:
        assert Api().load_state() == {}   # never raises
    finally:
        os.environ.pop("UHAUL_STATE_FILE", None)
        os.remove(tmp)


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
