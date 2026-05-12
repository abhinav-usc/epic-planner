"""
Historic worst-case wait lookup.

For each (attraction, hour, holiday-bucket) we precompute the 90th
percentile of observed waits from data/historical_waits.csv. That's our
"worst case you might realistically encounter" number — filters out the
99th-percentile fluke spikes but covers the long-tail bad days.

The bucket is:
  - hour (8-22)
  - is_holiday (True/False, per crowd_factors)
  - is_weekend (True/False)

If a particular bucket has < 5 samples we fall back to a broader one.
"""
from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from backend.ml.crowd_factors import holiday_factor


log = logging.getLogger(__name__)
HISTORICAL_CSV = Path(__file__).resolve().parent.parent.parent / "data" / "historical_waits.csv"

# Map thrill-data slugs → our local attraction IDs. Same mapping as the trainer.
TD_SLUG_TO_LOCAL = {
    "stardustracers": "stardust_racers",
    "constellationcarousel": "constellation_carousel",
    "astronomica": "astronomica",
    "mariokartbowserschallenge": "mario_kart",
    "minecartmadness": "mine_cart_madness",
    "yoshisadventure": "yoshis_adventure",
    "bowserjrchallenge": "bowser_jr_showdown",
    "meetmarioandluigi": "meet_mario_luigi",
    "meetprincesspeach": "meet_princess_peach",
    "meetdonkeykong": "meet_donkey_kong",
    "harrypotterandthebattleattheministry": "battle_at_ministry",
    "lecirquearcanus": "le_cirque_arcanus",
    "hiccupswinggliders": "hiccups_wing_gliders",
    "dragonracersrally": "dragon_racers_rally",
    "fyredrill": "fyre_drill",
    "theuntrainabledragon": "untrainable_dragon",
    "vikingtrainingcamp": "viking_training_camp",
    "meettoothlessandfriends": "meet_toothless",
    "meettoothlesshiccup": "meet_toothless_hiccup",
    "monstersunchainedthefrankensteinexperiment": "monsters_unchained",
    "curseofthewerewolf": "curse_of_werewolf",
    "darkuniversecharactermeetgreet": "dark_universe_meet",
}


def _percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    s = sorted(values)
    k = int(round((p / 100.0) * (len(s) - 1)))
    return s[max(0, min(len(s) - 1, k))]


class WorstCaseLookup:
    """Pre-computes 90th-percentile waits keyed by (attraction_id, hour, is_holiday, is_weekend)."""

    def __init__(self) -> None:
        # Bucketed samples: dict[(local_id, hour, is_holiday, is_weekend)] -> list[int]
        self._buckets: dict[tuple, list[int]] = {}
        # By-attraction-by-hour fallback: dict[(local_id, hour)] -> list[int]
        self._by_attr_hour: dict[tuple, list[int]] = {}
        self._loaded = False
        self._n_rows = 0

    def load(self) -> None:
        if self._loaded:
            return
        if not HISTORICAL_CSV.exists() or HISTORICAL_CSV.stat().st_size == 0:
            log.warning("WorstCaseLookup: no %s yet", HISTORICAL_CSV)
            self._loaded = True
            return
        with HISTORICAL_CSV.open() as f:
            for r in csv.DictReader(f):
                local_id = TD_SLUG_TO_LOCAL.get(r["attraction_slug"])
                if not local_id:
                    continue
                try:
                    d = date.fromisoformat(r["date"])
                    h = int(r["hour"])
                    w = int(r["wait_minutes"])
                except Exception:
                    continue
                hol_mult, hol_label = holiday_factor(d)
                is_hol = int(hol_label is not None)
                is_we = int(d.weekday() >= 5)
                self._buckets.setdefault((local_id, h, is_hol, is_we), []).append(w)
                self._by_attr_hour.setdefault((local_id, h), []).append(w)
                self._n_rows += 1
        self._loaded = True
        log.info("WorstCaseLookup: loaded %d rows, %d buckets", self._n_rows, len(self._buckets))

    def worst_case(self, attraction_id: str, when_date: date, hour: int, p: float = 90.0) -> Optional[dict]:
        """Return {'wait_minutes': N, 'sample_size': n, 'bucket': '...'} or None if no data."""
        self.load()
        _, hol_label = holiday_factor(when_date)
        is_hol = int(hol_label is not None)
        is_we = int(when_date.weekday() >= 5)

        # Try most-specific bucket first, fall back to broader ones if too small.
        bucket_chain = [
            ((attraction_id, hour, is_hol, is_we), f"holiday={bool(is_hol)},weekend={bool(is_we)}"),
            ((attraction_id, hour, is_hol, 1 - is_we), "weekend-mismatch"),
            (None, "attraction+hour only"),
        ]
        for key, label in bucket_chain:
            if key is None:
                samples = self._by_attr_hour.get((attraction_id, hour), [])
            else:
                samples = self._buckets.get(key, [])
            if len(samples) >= 5:
                return {
                    "wait_minutes": _percentile(samples, p),
                    "sample_size": len(samples),
                    "bucket": label,
                }
        # Final fallback: any data at all for this attraction
        if (attraction_id, hour) in self._by_attr_hour:
            samples = self._by_attr_hour[(attraction_id, hour)]
            return {
                "wait_minutes": _percentile(samples, p),
                "sample_size": len(samples),
                "bucket": "fallback (any)",
            }
        return None


lookup = WorstCaseLookup()
