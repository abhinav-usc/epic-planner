"""Itinerary optimization endpoint.

Algorithm (v2 — land-clustering + permutation search):
  1. Anchor shows at their chosen (or first available) showtime.
  2. Group non-show attractions by land.
  3. Try all permutations of land visit order (5! = 120 max), optionally
     pinning the first land to `rope_drop_land`.
  4. For each permutation, simulate the day:
       - Walk to each land, schedule attractions greedily by predicted wait.
       - Reserve `break_minutes` of buffer around midday.
  5. Pick the permutation with the lowest total (wait + walk).
"""
from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.data.attractions_db import (
    Attraction,
    LANDS,
    attraction_by_id,
    walk_minutes,
    ll_wait_minutes,
)
from backend.data.disney_db import (
    disney_attraction_by_id,
    disney_walk_minutes,
    DISNEY_PARKS,
)
from backend.data.disneyland_db import (
    disneyland_attraction_by_id,
    disneyland_walk_minutes,
    DISNEYLAND_PARKS,
)

# Canonical close hours per park (source of truth).
_PARK_CLOSE_HOURS: dict[str, int] = {
    "epic_universe": 21,
    **{pid: meta["close_hour"] for pid, meta in DISNEY_PARKS.items()},
    **{pid: meta["close_hour"] for pid, meta in DISNEYLAND_PARKS.items()},
}
from backend.data.historical_waits import historical_db, disney_historical_db

import re as _re
def _slugify(name: str) -> str:
    return _re.sub(r"[^a-z0-9]", "", name.lower())
from backend.ml.model import predictor

EPIC_PARK_ID = "epic_universe"


def _resolve_attraction(attraction_id: str, park_id: str):
    if park_id == EPIC_PARK_ID:
        return attraction_by_id(attraction_id)
    if park_id == "disneyland":
        return disneyland_attraction_by_id(attraction_id)
    return disney_attraction_by_id(attraction_id)


def _walk(park_id: str, from_land: Optional[str], to_land: str) -> int:
    if from_land is None or from_land == to_land:
        return 0
    if park_id == EPIC_PARK_ID:
        return walk_minutes(from_land, to_land)
    if park_id == "disneyland":
        return disneyland_walk_minutes(from_land, to_land)
    return disney_walk_minutes(park_id, from_land, to_land)


router = APIRouter(prefix="/api", tags=["optimize"])

PARK_CLOSE_HOUR = 21
MUST_DO_BUFFER_HOURS = 3   # must-dos should start before close minus this many hours

DEFAULT_FOOD_BREAKS = [
    {"duration_minutes": 30, "earliest_hour": 10, "latest_hour": 11},
    {"duration_minutes": 60, "earliest_hour": 12, "latest_hour": 13},
    {"duration_minutes": 30, "earliest_hour": 15, "latest_hour": 16},
]


# ── Request / Response models ──────────────────────────────────────────────────

class PriorityItem(BaseModel):
    attraction_id: str
    must_do: bool = False
    rank: int = 100
    chosen_showtime: Optional[str] = None   # "HH:MM" — user-selected showtime


class FoodBreakConfig(BaseModel):
    duration_minutes: int = 60
    earliest_hour: int = 12
    latest_hour: int = 13   # latest allowed start hour (inclusive)
    start_minute: Optional[int] = None   # pinned start (minutes since park open)
    end_minute: Optional[int] = None     # paired with start_minute; duration = end_minute - start_minute


class ShoppingBreakConfig(BaseModel):
    land: str
    duration_minutes: int = 15


class LlReservationIn(BaseModel):
    attraction_id: str
    window_start_minute: int   # minutes since park open when the return window opens


class OptimizeRequest(BaseModel):
    target_date: str = Field(..., description="YYYY-MM-DD")
    priorities: list[PriorityItem]
    early_entry: bool = False
    park_open_hour: int = 9
    early_entry_hour: int = 8
    park_close_hour: int = PARK_CLOSE_HOUR
    arrival_hour: Optional[int] = None   # override: simulate starting from this hour
    rope_drop_land: Optional[str] = None
    break_minutes: int = 60              # legacy — used only if food_breaks is None
    food_breaks: Optional[list[FoodBreakConfig]] = None   # None → use DEFAULT_FOOD_BREAKS
    shopping_breaks: list[ShoppingBreakConfig] = Field(default_factory=list)
    park_id: str = EPIC_PARK_ID
    use_ll_multi: bool = False        # user has LL Multi Pass (reduces all LLMP rides)
    ll_single_ids: list[str] = Field(default_factory=list)  # ride IDs where user bought LLSP
    ll_reservations: list[LlReservationIn] = Field(default_factory=list)  # pre-booked LLSP return windows
    land_hopping: bool = False        # greedy global scheduler (ignore land clustering)


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dt(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(d, datetime.min.time()).replace(hour=hour, minute=minute)


def _fits(start: datetime, end: datetime, occupied: list[tuple[datetime, datetime]]) -> bool:
    return all(end <= os or start >= oe for os, oe in occupied)


def _predict_total(a: Attraction, start: datetime, early_entry: bool,
                   park_id: str = EPIC_PARK_ID,
                   use_ll_multi: bool = False,
                   ll_single_ids: frozenset[str] = frozenset()) -> tuple[int, datetime]:
    """Return (wait_minutes, end_time).

    For Epic past dates, uses actual recorded wait times from historical DB.
    For Disney parks and future dates, uses model predictions.
    Applies LL wait reductions when use_ll_multi / ll_single_ids indicate access.
    """
    wait: int
    if start.date() < date.today():
        if park_id == EPIC_PARK_ID:
            actual = historical_db.get_wait(start.date().isoformat(), a.name, start.hour)
        else:
            actual = disney_historical_db.get_wait(park_id, start.date().isoformat(), _slugify(a.name), start.hour)
        wait = actual if actual is not None else predictor.predict(a, start, early_entry=early_entry, park_id=park_id).wait_minutes
    else:
        wait = predictor.predict(a, start, early_entry=early_entry, park_id=park_id).wait_minutes
    ll_type = getattr(a, "ll_type", None)
    if ll_type == "multi" and use_ll_multi:
        wait = ll_wait_minutes(wait, "multi")
    elif ll_type == "single" and a.id in ll_single_ids:
        wait = ll_wait_minutes(wait, "single")
    end = start + timedelta(minutes=wait + a.duration_minutes)
    return wait, end


def _simulate_land(
    attractions: list[Attraction],
    arrive: datetime,
    close: datetime,
    occupied: list[tuple[datetime, datetime]],
    early_entry: bool,
    must_do_ids: set[str] | None = None,
    park_id: str = EPIC_PARK_ID,
    use_ll_multi: bool = False,
    ll_single_ids: frozenset[str] = frozenset(),
) -> tuple[list[ItineraryItem], int, datetime, set[str]]:
    """
    Greedy schedule attractions within one land starting from `arrive`.
    Returns (items_scheduled, total_wait, time_when_land_done, unscheduled_must_do_ids).

    Must-do attractions are always scheduled before optional ones while the
    current time is earlier than `close - MUST_DO_BUFFER_HOURS`.
    Must-dos are allowed to start before close even if they'd finish after
    (guests can queue up to closing and complete the ride).
    """
    remaining = list(attractions)
    current_time = arrive
    items: list[ItineraryItem] = []
    total_wait = 0
    must_do_ids = must_do_ids or set()
    must_do_deadline = close - timedelta(hours=MUST_DO_BUFFER_HOURS)

    while remaining:
        # Prefer must-dos while any remain and we're still before their deadline.
        must_do_priority = False
        candidates = remaining
        if must_do_ids and current_time < must_do_deadline:
            must_do_left = [a for a in remaining if a.id in must_do_ids]
            if must_do_left:
                candidates = must_do_left
                must_do_priority = True

        best_attr: Optional[Attraction] = None
        best_wait = 999999
        best_end: Optional[datetime] = None
        best_start = current_time

        for a in candidates:
            is_must_do = a.id in must_do_ids
            t = current_time
            wait, end = _predict_total(a, t, early_entry, park_id=park_id, use_ll_multi=use_ll_multi, ll_single_ids=ll_single_ids)
            # Must-dos: allow queuing before close even if the ride finishes after.
            if t >= close:
                continue
            if end > close and not is_must_do:
                continue
            if not _fits(t, end, occupied):
                # Try up to 15-min increments to dodge occupied windows.
                bumped = t
                for _ in range(20):
                    bumped += timedelta(minutes=15)
                    if bumped >= close:
                        break
                    wait, end = _predict_total(a, bumped, early_entry, park_id=park_id, use_ll_multi=use_ll_multi, ll_single_ids=ll_single_ids)
                    fits_time = end <= close or is_must_do
                    if fits_time and _fits(bumped, end, occupied):
                        if wait < best_wait:
                            best_wait = wait
                            best_attr = a
                            best_end = end
                            best_start = bumped
                        break
                continue
            if wait < best_wait:
                best_wait = wait
                best_attr = a
                best_end = end
                best_start = t

        if best_attr is None:
            if must_do_priority:
                # Must-dos didn't fit right now; fall back to optional items so
                # the clock advances and we can retry the must-do later.
                optional = [a for a in remaining if a.id not in must_do_ids]
                for a in optional:
                    t = current_time
                    wait, end = _predict_total(a, t, early_entry, park_id=park_id, use_ll_multi=use_ll_multi, ll_single_ids=ll_single_ids)
                    if end > close or not _fits(t, end, occupied):
                        continue
                    if wait < best_wait:
                        best_wait = wait
                        best_attr = a
                        best_end = end
                        best_start = t
            if best_attr is None:
                break  # nothing fits

        current_time = best_start
        remaining.remove(best_attr)
        items.append(ItineraryItem(
            attraction_id=best_attr.id, name=best_attr.name, land=best_attr.land,
            start_time=current_time, end_time=best_end,
            wait_minutes=best_wait, activity_minutes=best_attr.duration_minutes,
            walk_minutes_from_prev=0,
        ))
        occupied.append((current_time, best_end))
        total_wait += best_wait
        current_time = best_end

    unscheduled_must_dos = {a.id for a in remaining if a.id in must_do_ids}
    return items, total_wait, current_time, unscheduled_must_dos


def _simulate_order(
    land_order: list[str],
    by_land: dict[str, list[Attraction]],
    anchored_items: list[ItineraryItem],
    anchored_occupied: list[tuple[datetime, datetime]],
    d: date,
    open_hour: int,
    close_hour: int,
    early_entry: bool,
    food_break_windows: list[tuple[datetime, datetime]],
    shopping_by_land: dict[str, int],
    must_do_ids: set[str] | None = None,
    park_id: str = EPIC_PARK_ID,
    use_ll_multi: bool = False,
    ll_single_ids: frozenset[str] = frozenset(),
) -> tuple[list[ItineraryItem], int, int, set[str]]:
    """
    Simulate visiting lands in given order.
    Returns (all_items_including_shopping_breaks, total_wait, total_walk+penalty).
    Food break items are added in optimize() after the best permutation is chosen.
    """
    must_do_ids = must_do_ids or set()
    occupied = list(anchored_occupied) + list(food_break_windows)
    close = _dt(d, close_hour)
    must_do_deadline = close - timedelta(hours=MUST_DO_BUFFER_HOURS)

    current_time = _dt(d, open_hour)
    all_items: list[ItineraryItem] = []
    total_wait = 0
    total_walk = 0
    prev_land: Optional[str] = None
    unscheduled_must_dos: set[str] = set()

    for land in land_order:
        attractions = by_land.get(land, [])
        if not attractions:
            continue

        # Walk to this land
        walk = _walk(park_id, prev_land, land) if prev_land else 0
        current_time += timedelta(minutes=walk)
        total_walk += walk

        if current_time >= close:
            # Park is closed — any must-dos in this land are unscheduled.
            unscheduled_must_dos.update(a.id for a in attractions if a.id in must_do_ids)
            break

        items, wait, done_time, land_unscheduled = _simulate_land(
            list(attractions), current_time, close, occupied, early_entry,
            must_do_ids=must_do_ids, park_id=park_id,
            use_ll_multi=use_ll_multi, ll_single_ids=ll_single_ids,
        )
        unscheduled_must_dos.update(land_unscheduled)
        if items:
            items[0].walk_minutes_from_prev = walk
        all_items.extend(items)
        total_wait += wait
        current_time = done_time

        # Insert shopping break for this land (if configured).
        shop_dur = shopping_by_land.get(land, 0)
        if shop_dur > 0 and current_time < close:
            shop_end = current_time + timedelta(minutes=shop_dur)
            occupied.append((current_time, shop_end))
            all_items.append(ItineraryItem(
                attraction_id=f"break_shop_{land}",
                name="Shopping break",
                land=land,
                start_time=current_time,
                end_time=shop_end,
                wait_minutes=0,
                activity_minutes=shop_dur,
                walk_minutes_from_prev=0,
            ))
            current_time = shop_end

        prev_land = land

    # Penalise permutations where must-dos end up in the last 3 hours.
    late_penalty = sum(
        50_000 for it in all_items
        if it.attraction_id in must_do_ids and it.start_time >= must_do_deadline
    )
    # Heavy penalty per unscheduled must-do — ensures the permutation search
    # strongly prefers orderings that actually include all must-dos.
    missed_penalty = len(unscheduled_must_dos) * 500_000
    total_walk += late_penalty + missed_penalty

    return all_items, total_wait, total_walk, unscheduled_must_dos


def _simulate_hopping(
    by_land: dict[str, list[Attraction]],
    anchored_occupied: list[tuple[datetime, datetime]],
    d: date,
    open_hour: int,
    close_hour: int,
    early_entry: bool,
    food_break_windows: list[tuple[datetime, datetime]],
    shopping_by_land: dict[str, int],
    must_do_ids: set[str] | None = None,
    park_id: str = EPIC_PARK_ID,
    use_ll_multi: bool = False,
    ll_single_ids: frozenset[str] = frozenset(),
) -> tuple[list[ItineraryItem], int, int, set[str]]:
    """
    Greedy global scheduler: at each step pick the attraction across ALL remaining
    attractions that minimises walk_to_it + predicted_wait. Must-dos are prioritised
    until must_do_deadline. No land-visit-order permutation search needed.

    Returns (all_items, total_wait, score, unscheduled_must_dos).
    """
    must_do_ids = must_do_ids or set()
    occupied = list(anchored_occupied) + list(food_break_windows)
    close = _dt(d, close_hour)
    must_do_deadline = close - timedelta(hours=MUST_DO_BUFFER_HOURS)

    current_time = _dt(d, open_hour)
    current_land: Optional[str] = None
    all_items: list[ItineraryItem] = []
    total_wait = 0
    total_walk = 0

    remaining: list[Attraction] = [a for atts in by_land.values() for a in atts]

    while remaining:
        must_do_left = [a for a in remaining if a.id in must_do_ids]
        use_must_do_priority = bool(must_do_left) and current_time < must_do_deadline
        candidates = must_do_left if use_must_do_priority else remaining

        best_attr: Optional[Attraction] = None
        best_score: float = float("inf")
        best_wait = 0
        best_end: Optional[datetime] = None
        best_start = current_time
        best_walk = 0

        def _score_candidate(a: Attraction) -> None:
            nonlocal best_attr, best_score, best_wait, best_end, best_start, best_walk
            is_must_do = a.id in must_do_ids
            walk = _walk(park_id, current_land, a.land) if current_land else 0
            t = current_time + timedelta(minutes=walk)
            if t >= close:
                return
            wait, end = _predict_total(a, t, early_entry, park_id=park_id,
                                       use_ll_multi=use_ll_multi, ll_single_ids=ll_single_ids)
            if end > close and not is_must_do:
                return
            if not _fits(t, end, occupied):
                bumped = t
                found = False
                for _ in range(20):
                    bumped += timedelta(minutes=15)
                    if bumped >= close:
                        break
                    wait, end = _predict_total(a, bumped, early_entry, park_id=park_id,
                                               use_ll_multi=use_ll_multi, ll_single_ids=ll_single_ids)
                    if (end <= close or is_must_do) and _fits(bumped, end, occupied):
                        t = bumped
                        found = True
                        break
                if not found:
                    return
            score = walk + wait
            if score < best_score:
                best_score = score
                best_attr = a
                best_wait = wait
                best_end = end
                best_start = t
                best_walk = walk

        for a in candidates:
            _score_candidate(a)

        if best_attr is None and use_must_do_priority:
            for a in [x for x in remaining if x.id not in must_do_ids]:
                _score_candidate(a)

        if best_attr is None:
            break

        total_walk += best_walk
        total_wait += best_wait
        current_land = best_attr.land
        remaining.remove(best_attr)
        all_items.append(ItineraryItem(
            attraction_id=best_attr.id, name=best_attr.name, land=best_attr.land,
            start_time=best_start, end_time=best_end,
            wait_minutes=best_wait, activity_minutes=best_attr.duration_minutes,
            walk_minutes_from_prev=best_walk,
        ))
        occupied.append((best_start, best_end))
        current_time = best_end

    # Shopping breaks: insert right after the last scheduled attraction for each land.
    for land, dur in shopping_by_land.items():
        if dur <= 0:
            continue
        land_items = [it for it in all_items if it.land == land]
        if not land_items:
            continue
        last = max(land_items, key=lambda it: it.end_time)
        if last.end_time >= close:
            continue
        shop_end = last.end_time + timedelta(minutes=dur)
        all_items.append(ItineraryItem(
            attraction_id=f"break_shop_{land}",
            name="Shopping break",
            land=land,
            start_time=last.end_time,
            end_time=shop_end,
            wait_minutes=0,
            activity_minutes=dur,
            walk_minutes_from_prev=0,
        ))

    unscheduled_must_dos = {a.id for a in remaining if a.id in must_do_ids}
    missed_penalty = len(unscheduled_must_dos) * 500_000
    late_penalty = sum(
        50_000 for it in all_items
        if it.attraction_id in must_do_ids and it.start_time >= must_do_deadline
    )
    return all_items, total_wait, total_walk + late_penalty + missed_penalty, unscheduled_must_dos


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        d = date.fromisoformat(req.target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")

    park_id = req.park_id

    # Always use the canonical close hour for the park unless the client explicitly
    # sent a non-default value.
    close_hour = _PARK_CLOSE_HOURS.get(park_id, req.park_close_hour)

    resolved: list[tuple[PriorityItem, Attraction]] = []
    for pr in req.priorities:
        a = _resolve_attraction(pr.attraction_id, park_id)
        if not a:
            raise HTTPException(status_code=404, detail=f"Unknown attraction: {pr.attraction_id}")
        resolved.append((pr, a))

    open_hour = req.early_entry_hour if req.early_entry else req.park_open_hour
    # arrival_hour lets the user start the simulation later (e.g. arriving at 11 AM).
    effective_start_hour = max(open_hour, req.arrival_hour) if req.arrival_hour else open_hour
    close = _dt(d, close_hour)

    # ── 1a. Anchor pre-booked LLSP return windows ───────────────────────────
    anchored: list[ItineraryItem] = []
    anchored_occupied: list[tuple[datetime, datetime]] = []
    ll_reserved_ids: set[str] = set()

    for llr in req.ll_reservations:
        a = _resolve_attraction(llr.attraction_id, park_id)
        if not a:
            continue
        ll_reserved_ids.add(a.id)
        # Schedule the ride at the window start; use LLSP in-queue wait (~5-15 min).
        standby = predictor.predict(a, _dt(d, open_hour) + timedelta(minutes=llr.window_start_minute),
                                    early_entry=req.early_entry, park_id=park_id).wait_minutes
        ll_wait = ll_wait_minutes(standby, "single")
        start = _dt(d, open_hour) + timedelta(minutes=llr.window_start_minute)
        end = start + timedelta(minutes=ll_wait + a.duration_minutes)
        anchored.append(ItineraryItem(
            attraction_id=a.id, name=a.name, land=a.land,
            start_time=start, end_time=end,
            wait_minutes=ll_wait, activity_minutes=a.duration_minutes,
            walk_minutes_from_prev=0,
            notes=[f"Pre-booked LLSP — return window {start.strftime('%I:%M %p').lstrip('0')}"],
        ))
        anchored_occupied.append((start, end))

    # ── 1b. Anchor shows at user-chosen or first-available showtime ──────────
    show_prs = [(pr, a) for pr, a in resolved if a.kind == "show" and a.showtimes]
    for pr, a in show_prs:
        # Prefer user-chosen showtime, fall back to first available.
        candidates = []
        if pr.chosen_showtime:
            candidates = [pr.chosen_showtime]
        candidates += [st for st in (a.showtimes or []) if st != pr.chosen_showtime]

        chosen_start: Optional[datetime] = None
        for st in candidates:
            hh, mm = map(int, st.split(":"))
            start = _dt(d, hh, mm)
            end = start + timedelta(minutes=a.duration_minutes + 10)
            if (start.hour >= effective_start_hour and end <= close
                    and _fits(start, end, anchored_occupied)):
                chosen_start = start
                break

        if chosen_start is None:
            continue
        end = chosen_start + timedelta(minutes=a.duration_minutes + 10)
        note = f"Show at {chosen_start.strftime('%I:%M %p').lstrip('0')}"
        if pr.chosen_showtime:
            note += " (your choice)"
        anchored.append(ItineraryItem(
            attraction_id=a.id, name=a.name, land=a.land,
            start_time=chosen_start, end_time=end,
            wait_minutes=10, activity_minutes=a.duration_minutes,
            walk_minutes_from_prev=0,
            notes=[note],
        ))
        anchored_occupied.append((chosen_start, end))

    # ── 2. Group non-shows by land (exclude pre-booked LL rides) ──────────────
    non_shows = [(pr, a) for pr, a in resolved if a.kind != "show" and a.id not in ll_reserved_ids]
    # Must-dos first within each land, then by rank
    non_shows.sort(key=lambda pa: (not pa[0].must_do, pa[0].rank))

    must_do_ids: set[str] = {a.id for pr, a in non_shows if pr.must_do}

    by_land: dict[str, list[Attraction]] = {}
    for _, a in non_shows:
        by_land.setdefault(a.land, []).append(a)

    lands_to_visit = [l for l in by_land if by_land[l]]

    # ── 3. Resolve break configurations ────────────────────────────────────
    food_breaks: list[FoodBreakConfig] = req.food_breaks if req.food_breaks is not None else [
        FoodBreakConfig(**fb) for fb in DEFAULT_FOOD_BREAKS
    ]
    # Override the middle break's duration with legacy break_minutes if larger.
    if req.food_breaks is None and req.break_minutes > 60:
        food_breaks[1] = FoodBreakConfig(
            duration_minutes=req.break_minutes,
            earliest_hour=food_breaks[1].earliest_hour,
            latest_hour=food_breaks[1].latest_hour,
        )

    # Pre-compute food break occupied windows.
    food_break_windows: list[tuple[datetime, datetime]] = []
    for fb in food_breaks:
        if fb.start_minute is not None:
            # Pinned break (user has a reservation) — honour exactly, no nudging.
            start = _dt(d, open_hour) + timedelta(minutes=fb.start_minute)
            dur = (fb.end_minute - fb.start_minute) if fb.end_minute is not None else fb.duration_minutes
            end = start + timedelta(minutes=dur)
        else:
            start_h = max(fb.earliest_hour, effective_start_hour)
            start = _dt(d, start_h)
            end = start + timedelta(minutes=fb.duration_minutes)
            # Nudge forward in 5-min steps until clear of pre-booked LL reservations.
            for _ in range(24):  # max 2h of nudging
                if not any(start < oe and os < end for os, oe in anchored_occupied):
                    break
                start += timedelta(minutes=5)
                end = start + timedelta(minutes=fb.duration_minutes)
        if start < close:
            food_break_windows.append((start, end))

    shopping_by_land: dict[str, int] = {sb.land: sb.duration_minutes for sb in req.shopping_breaks}

    # ── 4. Schedule attractions ─────────────────────────────────────────────
    best_items: list[ItineraryItem] = []
    best_score = float("inf")
    best_unscheduled: set[str] = set()

    if req.land_hopping:
        # Global greedy: pick the next attraction minimising walk + wait regardless of land.
        items, total_wait, score, unscheduled = _simulate_hopping(
            by_land, anchored_occupied,
            d, effective_start_hour, close_hour, req.early_entry,
            food_break_windows=food_break_windows,
            shopping_by_land=shopping_by_land,
            must_do_ids=must_do_ids,
            park_id=park_id,
            use_ll_multi=req.use_ll_multi,
            ll_single_ids=frozenset(req.ll_single_ids),
        )
        best_items = items
        best_score = score
        best_unscheduled = unscheduled
    else:
        # Permutation search over land visit order (default, land-clustering).
        if req.rope_drop_land and req.rope_drop_land in lands_to_visit:
            first = [req.rope_drop_land]
            rest = [l for l in lands_to_visit if l != req.rope_drop_land]
            permutations = [first + list(p) for p in itertools.permutations(rest)]
        else:
            permutations = [list(p) for p in itertools.permutations(lands_to_visit)]

        permutations = permutations[:120]

        for perm in permutations:
            items, total_wait, total_walk, unscheduled = _simulate_order(
                perm, by_land, anchored, anchored_occupied,
                d, effective_start_hour, close_hour, req.early_entry,
                food_break_windows=food_break_windows,
                shopping_by_land=shopping_by_land,
                must_do_ids=must_do_ids,
                park_id=park_id,
                use_ll_multi=req.use_ll_multi,
                ll_single_ids=frozenset(req.ll_single_ids),
            )
            score = total_wait + total_walk * 2
            if score < best_score:
                best_score = score
                best_items = items
                best_unscheduled = unscheduled

    # ── 5. Build food break ItineraryItems from the reserved windows ───────
    food_break_items: list[ItineraryItem] = []
    names = ["Morning snack", "Lunch", "Afternoon snack", "Evening snack"]
    for i, (fb, (fb_start, fb_end)) in enumerate(zip(food_breaks, food_break_windows)):
        food_break_items.append(ItineraryItem(
            attraction_id=f"break_food_{i}",
            name=names[i] if i < len(names) else f"Food break {i+1}",
            land="break",
            start_time=fb_start,
            end_time=fb_end,
            wait_minutes=0,
            activity_minutes=fb.duration_minutes,
            walk_minutes_from_prev=0,
        ))

    # ── 6. Merge anchored shows + best non-show schedule + food breaks ─────
    all_items = best_items + anchored + food_break_items
    all_items.sort(key=lambda it: it.start_time)

    # Recompute walk_minutes_from_prev in final sorted order, skipping breaks
    # (breaks happen in-place; don't charge walk to the next ride either).
    prev_land_final: Optional[str] = None
    for it in all_items:
        if it.land == "break":
            it.walk_minutes_from_prev = 0
            # Leave prev_land_final unchanged so the next ride after a break
            # pays the correct walk cost from the last actual land visited.
        else:
            it.walk_minutes_from_prev = _walk(park_id, prev_land_final, it.land) if prev_land_final else 0
            prev_land_final = it.land

    # ── 6. Warnings ────────────────────────────────────────────────────────
    warnings: list[str] = []

    # Attractions that couldn't be scheduled
    scheduled_ids = {it.attraction_id for it in all_items}
    for pr, a in resolved:
        if a.id not in scheduled_ids:
            if pr.must_do:
                warnings.append(
                    f"⚠ Must-do {a.name} could not be fit — too many attractions "
                    f"or insufficient park time. Try removing lower-priority items."
                )
            else:
                warnings.append(f"Could not fit {a.name} — insufficient park time")

    for it in all_items:
        if it.land == "break":
            continue
        if it.wait_minutes >= 90:
            warnings.append(
                f"{it.name} at {it.start_time.strftime('%I:%M %p').lstrip('0')}: "
                f"{it.wait_minutes}-min wait"
            )

    total_wait = sum(it.wait_minutes for it in all_items)
    total_activity = sum(it.activity_minutes for it in all_items)
    feasible = all(it.end_time <= close for it in all_items)

    return OptimizeResponse(
        target_date=d.isoformat(),
        items=all_items,
        total_wait_minutes=total_wait,
        total_activity_minutes=total_activity,
        feasible=feasible,
        warnings=warnings,
    )
