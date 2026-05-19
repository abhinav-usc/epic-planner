"""Feature engineering for the wait time model.

Two feature sets:
- `PARK_FEATURE_NAMES` / `build_park_feature_row()`:
    Calendar + holiday features used to predict park-wide rolling-average
    wait. Trained on 10 years of Disney + Universal park data.

- `RIDE_FEATURE_NAMES` / `build_ride_feature_row()`:
    Park features + ride attributes + `park_avg_pred` (predicted by the
    park model) — used to predict per-ride wait. Trained on Epic Universe
    historical per-ride data.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from backend.data.attractions_db import Attraction
from backend.ml.crowd_factors import (
    forecast_for,
    holiday_factor,
    hourly_factor,
    novelty_factor,
)


# Park-level features: calendar / holiday only. No ride-specific or park-id
# features — we want this model to learn a single "average mature park" pattern.
PARK_FEATURE_NAMES: list[str] = [
    "hour",
    "minute_bucket",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "holiday_mult",
    "crowd_base_mult",
    "hour_mult",
    "crowd_x_hour",       # crowd_base_mult × hour_mult — captures multiplicative peak effect
    "log_crowd_base",     # log scale helps tree models split crowd levels more evenly
]


def build_park_feature_row(when: datetime) -> dict:
    """Calendar/holiday features for the park-level model."""
    d = when.date()
    f = forecast_for(d)
    hol_mult, hol_label = holiday_factor(d)
    import math
    h_mult = hourly_factor(when.hour)
    return {
        "hour": when.hour,
        "minute_bucket": (when.minute // 15) * 15,
        "day_of_week": d.weekday(),
        "month": d.month,
        "is_weekend": int(d.weekday() >= 5),
        "is_holiday": int(hol_label is not None),
        "holiday_mult": hol_mult,
        "crowd_base_mult": f.base_multiplier,
        "hour_mult": h_mult,
        "crowd_x_hour": f.base_multiplier * h_mult,
        "log_crowd_base": math.log(max(f.base_multiplier, 0.1)),
    }


# Per-ride features for FL parks (Epic Universe + WDW):
# Park features + ride attributes + park_avg_pred (borrowed strength from park_model).
# Used when the calling park is in Orlando and we want to leverage cross-park calendar averages.
RIDE_FEATURE_NAMES_FL: list[str] = PARK_FEATURE_NAMES + [
    "novelty_mult",
    "ride_tier",
    "capacity_per_hour",
    "is_first_hour_open",
    "is_last_hour_open",
    "has_express",
    "has_single_rider",
    "early_entry",
    "park_avg_pred",
    "crowd_x_tier",       # crowd_base_mult × ride_tier — high-tier rides amplify more on busy days
    "crowd_x_cap_inv",    # crowd_base_mult / log(capacity+1) — low capacity + high crowd = long waits
]

# Per-ride features for CA parks (Disneyland):
# Same as FL but WITHOUT park_avg_pred. Disneyland has ~10+ years of dense per-ride
# data so the ride model learns calendar/holiday effects directly from per-ride rows,
# without needing borrowed-strength from a regional park-average model.
RIDE_FEATURE_NAMES_CA: list[str] = [f for f in RIDE_FEATURE_NAMES_FL if f != "park_avg_pred"]

# Back-compat alias (old code imports RIDE_FEATURE_NAMES).
RIDE_FEATURE_NAMES = RIDE_FEATURE_NAMES_FL


def build_ride_feature_row(
    a: Attraction,
    when: datetime,
    early_entry: bool = False,
    park_avg_pred: float = 0.0,
) -> dict:
    import math
    row = build_park_feature_row(when)
    d = when.date()
    open_hour = 8 if early_entry else 9
    close_hour = 22
    crowd = row["crowd_base_mult"]
    cap = a.capacity_per_hour or 500
    row.update({
        "novelty_mult": novelty_factor(d),
        "ride_tier": a.tier,
        "capacity_per_hour": a.capacity_per_hour or 0,
        "is_first_hour_open": int(when.hour == open_hour),
        "is_last_hour_open": int(when.hour == close_hour - 1),
        "has_express": int(a.has_express),
        "has_single_rider": int(a.has_single_rider),
        "early_entry": int(early_entry),
        "park_avg_pred": float(park_avg_pred),
        "crowd_x_tier": crowd * a.tier,
        "crowd_x_cap_inv": crowd / math.log(cap + 1),
    })
    return row


# Back-compat alias for any code still importing the old name.
FEATURE_NAMES = RIDE_FEATURE_NAMES


def build_feature_row(a: Attraction, when: datetime, early_entry: bool = False) -> dict:
    """Legacy single-stage feature builder (no park_avg_pred). Kept for compatibility."""
    return build_ride_feature_row(a, when, early_entry=early_entry, park_avg_pred=0.0)
