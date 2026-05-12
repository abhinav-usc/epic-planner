"""
Wait time predictor.

Tries to load a trained scikit-learn model from ml/saved_model.pkl. If absent,
falls back to a deterministic rule-based predictor built from crowd_factors
and per-attraction baseline waits. This keeps the API usable even before the
model has been trained (which requires a one-time `python scripts/train_model.py`).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.data.attractions_db import Attraction
from backend.ml import features
from backend.ml.crowd_factors import crowd_multiplier_at, hourly_factor, forecast_for


log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "saved_model.pkl"


# Baseline standby wait representing "average minute of an average day"
# (mean over all operating hours on a typical weekday with no holiday).
# Calibrated against observed Epic Universe medians (queue-times averages,
# May 2025 – May 2026) for representative rides in each tier.
BASELINE_WAIT_BY_TIER = {
    1: 5,
    2: 12,
    3: 22,
    4: 38,
    5: 55,
}

# Capacity adjustment: rides with higher throughput run shorter lines.
# Reference capacity = 1200 riders/hr.
def _capacity_factor(capacity: Optional[int]) -> float:
    if not capacity:
        return 1.0
    return min(1.6, max(0.6, 1200.0 / capacity))


@dataclass
class Prediction:
    wait_minutes: int
    crowd_multiplier: float
    confidence: str  # "model" | "heuristic"


class WaitTimePredictor:
    def __init__(self) -> None:
        self._model = None
        self._feature_names: list[str] = []
        if MODEL_PATH.exists():
            try:
                import joblib  # noqa
                bundle = joblib.load(MODEL_PATH)
                self._model = bundle["model"]
                self._feature_names = bundle.get("feature_names", [])
                log.info("Loaded trained wait-time model from %s", MODEL_PATH)
            except Exception as e:
                log.warning("Failed to load %s, falling back to heuristic: %s", MODEL_PATH, e)
                self._model = None

    @property
    def has_model(self) -> bool:
        return self._model is not None

    def predict(self, a: Attraction, when: datetime, early_entry: bool = False) -> Prediction:
        crowd = crowd_multiplier_at(when)

        if self._model is not None:
            try:
                import pandas as pd
                row = features.build_feature_row(a, when, early_entry=early_entry)
                df = pd.DataFrame([row])[self._feature_names]
                wait = float(self._model.predict(df)[0])
                wait = max(0, int(round(wait)))
                return Prediction(wait_minutes=wait, crowd_multiplier=crowd, confidence="model")
            except Exception as e:
                log.warning("Model prediction failed (%s), using heuristic", e)

        # Heuristic fallback ─────────────────────────────────────────────
        if a.kind == "show":
            # Shows: queue forms ~20 min before showtime; otherwise N/A
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
