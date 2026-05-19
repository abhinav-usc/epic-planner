"""Historical wait-time explorer endpoints — Epic Universe + Disney/Disneyland."""
from __future__ import annotations

import csv
import re
import statistics
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.data.disneyland_db import DL_ATTRACTIONS, DL_LANDS

router = APIRouter(prefix="/api/history", tags=["history"])

# ── Data paths ─────────────────────────────────────────────────────────────────
CSV_PATH      = Path(__file__).parents[2] / "data" / "historical_waits.csv"
DISNEY_AGG    = Path(__file__).parents[2] / "data" / "disney_historical_agg.csv"

# ── Epic Universe slug → land mapping ──────────────────────────────────────────
EPIC_SLUG_TO_LAND = {
    "stardustracers":                              "celestial_park",
    "constellationcarousel":                       "celestial_park",
    "mariokartbowserschallenge":                   "super_nintendo_world",
    "minecartmadness":                             "super_nintendo_world",
    "yoshisadventure":                             "super_nintendo_world",
    "bowserjrchallenge":                           "super_nintendo_world",
    "harrypotterandthebattleattheministry":        "ministry_of_magic",
    "hiccupswinggliders":                          "isle_of_berk",
    "dragonracersrally":                           "isle_of_berk",
    "fyredrill":                                   "isle_of_berk",
    "meettoothlessandfriends":                     "isle_of_berk",
    "meettoothlesshiccup":                         "isle_of_berk",
    "monstersunchainedthefrankensteinexperiment":  "dark_universe",
    "curseofthewerewolf":                          "dark_universe",
}

# ── Land colours (all parks) ───────────────────────────────────────────────────
ALL_LAND_COLORS: dict[str, str] = {
    "celestial_park":       "#4F46E5",
    "super_nintendo_world": "#DC2626",
    "ministry_of_magic":    "#7C3AED",
    "isle_of_berk":         "#059669",
    "dark_universe":        "#9333EA",
    **{lid: info["color"] for lid, info in DL_LANDS.items()},
}

# ── Disneyland slug lookups (built from the attraction DB) ─────────────────────
DL_SLUG_TO_LAND = {re.sub(r"[^a-z0-9]", "", a.name.lower()): a.land for a in DL_ATTRACTIONS}
DL_SLUG_TO_NAME = {re.sub(r"[^a-z0-9]", "", a.name.lower()): a.name for a in DL_ATTRACTIONS}

# Fallback slug aliases for name mismatches between scrape and our DB
_SLUG_ALIASES: dict[str, str] = {
    "bowserjrshadowshowdown": "bowserjrchallenge",
    "hyperspacemountain":     "spacemountain",
}


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# ── CSV loaders ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_epic_csv() -> dict:
    """{ date_str: { slug: { "name": str, "hours": {hour: wait} } } }"""
    raw: dict = defaultdict(lambda: defaultdict(lambda: {"name": "", "hours": {}}))
    if not CSV_PATH.exists():
        return {}
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            slug = _SLUG_ALIASES.get(row["attraction_slug"], row["attraction_slug"])
            raw[row["date"]][slug]["name"] = row["attraction_name"]
            raw[row["date"]][slug]["hours"][int(row["hour"])] = int(float(row["wait_minutes"]))
    return dict(raw)


@lru_cache(maxsize=1)
def _load_disney_csv() -> dict:
    """{ park_id: { date_str: { slug: { hour: avg_wait } } } }"""
    raw: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    if not DISNEY_AGG.exists():
        return {}
    with open(DISNEY_AGG, newline="") as f:
        for row in csv.DictReader(f):
            raw[row["park_id"]][row["date"]][row["attraction_slug"]][int(row["hour"])] = float(row["avg_wait"])
    return raw


# ── Pydantic models ────────────────────────────────────────────────────────────

class FeasibilityItem(BaseModel):
    name: str
    land: str
    start_minute: int
    wait_minutes: int
    ride_minutes: int
    duration_minute: int
    kind: str = "ride"


class FeasibilityRequest(BaseModel):
    items: list[FeasibilityItem]
    park_open_hour: int = 9
    arrival_minute: int = 0
    park_id: str = "epic_universe"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/dates")
def list_dates(park: str = Query("epic_universe")) -> list[dict]:
    """All dates with recorded data, with avg/peak wait summary."""
    if park == "epic_universe":
        db = _load_epic_csv()
        out = []
        for date in sorted(db.keys()):
            day = db[date]
            all_waits = [w for s in day for w in day[s]["hours"].values()]
            out.append({
                "date": date,
                "attraction_count": len(day),
                "avg_wait": round(statistics.mean(all_waits)) if all_waits else 0,
                "peak_wait": max(all_waits) if all_waits else 0,
            })
        return out
    else:
        disney = _load_disney_csv()
        park_data = disney.get(park, {})
        out = []
        for date in sorted(park_data.keys()):
            day = park_data[date]
            all_waits = [w for slug_hrs in day.values() for w in slug_hrs.values()]
            out.append({
                "date": date,
                "attraction_count": len(day),
                "avg_wait": round(sum(all_waits) / len(all_waits)) if all_waits else 0,
                "peak_wait": round(max(all_waits)) if all_waits else 0,
            })
        return out


@router.get("/day/{date}")
def day_detail(date: str, park: str = Query("epic_universe")) -> dict:
    """Full per-hour wait heatmap for all tracked attractions on a given date."""
    if park == "epic_universe":
        db = _load_epic_csv()
        if date not in db:
            raise HTTPException(status_code=404, detail=f"No data for {date}")
        day = db[date]
        attractions = []
        for slug, info in sorted(day.items()):
            hours_raw = info["hours"]
            hours = [{"hour": h, "wait_minutes": hours_raw.get(h)} for h in range(8, 22)]
            all_waits = [v for v in hours_raw.values() if v is not None]
            land = EPIC_SLUG_TO_LAND.get(slug, "celestial_park")
            attractions.append({
                "slug": slug,
                "name": info["name"],
                "land": land,
                "color": ALL_LAND_COLORS.get(land, "#888"),
                "hours": hours,
                "avg_wait": round(statistics.mean(all_waits)) if all_waits else 0,
                "peak_wait": max(all_waits) if all_waits else 0,
            })
        return {"date": date, "attractions": attractions}
    else:
        disney = _load_disney_csv()
        park_data = disney.get(park, {})
        if date not in park_data:
            raise HTTPException(status_code=404, detail=f"No data for {date} in {park}")
        day = park_data[date]
        attractions = []
        for slug, hours_raw in sorted(day.items()):
            land = DL_SLUG_TO_LAND.get(slug, "dl_main_street")
            name = DL_SLUG_TO_NAME.get(slug, slug.replace("_", " ").title())
            hours = [{"hour": h, "wait_minutes": round(hours_raw[h]) if h in hours_raw else None}
                     for h in range(8, 22)]
            all_waits = list(hours_raw.values())
            attractions.append({
                "slug": slug,
                "name": name,
                "land": land,
                "color": ALL_LAND_COLORS.get(land, "#888"),
                "hours": hours,
                "avg_wait": round(sum(all_waits) / len(all_waits)) if all_waits else 0,
                "peak_wait": round(max(all_waits)) if all_waits else 0,
            })
        return {"date": date, "attractions": attractions}


@router.post("/feasibility")
def check_feasibility(req: FeasibilityRequest) -> dict:
    """
    Sequential-simulation feasibility check using actual historical waits.
    Cascading: a long queue at ride 3 pushes rides 4, 5, … later.
    A day passes if the sequence finishes within the planned window + 30 min slack.
    """
    if req.park_id == "epic_universe":
        db = _load_epic_csv()
        def _get_wait(slug: str, date: str, hour: int) -> Optional[int]:
            day = db.get(date, {})
            hm = day.get(slug, {}).get("hours", {})
            return hm.get(hour) or hm.get(hour + 1) or hm.get(hour - 1)
    else:
        disney = _load_disney_csv()
        park_data = disney.get(req.park_id, {})
        def _get_wait(slug: str, date: str, hour: int) -> Optional[int]:
            hm = park_data.get(date, {}).get(slug, {})
            v = hm.get(hour) or hm.get(hour + 1) or hm.get(hour - 1)
            return round(v) if v is not None else None

    all_dates = (sorted(_load_epic_csv().keys()) if req.park_id == "epic_universe"
                 else sorted(park_data.keys()))

    if not req.items:
        return {"days_checked": 0, "days_passed": 0, "pass_rate": None, "error": "No items in plan."}

    items = sorted(req.items, key=lambda x: x.start_minute)
    first_start = min(i.start_minute for i in items)
    planned_end = max(i.start_minute + i.duration_minute for i in items)
    SLACK = 30
    WALK_SAME = 2
    WALK_DIFF = 7

    date_results = []
    ride_actual_waits: dict[str, list[int]] = {}

    for date in all_dates:
        current = max(req.arrival_minute, first_start)
        prev_land: Optional[str] = None

        for item in items:
            if item.kind in ("break_food", "break_shop", "show"):
                current = max(current, item.start_minute)
                current += item.duration_minute
                prev_land = item.land if item.land != "break" else prev_land
                continue

            if prev_land is not None:
                current += WALK_SAME if prev_land == item.land else WALK_DIFF
            prev_land = item.land

            slug = _SLUG_ALIASES.get(_slugify(item.name), _slugify(item.name))
            hour = min(21, max(8, req.park_open_hour + current // 60))
            actual_wait = _get_wait(slug, date, hour)
            if actual_wait is None:
                actual_wait = item.wait_minutes

            ride_actual_waits.setdefault(item.name, []).append(actual_wait)
            current += actual_wait + item.ride_minutes

        overrun = max(0, current - planned_end)
        date_results.append({
            "date": date,
            "passed": current <= planned_end + SLACK,
            "total_minutes": current,
            "overrun": overrun,
        })

    days_checked = len(date_results)
    days_passed = sum(1 for r in date_results if r["passed"])
    pass_rate = round(days_passed / days_checked, 3) if days_checked else None

    ride_stats = []
    for item in items:
        if item.kind in ("break_food", "break_shop", "show"):
            continue
        waits = ride_actual_waits.get(item.name, [])
        ride_stats.append({
            "name": item.name,
            "planned_wait": item.wait_minutes,
            "avg_actual_wait": round(sum(waits) / len(waits)) if waits else item.wait_minutes,
            "days_with_data": len(waits),
        })

    all_mins = [r["total_minutes"] for r in date_results]
    overruns = [r["overrun"] for r in date_results]
    sample_failures = sorted(
        [r for r in date_results if not r["passed"]], key=lambda r: -r["overrun"]
    )[:10]

    return {
        "days_checked": days_checked,
        "days_passed": days_passed,
        "pass_rate": pass_rate,
        "planned_end_minutes": planned_end,
        "avg_actual_end_minutes": round(sum(all_mins) / len(all_mins)) if all_mins else planned_end,
        "avg_overrun_minutes": round(sum(overruns) / len(overruns)) if overruns else 0,
        "slack_minutes": SLACK,
        "ride_stats": ride_stats,
        "sample_failures": sample_failures,
        "all_results": date_results,
        "error": None,
    }
