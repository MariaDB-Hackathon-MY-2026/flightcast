"""
One-shot Playwright screenshot capture for the Streamlit dashboard.

Generates 5 PNG files into /tmp/screenshots inside the app container,
which can then be `docker cp`-ed out to docs/screenshots/.

Run from inside the container:
    python -m flightcast.benchmarks.capture_screenshots

Or from the host:
    docker compose exec -T --user root app python -m flightcast.benchmarks.capture_screenshots
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT_DIR = Path("/tmp/screenshots")
BASE = "http://localhost:8501"

PAGES: list[tuple[str, str, float]] = [
    ("01_landing_forecast",  f"{BASE}/forecast",        4.0),
    ("02_time_travel_hero",  f"{BASE}/time_travel",     5.0),
    ("03_coverage_drift",    f"{BASE}/coverage_drift",  5.0),
    ("04_about_systemtime",  f"{BASE}/about",           4.0),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        page.goto(BASE, wait_until="networkidle", timeout=45000)
        time.sleep(3)
        landing = OUT_DIR / "00_landing.png"
        page.screenshot(path=str(landing), full_page=True)
        print(f"  ✓ {landing.name}")

        for slug, url, settle in PAGES:
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
                time.sleep(settle)
                target = OUT_DIR / f"{slug}.png"
                page.screenshot(path=str(target), full_page=True)
                print(f"  ✓ {target.name}")
            except Exception as e:
                print(f"  ✗ {slug}: {e}", file=sys.stderr)

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
