"""Probe for the right URL that gives per-hour wait time data per ride."""
import re
import sys
from pathlib import Path
from camoufox.sync_api import Camoufox

URLS = [
    # Per-attraction overview (all-time history)
    "https://www.thrill-data.com/waits/attraction/epic-universe/harrypotterandthebattleattheministry/",
    # Try per-attraction + date
    "https://www.thrill-data.com/waits/attraction/epic-universe/harrypotterandthebattleattheministry/2025/10/16",
    # park-by-date but viewed at park30 endpoint (might be 30-day rolling)
    "https://www.thrill-data.com/waits/park/uor/epic-universe/park30/2026/05/11",
    # parkflow on date
    "https://www.thrill-data.com/waits/park/uor/epic-universe/parkflow/2026/05/11",
]


def probe(page, url, slug):
    print(f"\n══ {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    except Exception as e:
        print(f"  goto error: {e}")
        return
    for i in range(30):
        t = page.title()
        if t and "moment" not in t.lower():
            print(f"  cleared after {i}s, title={t!r}")
            break
        page.wait_for_timeout(1000)
    else:
        print("  STILL stuck")
        return

    page.wait_for_timeout(3500)
    html = page.content()
    out = Path(f"/tmp/td_{slug}.html")
    out.write_text(html)
    print(f"  HTML {len(html)}B → {out}")

    # Plotly calls — fixed regex with DOTALL
    plotly_calls = re.findall(
        r'Plotly\.(?:newPlot|react)\s*\(\s*[\"\'](\w+)[\"\']\s*,\s*(\[)', html, re.DOTALL,
    )
    print(f"  Plotly calls: {len(plotly_calls)}  ids={[c[0][:12] for c in plotly_calls[:5]]}")

    # Trace names
    names = list(set(re.findall(r'"name"\s*:\s*"([^"]+)"', html)))
    print(f"  Trace names ({len(names)}):")
    for n in names[:15]:
        print(f'    → {n}')

    # x-axis values — if hourly, we'd see HH:MM
    hhmm = re.findall(r'\"\d{1,2}:\d{2}\"', html)
    print(f"  HH:MM tokens: {len(hhmm)}  samples={hhmm[:5]}")

    # ISO timestamps
    iso = re.findall(r'\"20\d{2}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?\"', html)
    print(f"  ISO date tokens: {len(iso)}  samples={iso[:5]}")


def main():
    with Camoufox(headless=True, humanize=True, os="macos") as browser:
        page = browser.new_page()
        for url in URLS:
            slug = re.sub(r'[^a-z0-9]', '_', url.rsplit("epic-universe/", 1)[-1].rstrip("/"))[:30] or "root"
            probe(page, url, slug)


if __name__ == "__main__":
    main()
