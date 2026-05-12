"""
Two-stage trainer:
  Stage 1 — park_model: trained on 10 years of WDW + UOR park-level data
            from data/park_level_history.csv (predicts park-wide rolling
            avg wait given calendar/holiday features).
  Stage 2 — ride_model: trained on Epic Universe per-ride data from
            data/historical_waits.csv (predicts per-ride wait given
            calendar + ride attributes + park_avg_pred from stage 1).

Held-out test set is constructed by picking 20% of Epic *dates* at random and
reserving every row on those dates for evaluation. MAE is reported on
training (model never saw these days).

Output: backend/ml/saved_model.pkl with both models bundled.

Usage:
  python scripts/train_v2.py
"""
from __future__ import annotations

import logging
import random
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.data.attractions_db import attraction_by_id
from backend.ml.features import (
    PARK_FEATURE_NAMES,
    RIDE_FEATURE_NAMES,
    build_park_feature_row,
    build_ride_feature_row,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("train_v2")

PARK_CSV = ROOT / "data" / "park_level_history.csv"
EPIC_CSV = ROOT / "data" / "historical_waits.csv"
MODEL_OUT = ROOT / "backend" / "ml" / "saved_model.pkl"

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


# ── Stage 1: park-level data ────────────────────────────────────────────────

def load_park_rows() -> pd.DataFrame:
    if not PARK_CSV.exists() or PARK_CSV.stat().st_size == 0:
        log.warning("No park-level CSV at %s — stage 1 will be skipped.", PARK_CSV)
        return pd.DataFrame()
    df = pd.read_csv(PARK_CSV)
    if df.empty:
        return df
    log.info("Loaded %d park-level rows from %d distinct (chain, park) pairs",
             len(df), df.groupby(["chain", "park_slug"]).ngroups)

    rows = []
    for _, r in df.iterrows():
        try:
            d = datetime.fromisoformat(r["date"])
            hour = int(r["hour"])
            wait = float(r["wait_minutes"])
        except Exception:
            continue
        when = d.replace(hour=hour)
        feat = build_park_feature_row(when)
        feat["__target"] = wait
        rows.append(feat)
    return pd.DataFrame(rows)


# ── Stage 2: Epic per-ride data ─────────────────────────────────────────────

def load_epic_rows(park_model) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Returns (train_df, test_df, test_dates) for Epic per-ride data."""
    if not EPIC_CSV.exists() or EPIC_CSV.stat().st_size == 0:
        return pd.DataFrame(), pd.DataFrame(), []

    df = pd.read_csv(EPIC_CSV)
    log.info("Loaded %d Epic per-ride rows", len(df))

    # Hold out 20% of distinct dates as test.
    all_dates = sorted(df["date"].unique())
    random.seed(42)
    test_dates = set(random.sample(all_dates, max(1, len(all_dates) // 5)))
    log.info("Reserving %d / %d Epic dates as test set (e.g. %s)",
             len(test_dates), len(all_dates), list(sorted(test_dates))[:3])

    # Build park-feature rows for ALL Epic rows in one pass, then batch-predict.
    log.info("Building feature rows and batch-predicting park_avg…")
    epic_records = []
    skipped = 0
    for _, r in df.iterrows():
        local_id = TD_SLUG_TO_LOCAL.get(r["attraction_slug"])
        if not local_id:
            skipped += 1
            continue
        a = attraction_by_id(local_id)
        if a is None:
            skipped += 1
            continue
        try:
            d = datetime.fromisoformat(r["date"])
            hour = int(r["hour"])
            wait = float(r["wait_minutes"])
        except Exception:
            continue
        when = d.replace(hour=hour)
        epic_records.append((a, when, hour < 9, wait, r["date"]))

    if not epic_records:
        return pd.DataFrame(), pd.DataFrame(), []

    # Batch-predict park_avg for all Epic rows
    park_feats_df = pd.DataFrame([build_park_feature_row(when) for (_, when, _, _, _) in epic_records])
    if park_model is not None:
        park_avgs = park_model.predict(park_feats_df[PARK_FEATURE_NAMES])
        log.info("  park_avg predicted for %d Epic rows (mean=%.1f, range=%.0f→%.0f)",
                 len(park_avgs), park_avgs.mean(), park_avgs.min(), park_avgs.max())
    else:
        park_avgs = np.zeros(len(epic_records))

    train_rows = []
    test_rows = []
    for (a, when, early, wait, date_str), park_avg in zip(epic_records, park_avgs):
        feat = build_ride_feature_row(a, when, early_entry=early, park_avg_pred=float(park_avg))
        feat["__target"] = wait
        feat["__date"] = date_str
        (test_rows if date_str in test_dates else train_rows).append(feat)

    log.info("Mapped %d train rows, %d test rows (%d skipped: unknown slug)",
             len(train_rows), len(test_rows), skipped)
    return pd.DataFrame(train_rows), pd.DataFrame(test_rows), sorted(test_dates)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    # Stage 1: park model
    park_df = load_park_rows()
    park_model = None
    if not park_df.empty:
        Xp = park_df[PARK_FEATURE_NAMES]
        yp = park_df["__target"]
        log.info("Stage 1: fitting park_model on %d rows…", len(Xp))
        park_model = GradientBoostingRegressor(
            n_estimators=400, max_depth=4, learning_rate=0.05, random_state=42
        )
        park_model.fit(Xp, yp)
        mae_park = mean_absolute_error(yp, park_model.predict(Xp))
        log.info("  park_model in-sample MAE: %.2f min  (this is the 'expected mature park rolling avg')", mae_park)
    else:
        log.warning("Stage 1 skipped — no park data. Stage 2 will run without park_avg_pred feature.")

    # Stage 2: ride model on Epic
    train_df, test_df, test_dates = load_epic_rows(park_model)
    if train_df.empty:
        log.error("No Epic per-ride training data — aborting.")
        return

    Xr_train = train_df[RIDE_FEATURE_NAMES]
    yr_train = train_df["__target"]
    log.info("Stage 2: fitting ride_model on %d Epic rows…", len(Xr_train))
    ride_model = GradientBoostingRegressor(
        n_estimators=600, max_depth=5, learning_rate=0.05, random_state=42
    )
    ride_model.fit(Xr_train, yr_train)
    log.info("  ride_model in-sample MAE: %.2f min", mean_absolute_error(yr_train, ride_model.predict(Xr_train)))

    if not test_df.empty:
        Xr_test = test_df[RIDE_FEATURE_NAMES]
        yr_test = test_df["__target"]
        preds = ride_model.predict(Xr_test)
        mae_test = mean_absolute_error(yr_test, preds)
        log.info("  ride_model held-out-dates MAE: %.2f min  (n_test=%d, %d dates never seen during training)",
                 mae_test, len(Xr_test), len(test_dates))
        # Per-attraction breakdown
        test_df = test_df.copy()
        test_df["__pred"] = preds
        log.info("  Per-attraction held-out MAE:")
        for slug, grp in test_df.groupby(test_df.index // 1).head(1).iterrows():
            pass
        # simpler: group by ride_tier as a proxy
        for tier, grp in test_df.groupby("ride_tier"):
            mae_tier = mean_absolute_error(grp["__target"], grp["__pred"])
            log.info("    tier %d: n=%d  MAE=%.2f min  mean_actual=%.1f", int(tier), len(grp), mae_tier, grp["__target"].mean())

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "park_model": park_model,
        "ride_model": ride_model,
        "park_feature_names": PARK_FEATURE_NAMES,
        "ride_feature_names": RIDE_FEATURE_NAMES,
        "test_dates": test_dates,
    }
    joblib.dump(bundle, MODEL_OUT)
    log.info("Saved 2-stage bundle → %s", MODEL_OUT)


if __name__ == "__main__":
    main()
