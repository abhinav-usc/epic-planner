"""
Data-freshness + on-demand refresh endpoints.

On app load the frontend hits /api/data/freshness to see how stale our
historical CSV is. If `needs_refresh=True`, the frontend can POST
/api/data/refresh to trigger a quick (single-window) scrape in the background.

The refresh runs `td_scrape.py` with --since set to the most recent date
in the existing CSV, capturing only the days that have appeared since the
last full backfill. The model is NOT auto-retrained — we just collect data;
retraining is an explicit step the user runs.
"""
from __future__ import annotations

import asyncio
import csv
import logging
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel


router = APIRouter(prefix="/api/data", tags=["data"])
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
EPIC_CSV = ROOT / "data" / "historical_waits.csv"
PARK_CSV = ROOT / "data" / "park_level_history.csv"
TD_SCRAPE = ROOT / "scripts" / "td_scrape.py"
VENV_PY = ROOT / ".venv" / "bin" / "python"

# How old data must be before we consider a refresh worthwhile.
STALE_AFTER_DAYS = 2

# Lock so two simultaneous refresh requests don't both spawn scrapers.
_refresh_running: bool = False


def _latest_date_in(csv_path: Path) -> Optional[str]:
    """Return the most recent YYYY-MM-DD date appearing in `csv_path`, or None."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return None
    latest = None
    try:
        with csv_path.open() as f:
            r = csv.DictReader(f)
            for row in r:
                d = row.get("date")
                if d and (latest is None or d > latest):
                    latest = d
    except Exception as e:
        log.warning("freshness scan failed: %s", e)
    return latest


class FreshnessResponse(BaseModel):
    latest_epic_date: Optional[str]
    latest_park_date: Optional[str]
    epic_age_days: Optional[int]
    park_age_days: Optional[int]
    needs_refresh: bool
    refresh_running: bool


@router.get("/freshness", response_model=FreshnessResponse)
def freshness() -> FreshnessResponse:
    epic = _latest_date_in(EPIC_CSV)
    parks = _latest_date_in(PARK_CSV)
    today = date.today()
    epic_age = (today - date.fromisoformat(epic)).days if epic else None
    park_age = (today - date.fromisoformat(parks)).days if parks else None
    needs = (epic_age is not None and epic_age >= STALE_AFTER_DAYS) or epic is None
    return FreshnessResponse(
        latest_epic_date=epic,
        latest_park_date=parks,
        epic_age_days=epic_age,
        park_age_days=park_age,
        needs_refresh=needs,
        refresh_running=_refresh_running,
    )


class RefreshResponse(BaseModel):
    started: bool
    reason: str


def _run_quick_scrape() -> None:
    """Run a quick scrape of the most recent 30-day window for all Epic rides."""
    global _refresh_running
    _refresh_running = True
    try:
        latest = _latest_date_in(EPIC_CSV)
        # Re-scrape the last 30 days regardless — recent days were partially
        # observed when previously scraped (heatmap shows up to "now") so they
        # benefit from refresh.
        since_dt = date.today() - timedelta(days=35)
        if latest:
            since_dt = min(since_dt, date.fromisoformat(latest))
        cmd = [
            str(VENV_PY), str(TD_SCRAPE),
            "--since", since_dt.isoformat(),
            "--step", "30",
            "--delay", "1.5",
        ]
        log.info("Spawning quick refresh: %s", " ".join(cmd))
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=20 * 60)
        log.info("Quick refresh finished rc=%s, stdout tail: %s",
                 result.returncode, result.stdout.splitlines()[-3:] if result.stdout else "")
    except Exception as e:
        log.exception("Quick refresh crashed: %s", e)
    finally:
        _refresh_running = False


@router.post("/refresh", response_model=RefreshResponse)
def refresh(background: BackgroundTasks) -> RefreshResponse:
    global _refresh_running
    if _refresh_running:
        return RefreshResponse(started=False, reason="Refresh already in progress")
    if not TD_SCRAPE.exists():
        return RefreshResponse(started=False, reason="td_scrape.py not found")
    background.add_task(_run_quick_scrape)
    return RefreshResponse(started=True, reason="Quick scrape spawned in background")
