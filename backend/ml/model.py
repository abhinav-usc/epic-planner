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

# Disney parks use the park_model output scaled by tier.
# These factors are calibrated to typical WDW peak-day wait levels.
# (park_avg ≈ 30 min on a normal WDW day; these scale relative to that.)
DISNEY_TIER_FACTOR = {
    1: 0.20,   # ~6 min
    2: 0.50,   # ~15 min
    3: 1.00,   # ~30 min (park average)
    4: 1.70,   # ~51 min
    5: 2.80,   # ~84 min
}

# Disneyland CA heuristic: baseline wait to multiply by crowd_multiplier_at().
# crowd_multiplier_at() = day_base × hourly_factor, where a typical busy Saturday
# at 11am ≈ 2.1x.  baseline × 2.1 should give realistic Saturday-peak waits.
# Only active while the CA ride model isn't loaded.
DISNEYLAND_BASELINE_BY_TIER = {
    1: 4,    # minor: Alice, Pinocchio, Dumbo   → Sat peak ~8 min
    2: 10,   # moderate: Small World, Buzz       → Sat peak ~21 min
    3: 22,   # popular: Space Mountain, Pirates  → Sat peak ~46 min
    4: 32,   # top: Peter Pan, Matterhorn        → Sat peak ~67 min
    5: 45,   # premier: Indiana Jones, Rise      → Sat peak ~95 min
}

# Parks that always use the tier-factor heuristic (no per-ride training data in any bundle version).
ALWAYS_HEURISTIC_PARK_IDS = {
    "magic_kingdom", "epcot", "hollywood_studios", "animal_kingdom",
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
    ll_return_minutes: Optional[int] = None  # estimated LL return window (None if no LL)


def _ll_return_minutes(ll_type: Optional[str], standby_wait: int) -> Optional[int]:
    """Estimate LL return window (minutes from booking) based on ll_type and standby demand.

    LLSP (single) = no return time, just purchase and walk into the LL queue immediately.
    LLMP (multi) = return window scales with demand (~45% of standby, min 15, max 180 min).
    """
    if ll_type == "single":
        return 0  # immediate entry after purchase
    if ll_type == "multi":
        return max(15, min(180, int(standby_wait * 0.45)))
    return None


class WaitTimePredictor:
    def __init__(self) -> None:
        self._park_model = None
        self._ride_model = None
        self._park_features: list[str] = []
        self._ride_features: list[str] = []
        self._ride_model_ca = None
        self._ride_features_ca: list[str] = []

        if MODEL_PATH.exists():
            try:
                import joblib  # noqa
                bundle = joblib.load(MODEL_PATH)
                # v5 bundle: split FL/CA ride models
                if "ride_model_fl" in bundle:
                    self._park_model = bundle.get("park_model")
                    self._ride_model = bundle["ride_model_fl"]
                    self._ride_model_ca = bundle.get("ride_model_ca")
                    self._park_features = bundle.get("park_feature_names", [])
                    self._ride_features = bundle.get("ride_feature_names_fl", [])
                    self._ride_features_ca = bundle.get("ride_feature_names_ca", [])
                    # Sanity-check the CA model: a tier-5 Disneyland ride on a busy
                    # mid-day should predict 45+ min. If it doesn't, the training data
                    # was bad (e.g., queue-times API returning capped/wrong values) and
                    # we fall back to the heuristic rather than serving garbage predictions.
                    if self._ride_model_ca is not None and self._ride_features_ca:
                        try:
                            import pandas as _pd
                            from datetime import datetime as _dt
                            from backend.data.disneyland_db import DL_ATTRACTIONS
                            _tier5 = next((a for a in DL_ATTRACTIONS if a.tier == 5), None)
                            if _tier5:
                                _when = _dt(2026, 1, 15, 11, 0)
                                _row = features.build_ride_feature_row(
                                    _tier5, _when, early_entry=False, park_avg_pred=0.0
                                )
                                _df = _pd.DataFrame([_row])[self._ride_features_ca]
                                _pred = float(self._ride_model_ca.predict(_df)[0])
                                if _pred < 30:
                                    log.warning(
                                        "CA model validation failed (tier-5 @ 11am → %.0f min, "
                                        "expected 45+). Training data likely capped/corrupted. "
                                        "Disabling ride_model_ca — falling back to DL heuristic.",
                                        _pred,
                                    )
                                    self._ride_model_ca = None
                        except Exception as _e:
                            log.warning("CA model validation error (%s) — disabling ride_model_ca", _e)
                            self._ride_model_ca = None
                    log.info("Loaded v%s wait-time bundle (park=%s, ride_fl=%s, ride_ca=%s)",
                             bundle.get("version", "?"),
                             "yes" if self._park_model else "no",
                             "yes" if self._ride_model else "no",
                             "yes" if self._ride_model_ca else "no")
                # Legacy 2-stage bundle (v2/v3/v4): single ride_model
                elif "ride_model" in bundle:
                    self._park_model = bundle.get("park_model")
                    self._ride_model = bundle["ride_model"]
                    self._park_features = bundle.get("park_feature_names", [])
                    self._ride_features = bundle.get("ride_feature_names", [])
                    log.info("Loaded legacy 2-stage wait-time model from %s "
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
                self._park_model = self._ride_model = self._ride_model_ca = None

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

    def predict_hours_batch(
        self,
        a: Attraction,
        d,          # date object
        hours: list,
        early_entry: bool = False,
        park_id: str = "epic_universe",
    ) -> list[dict]:
        """Predict wait times for a list of hours in one batch.

        Returns list of {hour, wait_minutes, crowd_multiplier} dicts.
        Calls park_model.predict() once for all hours combined.
        """
        import pandas as pd
        from datetime import datetime as _dt

        whens = [_dt.combine(d, _dt.min.time()).replace(hour=h) for h in hours]
        crowd_vals = [crowd_multiplier_at(w) for w in whens]

        # Batch park_avg predictions for all hours at once
        park_avgs: list[Optional[float]] = []
        if self._park_model is not None and self._park_features:
            try:
                park_rows = [features.build_park_feature_row(w) for w in whens]
                park_df = pd.DataFrame(park_rows)[self._park_features]
                avgs = self._park_model.predict(park_df)
                park_avgs = [float(v) for v in avgs]
            except Exception as e:
                log.warning("batch park_model failed (%s)", e)
                park_avgs = [None] * len(hours)
        else:
            park_avgs = [None] * len(hours)

        # Decide which model path to use:
        #   - Disneyland → ride_model_ca (no park_avg in features)
        #   - Epic Universe → ride_model_fl (with park_avg)
        #   - WDW (MK/EPCOT/HS/AK) → tier-factor heuristic (park_avg × DISNEY_TIER_FACTOR)
        use_ca_model  = park_id == "disneyland" and self._ride_model_ca is not None
        use_fl_model  = park_id == "epic_universe" and self._ride_model is not None
        use_heuristic = park_id in ALWAYS_HEURISTIC_PARK_IDS or (park_id == "disneyland" and not use_ca_model)

        results = []
        if use_heuristic:
            cap_factor = _capacity_factor(a.capacity_per_hour)
            if park_id == "disneyland":
                # DL heuristic: absolute tier baseline × hourly crowd.
                # cap_factor deliberately excluded: DL baselines were calibrated
                # without it, and high-throughput headliners (Rise, Indiana Jones)
                # were being penalised ~30% for their own efficiency.
                dl_base = DISNEYLAND_BASELINE_BY_TIER.get(a.tier, 30)
                for h, when, crowd, park_avg in zip(hours, whens, crowd_vals, park_avgs):

                    if a.kind == "show":
                        wait = 10
                    elif a.kind in ("experience", "restaurant"):
                        wait = int(round(dl_base * 0.3 * crowd))
                    else:
                        wait = int(round(dl_base * crowd))
                    wait = max(0, wait)
                    results.append({
                        "hour": h,
                        "wait_minutes": wait,
                        "crowd_multiplier": crowd,
                        "ll_return_minutes": _ll_return_minutes(a.ll_type, wait),
                    })
            else:
                # WDW heuristic: park_model output × tier factor
                factor = DISNEY_TIER_FACTOR.get(a.tier, 1.0)
                for h, when, crowd, park_avg in zip(hours, whens, crowd_vals, park_avgs):
                    if a.kind == "show":
                        wait = 10
                    elif a.kind in ("experience", "restaurant"):
                        wait = int(round((park_avg or 30) * 0.3))
                    else:
                        wait = int(round((park_avg or 30) * factor * cap_factor))
                    wait = max(0, wait)
                    results.append({
                        "hour": h,
                        "wait_minutes": wait,
                        "crowd_multiplier": crowd,
                        "ll_return_minutes": _ll_return_minutes(a.ll_type, wait),
                    })
        elif use_ca_model:
            try:
                ride_rows = [
                    features.build_ride_feature_row(a, w, early_entry=early_entry, park_avg_pred=0.0)
                    for w in whens
                ]
                ride_df = pd.DataFrame(ride_rows)[self._ride_features_ca]
                waits = self._ride_model_ca.predict(ride_df)
                for h, crowd, wait in zip(hours, crowd_vals, waits):
                    wait = max(0, int(round(wait)))
                    results.append({
                        "hour": h,
                        "wait_minutes": wait,
                        "crowd_multiplier": crowd,
                        "ll_return_minutes": _ll_return_minutes(a.ll_type, wait),
                    })
            except Exception as e:
                log.warning("batch ride_model_ca failed (%s), falling back to heuristic", e)
                for h, when, crowd, pa in zip(hours, whens, crowd_vals, park_avgs):
                    p = self.predict(a, when, early_entry=early_entry, park_id=park_id)
                    results.append({
                        "hour": h,
                        "wait_minutes": p.wait_minutes,
                        "crowd_multiplier": crowd,
                        "ll_return_minutes": p.ll_return_minutes,
                    })
        elif use_fl_model:
            try:
                ride_rows = [
                    features.build_ride_feature_row(a, w, early_entry=early_entry, park_avg_pred=pa or 0.0)
                    for w, pa in zip(whens, park_avgs)
                ]
                ride_df = pd.DataFrame(ride_rows)[self._ride_features]
                waits = self._ride_model.predict(ride_df)
                for h, crowd, wait in zip(hours, crowd_vals, waits):
                    wait = max(0, int(round(wait)))
                    results.append({
                        "hour": h,
                        "wait_minutes": wait,
                        "crowd_multiplier": crowd,
                        "ll_return_minutes": _ll_return_minutes(a.ll_type, wait),
                    })
            except Exception as e:
                log.warning("batch ride_model_fl failed (%s), falling back", e)
                for h, when, crowd, pa in zip(hours, whens, crowd_vals, park_avgs):
                    p = self.predict(a, when, early_entry=early_entry, park_id=park_id)
                    results.append({
                        "hour": h,
                        "wait_minutes": p.wait_minutes,
                        "crowd_multiplier": crowd,
                        "ll_return_minutes": p.ll_return_minutes,
                    })
        else:
            for h, when, crowd in zip(hours, whens, crowd_vals):
                p = self.predict(a, when, early_entry=early_entry, park_id=park_id)
                results.append({
                    "hour": h,
                    "wait_minutes": p.wait_minutes,
                    "crowd_multiplier": crowd,
                    "ll_return_minutes": p.ll_return_minutes,
                })

        return results

    def predict(self, a: Attraction, when: datetime, early_entry: bool = False,
                park_id: str = "epic_universe") -> Prediction:
        crowd = crowd_multiplier_at(when)
        park_avg = self._predict_park_avg(when)

        # Routing:
        #   - Disneyland → ride_model_ca (no park_avg feature)
        #   - Epic Universe → ride_model_fl (with park_avg feature)
        #   - WDW (always heuristic) → park_avg × DISNEY_TIER_FACTOR[tier] × cap_factor
        use_ca_model = park_id == "disneyland" and self._ride_model_ca is not None
        use_fl_model = park_id == "epic_universe" and self._ride_model is not None
        use_heuristic = park_id in ALWAYS_HEURISTIC_PARK_IDS or (park_id == "disneyland" and not use_ca_model)

        if use_heuristic:
            cap_factor = _capacity_factor(a.capacity_per_hour)
            if park_id == "disneyland":
                # DL: absolute tier baseline × crowd_multiplier_at (which already
                # embeds hourly shape). No Orlando park_model used.
                # cap_factor excluded — see batch path comment.
                dl_base = DISNEYLAND_BASELINE_BY_TIER.get(a.tier, 30)
                if a.kind == "show":
                    wait = 10
                elif a.kind in ("experience", "restaurant"):
                    wait = int(round(dl_base * 0.3 * crowd))
                else:
                    wait = int(round(dl_base * crowd))
            else:
                # WDW: park_model output × tier factor
                if park_avg is not None and park_avg > 0:
                    factor = DISNEY_TIER_FACTOR.get(a.tier, 1.0)
                    if a.kind == "show":
                        wait = 10
                    elif a.kind in ("experience", "restaurant"):
                        wait = int(round(park_avg * 0.3))
                    else:
                        wait = int(round(park_avg * factor * cap_factor))
                else:
                    baseline = {1: 5, 2: 15, 3: 25, 4: 45, 5: 70}.get(a.tier, 30)
                    wait = int(round(baseline * crowd))
            wait = max(0, wait)
            return Prediction(
                wait_minutes=wait,
                crowd_multiplier=crowd,
                confidence="heuristic",
                park_avg_pred=park_avg,
                ll_return_minutes=_ll_return_minutes(a.ll_type, wait),
            )

        if use_ca_model:
            try:
                import pandas as pd
                row = features.build_ride_feature_row(
                    a, when, early_entry=early_entry, park_avg_pred=0.0,
                )
                df = pd.DataFrame([row])[self._ride_features_ca]
                wait = max(0, int(round(float(self._ride_model_ca.predict(df)[0]))))
                return Prediction(
                    wait_minutes=wait,
                    crowd_multiplier=crowd,
                    confidence="model",
                    park_avg_pred=park_avg,
                    ll_return_minutes=_ll_return_minutes(a.ll_type, wait),
                )
            except Exception as e:
                log.warning("ride_model_ca prediction failed (%s), using heuristic", e)

        if use_fl_model:
            try:
                import pandas as pd
                row = features.build_ride_feature_row(
                    a, when, early_entry=early_entry, park_avg_pred=park_avg or 0.0,
                )
                df = pd.DataFrame([row])[self._ride_features]
                wait = max(0, int(round(float(self._ride_model.predict(df)[0]))))
                return Prediction(
                    wait_minutes=wait,
                    crowd_multiplier=crowd,
                    confidence="model",
                    park_avg_pred=park_avg,
                    ll_return_minutes=_ll_return_minutes(a.ll_type, wait),
                )
            except Exception as e:
                log.warning("ride_model_fl prediction failed (%s), using heuristic", e)

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
