"""
Backfill per-ride historical wait-time data for all four Disney World parks
from thrill-data.com, using Camoufox to defeat Cloudflare.

Output: data/disney_waits.csv with columns:
    park_id, attraction_slug, attraction_name, date, hour, wait_minutes

URL pattern (verified via --probe):
    /waits/attraction/{park_slug}/{attraction_slug}/{YYYY}/{MM}/{DD}
    e.g. /waits/attraction/magic-kingdom/sevendwarfsminetrain/2024/06/15

Defaults to the last 4 years (since 2022-05-14).

Run:
    .venv/bin/python scripts/td_scrape_disney.py --dry-run          # preview plan
    .venv/bin/python scripts/td_scrape_disney.py                     # full backfill
    .venv/bin/python scripts/td_scrape_disney.py --park magic-kingdom
    .venv/bin/python scripts/td_scrape_disney.py --limit 10          # test a few
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


OUT_CSV = ROOT / "data" / "disney_waits.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = ROOT / "data" / "td_disney_progress.txt"

DEFAULT_SINCE = date(2021, 5, 14)   # 5 years back
DEFAULT_STEP_DAYS = 30


# (park_id, park_slug_on_thrill_data, attraction_slug, display_name)
# Slugs verified against thrill-data listing pages.
ATTRACTIONS: list[tuple[str, str, str, str]] = [
    # ── Magic Kingdom ──────────────────────────────────────────────────────────
    ("magic_kingdom", "magic-kingdom", "sevendwarfsminetrain",                "Seven Dwarfs Mine Train"),
    ("magic_kingdom", "magic-kingdom", "peterpansflight",                     "Peter Pan's Flight"),
    ("magic_kingdom", "magic-kingdom", "undertheseajourneyofthelittlemermaid","Under the Sea – Journey of The Little Mermaid"),
    ("magic_kingdom", "magic-kingdom", "themanyadventuresofwinniethepooh",    "The Many Adventures of Winnie the Pooh"),
    ("magic_kingdom", "magic-kingdom", "itsasmallworld",                      "it's a small world"),
    ("magic_kingdom", "magic-kingdom", "dumbotheflyingelephant",              "Dumbo the Flying Elephant"),
    ("magic_kingdom", "magic-kingdom", "enchantedtaleswithbelle",             "Enchanted Tales with Belle"),
    ("magic_kingdom", "magic-kingdom", "mickeysphilharmagic",                 "Mickey's PhilharMagic"),
    ("magic_kingdom", "magic-kingdom", "tronlightcyclerun",                   "TRON Lightcycle / Run"),
    ("magic_kingdom", "magic-kingdom", "spacemountain",                       "Space Mountain"),
    ("magic_kingdom", "magic-kingdom", "buzzlightyearsspacerangerspin",       "Buzz Lightyear's Space Ranger Spin"),
    ("magic_kingdom", "magic-kingdom", "monstersinclaughfloor",               "Monsters, Inc. Laugh Floor"),
    ("magic_kingdom", "magic-kingdom", "piratesofthecaribbean",               "Pirates of the Caribbean"),
    ("magic_kingdom", "magic-kingdom", "junglecruise",                        "Jungle Cruise"),
    ("magic_kingdom", "magic-kingdom", "themagiccarpetsofaladdin",            "Magic Carpets of Aladdin"),
    ("magic_kingdom", "magic-kingdom", "waltdisneysenchantedtikiroom",        "Walt Disney's Enchanted Tiki Room"),
    ("magic_kingdom", "magic-kingdom", "hauntedmansion",                      "Haunted Mansion"),
    ("magic_kingdom", "magic-kingdom", "thehallofpresidents",                 "Hall of Presidents"),
    ("magic_kingdom", "magic-kingdom", "bigthundermountainrailroad",          "Big Thunder Mountain Railroad"),
    ("magic_kingdom", "magic-kingdom", "tianasbayouadventure",                "Tiana's Bayou Adventure"),
    ("magic_kingdom", "magic-kingdom", "countrybearjamboree",                 "Country Bear Jamboree"),

    # ── EPCOT ─────────────────────────────────────────────────────────────────
    ("epcot", "epcot", "guardiansofthegalaxycosmicrewind",   "Guardians of the Galaxy: Cosmic Rewind"),
    ("epcot", "epcot", "testtrack",                           "Test Track"),
    ("epcot", "epcot", "missionspace",                        "Mission: SPACE"),
    ("epcot", "epcot", "soarinaroundtheworld",                "Soarin' Around the World"),
    ("epcot", "epcot", "livingwiththeland",                   "Living with the Land"),
    ("epcot", "epcot", "theseaswithnemofriends",              "The Seas with Nemo & Friends"),
    ("epcot", "epcot", "turtletalkwithcrush",                 "Turtle Talk with Crush"),
    ("epcot", "epcot", "spaceshipearth",                      "Spaceship Earth"),
    ("epcot", "epcot", "journeyintoimaginationwithfigment",   "Journey Into Imagination with Figment"),
    ("epcot", "epcot", "remysratatouilleadventure",           "Remy's Ratatouille Adventure"),
    ("epcot", "epcot", "frozeneverafter",                     "Frozen Ever After"),
    ("epcot", "epcot", "granfiestatourstarringthethreecaballeros", "Gran Fiesta Tour"),
    ("epcot", "epcot", "reflectionsofchina",                  "Reflections of China"),

    # ── Hollywood Studios ─────────────────────────────────────────────────────
    ("hollywood_studios", "hollywood-studios", "starwarsriseoftheresistance",         "Star Wars: Rise of the Resistance"),
    ("hollywood_studios", "hollywood-studios", "millenniumfalconsmugglersrun",        "Millennium Falcon: Smugglers Run"),
    ("hollywood_studios", "hollywood-studios", "slinkydogdash",                       "Slinky Dog Dash"),
    ("hollywood_studios", "hollywood-studios", "toystorymania",                       "Toy Story Mania!"),
    ("hollywood_studios", "hollywood-studios", "alienswirlingsaucers",                "Alien Swirling Saucers"),
    ("hollywood_studios", "hollywood-studios", "thetwilightzonetowerofterror",        "The Twilight Zone Tower of Terror"),
    ("hollywood_studios", "hollywood-studios", "rocknrollercoasterstarringaerosmith", "Rock 'n' Roller Coaster Starring Aerosmith"),
    ("hollywood_studios", "hollywood-studios", "mickeyminniesrunawayrailway",         "Mickey & Minnie's Runaway Railway"),
    ("hollywood_studios", "hollywood-studios", "startourstheadventurescontinue",      "Star Tours – The Adventures Continue"),
    ("hollywood_studios", "hollywood-studios", "muppetvisiond",                       "Muppet*Vision 3D"),
    ("hollywood_studios", "hollywood-studios", "indianajonesepicstuntspectacular",    "Indiana Jones Epic Stunt Spectacular!"),
    ("hollywood_studios", "hollywood-studios", "fantasmic",                           "Fantasmic!"),
    ("hollywood_studios", "hollywood-studios", "beautyandthebeastliveonstage",        "Beauty and the Beast Live on Stage"),

    # ── Animal Kingdom ────────────────────────────────────────────────────────
    ("animal_kingdom", "animal-kingdom", "avatarflightofpassage",                     "Avatar Flight of Passage"),
    ("animal_kingdom", "animal-kingdom", "naviriverjourney",                          "Na'vi River Journey"),
    ("animal_kingdom", "animal-kingdom", "kilimanjarosafaris",                        "Kilimanjaro Safaris"),
    ("animal_kingdom", "animal-kingdom", "festivalofthelionking",                     "Festival of the Lion King"),
    ("animal_kingdom", "animal-kingdom", "gorillafallsexplorationtrail",              "Gorilla Falls Exploration Trail"),
    ("animal_kingdom", "animal-kingdom", "expeditioneverestlegendoftheforbiddenmountain", "Expedition Everest"),
    ("animal_kingdom", "animal-kingdom", "kaliriverrapids",                           "Kali River Rapids"),
    ("animal_kingdom", "animal-kingdom", "maharajahjungletrek",                       "Maharajah Jungle Trek"),
    ("animal_kingdom", "animal-kingdom", "itstoughtobeabug",                         "It's Tough to Be a Bug!"),
    ("animal_kingdom", "animal-kingdom", "dinosaur",                                  "DINOSAUR"),
    ("animal_kingdom", "animal-kingdom", "triceratopspin",                            "TriceraTop Spin"),
]


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


def csv_writer(append: bool):
    new_file = not OUT_CSV.exists() or OUT_CSV.stat().st_size == 0
    f = OUT_CSV.open("a" if append else "w", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["park_id", "attraction_slug", "attraction_name", "date", "hour", "wait_minutes"])
    return f, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=DEFAULT_SINCE.isoformat(),
                    help=f"Earliest date (default: {DEFAULT_SINCE})")
    ap.add_argument("--until", default=date.today().isoformat(),
                    help="Latest date (default: today)")
    ap.add_argument("--step", type=int, default=DEFAULT_STEP_DAYS)
    ap.add_argument("--delay", type=float, default=2.0,
                    help="Seconds between page loads")
    ap.add_argument("--limit", type=int, default=0,
                    help="Stop after N successful fetches (0=no limit)")
    ap.add_argument("--park", help="Only scrape this park (e.g. magic-kingdom)")
    ap.add_argument("--only", help="Comma-separated attraction slugs to scrape")
    ap.add_argument("--dry-run", action="store_true", help="Print plan, don't fetch")
    args = ap.parse_args()

    since = date.fromisoformat(args.since)
    until = date.fromisoformat(args.until)
    windows = date_windows(since, until, args.step)

    targets = ATTRACTIONS
    if args.park:
        targets = [
            (p, ps, s, n) for p, ps, s, n in targets
            if ps == args.park or p == args.park.replace("-", "_")
        ]
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

    total = len(targets) * len(windows)
    print(f"Parks:      {len({ps for _, ps, _, _ in targets})} Disney parks")
    print(f"Rides:      {len(targets)} attractions")
    print(f"Windows:    {len(windows)} × 30-day chunks  ({windows[-1] if windows else '-'} → {windows[0] if windows else '-'})")
    print(f"Total:      {total}  already done: {len(done)}  pending: {len(pending)}")

    if args.dry_run:
        for p, ps, s, n, w in pending[:15]:
            print(f"  would fetch  {url_for(ps, s, w)}")
        if len(pending) > 15:
            print(f"  ... and {len(pending) - 15} more")
        return

    with Camoufox(headless=True, humanize=True, os="macos") as browser:
        page = browser.new_page()
        f_csv, w_csv = csv_writer(append=True)
        success = failed = empty = 0
        consecutive_fail = 0
        MAX_CONSECUTIVE = 3

        try:
            for idx, (park_id, park_slug, slug, name, window) in enumerate(pending, 1):
                if args.limit and success >= args.limit:
                    print(f"Hit --limit={args.limit}, stopping.")
                    break

                if consecutive_fail >= MAX_CONSECUTIVE:
                    print(f"  ⟳ recycling browser after {consecutive_fail} consecutive failures")
                    page = browser.new_page()
                    consecutive_fail = 0

                url = url_for(park_slug, slug, window)
                t0 = time.time()
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                    for _ in range(25):
                        title = page.title()
                        if title and "just a moment" not in title.lower():
                            break
                        page.wait_for_timeout(1000)
                    else:
                        raise RuntimeError(f"never cleared cloudflare: {title!r}")
                    page.wait_for_timeout(2500)
                    html = page.content()
                except Exception as e:
                    failed += 1
                    consecutive_fail += 1
                    print(f"  [{idx}/{len(pending)}] ✗ {park_slug}/{slug} @ {window}: {str(e).splitlines()[0][:100]}")
                    continue

                rows = list(iter_heatmap_rows(html))
                dt = time.time() - t0

                if not rows:
                    empty += 1
                    consecutive_fail = 0
                    print(f"  [{idx}/{len(pending)}] ⚠ {park_slug}/{slug:<45} @ {window}: no heatmap ({len(html)}B)")
                    record_progress(park_id, slug, window)
                    continue

                for d_iso, h, wait in rows:
                    w_csv.writerow([park_id, slug, name, d_iso, h, wait])
                f_csv.flush()
                record_progress(park_id, slug, window)
                success += 1
                consecutive_fail = 0
                print(f"  [{idx}/{len(pending)}] ✓ {park_slug}/{slug:<45} @ {window}  +{len(rows):>3} rows  ({dt:.1f}s)")
                time.sleep(args.delay)

        finally:
            f_csv.close()

    print(f"\nDone. success={success}  empty={empty}  failed={failed}")
    if OUT_CSV.exists():
        n = sum(1 for _ in OUT_CSV.open()) - 1
        print(f"CSV: {OUT_CSV}  total rows={n:,}")


if __name__ == "__main__":
    main()
