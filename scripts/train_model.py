"""
Train the wait-time model.

Two data sources:
1. data/live_log.csv  — accumulated real waits scraped from queue-times.com
                        via scripts/fetch_historical.py
2. Synthetic rows     — generated from crowd_factors + per-tier baselines,
                        sampled across the year. This ensures the model can
                        predict for dates not yet observed (Memorial Day 2026)
                        and rides without enough live data.

Output: backend/ml/saved_model.pkl (joblib bundle with model + feature_names)

Usage:
  python scripts/train_model.py
"""
from __future__ import annotations

import logging
import math
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.data.attractions_db import ATTRACTIONS, Attraction, attraction_by_id
from backend.ml.crowd_factors import (
    DOW_MULTIPLIER,
    MONTH_MULTIPLIER,
    forecast_for,
    holiday_factor,
    hourly_factor,
    novelty_factor,
)
from backend.ml.features import FEATURE_NAMES, build_feature_row
from backend.ml.model import BASELINE_WAIT_BY_TIER, _capacity_factor


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("train")

MODEL_OUT = ROOT / "backend" / "ml" / "saved_model.pkl"
LIVE_LOG = ROOT / "data" / "live_log.csv"


# ── Synthetic generator ──────────────────────────────────────────────────────

def synthetic_wait(a: Attraction, when: datetime, early_entry: bool = False) -> float:
    """Heuristic wait used to seed the model with sensible behavior."""
    f = forecast_for(when.date())
    hour_mult = hourly_factor(when.hour)
    crowd = f.base_multiplier * hour_mult

    if a.kind == "show":
        return 15.0 + 5.0 * crowd
    if a.kind == "restaurant":
        return 12.0 + 6.0 * crowd
    if a.kind == "experience":
        return 8.0 * crowd

    baseline = BASELINE_WAIT_BY_TIER.get(a.tier, 30)
    cap = _capacity_factor(a.capacity_per_hour)
    first_hour = 9
    first_bonus = 0.55 if when.hour == first_hour else 1.0
    if early_entry and when.hour < first_hour:
        first_bonus = 0.40

    noise = random.gauss(1.0, 0.10)
    return max(0.0, baseline * crowd * cap * first_bonus * noise)


def generate_synthetic(n_dates: int = 90) -> pd.DataFrame:
    """Generate rows across diverse dates × every hour × every ride."""
    random.seed(42)
    np.random.seed(42)

    # Sample a year of dates with extra weight on holiday windows.
    start = date(2025, 5, 22)  # Epic opening
    end = date(2027, 6, 30)    # cover next year too
    span_days = (end - start).days

    dates: list[date] = []
    while len(dates) < n_dates:
        d = start + timedelta(days=random.randint(0, span_days))
        dates.append(d)
    # Force-include Memorial Day & nearby
    dates.extend([
        date(2025, 5, 26), date(2026, 5, 25), date(2026, 5, 24), date(2026, 5, 23),
        date(2025, 7, 4), date(2025, 12, 25), date(2026, 3, 30),
    ])

    rows = []
    rides = [a for a in ATTRACTIONS if a.kind in ("ride", "experience")]
    for d in dates:
        for a in rides:
            for h in range(8, 22):
                when = datetime.combine(d, datetime.min.time()).replace(hour=h, minute=random.choice([0, 15, 30, 45]))
                early = (h == 8)
                feat = build_feature_row(a, when, early_entry=early)
                feat["__target"] = synthetic_wait(a, when, early_entry=early)
                rows.append(feat)
    return pd.DataFrame(rows)


# ── Live log ingest ──────────────────────────────────────────────────────────

QT_ID_TO_LOCAL = {
    14683: "mario_kart",
    14686: "mine_cart_madness",
    14685: "meet_toothless",
    14682: "bowser_jr_showdown",
}


def load_live_log() -> pd.DataFrame:
    if not LIVE_LOG.exists():
        return pd.DataFrame()
    df = pd.read_csv(LIVE_LOG)
    if df.empty:
        return df

    df["ts"] = pd.to_datetime(df["timestamp_utc"], utc=True).dt.tz_convert("America/New_York")
    df = df[df["is_open"] == 1]
    df = df[df["wait_minutes"].notna()]

    rows = []
    for _, r in df.iterrows():
        local_id = QT_ID_TO_LOCAL.get(int(r["ride_id"])) if pd.notna(r["ride_id"]) else None
        if local_id is None:
            # Try to match by ride name
            name = (r.get("ride_name") or "").lower()
            matches = [a for a in ATTRACTIONS if a.name.lower() in name or name in a.name.lower()]
            if matches:
                local_id = matches[0].id
        a = attraction_by_id(local_id) if local_id else None
        if a is None:
            continue
        when = r["ts"].to_pydatetime()
        feat = build_feature_row(a, when, early_entry=(when.hour < 9))
        feat["__target"] = float(r["wait_minutes"])
        rows.append(feat)
    return pd.DataFrame(rows)


# ── Train ────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Generating synthetic training rows…")
    syn = generate_synthetic(n_dates=120)
    log.info("  synthetic rows: %d", len(syn))

    live = load_live_log()
    if not live.empty:
        log.info("Loaded %d live-log rows from %s", len(live), LIVE_LOG)
        # Live data is *much* more trustworthy; oversample it.
        live = pd.concat([live] * 5, ignore_index=True)
        df = pd.concat([syn, live], ignore_index=True)
    else:
        log.info("No live log yet — training on synthetic only.")
        df = syn

    X = df[FEATURE_NAMES]
    y = df["__target"]

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(
        n_estimators=400,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
    )
    log.info("Fitting GradientBoostingRegressor…")
    model.fit(Xtr, ytr)

    preds = model.predict(Xte)
    mae = mean_absolute_error(yte, preds)
    log.info("Test MAE: %.2f minutes  (n_test=%d)", mae, len(yte))

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES, "mae": mae}, MODEL_OUT)
    log.info("Saved model → %s", MODEL_OUT)


if __name__ == "__main__":
    main()
