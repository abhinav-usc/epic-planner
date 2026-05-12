"""Attractions / restaurants / lands endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.data.attractions_db import (
    LANDS,
    all_attractions,
    all_restaurants,
    attraction_by_id,
    restaurant_by_id,
)


router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/lands")
def get_lands() -> dict:
    return LANDS


@router.get("/attractions")
def get_attractions() -> list[dict]:
    return all_attractions()


@router.get("/attractions/{attraction_id}")
def get_attraction(attraction_id: str) -> dict:
    a = attraction_by_id(attraction_id)
    if not a:
        raise HTTPException(status_code=404, detail=f"Attraction '{attraction_id}' not found")
    return a.to_dict()


@router.get("/restaurants")
def get_restaurants() -> list[dict]:
    return all_restaurants()


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str) -> dict:
    r = restaurant_by_id(restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"Restaurant '{restaurant_id}' not found")
    return r.to_dict()
