"""
Backfill historical wait-time data for every Epic Universe attraction from
thrill-data.com, using Camoufox to defeat Cloudflare.

Output: data/historical_waits.csv with columns:
    attraction_slug, attraction_name, date, hour, wait_minutes

Strategy:
- For each attraction:
    - Walk back from today in ~30-day windows to the park opening date
    - For each window-end date, GET /waits/attraction/epic-universe/{slug}/{Y/M/D}
    - Parse the embedded Plotly heatmap (date × hour → wait minutes)
- Polite throttling: 2.0s between fetches by default.
- Resume support: skip (attraction, window_date) pairs already in the CSV.

Run:
    .venv/bin/python scripts/td_scrape.py            # full backfill
    .venv/bin/python scripts/td_scrape.py --since 2026-04-01   # narrower window
    .venv/bin/python scripts/td_scrape.py --limit 3 --dry-run  # test
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


OUT_CSV = ROOT / "data" / "historical_waits.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = ROOT / "data" / "td_scrape_progress.txt"

PARK_OPENED = date(2025, 5, 22)
DEFAULT_WINDOW_DAYS = 30  # thrill-data's heatmap shows ~32 days, we step by 30 to overlap a little

# Attraction slugs found on the thrill-data per-park page.
# (attraction_slug, human_display_name)
ATTRACTIONS = [
    ("stardustracers", "Stardust Racers"),
    ("constellationcarousel", "Constellation Carousel"),
    ("astronomica", "Astronomica"),
    ("mariokartbowserschallenge", "Mario Kart: Bowser's Challenge"),
    ("minecartmadness", "Mine-Cart Madness"),
    ("yoshisadventure", "Yoshi's Adventure"),
    ("bowserjrchallenge", "Bowser Jr. Shadow Showdown"),
    ("meetmarioandluigi", "Meet Mario and Luigi"),
    ("meetprincesspeach", "Meet Princess Peach"),
    ("meetdonkeykong", "Meet Donkey Kong"),
    ("harrypotterandthebattleattheministry", "Harry Potter and the Battle at the Ministry"),
    ("lecirquearcanus", "Le Cirque Arcanus"),
    ("hiccupswinggliders", "Hiccup's Wing Gliders"),
    ("dragonracersrally", "Dragon Racer's Rally"),
    ("fyredrill", "Fyre Drill"),
    ("theuntrainabledragon", "The Untrainable Dragon"),
    ("vikingtrainingcamp", "Viking Training Camp"),
    ("meettoothlessandfriends", "Meet Toothless and Friends"),
    ("meettoothlesshiccup", "Meet Toothless & Hiccup"),
    ("monstersunchainedthefrankensteinexperiment", "Monsters Unchained: The Frankenstein Experiment"),
    ("curseofthewerewolf", "Curse of the Werewolf"),
    ("darkuniversecharactermeetgreet", "Dark Universe Character Meet & Greet"),
]


def url_for(slug: str, d: date) -> str:
    return f"https://www.thrill-data.com/waits/attraction/epic-universe/{slug}/{d.year}/{d.month:02d}/{d.day:02d}"


def date_windows(since: date, until: date, step_days: int) -> list[date]:
    """Return window-end dates from `until` walking back by `step_days`, down to `since`."""
    out = []
    d = until
    while d > since:
        out.append(d)
        d -= timedelta(days=step_days)
    return out


def load_existing_keys() -> set[tuple[str, str]]:
    """Return set of (slug, window_date_iso) pairs that we've already fetched."""
    if not PROGRESS_FILE.exists():
        return set()
    keys = set()
    for line in PROGRESS_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            slug, d = line.split("\t")
            keys.add((slug, d))
        except ValueError:
            continue
    return keys


def record_progress(slug: str, window_date: date) -> None:
    with PROGRESS_FILE.open("a") as f:
        f.write(f"{slug}\t{window_date.isoformat()}\n")


def csv_writer(append: bool):
    new_file = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
    f = OUT_CSV.open("a" if append else "w", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["attraction_slug", "attraction_name", "date", "hour", "wait_minutes"])
    return f, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=PARK_OPENED.isoformat(),
                    help=f"Earliest window-end date (default: {PARK_OPENED.isoformat()})")
    ap.add_argument("--until", default=date.today().isoformat(),
                    help="Latest window-end date (default: today)")
    ap.add_argument("--step", type=int, default=DEFAULT_WINDOW_DAYS,
                    help=f"Days between window ends (default: {DEFAULT_WINDOW_DAYS})")
    ap.add_argument("--delay", type=float, default=2.0,
                    help="Seconds between page loads")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N successful fetches (0=no limit)")
    ap.add_argument("--dry-run", action="store_true", help="Print plan, don't fetch")
    ap.add_argument("--only", help="Comma-separated slugs to scrape (default: all)")
    args = ap.parse_args()

    since = date.fromisoformat(args.since)
    until = date.fromisoformat(args.until)

    targets = ATTRACTIONS
    if args.only:
        wanted = set(args.only.split(","))
        targets = [(s, n) for s, n in ATTRACTIONS if s in wanted]

    windows = date_windows(since, until, args.step)
    total = len(targets) * len(windows)
    done = load_existing_keys()
    pending = [(s, n, w) for (s, n) in targets for w in windows if (s, w.isoformat()) not in done]

    print(f"Targets: {len(targets)} attractions × {len(windows)} windows = {total} fetches")
    print(f"  already done: {len(done)}")
    print(f"  pending:      {len(pending)}")
    print(f"  date range:   {windows[-1] if windows else '-'} → {windows[0] if windows else '-'}")
    if args.dry_run:
        for slug, name, w in pending[:20]:
            print(f"  would fetch  {url_for(slug, w)}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")
        return

    f_csv, w_csv = csv_writer(append=True)
    success = 0
    failed = 0
    consecutive_failures = 0
    MAX_CONSECUTIVE = 3  # restart browser after this many in a row

    def launch_browser():
        b = Camoufox(headless=True, humanize=True, os="macos").__enter__()
        return b, b.new_page()

    def close_browser(b):
        try:
            b.__exit__(None, None, None)
        except Exception:
            pass

    browser, page = launch_browser()

    try:
        for idx, (slug, name, window) in enumerate(pending, 1):
            if args.limit and success >= args.limit:
                print(f"Hit --limit={args.limit}, stopping.")
                break

            # If we've hit several errors in a row, the browser session is likely
            # dead. Recycle it.
            if consecutive_failures >= MAX_CONSECUTIVE:
                print(f"  ⟳ recycling browser session after {consecutive_failures} consecutive failures")
                close_browser(browser)
                time.sleep(5)
                browser, page = launch_browser()
                consecutive_failures = 0

            url = url_for(slug, window)
            t0 = time.time()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                # Cloudflare's challenge page always has title "Just a moment...".
                for _ in range(25):
                    title = page.title()
                    if title and "just a moment" not in title.lower():
                        break
                    page.wait_for_timeout(1000)
                else:
                    raise RuntimeError(f"never cleared: title={title!r}")
                page.wait_for_timeout(2500)  # let Plotly script render
                html = page.content()
            except Exception as e:
                failed += 1
                consecutive_failures += 1
                msg = str(e).splitlines()[0][:120]
                print(f"  [{idx}/{len(pending)}] ✗ {slug} @ {window}: {msg}")
                continue

            rows = list(iter_heatmap_rows(html))
            if not rows:
                failed += 1
                consecutive_failures = 0  # page loaded, just had no chart — that's normal for shows
                print(f"  [{idx}/{len(pending)}] ⚠ {slug} @ {window}: no heatmap data ({len(html)}B)")
                record_progress(slug, window)  # mark done so we don't retry forever
                continue

            for d_iso, h, w in rows:
                w_csv.writerow([slug, name, d_iso, h, w])
            f_csv.flush()
            record_progress(slug, window)
            success += 1
            consecutive_failures = 0
            dt = time.time() - t0
            print(f"  [{idx}/{len(pending)}] ✓ {slug:<45} @ {window}  +{len(rows):>3} rows  ({dt:.1f}s)")

            time.sleep(args.delay)
    finally:
        f_csv.close()
        close_browser(browser)

    print(f"\nDone. success={success}  failed={failed}")
    print(f"CSV: {OUT_CSV}  rows={sum(1 for _ in OUT_CSV.open()) - 1}")


if __name__ == "__main__":
    main()
