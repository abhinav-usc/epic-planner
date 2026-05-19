"""Live wait-time polling + calibration endpoints.

POST /api/live/poll
  Body: { park: str }
  Action: fetch current waits from queue-times.com, record to live cache,
          compute per-ride calibration factor against the model's predictions
          for the past 2 hours.
  Returns: the snapshot + calibration factors.

GET /api/live/calibration?park=X
  Returns the current calibration state without re-polling.
"""
from __future__ import annotations

import asyncio
import logging
import statistics
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.data.live_waits_cache import live_cache
from backend.data.queue_times_client import QueueTimesClient, flatten_live
from backend.data.queue_times_mapping import (
    PARK_MAPPINGS, queue_times_park_id,
)
from backend.data.attractions_db import attraction_by_id
from backend.data.disney_db import disney_attraction_by_id
from backend.data.disneyland_db import disneyland_attraction_by_id
from backend.ml.model import predictor


router = APIRouter(prefix="/api/live", tags=["live"])
log = logging.getLogger(__name__)


_RESOLVERS = {
    "epic_universe": attraction_by_id,
    "disneyland":    disneyland_attraction_by_id,
}


def _resolve(park: str, attraction_id: str):
    return _RESOLVERS.get(park, disney_attraction_by_id)(attraction_id)


class LivePollRequest(BaseModel):
    park: str


class RideWait(BaseModel):
    attraction_id: str
    wait_minutes: int
    is_open: bool


class Calibration(BaseModel):
    park_wide_factor: float       # median across rides with sufficient data
    by_ride_factor: dict[str, float]  # per-ride factor when ≥3 samples
    samples_used: int             # total (ride, hour) pairs compared
    minutes_of_history: int       # span of today's data in minutes


class LivePollResponse(BaseModel):
    park: str
    fetched_at: str
    rides: list[RideWait]
    calibration: Calibration


def _compute_calibration(park: str, target_date: date) -> Calibration:
    """For each ride with ≥3 live observations in the last 2h, compare against
    the model's predicted standby for that hour and compute the ratio.
    """
    mapping = PARK_MAPPINGS.get(park, {})
    by_ride: dict[str, float] = {}
    ratios: list[float] = []
    samples_used = 0
    timestamps: list[datetime] = []

    for aid in set(mapping.values()):
        recent = live_cache.recent(park, aid, hours=2.0)
        if len(recent) < 3:
            continue

        ride = _resolve(park, aid)
        if ride is None:
            continue

        # Predict the model's standby for each observation hour
        per_hour_actual: dict[int, list[int]] = {}
        for ts, wait in recent:
            per_hour_actual.setdefault(ts.hour, []).append(wait)
            timestamps.append(ts)

        ride_ratios = []
        for hour, actuals in per_hour_actual.items():
            try:
                rows = predictor.predict_hours_batch(
                    ride, target_date, [hour], park_id=park,
                )
                predicted = rows[0]["wait_minutes"] if rows else None
            except Exception:
                predicted = None
            if predicted is None or predicted < 1:
                continue
            actual_med = statistics.median(actuals)
            if actual_med < 1:
                continue
            ride_ratios.append(actual_med / predicted)
            samples_used += 1

        if ride_ratios:
            factor = statistics.median(ride_ratios)
            factor = max(0.5, min(2.0, factor))
            by_ride[aid] = round(factor, 3)
            ratios.append(factor)

    park_wide = round(statistics.median(ratios), 3) if ratios else 1.0

    span_min = 0
    if timestamps:
        span_min = int((max(timestamps) - min(timestamps)).total_seconds() / 60)

    return Calibration(
        park_wide_factor=park_wide,
        by_ride_factor=by_ride,
        samples_used=samples_used,
        minutes_of_history=span_min,
    )


@router.post("/poll", response_model=LivePollResponse)
async def poll(req: LivePollRequest) -> LivePollResponse:
    qt_park_id = queue_times_park_id(req.park)
    if qt_park_id is None:
        raise HTTPException(status_code=400, detail=f"No queue-times mapping for park '{req.park}'")
    mapping = PARK_MAPPINGS.get(req.park, {})
    if not mapping:
        raise HTTPException(status_code=400, detail=f"No ride mapping defined for park '{req.park}'")

    # Fetch live snapshot
    try:
        async with QueueTimesClient() as c:
            payload = await c.live_queue_times(park_id=qt_park_id)
    except Exception as e:
        log.warning("queue-times fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=f"queue-times fetch failed: {e}")

    qt_rides = flatten_live(payload)
    observations: list[tuple[str, int, bool]] = []
    ride_waits: list[RideWait] = []
    for r in qt_rides:
        local_id = mapping.get(r.get("id"))
        if not local_id:
            continue
        wait = int(r.get("wait_time") or 0)
        is_open = bool(r.get("is_open", False))
        observations.append((local_id, wait, is_open))
        ride_waits.append(RideWait(attraction_id=local_id, wait_minutes=wait, is_open=is_open))

    live_cache.record_snapshot(req.park, observations)

    cal = _compute_calibration(req.park, date.today())

    return LivePollResponse(
        park=req.park,
        fetched_at=datetime.now().isoformat(timespec="seconds"),
        rides=ride_waits,
        calibration=cal,
    )


@router.get("/calibration", response_model=Calibration)
def calibration(park: str) -> Calibration:
    return _compute_calibration(park, date.today())
