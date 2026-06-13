"""Best-effort extraction of furniture dimensions from a product listing URL.

``parse_listing(html)`` is pure (no network) so it can be unit-tested against
saved HTML. ``fetch_listing(url)`` is the thin wrapper that actually downloads
a page and parses it.

Two strategies, tried in order:

1. **Structured data** -- schema.org ``Product`` JSON-LD with
   ``width``/``depth``/``height``/``weight`` ``QuantitativeValue``s. Most major
   retailers embed this, and it is the most reliable source.
2. **Page text** -- regexes for "34 x 38 x 30 in" triples and for labeled
   "Width: 34 in" / "Height: 30 in" lines.

Everything is returned for the user to review and edit; furniture listings are
inconsistent, so this is an assist, not an oracle.
"""

from __future__ import annotations

import json
import re
import urllib.request
from html import unescape
from urllib.parse import urlparse

# Length units -> inches.
_LEN_TO_IN = {
    "in": 1.0, "inch": 1.0, "inches": 1.0, '"': 1.0,
    "ft": 12.0, "foot": 12.0, "feet": 12.0, "'": 12.0,
    "cm": 0.393701, "centimeter": 0.393701, "centimeters": 0.393701,
    "mm": 0.0393701, "millimeter": 0.0393701,
    "m": 39.3701, "meter": 39.3701, "meters": 39.3701,
}
# Weight units -> pounds.
_WT_TO_LB = {
    "lb": 1.0, "lbs": 1.0, "pound": 1.0, "pounds": 1.0,
    "kg": 2.20462, "kgs": 2.20462, "kilogram": 2.20462, "kilograms": 2.20462,
    "g": 0.00220462, "gram": 0.00220462, "grams": 0.00220462,
}
# UN/CEFACT unit codes used in schema.org QuantitativeValue.
_UNIT_CODE = {
    "INH": ("len", 1.0), "FOT": ("len", 12.0), "CMT": ("len", 0.393701),
    "MMT": ("len", 0.0393701), "MTR": ("len", 39.3701),
    "LBR": ("wt", 1.0), "KGM": ("wt", 2.20462), "GRM": ("wt", 0.00220462),
}

_MAX_BYTES = 3_000_000
_TIMEOUT = 12
_UA = "Mozilla/5.0 (compatible; UHaulOptimizer/1.0; +furniture sizing)"


def _round(x: float | None) -> float | None:
    return round(x, 1) if x is not None else None


def _qv_to_inches(node) -> float | None:
    """Convert a schema.org dimension (QuantitativeValue, number, or string)."""
    if node is None:
        return None
    if isinstance(node, (int, float)):
        return float(node)
    if isinstance(node, str):
        m = re.search(r"(\d+(?:\.\d+)?)", node)
        if not m:
            return None
        val = float(m.group(1))
        for unit, factor in _LEN_TO_IN.items():
            if unit.isalpha() and re.search(rf"\b{unit}\b", node.lower()):
                return val * factor
        return val  # assume inches if unlabeled
    if isinstance(node, dict):
        val = node.get("value")
        if val is None:
            return None
        try:
            val = float(val)
        except (TypeError, ValueError):
            return None
        code = (node.get("unitCode") or "").upper()
        if code in _UNIT_CODE and _UNIT_CODE[code][0] == "len":
            return val * _UNIT_CODE[code][1]
        text = (node.get("unitText") or "").lower().strip()
        if text in _LEN_TO_IN:
            return val * _LEN_TO_IN[text]
        return val  # assume inches
    return None


def _qv_to_lbs(node) -> float | None:
    if node is None:
        return None
    if isinstance(node, (int, float)):
        return float(node)
    if isinstance(node, str):
        m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]+)?", node.lower())
        if not m:
            return None
        val = float(m.group(1))
        unit = (m.group(2) or "lb")
        return val * _WT_TO_LB.get(unit, 1.0)
    if isinstance(node, dict):
        val = node.get("value")
        try:
            val = float(val)
        except (TypeError, ValueError):
            return None
        code = (node.get("unitCode") or "").upper()
        if code in _UNIT_CODE and _UNIT_CODE[code][0] == "wt":
            return val * _UNIT_CODE[code][1]
        text = (node.get("unitText") or "").lower().strip()
        return val * _WT_TO_LB.get(text, 1.0)
    return None


def _iter_nodes(data):
    """Yield every dict in a nested JSON-LD structure (objects, arrays, @graph)."""
    if isinstance(data, dict):
        yield data
        for v in data.values():
            yield from _iter_nodes(v)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)


def _is_product(node: dict) -> bool:
    t = node.get("@type")
    if isinstance(t, list):
        return any("Product" in str(x) for x in t)
    return "Product" in str(t or "")


def _from_jsonld(html: str) -> dict | None:
    """Pull name/dimensions/weight from schema.org Product JSON-LD, if present."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.S | re.I,
    )
    for raw in blocks:
        raw = raw.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _iter_nodes(data):
            if not isinstance(node, dict) or not _is_product(node):
                continue
            length = _qv_to_inches(node.get("depth")) or _qv_to_inches(node.get("length"))
            width = _qv_to_inches(node.get("width"))
            height = _qv_to_inches(node.get("height"))
            if not any((length, width, height)):
                continue
            name = node.get("name")
            if isinstance(name, dict):
                name = name.get("@value")
            return {
                "name": unescape(name.strip()) if isinstance(name, str) else None,
                "length": _round(length),
                "width": _round(width),
                "height": _round(height),
                "weight": _round(_qv_to_lbs(node.get("weight"))),
                "source": "structured data",
            }
    return None


def _strip_tags(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return unescape(re.sub(r"<[^>]+>", " ", html))


_NUM = r"(\d+(?:\.\d+)?)"
_LEN_UNIT = r'(?:in(?:ch(?:es)?)?|"|cm|mm|ft|feet|foot|\'|m)'

# "34 x 38 x 30 in"  /  "34\" W x 38\" D x 30\" H"  -- a trailing unit (or inch
# mark) is required so we don't match things like a "2 x 4 x 6" board count.
_TRIPLE = re.compile(
    rf'{_NUM}\s*(?:{_LEN_UNIT})?\s*[a-z]?\s*[x×]\s*'
    rf'{_NUM}\s*(?:{_LEN_UNIT})?\s*[a-z]?\s*[x×]\s*'
    rf'{_NUM}\s*({_LEN_UNIT})',
    re.I,
)
_LABELLED = {
    "length": re.compile(rf'(?:length|depth)\s*[:=]?\s*{_NUM}\s*({_LEN_UNIT})?', re.I),
    "width": re.compile(rf'\bwidth\s*[:=]?\s*{_NUM}\s*({_LEN_UNIT})?', re.I),
    "height": re.compile(rf'\bheight\s*[:=]?\s*{_NUM}\s*({_LEN_UNIT})?', re.I),
}
_WEIGHT = re.compile(rf'weight\s*[:=]?\s*{_NUM}\s*(lbs?|pounds?|kgs?|kilograms?)', re.I)


def _unit_factor(unit: str | None) -> float:
    if not unit:
        return 1.0
    return _LEN_TO_IN.get(unit.lower().strip(), 1.0)


def _from_text(text: str) -> dict:
    out: dict = {"name": None, "length": None, "width": None, "height": None,
                 "weight": None, "source": None}
    m = _TRIPLE.search(text)
    if m:
        factor = _unit_factor(m.group(4))
        out["length"] = _round(float(m.group(1)) * factor)
        out["width"] = _round(float(m.group(2)) * factor)
        out["height"] = _round(float(m.group(3)) * factor)
        out["source"] = "page text"
    else:
        for field, rx in _LABELLED.items():
            lm = rx.search(text)
            if lm:
                out[field] = _round(float(lm.group(1)) * _unit_factor(lm.group(2)))
                out["source"] = "page text"
    wm = _WEIGHT.search(text)
    if wm:
        out["weight"] = _round(float(wm.group(1)) * _WT_TO_LB.get(wm.group(2).lower(), 1.0))
    return out


def _title(html: str) -> str | None:
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I)
    if m:
        return unescape(m.group(1).strip())
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if m:
        return unescape(re.sub(r"\s+", " ", m.group(1)).strip())
    return None


def parse_listing(html: str, url: str | None = None) -> dict:
    """Extract what we can from a listing's HTML (no network).

    Returns a dict with ``name``/``length``/``width``/``height``/``weight``
    (any may be ``None``), a ``source`` label, an ``ok`` flag (all three
    dimensions found), and a human ``note``.
    """
    result = {"name": None, "length": None, "width": None, "height": None,
              "weight": None, "source": None, "url": url}

    structured = _from_jsonld(html)
    if structured:
        result.update(structured)

    # Fill any gaps from page text.
    if not all(result.get(k) for k in ("length", "width", "height")):
        text = _strip_tags(html)
        text_hit = _from_text(text)
        for k in ("length", "width", "height", "weight"):
            if not result.get(k) and text_hit.get(k):
                result[k] = text_hit[k]
        if result["source"] is None:
            result["source"] = text_hit["source"]

    if not result.get("name"):
        result["name"] = _title(html)

    dims = [result.get("length"), result.get("width"), result.get("height")]
    result["ok"] = all(d for d in dims)
    found = sum(1 for d in dims if d)
    if result["ok"]:
        result["note"] = f"Found dimensions from {result['source']}. Double-check before adding."
    elif found:
        result["note"] = (
            f"Found {found} of 3 dimensions. Fill in the rest from the listing."
        )
    else:
        result["note"] = "Couldn't find dimensions on that page — enter them manually."
    return result


def _host_blocked(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return True
    return bool(re.match(r"^(10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)", host))


def fetch_listing(url: str) -> dict:
    """Download ``url`` and parse it. Raises ``ValueError`` on a bad/blocked URL."""
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("Enter a full http(s) product link.")
    if _host_blocked(url):
        raise ValueError("That address isn't allowed.")

    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read(_MAX_BYTES).decode(charset, errors="replace")
    return parse_listing(html, url)
