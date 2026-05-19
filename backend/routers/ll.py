"""Lightning Lane booking plan endpoint.

POST /api/ll-plan
  Input: a planned itinerary + park + date.
  Output: ordered booking actions with predicted return windows and priority.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.data.attractions_db import attraction_by_id
from backend.data.disney_db import disney_attraction_by_id
from backend.data.disneyland_db import disneyland_attraction_by_id
from backend.ml.crowd_factors import forecast_for
from backend.ml.ll_strategy import optimize_ll_plan, PlannedRide
from backend.ml.model import predictor


router = APIRouter(prefix="/api", tags=["ll"])

_RESOLVERS = {
    "epic_universe": attraction_by_id,
    "disneyland":    disneyland_attraction_by_id,
}


def _resolve(attraction_id: str, park: str):
    return _RESOLVERS.get(park, disney_attraction_by_id)(attraction_id)


# Canonical park open/close (in hours) for default plan windows.
_PARK_HOURS: dict[str, tuple[int, int]] = {
    "epic_universe":      (9, 21),
    "magic_kingdom":      (9, 22),
    "epcot":              (9, 21),
    "hollywood_studios":  (9, 21),
    "animal_kingdom":     (9, 18),
    "disneyland":         (9, 23),
}


class LLPlanRideIn(BaseModel):
    attraction_id: str
    planned_minute: int = Field(..., description="Minutes since park open you plan to ride")
    must_do: bool = False


class LLPlanRequest(BaseModel):
    target_date: str
    park: str
    early_entry: bool = False
    rides: list[LLPlanRideIn]
    arrival_minute: Optional[int] = None  # minutes since park open the user arrives
    ll_reserved_ids: list[str] = Field(default_factory=list)  # LLSP pre-booked attraction IDs — skip from LLMP


class LLBookingOut(BaseModel):
    attraction_id: str
    attraction_name: str
    book_at_minute: int
    predicted_return_minute: int
    savings_minutes: int
    priority: str
    reason: str


class LLPlanResponse(BaseModel):
    bookings: list[LLBookingOut]
    park_open_minute: int
    park_close_minute: int
    day_crowd_multiplier: float


@router.post("/ll-plan", response_model=LLPlanResponse)
def ll_plan(req: LLPlanRequest) -> LLPlanResponse:
    try:
        d = date.fromisoformat(req.target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")

    park_open_h, park_close_h = _PARK_HOURS.get(req.park, (9, 21))
    if req.early_entry:
        park_open_h -= 1
    park_open_minute = 0
    park_close_minute = (park_close_h - park_open_h) * 60

    crowd = forecast_for(d).base_multiplier

    ll_reserved_set = set(req.ll_reserved_ids)
    planned: list[PlannedRide] = []
    for r in req.rides:
        a = _resolve(r.attraction_id, req.park)
        if a is None:
            continue
        if a.ll_type != "multi":
            continue  # LLSP and no-LL rides aren't part of the LLMP booking strategy
        if a.id in ll_reserved_set:
            continue  # already booked via LLSP pre-booking — skip from LLMP plan
        planned.append(PlannedRide(
            attraction=a,
            planned_minute=r.planned_minute,
            must_do=r.must_do,
        ))

    # Optional: hook a standby predictor in to refine savings estimates.
    # For v1, the strategy module uses a tier-based default.
    def _predict_standby(ride, planned_min: int) -> int:
        # Convert planned_min to absolute hour for the predictor.
        hour_of_day = park_open_h + planned_min // 60
        rows = predictor.predict_hours_batch(
            ride, d, [hour_of_day], early_entry=req.early_entry, park_id=req.park,
        )
        return rows[0]["wait_minutes"] if rows else 30

    bookings = optimize_ll_plan(
        planned, crowd, park_open_minute, park_close_minute,
        predict_standby=_predict_standby,
        first_booking_minute=req.arrival_minute,
    )

    return LLPlanResponse(
        bookings=[LLBookingOut(**b.to_dict()) for b in bookings],
        park_open_minute=park_open_minute,
        park_close_minute=park_close_minute,
        day_crowd_multiplier=round(crowd, 3),
    )
