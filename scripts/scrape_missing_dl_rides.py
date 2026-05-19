"""
One-shot scrape for DL rides missing from new_parks_waits.csv:
  - junglecruise (Jungle Cruise) — was typo'd as junglelcruise before
  - mickeyminniesrunawayrailway (Mickey & Minnie's Runaway Railway) — opened 2024
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from camoufox.sync_api import Camoufox
from td_parse import iter_heatmap_rows

OUT_CSV = ROOT / "data" / "new_parks_waits.csv"

TARGETS = [
    ("disneyland", "disneyland", "mickeyminniesrunawayrailway", "Mickey & Minnie's Runaway Railway", date(2023, 11, 1)),
]

STEP_DAYS = 30
DELAY = 1.5


def url_for(park_slug: str, slug: str, d: date) -> str:
    return f"https://www.thrill-data.com/waits/attraction/{park_slug}/{slug}/{d.year}/{d.month:02d}/{d.day:02d}"


def date_windows(since: date, until: date) -> list[date]:
    out = []
    d = until
    while d >= since:
        out.append(d)
        d -= timedelta(days=STEP_DAYS)
    return out


def main():
    today = date.today()
    total_rows = 0

    with Camoufox(headless=True) as fox:
        page = fox.new_page()
        with OUT_CSV.open("a", newline="") as f:
            writer = csv.writer(f)
            for park_id, park_slug, slug, name, since in TARGETS:
                windows = date_windows(since, today)
                print(f"\n[{park_id}] {name} — {len(windows)} windows to fetch", flush=True)
                for win_date in windows:
                    url = url_for(park_slug, slug, win_date)
                    print(f"  {win_date}  {url}", end="  ", flush=True)
                    try:
                        page.goto(url, wait_until="networkidle", timeout=30_000)
                        time.sleep(3)
                        rows = list(iter_heatmap_rows(page.content()))
                        print(f"→ {len(rows)} rows", flush=True)
                        for date_iso, hour_24, wait in rows:
                            writer.writerow([park_id, slug, name, date_iso, hour_24, wait])
                            total_rows += 1
                    except Exception as e:
                        print(f"→ ERROR: {e}", flush=True)
                    time.sleep(DELAY)

    print(f"\nDone. {total_rows} rows written to {OUT_CSV}")


if __name__ == "__main__":
    main()
