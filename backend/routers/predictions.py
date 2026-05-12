"""Wait time prediction endpoints."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.data.attractions_db import attraction_by_id
from backend.ml.model import predictor


router = APIRouter(prefix="/api", tags=["predictions"])


class PredictRequest(BaseModel):
    attraction_id: str
    when: datetime
    early_entry: bool = False


class PredictResponse(BaseModel):
    attraction_id: str
    when: datetime
    wait_minutes: int
    crowd_multiplier: float
    confidence: str


@router.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    a = attraction_by_id(req.attraction_id)
    if not a:
        raise HTTPException(status_code=404, detail=f"Attraction '{req.attraction_id}' not found")
    pred = predictor.predict(a, req.when, early_entry=req.early_entry)
    return PredictResponse(
        attraction_id=a.id,
        when=req.when,
        wait_minutes=pred.wait_minutes,
        crowd_multiplier=pred.crowd_multiplier,
        confidence=pred.confidence,
    )


@router.get("/attractions/{attraction_id}/wait-times")
def attraction_day_curve(
    attraction_id: str,
    target_date: str,
    early_entry: bool = False,
) -> dict:
    """Predicted wait times for every operating hour on a given date."""
    a = attraction_by_id(attraction_id)
    if not a:
        raise HTTPException(status_code=404, detail=f"Attraction '{attraction_id}' not found")
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="target_date must be YYYY-MM-DD")

    # Park hours: 8 AM (early entry) to 10 PM on busy days
    open_h = 8 if early_entry else 9
    close_h = 22

    hours = []
    for h in range(open_h, close_h):
        when = datetime.combine(d, datetime.min.time()).replace(hour=h)
        p = predictor.predict(a, when, early_entry=early_entry)
        hours.append({
            "hour": h,
            "wait_minutes": p.wait_minutes,
            "crowd_multiplier": p.crowd_multiplier,
        })
    return {"attraction_id": a.id, "date": d.isoformat(), "hours": hours}
