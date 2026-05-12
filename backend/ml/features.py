"""Feature engineering for the wait time model."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from backend.data.attractions_db import Attraction, attraction_by_id
from backend.ml.crowd_factors import (
    DOW_MULTIPLIER,
    MONTH_MULTIPLIER,
    forecast_for,
    holiday_factor,
    hourly_factor,
    novelty_factor,
)


FEATURE_NAMES: list[str] = [
    "hour",
    "minute_bucket",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "holiday_mult",
    "crowd_base_mult",
    "hour_mult",
    "novelty_mult",
    "ride_tier",
    "capacity_per_hour",
    "is_first_hour_open",
    "is_last_hour_open",
    "has_express",
    "has_single_rider",
    "early_entry",
]


def build_feature_row(
    a: Attraction,
    when: datetime,
    early_entry: bool = False,
) -> dict:
    d = when.date()
    f = forecast_for(d)
    hol_mult, hol_label = holiday_factor(d)

    open_hour = 8 if early_entry else 9
    close_hour = 22

    return {
        "hour": when.hour,
        "minute_bucket": (when.minute // 15) * 15,
        "day_of_week": d.weekday(),
        "month": d.month,
        "is_weekend": int(d.weekday() >= 5),
        "is_holiday": int(hol_label is not None),
        "holiday_mult": hol_mult,
        "crowd_base_mult": f.base_multiplier,
        "hour_mult": hourly_factor(when.hour),
        "novelty_mult": novelty_factor(d),
        "ride_tier": a.tier,
        "capacity_per_hour": a.capacity_per_hour or 0,
        "is_first_hour_open": int(when.hour == open_hour),
        "is_last_hour_open": int(when.hour == close_hour - 1),
        "has_express": int(a.has_express),
        "has_single_rider": int(a.has_single_rider),
        "early_entry": int(early_entry),
    }
