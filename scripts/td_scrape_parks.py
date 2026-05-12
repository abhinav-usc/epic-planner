"""
Backfill park-level (not per-ride) historical wait-time data from thrill-data.

URL pattern: /waits/park/{chain}/{park-slug}/park30/{YYYY}/{MM}/{DD}
Each fetch returns a 30-day × per-hour heatmap of park-wide rolling-average waits.

Output: data/park_level_history.csv with columns:
    chain, park_slug, date, hour, wait_minutes

We pre-train the model on this so it learns calendar/holiday/seasonality
patterns across mature parks, then fine-tune on the Epic per-ride data.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from camoufox.sync_api import Camoufox
from td_parse import iter_heatmap_rows


OUT_CSV = ROOT / "data" / "park_level_history.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = ROOT / "data" / "td_parks_progress.txt"

DEFAULT_SINCE = date(2016, 1, 1)         # ~10 years back
DEFAULT_UNTIL = date.today()
DEFAULT_STEP_DAYS = 30                    # heatmap window size

# (chain, park_slug, display_name)
PARKS = [
    ("wdw", "magic-kingdom",     "Magic Kingdom"),
    ("wdw", "epcot",             "EPCOT"),
    ("wdw", "hollywood-studios", "Hollywood Studios"),
    ("wdw", "animal-kingdom",    "Animal Kingdom"),
    ("uor", "universal-studios",     "Universal Studios Florida"),
    ("uor", "islands-of-adventure",  "Islands of Adventure"),
]


def url_for(chain: str, park_slug: str, d: date) -> str:
    return f"https://www.thrill-data.com/waits/park/{chain}/{park_slug}/park30/{d.year}/{d.month:02d}/{d.day:02d}"


def windows_for(since: date, until: date, step_days: int) -> list[date]:
    out = []
    d = until
    while d > since:
        out.append(d)
        d -= timedelta(days=step_days)
    return out


def load_progress() -> set[tuple[str, str, str]]:
    if not PROGRESS_FILE.exists():
        return set()
    out = set()
    for line in PROGRESS_FILE.read_text().splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 3:
            out.add(tuple(parts))
    return out


def record(chain: str, slug: str, d: date) -> None:
    with PROGRESS_FILE.open("a") as f:
        f.write(f"{chain}\t{slug}\t{d.isoformat()}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=DEFAULT_SINCE.isoformat())
    ap.add_argument("--until", default=DEFAULT_UNTIL.isoformat())
    ap.add_argument("--step",  type=int, default=DEFAULT_STEP_DAYS)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only",  help="Comma-separated park slugs to scrape")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    since = date.fromisoformat(args.since)
    until = date.fromisoformat(args.until)
    windows = windows_for(since, until, args.step)

    targets = PARKS
    if args.only:
        wanted = set(args.only.split(","))
        targets = [(c, s, n) for c, s, n in PARKS if s in wanted]

    done = load_progress()
    pending = [(c, s, n, w) for (c, s, n) in targets for w in windows
               if (c, s, w.isoformat()) not in done]

    print(f"Targets: {len(targets)} parks × {len(windows)} windows = {len(targets)*len(windows)} fetches")
    print(f"  date range: {windows[-1] if windows else '-'} → {windows[0] if windows else '-'}")
    print(f"  pending:    {len(pending)}  (already done: {len(done)})")

    if args.dry_run:
        for c, s, n, w in pending[:8]:
            print(f"  would fetch {url_for(c, s, w)}")
        if len(pending) > 8:
            print(f"  ... and {len(pending)-8} more")
        return

    new_csv = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
    f_csv = OUT_CSV.open("a", newline="")
    w_csv = csv.writer(f_csv)
    if new_csv:
        w_csv.writerow(["chain", "park_slug", "park_name", "date", "hour", "wait_minutes"])

    success = failed = empty = 0
    consecutive_fail = 0
    MAX_CONSECUTIVE = 3

    def launch():
        b = Camoufox(headless=True, humanize=True, os="macos").__enter__()
        return b, b.new_page()
    def close(b):
        try: b.__exit__(None, None, None)
        except Exception: pass

    browser, page = launch()

    try:
        for idx, (chain, slug, name, window) in enumerate(pending, 1):
            if args.limit and success >= args.limit:
                print(f"Hit --limit={args.limit}; stopping.")
                break

            if consecutive_fail >= MAX_CONSECUTIVE:
                print(f"  ⟳ recycling browser after {consecutive_fail} consecutive failures")
                close(browser); time.sleep(5)
                browser, page = launch()
                consecutive_fail = 0

            url = url_for(chain, slug, window)
            t0 = time.time()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                for _ in range(25):
                    t = page.title()
                    if t and "just a moment" not in t.lower():
                        break
                    page.wait_for_timeout(1000)
                else:
                    raise RuntimeError(f"never cleared: {t!r}")
                page.wait_for_timeout(2000)
                html = page.content()
            except Exception as e:
                failed += 1
                consecutive_fail += 1
                msg = str(e).splitlines()[0][:120]
                print(f"  [{idx}/{len(pending)}] ✗ {chain}/{slug} @ {window}: {msg}")
                continue

            # If we hit a "Not Found" page (pre-data date), record so we skip
            if "Not Found" in (page.title() or ""):
                empty += 1
                consecutive_fail = 0
                print(f"  [{idx}/{len(pending)}] ⊘ {chain}/{slug} @ {window}: 404 (pre-data)")
                record(chain, slug, window)
                continue

            rows = list(iter_heatmap_rows(html))
            if not rows:
                empty += 1
                consecutive_fail = 0
                print(f"  [{idx}/{len(pending)}] ⚠ {chain}/{slug} @ {window}: no heatmap ({len(html)}B)")
                record(chain, slug, window)
                continue

            for d_iso, h, wait in rows:
                w_csv.writerow([chain, slug, name, d_iso, h, wait])
            f_csv.flush()
            record(chain, slug, window)
            success += 1
            consecutive_fail = 0
            dt = time.time() - t0
            print(f"  [{idx}/{len(pending)}] ✓ {chain}/{slug:<28} @ {window}  +{len(rows):>3} rows  ({dt:.1f}s)")
            time.sleep(args.delay)
    finally:
        f_csv.close()
        close(browser)

    print(f"\nDone. success={success}  empty/404={empty}  failed={failed}")
    n_rows = sum(1 for _ in OUT_CSV.open()) - 1 if OUT_CSV.exists() else 0
    print(f"CSV: {OUT_CSV}  rows={n_rows}")


if __name__ == "__main__":
    main()
