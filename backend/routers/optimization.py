"""Itinerary optimization endpoint."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.data.attractions_db import (
    Attraction,
    attraction_by_id,
    walk_minutes,
)
from backend.ml.model import predictor


router = APIRouter(prefix="/api", tags=["optimize"])


class PriorityItem(BaseModel):
    attraction_id: str
    must_do: bool = False
    rank: int = 100  # lower = higher priority among non-must-dos


class OptimizeRequest(BaseModel):
    target_date: str = Field(..., description="YYYY-MM-DD")
    priorities: list[PriorityItem]
    early_entry: bool = False
    park_open_hour: int = 9   # standard open
    early_entry_hour: int = 8
    park_close_hour: int = 22


class ItineraryItem(BaseModel):
    attraction_id: str
    name: str
    land: str
    start_time: datetime
    end_time: datetime
    wait_minutes: int
    activity_minutes: int
    walk_minutes_from_prev: int
    notes: list[str] = []


class OptimizeResponse(BaseModel):
    target_date: str
    items: list[ItineraryItem]
    total_wait_minutes: int
    total_activity_minutes: int
    feasible: bool
    warnings: list[str]


def _slots_for(d: date, open_hour: int, close_hour: int, granularity_min: int = 15) -> list[datetime]:
    base = datetime.combine(d, datetime.min.time()).replace(hour=open_hour)
    end = datetime.combine(d, datetime.min.time()).replace(hour=close_hour)
    slots = []
    cur = base
    while cur < end:
        slots.append(cur)
        cur += timedelta(minutes=granularity_min)
    return slots


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        d = date.fromisoformat(req.target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")

    # Resolve attraction objects, validate IDs.
    resolved: list[tuple[PriorityItem, Attraction]] = []
    for pr in req.priorities:
        a = attraction_by_id(pr.attraction_id)
        if not a:
            raise HTTPException(status_code=404, detail=f"Unknown attraction: {pr.attraction_id}")
        resolved.append((pr, a))

    open_hour = req.early_entry_hour if req.early_entry else req.park_open_hour
    close_hour = req.park_close_hour
    granularity = 15

    # ── 1. Anchor scheduled shows ───────────────────────────────────────────
    scheduled: list[ItineraryItem] = []
    occupied: list[tuple[datetime, datetime]] = []  # (start, end) windows

    def overlaps(s: datetime, e: datetime) -> bool:
        return any(not (e <= os or s >= oe) for os, oe in occupied)

    show_items = [(p, a) for p, a in resolved if a.kind == "show" and a.showtimes]
    for pr, a in show_items:
        chosen: Optional[datetime] = None
        for st in a.showtimes or []:
            hh, mm = map(int, st.split(":"))
            start = datetime.combine(d, datetime.min.time()).replace(hour=hh, minute=mm)
            end = start + timedelta(minutes=a.duration_minutes + 10)  # +10 min queue/exit
            if not overlaps(start, end) and start.hour >= open_hour and end.hour <= close_hour:
                chosen = start
                break
        if chosen is None:
            continue  # couldn't fit any showtime
        end = chosen + timedelta(minutes=a.duration_minutes + 10)
        scheduled.append(ItineraryItem(
            attraction_id=a.id, name=a.name, land=a.land,
            start_time=chosen, end_time=end,
            wait_minutes=10, activity_minutes=a.duration_minutes,
            walk_minutes_from_prev=0,
            notes=[f"Scheduled showtime {chosen.strftime('%I:%M %p').lstrip('0')}"],
        ))
        occupied.append((chosen, end))

    # ── 2. Sort non-show priorities: must-dos first, then by rank ───────────
    non_shows = [(p, a) for p, a in resolved if a.kind != "show"]
    non_shows.sort(key=lambda pa: (not pa[0].must_do, pa[0].rank))

    # ── 3. Greedy schedule: place each at its best-available slot ───────────
    items_by_start: list[ItineraryItem] = list(scheduled)

    def best_slot_for(a: Attraction) -> Optional[tuple[datetime, int]]:
        """Return (start_time, predicted_wait_minutes) for cheapest available slot."""
        best: Optional[tuple[datetime, int]] = None
        for slot in _slots_for(d, open_hour, close_hour, granularity):
            duration = a.duration_minutes
            pred = predictor.predict(a, slot, early_entry=req.early_entry)
            end = slot + timedelta(minutes=pred.wait_minutes + duration)
            if end.hour >= close_hour and not (end.hour == close_hour and end.minute == 0):
                continue
            if overlaps(slot, end):
                continue
            if best is None or pred.wait_minutes < best[1]:
                best = (slot, pred.wait_minutes)
        return best

    warnings: list[str] = []

    for pr, a in non_shows:
        sel = best_slot_for(a)
        if sel is None:
            warnings.append(f"Could not fit {a.name} — too crowded or insufficient park time")
            continue
        start, wait = sel
        end = start + timedelta(minutes=wait + a.duration_minutes)
        items_by_start.append(ItineraryItem(
            attraction_id=a.id, name=a.name, land=a.land,
            start_time=start, end_time=end,
            wait_minutes=wait, activity_minutes=a.duration_minutes,
            walk_minutes_from_prev=0,  # filled in below
        ))
        occupied.append((start, end))

    # ── 4. Sort by start time, add walking transitions ─────────────────────
    items_by_start.sort(key=lambda it: it.start_time)
    prev_land: Optional[str] = None
    for it in items_by_start:
        if prev_land:
            it.walk_minutes_from_prev = walk_minutes(prev_land, it.land)
        prev_land = it.land

    # ── 5. Warnings ────────────────────────────────────────────────────────
    total_wait = sum(it.wait_minutes for it in items_by_start)
    total_activity = sum(it.activity_minutes for it in items_by_start)
    feasible = all(it.end_time.hour <= close_hour for it in items_by_start)

    for it in items_by_start:
        if it.wait_minutes >= 90:
            warnings.append(f"{it.name} at {it.start_time.strftime('%I:%M %p').lstrip('0')}: {it.wait_minutes}-min wait")

    return OptimizeResponse(
        target_date=d.isoformat(),
        items=items_by_start,
        total_wait_minutes=total_wait,
        total_activity_minutes=total_activity,
        feasible=feasible,
        warnings=warnings,
    )
