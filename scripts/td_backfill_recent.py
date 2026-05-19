"""
Backfill the past 2 weeks of Disneyland wait data from thrill-data.com heatmaps.

When you navigate to today's date on thrill-data, the heatmap shows ~14 days of
surrounding data on the y-axis (one row per date, columns = hours).  Visiting ONE
URL per ride gives us the full 2-week window in a single page load.

Output: populates data/live_waits/disneyland/{YYYY-MM-DD}.csv for each date found,
in the same format the LiveWaitsCache expects.  The worst_n_avg_by_hour() function
will automatically pick up this data for predictions.

Usage:
    .venv/bin/python scripts/td_backfill_recent.py [--dry-run] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from camoufox.sync_api import Camoufox
from td_parse import iter_heatmap_rows

LIVE_DIR = ROOT / "data" / "live_waits" / "disneyland"
LIVE_DIR.mkdir(parents=True, exist_ok=True)

# Thrill-data park slug for Disneyland
PARK_SLUG = "disneyland"

# Ride slug → local attraction_id (must match DISNEYLAND_SLUG_TO_LOCAL from train_v5)
RIDE_MAP: dict[str, str] = {
    "indianajonesadventure":        "dl_indiana_jones",
    "starwarsriseoftheresistance":  "dl_rise_resistance",
    "millenniumfalconsmugglersrun": "dl_smugglers_run",
    "matterhornbobsleds":           "dl_matterhorn",
    "hauntedmansion":               "dl_haunted_mansion",
    "piratesofthecaribbean":        "dl_pirates",
    "bigthundermountainrailroad":   "dl_big_thunder",
    "tianasbayouadventure":         "dl_tianas_bayou",
    "spacemountain":                "dl_space_mountain",
    "peterpansflight":              "dl_peter_pan",
    "itsasmallworld":               "dl_small_world",
    "rogerrabbitscartoontoonspin":  "dl_roger_rabbit",
    "themanyadventuresofwinniethepooh": "dl_winnie_pooh",
    "dumbotheflyingelephant":       "dl_dumbo",
    "aliceinwonderland":            "dl_alice",
    "pinocchiosdaringjourney":      "dl_pinocchio",
    "snowwhitesenchantedwish":      "dl_snow_white",
    "buzzlightyearastroblasters":   "dl_buzz_lightyear",
    "junglecruise":                 "dl_jungle_cruise",
    "mickeyminniesrunawayrailway":  "dl_runaway_railway",
}

TODAY_STR = date.today().isoformat().replace("-", "/")  # YYYY/MM/DD


def url(ride_slug: str) -> str:
    return f"https://www.thrill-data.com/waits/attraction/{PARK_SLUG}/{ride_slug}/{TODAY_STR}"


def csv_path(date_iso: str) -> Path:
    return LIVE_DIR / f"{date_iso}.csv"


def write_rows(rows_by_date: dict[str, list[tuple[str, int, int]]]) -> None:
    """Write (attraction_id, hour, wait) rows to per-date CSVs."""
    for date_iso, entries in rows_by_date.items():
        path = csv_path(date_iso)
        # Merge with existing file if present
        existing: list[dict] = []
        if path.exists():
            with path.open() as f:
                existing = list(csv.DictReader(f))
            # Remove any rows already written by this script (source=thrill_data)
            existing = [r for r in existing if r.get("source") != "thrill_data"]
        with path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "attraction_id", "wait_minutes", "is_open", "source"])
            for r in existing:
                w.writerow([r["timestamp"], r["attraction_id"], r["wait_minutes"],
                            r.get("is_open", "True"), r.get("source", "live")])
            for aid, hour, wait in entries:
                ts = f"{date_iso}T{hour:02d}:30:00"
                w.writerow([ts, aid, wait, wait > 0, "thrill_data"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Max rides to scrape (0 = all)")
    args = ap.parse_args()

    rides = list(RIDE_MAP.items())
    if args.limit:
        rides = rides[:args.limit]

    total_rows = 0
    rows_by_date: dict[str, list[tuple[str, int, int]]] = {}

    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        for i, (slug, local_id) in enumerate(rides, 1):
            u = url(slug)
            print(f"[{i}/{len(rides)}] {slug} → {local_id}")
            print(f"  {u}")
            try:
                page.goto(u, wait_until="networkidle", timeout=30_000)
                html = page.content()
                ride_rows = list(iter_heatmap_rows(html))
                if not ride_rows:
                    print("  ⚠ no heatmap data found")
                    continue
                dates = sorted(set(r[0] for r in ride_rows))
                waits = [r[2] for r in ride_rows]
                print(f"  ✓ {len(ride_rows)} cells · dates {dates[0]} → {dates[-1]} · wait {min(waits)}–{max(waits)} min")
                for date_iso, hour, wait in ride_rows:
                    if wait <= 0:
                        continue
                    rows_by_date.setdefault(date_iso, []).append((local_id, hour, wait))
                    total_rows += 1
            except Exception as e:
                print(f"  ✗ error: {e}")

    print(f"\nTotal data points: {total_rows} across {len(rows_by_date)} dates")
    if args.dry_run:
        print("Dry run — not writing files.")
        return

    write_rows(rows_by_date)
    print(f"Written to {LIVE_DIR}/")
    for d in sorted(rows_by_date):
        print(f"  {d}: {len(rows_by_date[d])} rows")


if __name__ == "__main__":
    main()
