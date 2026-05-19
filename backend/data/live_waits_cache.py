"""In-memory + persistent cache for today's live wait observations.

Data flows:
  - `/api/live/poll` fetches queue-times.com and calls `record_snapshot()` to add
    one observation per ride to the cache.
  - Predictors call `calibration_factor()` to get a per-ride (or park-wide)
    multiplier derived from the last 2 hours of observations.

Persistence:
  Each park gets a daily CSV at `data/live_waits/{park}/{YYYY-MM-DD}.csv`
  with columns: timestamp_iso, attraction_id, wait_minutes, is_open.
  Survives backend restarts.
"""
from __future__ import annotations

import csv
import logging
import threading
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional


log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_DIR = ROOT / "data" / "live_waits"
LIVE_DIR.mkdir(parents=True, exist_ok=True)


class LiveWaitsCache:
    """Thread-safe in-memory store for today's per-ride live observations."""

    def __init__(self) -> None:
        # park → list of (timestamp, attraction_id, wait_minutes, is_open)
        self._data: dict[str, list[tuple[datetime, str, int, bool]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._loaded_dates: dict[str, str] = {}  # park → date_str last loaded

    def _csv_path(self, park: str, d: date) -> Path:
        park_dir = LIVE_DIR / park
        park_dir.mkdir(parents=True, exist_ok=True)
        return park_dir / f"{d.isoformat()}.csv"

    def _ensure_loaded(self, park: str) -> None:
        today_str = date.today().isoformat()
        if self._loaded_dates.get(park) == today_str:
            return
        # New day: reset in-memory cache for that park and load today's CSV (if any).
        self._data[park] = []
        path = self._csv_path(park, date.today())
        if path.exists():
            try:
                with path.open() as f:
                    for row in csv.DictReader(f):
                        ts = datetime.fromisoformat(row["timestamp"])
                        self._data[park].append((
                            ts,
                            row["attraction_id"],
                            int(row["wait_minutes"]),
                            row.get("is_open", "true").lower() == "true",
                        ))
            except Exception as e:
                log.warning("Failed to load live cache %s: %s", path, e)
        self._loaded_dates[park] = today_str

    def record_snapshot(self, park: str, observations: list[tuple[str, int, bool]]) -> int:
        """Record a batch of (attraction_id, wait_minutes, is_open) observations.

        Returns the count of observations recorded.
        """
        if not observations:
            return 0
        now = datetime.now()
        path = self._csv_path(park, now.date())
        with self._lock:
            self._ensure_loaded(park)
            new_file = not path.exists() or path.stat().st_size == 0
            with path.open("a", newline="") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(["timestamp", "attraction_id", "wait_minutes", "is_open"])
                for aid, wait, is_open in observations:
                    self._data[park].append((now, aid, int(wait), bool(is_open)))
                    w.writerow([now.isoformat(timespec="seconds"), aid, int(wait), bool(is_open)])
        return len(observations)

    def recent(self, park: str, attraction_id: str, hours: float = 2.0) -> list[tuple[datetime, int]]:
        """Return (timestamp, wait) tuples for `attraction_id` within last `hours`."""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            self._ensure_loaded(park)
            return [
                (ts, wait)
                for ts, aid, wait, is_open in self._data[park]
                if aid == attraction_id and is_open and ts >= cutoff
            ]

    def latest(self, park: str) -> dict[str, int]:
        """Return the most recent observation per attraction (today, open rides only)."""
        with self._lock:
            self._ensure_loaded(park)
            out: dict[str, tuple[datetime, int]] = {}
            for ts, aid, wait, is_open in self._data[park]:
                if not is_open:
                    continue
                if aid not in out or ts > out[aid][0]:
                    out[aid] = (ts, wait)
        return {aid: w for aid, (_, w) in out.items()}

    def has_recent_data(self, park: str, min_minutes: int = 60) -> bool:
        """Whether we have at least `min_minutes` minutes of accumulated data today."""
        with self._lock:
            self._ensure_loaded(park)
            timestamps = [ts for ts, _, _, _ in self._data[park]]
            if len(timestamps) < 2:
                return False
            span = (max(timestamps) - min(timestamps)).total_seconds() / 60
            return span >= min_minutes

    def _collect_hour_waits(
        self, park: str, attraction_id: str, days: int
    ) -> dict[int, list[tuple[date, int]]]:
        """Collect all open, positive wait observations per hour across the past `days` days.

        Returns {hour: [(obs_date, wait_minutes), ...]} so callers can apply
        day-of-week or recency weighting.
        """
        from collections import defaultdict
        today = date.today()
        hour_waits: dict[int, list[tuple[date, int]]] = defaultdict(list)

        for offset in range(days):
            d = today - timedelta(days=offset)
            if offset == 0:
                with self._lock:
                    self._ensure_loaded(park)
                    for ts, aid, wait, is_open in self._data[park]:
                        if aid == attraction_id and is_open and wait > 0:
                            hour_waits[ts.hour].append((d, wait))
            else:
                path = self._csv_path(park, d)
                if not path.exists():
                    continue
                try:
                    with path.open() as f:
                        for row in csv.DictReader(f):
                            if row.get("attraction_id") != attraction_id:
                                continue
                            if row.get("is_open", "true").lower() != "true":
                                continue
                            try:
                                w = int(row["wait_minutes"])
                                h = datetime.fromisoformat(row["timestamp"]).hour
                                if w > 0:
                                    hour_waits[h].append((d, w))
                            except (ValueError, KeyError):
                                pass
                except Exception as e:
                    log.debug("Could not read %s: %s", path, e)

        return dict(hour_waits)

    def worst_n_avg_by_hour(
        self,
        park: str,
        attraction_id: str,
        days: int = 14,
        n: int = 3,
        target_date: Optional[date] = None,
    ) -> dict[int, int]:
        """Return {hour: avg_of_worst_n_waits} across the past `days` daily CSVs.

        When `target_date` is given, observations are weighted by relevance:
          - Same weekday as target_date → 3× weight
          - Within last 7 days            → 2× weight  (stacks with weekday)
          - Both                          → 4× weight
          - Neither                       → 1× weight

        Weighting is achieved by repeating observations in the pool before
        taking the worst-N, so high-relevance days dominate the average.
        Hours with fewer than `n` observations in the weighted pool are omitted.
        """
        hour_waits = self._collect_hour_waits(park, attraction_id, days)
        today = date.today()
        target_weekday = target_date.weekday() if target_date is not None else None
        result: dict[int, int] = {}

        for h, entries in hour_waits.items():
            # Build weighted pool
            pool: list[int] = []
            for obs_date, wait in entries:
                same_dow = target_weekday is not None and obs_date.weekday() == target_weekday
                recent = (today - obs_date).days <= 7
                weight = 1 + (2 if same_dow else 0) + (1 if recent else 0)
                pool.extend([wait] * weight)

            if len(pool) < n:
                continue
            worst = sorted(pool, reverse=True)[:n]
            result[h] = int(round(sum(worst) / len(worst)))
        return result


# Module-level singleton.
live_cache = LiveWaitsCache()
