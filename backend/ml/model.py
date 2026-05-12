"""
Wait time predictor.

Loads a two-stage trained model bundle from ml/saved_model.pkl:
  - `park_model` predicts park-wide rolling-avg wait given calendar features
    (trained on 10 years of WDW + UOR park-level history).
  - `ride_model` predicts per-ride wait given the same calendar features +
    ride attributes + `park_avg_pred` from `park_model` (trained on Epic
    Universe per-ride history).

At inference time we chain them: first predict park_avg from `park_model`,
then feed that as a feature to `ride_model`.

If neither model is available, falls back to a deterministic rule-based
predictor built from crowd_factors and per-tier baselines so the API is
still usable before training has been done.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.data.attractions_db import Attraction
from backend.ml import features
from backend.ml.crowd_factors import crowd_multiplier_at, hourly_factor

log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "saved_model.pkl"


# Baseline standby wait representing "average minute of an average day"
# (used only by the heuristic fallback when no trained model is loaded).
BASELINE_WAIT_BY_TIER = {
    1: 5,
    2: 12,
    3: 22,
    4: 38,
    5: 55,
}


def _capacity_factor(capacity: Optional[int]) -> float:
    if not capacity:
        return 1.0
    return min(1.6, max(0.6, 1200.0 / capacity))


@dataclass
class Prediction:
    wait_minutes: int
    crowd_multiplier: float
    confidence: str  # "model" | "heuristic"
    park_avg_pred: Optional[float] = None


class WaitTimePredictor:
    def __init__(self) -> None:
        self._park_model = None
        self._ride_model = None
        self._park_features: list[str] = []
        self._ride_features: list[str] = []

        if MODEL_PATH.exists():
            try:
                import joblib  # noqa
                bundle = joblib.load(MODEL_PATH)
                # New 2-stage bundle
                if "ride_model" in bundle:
                    self._park_model = bundle.get("park_model")
                    self._ride_model = bundle["ride_model"]
                    self._park_features = bundle.get("park_feature_names", [])
                    self._ride_features = bundle.get("ride_feature_names", [])
                    log.info("Loaded 2-stage wait-time model from %s "
                             "(park_model=%s, ride_model=%s)",
                             MODEL_PATH,
                             "yes" if self._park_model else "no",
                             "yes" if self._ride_model else "no")
                # Legacy single-model bundle
                elif "model" in bundle:
                    self._ride_model = bundle["model"]
                    self._ride_features = bundle.get("feature_names", [])
                    log.info("Loaded legacy single-stage wait-time model from %s", MODEL_PATH)
            except Exception as e:
                log.warning("Failed to load %s, falling back to heuristic: %s", MODEL_PATH, e)
                self._park_model = self._ride_model = None

    @property
    def has_model(self) -> bool:
        return self._ride_model is not None

    def _predict_park_avg(self, when: datetime) -> Optional[float]:
        if self._park_model is None or not self._park_features:
            return None
        try:
            import pandas as pd
            row = features.build_park_feature_row(when)
            df = pd.DataFrame([row])[self._park_features]
            return float(self._park_model.predict(df)[0])
        except Exception as e:
            log.warning("park_model prediction failed (%s)", e)
            return None

    def predict(self, a: Attraction, when: datetime, early_entry: bool = False) -> Prediction:
        crowd = crowd_multiplier_at(when)
        park_avg = self._predict_park_avg(when)

        if self._ride_model is not None:
            try:
                import pandas as pd
                row = features.build_ride_feature_row(
                    a, when, early_entry=early_entry, park_avg_pred=park_avg or 0.0,
                )
                df = pd.DataFrame([row])[self._ride_features]
                wait = float(self._ride_model.predict(df)[0])
                wait = max(0, int(round(wait)))
                return Prediction(
                    wait_minutes=wait,
                    crowd_multiplier=crowd,
                    confidence="model",
                    park_avg_pred=park_avg,
                )
            except Exception as e:
                log.warning("ride_model prediction failed (%s), using heuristic", e)

        # Heuristic fallback ─────────────────────────────────────────────
        if a.kind == "show":
            return Prediction(wait_minutes=20, crowd_multiplier=crowd, confidence="heuristic")
        if a.kind == "restaurant":
            return Prediction(wait_minutes=15, crowd_multiplier=crowd, confidence="heuristic")
        if a.kind == "experience":
            return Prediction(
                wait_minutes=int(round(10 * crowd)),
                crowd_multiplier=crowd,
                confidence="heuristic",
            )

        baseline = BASELINE_WAIT_BY_TIER.get(a.tier, 30)
        cap_factor = _capacity_factor(a.capacity_per_hour)
        first_hour_open = 9
        first_hour_bonus = 0.55 if when.hour == first_hour_open else 1.0
        if early_entry and when.hour < first_hour_open:
            first_hour_bonus = 0.40

        wait = baseline * crowd * cap_factor * first_hour_bonus
        return Prediction(wait_minutes=int(round(wait)), crowd_multiplier=crowd, confidence="heuristic")


# Singleton instance for routers to import.
predictor = WaitTimePredictor()
