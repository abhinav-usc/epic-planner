"""
Backfill per-ride historical wait-time data for Disneyland CA and
Universal Studios Hollywood from thrill-data.com via Camoufox.

Output: data/new_parks_waits.csv with columns:
    park_id, attraction_slug, attraction_name, date, hour, wait_minutes

Thrill-data URL pattern (same as WDW scraper):
    /waits/attraction/{park_slug}/{attraction_slug}/{YYYY}/{MM}/{DD}

Verified park slugs:
    Disneyland:              disneyland  (chain: dlr)
    Universal Hollywood:     universal-studios-hollywood  (chain: ush)

Run:
    .venv/bin/python scripts/td_scrape_new_parks.py --dry-run      # preview plan
    .venv/bin/python scripts/td_scrape_new_parks.py                # full backfill
    .venv/bin/python scripts/td_scrape_new_parks.py --park disneyland
    .venv/bin/python scripts/td_scrape_new_parks.py --limit 20     # test a few pages
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


OUT_CSV       = ROOT / "data" / "new_parks_waits.csv"
PROGRESS_FILE = ROOT / "data" / "td_new_parks_progress.txt"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_SINCE     = date(2022, 1, 1)
DEFAULT_STEP_DAYS = 30


# (park_id, park_slug_on_thrill_data, attraction_slug, display_name)
ATTRACTIONS: list[tuple[str, str, str, str]] = [

    # ── Disneyland Park ───────────────────────────────────────────────────────
    # Slugs verified against thrill-data Disneyland listing page.
    ("disneyland", "disneyland", "indianajonesadventure",                    "Indiana Jones Adventure"),
    ("disneyland", "disneyland", "starwarsriseoftheresistance",              "Star Wars: Rise of the Resistance"),
    ("disneyland", "disneyland", "millenniumfalconsmugglersrun",             "Millennium Falcon: Smugglers Run"),
    ("disneyland", "disneyland", "matterhornbobsleds",                       "Matterhorn Bobsleds"),
    ("disneyland", "disneyland", "hauntedmansion",                           "Haunted Mansion"),
    ("disneyland", "disneyland", "piratesofthecaribbean",                    "Pirates of the Caribbean"),
    ("disneyland", "disneyland", "bigthundermountainrailroad",               "Big Thunder Mountain Railroad"),
    ("disneyland", "disneyland", "tianasbayouadventure",                     "Tiana's Bayou Adventure"),
    ("disneyland", "disneyland", "spacemountain",                            "Space Mountain"),
    ("disneyland", "disneyland", "peterpansflight",                          "Peter Pan's Flight"),
    ("disneyland", "disneyland", "itsasmallworld",                           "it's a small world"),
    ("disneyland", "disneyland", "rogerrabbitscartoontoonspin",              "Roger Rabbit's Car Toon Spin"),
    ("disneyland", "disneyland", "themanyadventuresofwinniethepooh",         "The Many Adventures of Winnie the Pooh"),
    ("disneyland", "disneyland", "dumbotheflyingelephant",                   "Dumbo the Flying Elephant"),
    ("disneyland", "disneyland", "aliceinwonderland",                        "Alice in Wonderland"),
    ("disneyland", "disneyland", "pinocchiosdaringjourney",                  "Pinocchio's Daring Journey"),
    ("disneyland", "disneyland", "snowwhitesenchantedwish",                  "Snow White's Enchanted Wish"),
    ("disneyland", "disneyland", "buzzlightyearastroblasters",               "Buzz Lightyear Astro Blasters"),
    ("disneyland", "disneyland", "startours",                                "Star Tours – The Adventures Continue"),
    ("disneyland", "disneyland", "junglecruise",                             "Jungle Cruise"),
    ("disneyland", "disneyland", "mickeyminniesrunawayrailway",              "Mickey & Minnie's Runaway Railway"),

    # ── Universal Studios Hollywood ───────────────────────────────────────────
    # Slugs verified against thrill-data USH listing page.
    ("universal_hollywood", "universal-studios-hollywood", "harrypotterandtheforbiddenjourney", "Harry Potter and the Forbidden Journey"),
    ("universal_hollywood", "universal-studios-hollywood", "flightofthehippogriff",              "Flight of the Hippogriff"),
    ("universal_hollywood", "universal-studios-hollywood", "jurassicworld",                       "Jurassic World – The Ride"),
    ("universal_hollywood", "universal-studios-hollywood", "transformerstheride3d",               "Transformers: The Ride-3D"),
    ("universal_hollywood", "universal-studios-hollywood", "revengeofthemummy",                   "Revenge of the Mummy – The Ride"),
    ("universal_hollywood", "universal-studios-hollywood", "despicablememinionmayhem",            "Despicable Me: Minion Mayhem"),
    ("universal_hollywood", "universal-studios-hollywood", "thesimpsonsride",                     "The Simpsons Ride"),
    ("universal_hollywood", "universal-studios-hollywood", "fastfurioussupercharged",             "Fast & Furious – Supercharged"),
    ("universal_hollywood", "universal-studios-hollywood", "thestudiotour",                       "Studio Tour"),
]

# Slug → local attraction ID map (mirrors train_v4.py usage)
SLUG_TO_LOCAL: dict[str, str] = {
    # Disneyland
    "indianajonesadventure":                   "dl_indiana_jones",
    "starwarsriseoftheresistance":             "dl_rise_resistance",
    "millenniumfalconsmugglersrun":            "dl_smugglers_run",
    "matterhornbobsleds":                      "dl_matterhorn",
    "hauntedmansion":                          "dl_haunted_mansion",
    "piratesofthecaribbean":                   "dl_pirates",
    "bigthundermountainrailroad":              "dl_big_thunder",
    "tianasbayouadventure":                    "dl_tianas_bayou",
    "spacemountain":                           "dl_space_mountain",
    "peterpansflight":                         "dl_peter_pan",
    "itsasmallworld":                          "dl_small_world",
    "rogerrabbitscartoontoonspin":             "dl_roger_rabbit",
    "themanyadventuresofwinniethepooh":        "dl_winnie_pooh",
    "dumbotheflyingelephant":                  "dl_dumbo",
    "aliceinwonderland":                       "dl_alice",
    "pinocchiosdaringjourney":                 "dl_pinocchio",
    "snowwhitesenchantedwish":                 "dl_snow_white",
    "buzzlightyearastroblasters":              "dl_buzz_lightyear",
    "startours":                               "dl_star_tours",
    "junglecruise":                            "dl_jungle_cruise",
    "mickeyminniesrunawayrailway":             "dl_runaway_railway",
    # Universal Hollywood
    "harrypotterandtheforbiddenjourney":       "uh_forbidden_journey",
    "flightofthehippogriff":                   "uh_hippogriff",
    "jurassicworld":                           "uh_jurassic_world",
    "transformerstheride3d":                   "uh_transformers",
    "revengeofthemummy":                       "uh_mummy",
    "despicablememinionmayhem":                "uh_despicable_me",
    "thesimpsonsride":                         "uh_simpsons_ride",
    "fastfurioussupercharged":                 "uh_fast_furious",
    "thestudiotour":                           "uh_studio_tour",
}


def url_for(park_slug: str, slug: str, d: date) -> str:
    return (
        f"https://www.thrill-data.com/waits/attraction"
        f"/{park_slug}/{slug}/{d.year}/{d.month:02d}/{d.day:02d}"
    )


def date_windows(since: date, until: date, step_days: int) -> list[date]:
    out = []
    d = until
    while d > since:
        out.append(d)
        d -= timedelta(days=step_days)
    return out


def load_progress() -> set[tuple[str, str, str]]:
    if not PROGRESS_FILE.exists():
        return set()
    keys: set[tuple[str, str, str]] = set()
    for line in PROGRESS_FILE.read_text().splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 3:
            keys.add((parts[0], parts[1], parts[2]))
    return keys


def record_progress(park_id: str, slug: str, window_date: date) -> None:
    with PROGRESS_FILE.open("a") as f:
        f.write(f"{park_id}\t{slug}\t{window_date.isoformat()}\n")


def csv_writer_ctx(append: bool):
    new_file = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
    f = OUT_CSV.open("a" if append else "w", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["park_id", "attraction_slug", "attraction_name", "date", "hour", "wait_minutes"])
    return f, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=DEFAULT_SINCE.isoformat())
    ap.add_argument("--until", default=date.today().isoformat())
    ap.add_argument("--step", type=int, default=DEFAULT_STEP_DAYS)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N successful fetches (0=no limit)")
    ap.add_argument("--park", help="Only scrape this park_id (e.g. disneyland)")
    ap.add_argument("--only", help="Comma-separated attraction slugs to scrape")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    since = date.fromisoformat(args.since)
    until = date.fromisoformat(args.until)
    windows = date_windows(since, until, args.step)

    targets = ATTRACTIONS
    if args.park:
        targets = [(p, ps, s, n) for p, ps, s, n in targets
                   if p == args.park or ps == args.park]
    if args.only:
        wanted = set(args.only.split(","))
        targets = [(p, ps, s, n) for p, ps, s, n in targets if s in wanted]

    done = load_progress()
    pending = [
        (p, ps, s, n, w)
        for (p, ps, s, n) in targets
        for w in windows
        if (p, s, w.isoformat()) not in done
    ]

    print(f"Parks:      {', '.join(sorted({p for p,_,_,_ in targets}))}")
    print(f"Rides:      {len(targets)} attractions")
    print(f"Windows:    {len(windows)} × {args.step}-day chunks")
    print(f"Total:      {len(targets) * len(windows)}  done: {len(done)}  pending: {len(pending)}")

    if args.dry_run or not pending:
        print("--dry-run: not fetching." if args.dry_run else "Nothing to do.")
        return

    fetched = 0
    f, w = csv_writer_ctx(append=True)

    try:
        with Camoufox(headless=True, humanize=True, os="macos") as browser:
            page = browser.new_page()
            for park_id, park_slug, slug, name, window_date in pending:
                url = url_for(park_slug, slug, window_date)
                print(f"  [{park_id}] {name}  window ending {window_date}  →  {url}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                    for _ in range(25):
                        t = page.title()
                        if t and "just a moment" not in t.lower():
                            break
                        page.wait_for_timeout(1_000)
                    page.wait_for_timeout(3_000)
                    html = page.content()
                    rows_found = 0
                    for row_date, hour, wait in iter_heatmap_rows(html):
                        w.writerow([park_id, slug, name, row_date, hour, wait])
                        rows_found += 1
                    f.flush()
                    record_progress(park_id, slug, window_date)
                    print(f"    → {rows_found} rows")
                    fetched += 1
                except Exception as e:
                    print(f"    ERROR: {e}")
                if args.limit and fetched >= args.limit:
                    print(f"Reached --limit {args.limit}; stopping.")
                    break
                time.sleep(args.delay)
    finally:
        f.close()

    print(f"\nDone. {fetched} pages fetched → {OUT_CSV}")
    print("Next step: python scripts/train_v4.py")


if __name__ == "__main__":
    main()
