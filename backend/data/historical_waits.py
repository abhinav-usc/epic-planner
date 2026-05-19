"""
Lookup actual recorded wait times from historical CSVs.

Epic Universe:   historical_waits.csv        (slug, date, hour → wait)
Disney / DL:     disney_historical_agg.csv   (park_id, slug, date, hour → avg_wait)

Both return real recorded data for past dates instead of model predictions.
"""
from __future__ import annotations

import csv
import re
import logging
from pathlib import Path
from collections import defaultdict
from typing import Optional

log = logging.getLogger(__name__)

CSV_PATH     = Path(__file__).parents[2] / "data" / "historical_waits.csv"
DISNEY_CSV   = Path(__file__).parents[2] / "data" / "disney_historical_agg.csv"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


# Manual overrides for attractions whose names differ between our DB and the
# queue-times.com scrape that produced the CSV (e.g. park renames).
_SLUG_ALIASES: dict[str, str] = {
    "bowserjrshadowshowdown": "bowserjrchallenge",
}


class HistoricalWaitsDB:
    def __init__(self) -> None:
        # { date_str: { slug: { hour: wait_minutes } } }
        self._data: dict[str, dict[str, dict[int, int]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not CSV_PATH.exists():
            log.warning("historical_waits.csv not found at %s", CSV_PATH)
            return
        try:
            with open(CSV_PATH, newline="") as f:
                for row in csv.DictReader(f):
                    slug = row["attraction_slug"]
                    date_str = row["date"]
                    hour = int(row["hour"])
                    wait = int(float(row["wait_minutes"]))
                    self._data[date_str][slug][hour] = wait
            log.info("Loaded historical waits: %d dates", len(self._data))
        except Exception as e:
            log.warning("Failed to load historical_waits.csv: %s", e)

    def has_date(self, date_str: str) -> bool:
        self._ensure_loaded()
        return date_str in self._data

    def _resolve_slug(self, attraction_name: str) -> str:
        slug = _slugify(attraction_name)
        return _SLUG_ALIASES.get(slug, slug)

    def get_wait(self, date_str: str, attraction_name: str, hour: int) -> Optional[int]:
        """Return actual wait for (date, attraction, hour), or None if not available."""
        self._ensure_loaded()
        slug = self._resolve_slug(attraction_name)
        day = self._data.get(date_str, {})
        return day.get(slug, {}).get(hour)

    def get_day_hours(
        self,
        date_str: str,
        attraction_name: str,
        open_h: int,
        close_h: int,
    ) -> Optional[list[dict]]:
        """
        Return a list of hourly dicts for the full operating day, or None if
        no data at all exists for this attraction on this date.
        """
        self._ensure_loaded()
        slug = self._resolve_slug(attraction_name)
        day = self._data.get(date_str, {})
        by_hour = day.get(slug, {})
        if not by_hour:
            return None

        result = []
        for h in range(open_h, close_h):
            wait = by_hour.get(h)
            if wait is None:
                # Fill gaps with linear interpolation between neighbors.
                prev_h = max((k for k in by_hour if k < h), default=None)
                next_h = min((k for k in by_hour if k > h), default=None)
                if prev_h is not None and next_h is not None:
                    frac = (h - prev_h) / (next_h - prev_h)
                    wait = int(round(by_hour[prev_h] + frac * (by_hour[next_h] - by_hour[prev_h])))
                elif prev_h is not None:
                    wait = by_hour[prev_h]
                elif next_h is not None:
                    wait = by_hour[next_h]
                else:
                    wait = 0
            result.append({"hour": h, "wait_minutes": wait})
        return result


# Singleton
historical_db = HistoricalWaitsDB()


class DisneyHistoricalDB:
    """Actual recorded waits for Disney/Disneyland parks from disney_historical_agg.csv."""

    def __init__(self) -> None:
        # { park_id: { date_str: { slug: { hour: avg_wait } } } }
        self._data: dict[str, dict[str, dict[str, dict[int, float]]]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not DISNEY_CSV.exists():
            log.warning("disney_historical_agg.csv not found at %s", DISNEY_CSV)
            return
        try:
            data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
            with open(DISNEY_CSV, newline="") as f:
                for row in csv.DictReader(f):
                    data[row["park_id"]][row["date"]][row["attraction_slug"]][int(row["hour"])] = float(row["avg_wait"])
            self._data = {p: dict(dates) for p, dates in data.items()}
            total = sum(len(s) for p in self._data.values() for s in p.values())
            log.info("Loaded Disney historical agg: %d parks, %d slug×date entries",
                     len(self._data), total)
        except Exception as e:
            log.warning("Failed to load disney_historical_agg.csv: %s", e)

    def get_wait(self, park_id: str, date_str: str, slug: str, hour: int) -> Optional[int]:
        self._ensure_loaded()
        w = self._data.get(park_id, {}).get(date_str, {}).get(slug, {}).get(hour)
        return int(round(w)) if w is not None else None

    def get_day_hours(
        self, park_id: str, date_str: str, slug: str, open_h: int, close_h: int
    ) -> Optional[list[dict]]:
        self._ensure_loaded()
        by_hour = self._data.get(park_id, {}).get(date_str, {}).get(slug, {})
        if not by_hour:
            return None
        result = []
        for h in range(open_h, close_h):
            wait = by_hour.get(h)
            if wait is None:
                prev_h = max((k for k in by_hour if k < h), default=None)
                next_h = min((k for k in by_hour if k > h), default=None)
                if prev_h is not None and next_h is not None:
                    frac = (h - prev_h) / (next_h - prev_h)
                    wait = by_hour[prev_h] + frac * (by_hour[next_h] - by_hour[prev_h])
                elif prev_h is not None:
                    wait = by_hour[prev_h]
                elif next_h is not None:
                    wait = by_hour[next_h]
                else:
                    wait = 0
            result.append({"hour": h, "wait_minutes": int(round(wait))})
        return result

    def has_date(self, park_id: str, date_str: str) -> bool:
        self._ensure_loaded()
        return date_str in self._data.get(park_id, {})


disney_historical_db = DisneyHistoricalDB()
