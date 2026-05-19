"""Wait time prediction endpoints (multi-park)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.data.attractions_db import attraction_by_id
from backend.data.disney_db import disney_attraction_by_id
from backend.data.disneyland_db import disneyland_attraction_by_id
from backend.data.historical_waits import historical_db, disney_historical_db
from backend.data.live_waits_cache import live_cache
from backend.ml.model import predictor
from backend.ml.worst_case import lookup as worst_case_lookup


router = APIRouter(prefix="/api", tags=["predictions"])

EPIC_PARK_ID = "epic_universe"
DISNEY_PARKS = {"magic_kingdom", "epcot", "hollywood_studios", "animal_kingdom", "disneyland"}

PARK_CLOSE_HOURS: dict[str, int] = {
    "epic_universe":     21,
    "magic_kingdom":     22,
    "epcot":             21,
    "hollywood_studios": 21,
    "animal_kingdom":    18,
    "disneyland":        23,
}

import re as _re
def _slugify(name: str) -> str:
    return _re.sub(r"[^a-z0-9]", "", name.lower())

_RESOLVERS = {
    "epic_universe": attraction_by_id,
    "disneyland":    disneyland_attraction_by_id,
}


def _resolve_attraction(attraction_id: str, park: str):
    resolver = _RESOLVERS.get(park, disney_attraction_by_id)
    return resolver(attraction_id)


def _apply_live_overlay(
    rows: list[dict],
    attraction_id: str,
    park: str,
    target_date: date,
    factor_by_ride: dict[str, float],
    park_wide_factor: float,
) -> list[dict]:
    """Overlay live data on prediction rows.

    For today's date:
      - Past hours: replace predicted wait with most-recent live observation in that hour
      - Future hours: multiply predicted wait by per-ride calibration factor
                       (falls back to park-wide factor if no ride-specific data)
    Other dates: no-op.
    """
    if target_date != date.today():
        return rows
    factor = factor_by_ride.get(attraction_id, park_wide_factor)
    now_hour = datetime.now().hour
    # Build a {hour: median_actual} for past hours today
    recent_by_hour: dict[int, list[int]] = {}
    for ts, wait in live_cache.recent(park, attraction_id, hours=14.0):
        recent_by_hour.setdefault(ts.hour, []).append(wait)
    out = []
    for row in rows:
        h = row["hour"]
        if h < now_hour and h in recent_by_hour:
            actuals = recent_by_hour[h]
            row = {**row, "wait_minutes": int(round(sum(actuals) / len(actuals))), "live": True}
        elif h >= now_hour and factor != 1.0:
            row = {**row, "wait_minutes": max(0, int(round(row["wait_minutes"] * factor))), "calibrated": True}
        out.append(row)
    return out


def _apply_live_history(
    rows: list[dict],
    attraction_id: str,
    park: str,
    target_date: Optional[date] = None,
) -> list[dict]:
    """Replace model/heuristic predictions with avg-of-worst-3 from live poll history.

    For each hour where the past 14 days of live polls have ≥3 real observations,
    we take the worst 3 wait values recorded at that hour (weighted by day-of-week
    and recency matching target_date) and average them.  This replaces the model
    output entirely for that hour — real data beats any heuristic.  Hours without
    enough observations are left as-is.
    """
    live_by_hour = live_cache.worst_n_avg_by_hour(
        park, attraction_id, days=14, n=3, target_date=target_date
    )
    if not live_by_hour:
        return rows
    out = []
    for row in rows:
        live_wait = live_by_hour.get(row["hour"])
        if live_wait is not None:
            row = {**row, "wait_minutes": live_wait, "source": "live_history"}
        out.append(row)
    return out


@router.get("/attractions/{attraction_id}/wait-times")
def attraction_day_curve(
    attraction_id: str,
    target_date: str,
    early_entry: bool = False,
    park: str = Query(EPIC_PARK_ID),
    live_calibration: bool = False,
) -> dict:
    a = _resolve_attraction(attraction_id, park)
    if not a:
        raise HTTPException(status_code=404, detail=f"Attraction '{attraction_id}' not found")
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")

    open_h = 8 if early_entry else 9
    close_h = PARK_CLOSE_HOURS.get(park, 22)

    # Past dates: serve actual recorded data where available.
    if d < date.today():
        if park == EPIC_PARK_ID:
            actual = historical_db.get_day_hours(target_date, a.name, open_h, close_h)
        else:
            actual = disney_historical_db.get_day_hours(park, target_date, _slugify(a.name), open_h, close_h)
        if actual:
            for row in actual:
                wc = worst_case_lookup.worst_case(a.id, d, row["hour"]) if park == EPIC_PARK_ID else None
                row["worst_case_wait"] = wc["wait_minutes"] if wc else None
                row["worst_case_n"] = wc["sample_size"] if wc else 0
                row["crowd_multiplier"] = None
            return {"attraction_id": a.id, "date": d.isoformat(), "hours": actual, "source": "actual"}

    # Future dates (or past with no data): batch prediction for all hours at once.
    hours = list(range(open_h, close_h))
    batch = predictor.predict_hours_batch(a, d, hours, early_entry=early_entry, park_id=park)

    # Optional live overlay for today
    factor_by_ride: dict[str, float] = {}
    park_wide_factor = 1.0
    if live_calibration and d == date.today():
        from backend.routers.live import _compute_calibration
        cal = _compute_calibration(park, d)
        factor_by_ride = cal.by_ride_factor
        park_wide_factor = cal.park_wide_factor

    result_hours = []
    for row in batch:
        h = row["hour"]
        wc = worst_case_lookup.worst_case(a.id, d, h) if park == EPIC_PARK_ID else None
        result_hours.append({
            "hour": h,
            "wait_minutes": row["wait_minutes"],
            "ll_return_minutes": row.get("ll_return_minutes"),
            "worst_case_wait": wc["wait_minutes"] if wc else None,
            "worst_case_n": wc["sample_size"] if wc else 0,
            "crowd_multiplier": row["crowd_multiplier"],
        })

    if live_calibration:
        result_hours = _apply_live_overlay(result_hours, a.id, park, d, factor_by_ride, park_wide_factor)

    result_hours = _apply_live_history(result_hours, a.id, park, target_date=d)

    return {"attraction_id": a.id, "date": d.isoformat(), "hours": result_hours, "source": "predicted"}


class DayCurvesRequest(BaseModel):
    attraction_ids: list[str]
    target_date: str
    early_entry: bool = False
    park: str = EPIC_PARK_ID
    live_calibration: bool = False


@router.post("/day-curves-batch")
def day_curves_batch(req: DayCurvesRequest) -> dict:
    """Fetch day curves for multiple attractions in one request.

    Returns {attraction_id: {hours: [...], source: "actual"|"predicted"}} dict.
    For Disney parks: vectorized park_model inference across all attractions × hours.
    For Epic past dates: falls back to historical data per-attraction.
    """
    try:
        d = date.fromisoformat(req.target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")

    open_h = 8 if req.early_entry else 9
    close_h = 22
    hours = list(range(open_h, close_h))
    result: dict[str, dict] = {}

    factor_by_ride: dict[str, float] = {}
    park_wide_factor = 1.0
    if req.live_calibration and d == date.today():
        from backend.routers.live import _compute_calibration
        cal = _compute_calibration(req.park, d)
        factor_by_ride = cal.by_ride_factor
        park_wide_factor = cal.park_wide_factor

    for aid in req.attraction_ids:
        a = _resolve_attraction(aid, req.park)
        if a is None:
            continue

        # Past dates: actual data.
        if d < date.today():
            if req.park == EPIC_PARK_ID:
                actual = historical_db.get_day_hours(req.target_date, a.name, open_h, close_h)
            else:
                actual = disney_historical_db.get_day_hours(req.park, req.target_date, _slugify(a.name), open_h, close_h)
            if actual:
                for row in actual:
                    wc = worst_case_lookup.worst_case(a.id, d, row["hour"]) if req.park == EPIC_PARK_ID else None
                    row["worst_case_wait"] = wc["wait_minutes"] if wc else None
                    row["worst_case_n"] = wc["sample_size"] if wc else 0
                    row["crowd_multiplier"] = None
                result[aid] = {"attraction_id": aid, "date": d.isoformat(), "hours": actual, "source": "actual"}
                continue

        batch = predictor.predict_hours_batch(a, d, hours, early_entry=req.early_entry, park_id=req.park)
        result_hours = []
        for row in batch:
            h = row["hour"]
            wc = worst_case_lookup.worst_case(a.id, d, h) if req.park == EPIC_PARK_ID else None
            result_hours.append({
                "hour": h,
                "wait_minutes": row["wait_minutes"],
                "ll_return_minutes": row.get("ll_return_minutes"),
                "worst_case_wait": wc["wait_minutes"] if wc else None,
                "worst_case_n": wc["sample_size"] if wc else 0,
                "crowd_multiplier": row["crowd_multiplier"],
            })
        if req.live_calibration:
            result_hours = _apply_live_overlay(result_hours, a.id, req.park, d, factor_by_ride, park_wide_factor)
        result_hours = _apply_live_history(result_hours, a.id, req.park, target_date=d)
        result[aid] = {"attraction_id": aid, "date": d.isoformat(), "hours": result_hours, "source": "predicted"}

    return result
