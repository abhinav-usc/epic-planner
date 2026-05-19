"""
Aggregate disney_waits.csv (raw WDW thrill-data scrape) into disney_historical_agg.csv.

disney_waits.csv has multiple observations per (park_id, slug, date, hour) due to
overlapping 30-day scrape windows.  This script deduplicates by averaging them.
Existing Disneyland rows in disney_historical_agg.csv are preserved.

Run once after scraping WDW data, then re-run whenever you add more scrape data:
    .venv/bin/python scripts/aggregate_wdw_waits.py

Usage:
    --chunk-size N   rows per read chunk (default 500000; reduce if low on RAM)
    --dry-run        print stats only, don't write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AGG_CSV   = ROOT / "data" / "disney_historical_agg.csv"
RAW_CSV   = ROOT / "data" / "disney_waits.csv"
WDW_PARKS = {"magic_kingdom", "epcot", "hollywood_studios", "animal_kingdom"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk-size", type=int, default=500_000)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not RAW_CSV.exists():
        print(f"ERROR: {RAW_CSV} not found — run td_scrape_disney.py first.")
        sys.exit(1)

    print(f"Reading {RAW_CSV} in chunks of {args.chunk_size:,} …")
    chunks = []
    total_raw = 0
    for chunk in pd.read_csv(RAW_CSV, chunksize=args.chunk_size):
        wdw = chunk[chunk["park_id"].isin(WDW_PARKS)]
        total_raw += len(chunk)
        if not wdw.empty:
            chunks.append(wdw)
        print(f"  read {total_raw:,} rows …", end="\r", flush=True)
    print(f"\nTotal raw rows: {total_raw:,}")

    if not chunks:
        print("No WDW rows found — nothing to aggregate.")
        sys.exit(0)

    raw = pd.concat(chunks, ignore_index=True)
    print(f"WDW rows to aggregate: {len(raw):,}")

    # Group and average — handles duplicate observations from overlapping windows.
    agg = (
        raw.groupby(["park_id", "attraction_slug", "attraction_name", "date", "hour"], sort=False)
        ["wait_minutes"]
        .mean()
        .reset_index()
        .rename(columns={"wait_minutes": "avg_wait"})
    )
    print(f"Aggregated to {len(agg):,} unique (park, slug, date, hour) rows")
    print(f"Parks: {sorted(agg['park_id'].unique())}")
    print(f"Date range: {agg['date'].min()} → {agg['date'].max()}")

    ride_counts = agg.groupby(["park_id", "attraction_slug"]).size().reset_index(name="n")
    print("\nPer-ride row counts:")
    print(ride_counts.sort_values(["park_id", "n"]).to_string(index=False))

    if args.dry_run:
        print("\n--dry-run: not writing.")
        return

    # Load existing Disneyland rows.
    dl_rows = pd.DataFrame()
    if AGG_CSV.exists():
        existing = pd.read_csv(AGG_CSV)
        dl_rows = existing[~existing["park_id"].isin(WDW_PARKS)]
        print(f"\nPreserving {len(dl_rows):,} existing Disneyland rows")

    combined = pd.concat([dl_rows, agg], ignore_index=True)
    combined.to_csv(AGG_CSV, index=False)
    print(f"Wrote {len(combined):,} rows → {AGG_CSV}")
    print("Done. Restart the backend to reload the history cache.")


if __name__ == "__main__":
    main()
