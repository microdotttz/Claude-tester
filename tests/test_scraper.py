"""Tests for the listing parser (pure, no network) and the Lovesac configurator."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uhaul_optimizer.scraper import parse_listing, fetch_listing
from uhaul_optimizer.lovesac import lovesac_items, lovesac_components_payload


# --- JSON-LD structured data ---------------------------------------------

JSONLD_HTML = """
<html><head><title>Acme Sofa | Store</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Acme 3-Seat Sofa",
 "width":{"@type":"QuantitativeValue","value":84,"unitCode":"INH"},
 "depth":{"@type":"QuantitativeValue","value":38,"unitText":"in"},
 "height":{"@type":"QuantitativeValue","value":34,"unitCode":"INH"},
 "weight":{"@type":"QuantitativeValue","value":150,"unitCode":"LBR"}}
</script></head><body>...</body></html>
"""


def test_jsonld_dimensions_and_weight():
    r = parse_listing(JSONLD_HTML, "https://x.test/sofa")
    assert r["ok"]
    assert r["name"] == "Acme 3-Seat Sofa"
    assert r["width"] == 84 and r["length"] == 38 and r["height"] == 34
    assert r["weight"] == 150
    assert r["source"] == "structured data"


def test_jsonld_metric_units_are_converted():
    html = """<script type="application/ld+json">
    {"@type":"Product","name":"Euro Table",
     "width":{"value":100,"unitCode":"CMT"},
     "depth":{"value":50,"unitCode":"CMT"},
     "height":{"value":75,"unitText":"cm"}}</script>"""
    r = parse_listing(html)
    assert r["ok"]
    assert abs(r["width"] - 39.4) < 0.2     # 100 cm
    assert abs(r["height"] - 29.5) < 0.2    # 75 cm


def test_jsonld_inside_graph_array():
    html = """<script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
      {"@type":"BreadcrumbList"},
      {"@type":["Product","Thing"],"name":"Graphy Dresser",
       "width":60,"depth":20,"height":34}]}</script>"""
    r = parse_listing(html)
    assert r["ok"]
    assert r["name"] == "Graphy Dresser"
    assert r["width"] == 60 and r["height"] == 34


# --- page-text fallbacks --------------------------------------------------

def test_text_triple_with_trailing_unit():
    html = "<html><body><p>Overall: 48 x 24 x 18 inches. Solid oak.</p></body></html>"
    r = parse_listing(html)
    assert r["ok"]
    assert r["length"] == 48 and r["width"] == 24 and r["height"] == 18
    assert r["source"] == "page text"


def test_text_labelled_dimensions():
    html = """<div>Width: 30 in</div><div>Depth: 28 in</div>
              <div>Height: 41 in</div><div>Weight: 52 lbs</div>"""
    r = parse_listing(html)
    assert r["ok"]
    assert r["width"] == 30 and r["length"] == 28 and r["height"] == 41
    assert r["weight"] == 52


def test_unitless_triple_is_not_mistaken_for_dimensions():
    # "2 x 4 x 6" with no unit must NOT be read as dimensions.
    html = "<p>Comes in a pack: 2 x 4 x 6 available.</p>"
    r = parse_listing(html)
    assert not r["ok"]
    assert r["note"]


def test_partial_dimensions_report_progress():
    html = "<div>Width: 30 in</div><div>Height: 41 in</div>"
    r = parse_listing(html)
    assert not r["ok"]
    assert "2 of 3" in r["note"]


def test_fetch_listing_rejects_non_http_and_blocked_hosts():
    for bad in ["ftp://x/y", "file:///etc/passwd", "javascript:alert(1)",
                "http://localhost/x", "http://192.168.1.5/x"]:
        try:
            fetch_listing(bad)
            assert False, f"should have rejected {bad}"
        except ValueError:
            pass


# --- Lovesac configurator -------------------------------------------------

def test_lovesac_items_expand_by_count_with_flags():
    items = lovesac_items(sides=2, bottoms=3, cushions=5, pillows=4)
    by_name = {i.name: i for i in items}
    assert by_name["Lovesac Side (arm/back)"].quantity == 2
    assert by_name["Lovesac Seat (base)"].quantity == 3
    # Soft pieces are flexible; frames are not.
    assert by_name["Lovesac Cushion"].flexible
    assert by_name["Lovesac Throw Pillow"].flexible
    assert not by_name["Lovesac Seat (base)"].flexible


def test_lovesac_skips_zero_counts():
    items = lovesac_items(sides=0, bottoms=2, cushions=0, pillows=0)
    assert [i.name for i in items] == ["Lovesac Seat (base)"]


def test_lovesac_payload_has_labels_and_volume():
    payload = lovesac_components_payload()
    keys = [c["key"] for c in payload]
    assert keys == ["sides", "bottoms", "cushions", "pillows"]
    assert all(c["label"] and c["volume"] > 0 for c in payload)


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
