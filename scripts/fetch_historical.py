"""
Fetch a snapshot of current queue-times.com waits for Epic Universe and append
to data/live_log.csv. Run this on a cron (every 15-30 min) to build up a real
historical dataset that the trainer can ingest.

Output schema:
  timestamp, ride_id, ride_name, land, is_open, wait_minutes

Usage:
  python scripts/fetch_historical.py
"""
from __future__ import annotations

import asyncio
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.data.queue_times_client import fetch_live_sample


OUT = ROOT / "data" / "live_log.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)


def append_rows(rows: list[dict]) -> None:
    write_header = not OUT.exists()
    with OUT.open("a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp_utc", "ride_id", "ride_name", "land", "is_open", "wait_minutes"])
        ts = datetime.now(timezone.utc).isoformat()
        for r in rows:
            w.writerow([
                ts,
                r.get("id"),
                r.get("name"),
                r.get("land"),
                int(bool(r.get("is_open"))),
                r.get("wait_time"),
            ])


async def main() -> None:
    data = await fetch_live_sample()
    if not data:
        print("queue-times returned nothing.")
        return
    append_rows(data)
    print(f"Logged {len(data)} ride rows to {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
