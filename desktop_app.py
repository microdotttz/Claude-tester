#!/usr/bin/env python3
"""
U-Haul Space Optimizer - native desktop app.

Renders the optimizer UI in a real OS window using pywebview (native WebKit on
macOS, WebView2 on Windows, GTK/Qt WebKit on Linux). The furniture catalog is
baked into the page, and the "Find my trailer" button calls straight into
Python through pywebview's JS bridge -- no web server, no port, no browser.

Run it:
    python desktop_app.py        (auto-installs pywebview the first time)

The window's title bar, resizing, and OS integration all come for free; this is
a genuine desktop application, not a browser tab.
"""

import json
import os
import pathlib
import subprocess
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape

from uhaul_optimizer.lovesac import lovesac_components_payload
from uhaul_optimizer.scraper import fetch_listing
from uhaul_optimizer.serialization import catalog_payload, optimize_payload

APP_TITLE = "U-Haul Space Optimizer"
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def state_file() -> pathlib.Path:
    """Path to the saved-load file (persists between launches).

    Honors ``UHAUL_STATE_FILE`` (used by tests), else a per-user app-data dir.
    """
    override = os.environ.get("UHAUL_STATE_FILE")
    if override:
        return pathlib.Path(override)
    if sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home()))
    else:
        base = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config"))
    return base / "UHaulOptimizer" / "state.json"


def render_html() -> str:
    """Render the UI template to a standalone HTML string with the catalog baked in."""
    env = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    return env.get_template("uhaul.html").render(
        catalog=catalog_payload(),
        lovesac=lovesac_components_payload(),
        desktop=True,   # tells the page to persist via the bridge, not localStorage
    )


class Api:
    """Methods exposed to the page via ``window.pywebview.api``.

    The frontend calls these exactly where the web build would ``fetch()`` the
    HTTP API, so the same UI code drives both.
    """

    def optimize(self, payload: dict | None = None) -> dict:
        """Run the optimizer for ``{items, enclosed_only}`` and return the result.

        Errors are returned as ``{"error": "..."}`` so the UI can show a toast
        instead of the bridge call rejecting.
        """
        payload = payload or {}
        try:
            return optimize_payload(
                payload.get("items", []),
                bool(payload.get("enclosed_only", False)),
            )
        except ValueError as e:
            return {"error": str(e)}
        except (KeyError, TypeError) as e:
            return {"error": f"Bad item data: {e}"}

    def fetch_url(self, url: str | None = None) -> dict:
        """Fetch a product listing and extract its dimensions for review."""
        try:
            return fetch_listing(url or "")
        except ValueError as e:
            return {"error": str(e)}
        except Exception:
            return {"error": "Couldn't reach or read that page. Enter the size by hand."}

    def load_state(self) -> dict:
        """Return the saved load from disk (empty dict if none/unreadable)."""
        path = state_file()
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return {}

    def save_state(self, state: dict | None = None) -> bool:
        """Persist the current load to disk so it survives relaunches."""
        path = state_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(state or {}))
            return True
        except OSError:
            return False


def _ensure_pywebview():
    """Import pywebview, installing it on first run so the app just works."""
    try:
        import webview  # noqa: F401
        return webview
    except ImportError:
        pass

    print("First run: installing the desktop UI engine (pywebview)...")
    # On Linux a GUI backend is needed; try the Qt extra there. macOS and
    # Windows ship a usable webview, so the bare package is enough.
    spec = "pywebview[qt]" if sys.platform.startswith("linux") else "pywebview"
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", spec]
    if subprocess.call(cmd) != 0:
        subprocess.call([sys.executable, "-m", "pip", "install", "--quiet", "pywebview"])

    try:
        import webview  # noqa: F811
        return webview
    except ImportError:
        sys.exit(
            "Couldn't load the desktop UI engine.\n"
            f"  Install it manually:  {sys.executable} -m pip install pywebview\n"
            "  On Linux you also need a backend, e.g.:  pip install 'pywebview[qt]'\n"
            "    (or 'pywebview[gtk]' with system GTK/WebKit2 packages).\n"
            "  Alternatively run the optional web version:  python launch_uhaul.py"
        )


def main() -> None:
    webview = _ensure_pywebview()
    api = Api()
    webview.create_window(
        APP_TITLE,
        html=render_html(),
        js_api=api,
        width=980,
        height=860,
        min_size=(380, 600),
        text_select=False,
    )
    webview.start()  # blocks until the window is closed


if __name__ == "__main__":
    main()
