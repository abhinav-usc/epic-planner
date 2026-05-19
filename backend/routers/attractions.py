"""Attractions / restaurants / lands endpoints (multi-park)."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, HTTPException, Query

from backend.data.attractions_db import (
    LANDS as EPIC_LANDS,
    all_attractions,
    all_restaurants,
    attraction_by_id,
    restaurant_by_id,
)
from backend.data.disney_db import (
    DISNEY_PARKS,
    disney_lands,
    disney_attractions,
    disney_restaurants,
    disney_attraction_by_id,
)
from backend.data.disneyland_db import (
    DISNEYLAND_PARKS,
    disneyland_lands,
    disneyland_attractions,
    disneyland_restaurants,
    disneyland_attraction_by_id,
)


router = APIRouter(prefix="/api", tags=["catalog"])

EPIC_PARK_ID = "epic_universe"

ALL_PARKS = {
    EPIC_PARK_ID: {
        "name": "Epic Universe",
        "icon": "🌌",
        "description": "Universal's newest park. Five themed worlds.",
        "open_hour": 9,
        "close_hour": 21,
    },
    **DISNEY_PARKS,
    **DISNEYLAND_PARKS,
}


def _resolve_lands(park: str) -> dict | None:
    if park == EPIC_PARK_ID:
        return EPIC_LANDS
    if park in DISNEY_PARKS:
        return disney_lands(park) or None
    if park == "disneyland":
        return disneyland_lands()
    return None


def _resolve_attractions(park: str, visit_date: date | None = None) -> list[dict] | None:
    if park == EPIC_PARK_ID:
        return all_attractions()
    if park in DISNEY_PARKS:
        return disney_attractions(park, visit_date)
    if park == "disneyland":
        return disneyland_attractions()
    return None


def _resolve_attraction_by_id(attraction_id: str, park: str):
    if park == EPIC_PARK_ID:
        return attraction_by_id(attraction_id)
    if park in DISNEY_PARKS:
        return disney_attraction_by_id(attraction_id)
    if park == "disneyland":
        return disneyland_attraction_by_id(attraction_id)
    return None


def _resolve_restaurants(park: str) -> list[dict]:
    if park == EPIC_PARK_ID:
        return all_restaurants()
    if park in DISNEY_PARKS:
        return disney_restaurants(park)
    if park == "disneyland":
        return disneyland_restaurants()
    return []


@router.get("/parks")
def get_parks() -> dict:
    return ALL_PARKS


@router.get("/lands")
def get_lands(park: str = Query(EPIC_PARK_ID)) -> dict:
    lands = _resolve_lands(park)
    if lands is None:
        raise HTTPException(status_code=404, detail=f"Unknown park: {park}")
    return lands


@router.get("/attractions")
def get_attractions(
    park: str = Query(EPIC_PARK_ID),
    visit_date: str = Query(None, description="YYYY-MM-DD — annotates closed/refurb rides"),
) -> list[dict]:
    parsed_date: date | None = None
    if visit_date:
        try:
            parsed_date = date.fromisoformat(visit_date)
        except ValueError:
            pass
    attrs = _resolve_attractions(park, parsed_date)
    if attrs is None:
        raise HTTPException(status_code=404, detail=f"Unknown park: {park}")
    return attrs


@router.get("/attractions/{attraction_id}")
def get_attraction(attraction_id: str, park: str = Query(EPIC_PARK_ID)) -> dict:
    a = _resolve_attraction_by_id(attraction_id, park)
    if not a:
        raise HTTPException(status_code=404, detail=f"Attraction '{attraction_id}' not found")
    return a.to_dict()


@router.get("/restaurants")
def get_restaurants(park: str = Query(EPIC_PARK_ID)) -> list[dict]:
    return _resolve_restaurants(park)


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str) -> dict:
    r = restaurant_by_id(restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Restaurant '{restaurant_id}' not found")
    return r.to_dict()
