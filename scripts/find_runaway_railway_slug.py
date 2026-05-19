"""Quick test to find the correct thrill-data slug for Runaway Railway at DL."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from camoufox.sync_api import Camoufox
from td_parse import iter_heatmap_rows
from datetime import date

SLUGS = [
    "runawayrailway",
    "mickeysrunawayrailway",
    "mickeyandminniesrunawayrailway",
    "mickeyminnierailway",
    "mickeyminniesrunawayrailwaydisneyland",
    "runawayrailwaydisneyland",
]

TEST_DATE = date(2024, 6, 30)

with Camoufox(headless=True) as fox:
    page = fox.new_page()
    for slug in SLUGS:
        url = f"https://www.thrill-data.com/waits/attraction/disneyland/{slug}/{TEST_DATE.year}/{TEST_DATE.month:02d}/{TEST_DATE.day:02d}"
        print(f"Trying: {slug}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            rows = list(iter_heatmap_rows(page.content()))
            print(f"  → {len(rows)} rows")
            if rows:
                print(f"  FOUND! Slug is: {slug}")
                break
        except Exception as e:
            print(f"  → ERROR: {e}")
        time.sleep(1.5)
