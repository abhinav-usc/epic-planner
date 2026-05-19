"""
Crowd factor model for Epic Universe.

Multipliers are derived from publicly documented theme park crowd patterns
(undercovertourist.com, touringplans.com historical crowd calendars,
queue-times.com observed averages) and calibrated to queue-times.com observed
data for Epic Universe since May 22, 2025.

The model returns a multiplier vs the park's average day; downstream wait-time
predictions multiply baseline standby waits by this.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


# ─── Day-type multipliers ─────────────────────────────────────────────────────

# Day of week relative to park average (Mon–Sun 0–6).
# Calibrated from 361 days of actual Epic Universe wait data.
# Year-1 novelty keeps all days busier than a mature park; the weekday/weekend
# spread is narrower than Disney/Universal norms but still present.
DOW_MULTIPLIER = {
    0: 1.03,   # Mon
    1: 1.02,   # Tue
    2: 1.02,   # Wed
    3: 0.99,   # Thu
    4: 0.99,   # Fri
    5: 1.03,   # Sat
    6: 0.92,   # Sun (checkout day — guests leave, waits softer)
}

# Month seasonality (Jan-Dec → multiplier).
# Derived from actual per-month averages in the historical CSV, normalised so
# the geometric mean ≈ 1.0, then blended with expected mature-park seasonality.
# May 2025 includes the opening-week ramp-up so it reads low in data; for
# future May dates we expect normal summer-onset demand.
MONTH_MULTIPLIER = {
    1: 1.14,   # Jan — post-holiday peak (highest in data: 52.5 min avg)
    2: 1.16,   # Feb — school holiday + Valentine crowds
    3: 0.95,   # Mar — spring break starts mid-month
    4: 0.92,   # Apr — lighter after spring break
    5: 0.90,   # May — pre-summer; data low due to opening novelty ramp-up
    6: 1.10,   # Jun — summer onset
    7: 1.10,   # Jul — peak summer
    8: 1.00,   # Aug — summer winding down
    9: 1.00,   # Sep — shoulder season
    10: 1.10,  # Oct — Halloween events, Canadian Thanksgiving
    11: 0.97,  # Nov — quiet before Thanksgiving
    12: 0.98,  # Dec — builds toward Christmas; Christmas week handled by holiday window
}


# ─── Named holiday windows ────────────────────────────────────────────────────
# (year, start MM-DD, end MM-DD, multiplier, label)
# Anchored multipliers for Memorial Day Monday and surrounding window:
#  Documented Disney/Universal Memorial Day Monday: ~2.0–2.4x average
#  Epic Universe Year-2 novelty premium: +15–20%
#  → Memorial Day Monday at Epic Universe = ~2.3x

HOLIDAY_WINDOWS = [
    # Spring Break (varies; broad window mid-Mar to mid-Apr)
    {"start": "03-10", "end": "04-20", "mult": 1.60, "label": "Spring Break"},
    # Memorial Day weekend (Sat–Mon)
    {"start": "05-23", "end": "05-25", "mult": 2.20, "label": "Memorial Day Weekend"},
    # Independence Day window
    {"start": "07-01", "end": "07-07", "mult": 2.10, "label": "July 4th"},
    # Labor Day weekend
    {"start": "08-30", "end": "09-02", "mult": 1.80, "label": "Labor Day"},
    # Halloween (HHN nights but daytime busy)
    {"start": "10-20", "end": "10-31", "mult": 1.55, "label": "Halloween Season"},
    # Thanksgiving week
    {"start": "11-22", "end": "11-30", "mult": 2.00, "label": "Thanksgiving Week"},
    # Christmas / New Year
    {"start": "12-20", "end": "01-02", "mult": 2.60, "label": "Christmas / NYE"},
]


def _within(d: date, start_mmdd: str, end_mmdd: str) -> bool:
    """Inclusive window check; supports year-wrapping windows (e.g. 12-20 → 01-02)."""
    mm_s, dd_s = map(int, start_mmdd.split("-"))
    mm_e, dd_e = map(int, end_mmdd.split("-"))
    if (mm_s, dd_s) <= (mm_e, dd_e):
        return (d.month, d.day) >= (mm_s, dd_s) and (d.month, d.day) <= (mm_e, dd_e)
    # year wraps
    return (d.month, d.day) >= (mm_s, dd_s) or (d.month, d.day) <= (mm_e, dd_e)


def holiday_factor(d: date) -> tuple[float, Optional[str]]:
    """Return (multiplier, label) for any active holiday window, else (1.0, None)."""
    # Memorial Day Monday specifically: bump even higher
    if d.month == 5 and d.weekday() == 0 and 25 <= d.day <= 31:
        return 2.30, "Memorial Day Monday"
    for w in HOLIDAY_WINDOWS:
        if _within(d, w["start"], w["end"]):
            return w["mult"], w["label"]
    return 1.0, None


# ─── Epic Universe novelty curve ──────────────────────────────────────────────
# Park opened May 22, 2025. Wait times for new parks decay roughly:
#   Month 0–3:   ~1.40x (peak hype)
#   Month 4–12:  ~1.25x
#   Month 13–24: ~1.10x
#   Month 25+:   ~1.00x

EPIC_OPENING = date(2025, 5, 22)


def novelty_factor(d: date) -> float:
    months = (d.year - EPIC_OPENING.year) * 12 + (d.month - EPIC_OPENING.month)
    if months < 0:
        return 1.0
    if months < 4:
        return 1.40
    if months < 13:
        return 1.25
    if months < 25:
        return 1.10
    return 1.00


# ─── Hourly crowd shape ───────────────────────────────────────────────────────
# Relative crowding by hour-of-day (mean across operating hours ≈ 1.0).
# Pattern: rope-drop surge, midday lull, afternoon peak, evening fade.
# Calibrated so peak hour ≈ 1.35× daily average (matches observed queue-times
# day-shape ratios at Universal/Disney parks).

HOURLY_SHAPE = {
    7:  0.32,  # pre-open / early entry trickle
    8:  0.47,  # early entry (calibrated from data: 21.7 / 46.2)
    9:  0.78,  # rope-drop rush still building (data: 35.8 / 46.2)
    10: 1.14,  # crowds pour in (data: 52.7 / 46.2)
    11: 1.39,  # single busiest hour (data: 64.0 / 46.2)
    12: 1.33,  # lunch crowds stay high — interpolated 11/13
    13: 1.27,  # data: 58.8 / 46.2
    14: 1.23,  # data: 56.9 / 46.2
    15: 1.23,  # data: 56.8 / 46.2
    16: 1.19,  # data: 54.9 / 46.2
    17: 1.10,  # data: 50.8 / 46.2 (no strong 2nd peak in Epic data)
    18: 0.98,  # data: 45.3 / 46.2
    19: 0.87,  # data: 40.0 / 46.2
    20: 0.74,  # data: 34.2 / 46.2
    21: 0.57,  # data: 26.3 / 46.2
    22: 0.43,  # data: 20.0 / 46.2
    23: 0.42,  # closing stragglers
}


def hourly_factor(hour: int) -> float:
    return HOURLY_SHAPE.get(hour, 1.0)


# ─── Composite crowd level ────────────────────────────────────────────────────

@dataclass
class CrowdForecast:
    date: str
    crowd_level: float     # 1–10 scale for UI display
    base_multiplier: float
    holiday_label: Optional[str]
    novelty_multiplier: float
    dow_multiplier: float
    month_multiplier: float
    hourly_multipliers: dict[int, float]


def forecast_for(d: date) -> CrowdForecast:
    dow = DOW_MULTIPLIER[d.weekday()]
    mon = MONTH_MULTIPLIER[d.month]
    nov = novelty_factor(d)
    hol, label = holiday_factor(d)

    # Multiplicative composite: holiday already absorbs dow/month for peak days,
    # so we max() against the day-of-week base instead of pure product to avoid
    # over-counting on holidays.
    base_day = max(dow * mon, hol)
    base = base_day * nov

    # Map to 1–10 crowd-level scale: 1.0x → 5, 2.0x → 8, 3.0x → 10
    crowd_level = min(10.0, max(1.0, 3.5 + 2.2 * (base - 1.0)))

    return CrowdForecast(
        date=d.isoformat(),
        crowd_level=round(crowd_level, 1),
        base_multiplier=round(base, 3),
        holiday_label=label,
        novelty_multiplier=nov,
        dow_multiplier=dow,
        month_multiplier=mon,
        hourly_multipliers={h: round(base * hourly_factor(h), 3) for h in HOURLY_SHAPE},
    )


def crowd_multiplier_at(when: datetime) -> float:
    """Composite multiplier for a specific datetime: day-base × hour-shape."""
    f = forecast_for(when.date())
    return f.base_multiplier * hourly_factor(when.hour)
