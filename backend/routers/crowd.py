"""Crowd forecast endpoint."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, HTTPException

from backend.ml.crowd_factors import forecast_for


router = APIRouter(prefix="/api/crowd", tags=["crowd"])


@router.get("/forecast/{target_date}")
def crowd_forecast(target_date: str) -> dict:
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
    return asdict(forecast_for(d))
