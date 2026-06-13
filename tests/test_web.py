"""Tests for the U-Haul optimizer web app (API layer)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uhaul_web import app


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_index_renders_catalog():
    r = client().get("/")
    assert r.status_code == 200
    assert b"CATALOG" in r.data
    assert b"category" in r.data  # catalog entries carry UI categories
    # Web build persists via localStorage, not the desktop bridge.
    assert b"const DESKTOP = false" in r.data


def test_optimize_returns_recommendation_with_placements():
    payload = {"items": [
        {"slug": "full_mattress", "quantity": 1},
        {"slug": "box_large", "quantity": 4},
    ]}
    r = client().post("/api/optimize", json=payload)
    assert r.status_code == 200
    d = r.get_json()
    assert d["fits_any"]
    rec = d["recommended"]
    assert rec["placements"], "fitting trailers must include load-plan placements"
    # 1 mattress + 4 boxes = 5 placed units.
    assert len(rec["placements"]) == 5
    c = rec["container"]
    for p in rec["placements"]:
        # Every placement stays inside the container.
        assert 0 <= p["x"] and p["x"] + p["l"] <= c["length"] + 1e-6
        assert 0 <= p["y"] and p["y"] + p["w"] <= c["width"] + 1e-6
        assert 0 <= p["z"] and p["z"] + p["h"] <= c["height"] + 1e-6


def test_optimize_custom_item_and_flags():
    payload = {"items": [
        {"name": "Glass case", "length": 30, "width": 20, "height": 40,
         "weight": 80, "quantity": 1, "keep_upright": True, "stackable": False},
    ]}
    r = client().post("/api/optimize", json=payload)
    assert r.status_code == 200
    assert r.get_json()["fits_any"]


def test_optimize_rejects_empty_and_bad_payloads():
    c = client()
    assert c.post("/api/optimize", json={"items": []}).status_code == 400
    assert c.post("/api/optimize", json={}).status_code == 400
    r = c.post("/api/optimize", json={"items": [{"name": "broken"}]})  # no dims
    assert r.status_code == 400


def test_non_fitting_trailers_have_blockers_not_placements():
    # A king mattress is 76" wide: too wide for the small trailers.
    r = client().post("/api/optimize", json={"items": [{"slug": "king_mattress", "quantity": 1}]})
    d = r.get_json()
    for ev in d["evaluations"]:
        if not ev["fits"]:
            assert ev["blockers"]
            assert ev["placements"] == []


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
