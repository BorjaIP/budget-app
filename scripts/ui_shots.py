"""Take screenshots of the running app (run inside the Playwright container).

Usage: python ui_shots.py <base-url> <out-dir> <route> [<route> ...]
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORTS = {"desktop": (1440, 900), "mobile": (390, 844)}
SCHEMES = ("light", "dark")


def main() -> None:
    base, out, routes = sys.argv[1].rstrip("/"), Path(sys.argv[2]), sys.argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        for scheme in SCHEMES:
            for name, (width, height) in VIEWPORTS.items():
                context = browser.new_context(viewport={"width": width, "height": height}, color_scheme=scheme)
                page = context.new_page()
                for route in routes:
                    slug = route.strip("/") or "home"
                    page.goto(f"{base}{route}", wait_until="networkidle", timeout=90_000)
                    page.wait_for_timeout(3000)
                    target = out / f"{slug}-{name}-{scheme}.png"
                    page.screenshot(path=str(target), full_page=True)
                    print(target.name)
                context.close()
        browser.close()


if __name__ == "__main__":
    main()
