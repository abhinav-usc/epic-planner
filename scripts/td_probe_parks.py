"""Probe thrill-data for the URL pattern that gives per-park heatmaps."""
import re
import sys
from pathlib import Path
from camoufox.sync_api import Camoufox

# Candidate URLs - we want to find one that returns a date×hour heatmap
# at the park (not per-ride) level.
CANDIDATES = [
    # WDW Magic Kingdom main page
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/",
    # MK with date — we already saw this gives a single rolling average for Epic
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/2024/10/16",
    # park30 variant
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/park30/2024/10/16",
    # parkflow
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/parkflow/2024/10/16",
    # graph/calendar by month
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/graph/calendar/2024/10",
    # chain-level page
    "https://www.thrill-data.com/waits/chain/wdw/",
    # Maybe a yearly view
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/2024",
    # Maybe a historical heatmap endpoint
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/heatmap",
    "https://www.thrill-data.com/waits/park/wdw/magic-kingdom/history",
]


def probe(page, url):
    print(f"\n══ {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    except Exception as e:
        print(f"  goto error: {str(e).splitlines()[0][:120]}")
        return
    for _ in range(20):
        t = page.title()
        if t and "just a moment" not in t.lower():
            break
        page.wait_for_timeout(1000)
    else:
        print("  STILL stuck on Cloudflare")
        return
    page.wait_for_timeout(2500)
    html = page.content()
    print(f"  HTML {len(html)}B  title={t[:80]!r}")

    # Look for heatmap markers
    has_heatmap = '"type":"heatmap"' in html or '"type": "heatmap"' in html
    n_plotly = len(re.findall(r'Plotly\.(?:newPlot|react)\(', html))
    iso_count = len(re.findall(r'"20\d{2}-\d{2}-\d{2}', html))
    mmddyyyy = re.findall(r'"(\d{1,2}/\d{1,2}/\d{4})"', html)
    hh_mm_am = re.findall(r'"(\d{1,2}:\d{2} [AP]M)"', html)
    print(f"  Plotly calls: {n_plotly}  has-heatmap-type: {has_heatmap}")
    print(f"  ISO date tokens: {iso_count}")
    print(f"  M/D/YYYY tokens: {len(mmddyyyy)} (e.g. {mmddyyyy[:3]})")
    print(f"  hh:mm AM/PM tokens: {len(hh_mm_am)} (e.g. {hh_mm_am[:3]})")

    # Save large pages
    if len(html) > 200_000:
        slug = re.sub(r'[^a-z0-9]', '_', url.split('://')[1])[:60]
        outpath = Path(f'/tmp/td_probe_{slug}.html')
        outpath.write_text(html)
        print(f'  saved → {outpath}')


def main():
    with Camoufox(headless=True, humanize=True, os="macos") as browser:
        page = browser.new_page()
        for url in CANDIDATES:
            probe(page, url)


if __name__ == "__main__":
    main()
