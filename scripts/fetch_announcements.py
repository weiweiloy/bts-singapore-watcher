"""
Fetches the BTS tour page using a headless browser (Playwright) so
that JavaScript renders before we extract text. Saves a clean text
snapshot to snapshots/YYYY-MM-DD.txt. Run daily by GitHub Actions.
"""

import datetime
import pathlib
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://ibighit.com/en/bts/tour/"
SNAPSHOT_DIR = pathlib.Path(__file__).parent.parent / "snapshots"


def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Dismiss cookie banner if present. Try several common selectors.
        for selector in [
            "button:has-text('Accept All')",
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "[aria-label='Accept All']",
        ]:
            try:
                page.locator(selector).first.click(timeout=2000)
                break
            except Exception:
                continue

        # Wait for content to render after dismissing banner
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()
        return html

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def main() -> int:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    output_path = SNAPSHOT_DIR / f"{today}.txt"

    try:
        html = fetch_rendered_html(URL)
    except Exception as exc:
        print(f"Fetch failed: {exc}", file=sys.stderr)
        return 1

    text = extract_text(html)
    header = (
        f"Source URL: {URL}\n"
        f"Fetched: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
        f"---\n\n"
    )
    output_path.write_text(header + text, encoding="utf-8")
    print(f"Wrote snapshot to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())