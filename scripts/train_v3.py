"""
Three-stage trainer (v3):
  Stage 1 — park_model: park-level calendar/holiday model (unchanged from v2).
             Trained on park_level_history.csv (WDW + UOR park averages).

  Stage 2 — ride_model: unified per-ride model trained on BOTH
             Epic Universe (historical_waits.csv) AND
             Disney World per-ride data (disney_waits.csv).
             Uses the same feature set as v2 (ride attributes + park_avg_pred),
             so at inference time the router no longer needs the tier heuristic
             for Disney parks — it can use the real model.

Output: backend/ml/saved_model.pkl (same format as v2, drop-in replacement).

Usage:
  .venv/bin/python scripts/train_v3.py
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
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.data.attractions_db import attraction_by_id
from backend.data.disney_db import disney_attraction_by_id
from backend.ml.features import (
    PARK_FEATURE_NAMES,
    RIDE_FEATURE_NAMES,
    build_park_feature_row,
    build_ride_feature_row,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("train_v3")

PARK_CSV   = ROOT / "data" / "park_level_history.csv"
EPIC_CSV   = ROOT / "data" / "historical_waits.csv"
DISNEY_CSV = ROOT / "data" / "disney_waits.csv"
MODEL_OUT  = ROOT / "backend" / "ml" / "saved_model.pkl"

# ── Slug → local attraction-id maps ──────────────────────────────────────────

EPIC_SLUG_TO_LOCAL = {
    "stardustracers":                             "stardust_racers",
    "constellationcarousel":                      "constellation_carousel",
    "astronomica":                                "astronomica",
    "mariokartbowserschallenge":                  "mario_kart",
    "minecartmadness":                            "mine_cart_madness",
    "yoshisadventure":                            "yoshis_adventure",
    "bowserjrchallenge":                          "bowser_jr_showdown",
    "meetmarioandluigi":                          "meet_mario_luigi",
    "meetprincesspeach":                          "meet_princess_peach",
    "meetdonkeykong":                             "meet_donkey_kong",
    "harrypotterandthebattleattheministry":       "battle_at_ministry",
    "lecirquearcanus":                            "le_cirque_arcanus",
    "hiccupswinggliders":                         "hiccups_wing_gliders",
    "dragonracersrally":                          "dragon_racers_rally",
    "fyredrill":                                  "fyre_drill",
    "theuntrainabledragon":                       "untrainable_dragon",
    "vikingtrainingcamp":                         "viking_training_camp",
    "meettoothlessandfriends":                    "meet_toothless",
    "meettoothlesshiccup":                        "meet_toothless_hiccup",
    "monstersunchainedthefrankensteinexperiment": "monsters_unchained",
    "curseofthewerewolf":                         "curse_of_werewolf",
    "darkuniversecharactermeetgreet":             "dark_universe_meet",
}

DISNEY_SLUG_TO_LOCAL = {
    # Magic Kingdom
    "sevendwarfsminetrain":                         "mk_seven_dwarfs",
    "peterpansflight":                              "mk_peter_pan",
    "undertheseajourneyofthelittlemermaid":         "mk_little_mermaid",
    "themanyadventuresofwinniethepooh":             "mk_winnie_pooh",
    "itsasmallworld":                               "mk_small_world",
    "dumbotheflyingelephant":                       "mk_dumbo",
    "enchantedtaleswithbelle":                      "mk_enchanted_tales",
    "mickeysphilharmagic":                          "mk_philharmagic",
    "tronlightcyclerun":                            "mk_tron",
    "spacemountain":                                "mk_space_mountain",
    "buzzlightyearsspacerangerspin":                "mk_buzz_lightyear",
    "monstersinclaughfloor":                        "mk_laugh_floor",
    "piratesofthecaribbean":                        "mk_pirates",
    "junglecruise":                                 "mk_jungle_cruise",
    "themagiccarpetsofaladdin":                     "mk_magic_carpets",
    "waltdisneysenchantedtikiroom":                 "mk_tiki_room",
    "hauntedmansion":                               "mk_haunted_mansion",
    "thehallofpresidents":                          "mk_hall_presidents",
    "bigthundermountainrailroad":                   "mk_big_thunder",
    "tianasbayouadventure":                         "mk_tianas_bayou",
    "countrybearjamboree":                          "mk_country_bears",
    # EPCOT
    "guardiansofthegalaxycosmicrewind":             "ep_guardians",
    "testtrack":                                    "ep_test_track",
    "missionspace":                                 "ep_mission_space",
    "soarinaroundtheworld":                         "ep_soarin",
    "livingwiththeland":                            "ep_living_land",
    "theseaswithnemofriends":                       "ep_nemo_seas",
    "turtletalkwithcrush":                          "ep_turtle_talk",
    "spaceshipearth":                               "ep_spaceship_earth",
    "journeyintoimaginationwithfigment":            "ep_figment",
    "remysratatouilleadventure":                    "ep_remy",
    "frozeneverafter":                              "ep_frozen",
    "granfiestatourstarringthethreecaballeros":     "ep_gran_fiesta",
    "reflectionsofchina":                           "ep_reflections_china",
    # Hollywood Studios
    "starwarsriseoftheresistance":                  "hs_rise_resistance",
    "millenniumfalconsmugglersrun":                 "hs_smugglers_run",
    "slinkydogdash":                                "hs_slinky_dog",
    "toystorymania":                                "hs_toy_story_mania",
    "alienswirlingsaucers":                         "hs_alien_saucers",
    "thetwilightzonetowerofterror":                 "hs_tower_of_terror",
    "rocknrollercoasterstarringaerosmith":          "hs_rock_n_roller",
    "mickeyminniesrunawayrailway":                  "hs_runaway_railway",
    "startourstheadventurescontinue":               "hs_star_tours",
    "muppetvisiond":                                "hs_muppets",
    "indianajonesepicstuntspectacular":             "hs_indiana_jones",
    "fantasmic":                                    "hs_fantasmic",
    "beautyandthebeastliveonstage":                 "hs_beauty_beast_show",
    # Animal Kingdom
    "avatarflightofpassage":                        "ak_flight_of_passage",
    "naviriverjourney":                             "ak_navi_river",
    "kilimanjarosafaris":                           "ak_kilimanjaro",
    "festivalofthelionking":                        "ak_lion_king",
    "gorillafallsexplorationtrail":                 "ak_gorilla_falls",
    "expeditioneverestlegendoftheforbiddenmountain":"ak_expedition_everest",
    "kaliriverrapids":                              "ak_kali_rapids",
    "maharajahjungletrek":                          "ak_maharajah_trek",
    "itstoughtobeabug":                             "ak_tough_bug",
    "dinosaur":                                     "ak_dinosaur",
    "triceratopspin":                               "ak_triceratop_spin",
}


# ── Stage 1: park-level model ─────────────────────────────────────────────────

def train_park_model():
    if not PARK_CSV.exists() or PARK_CSV.stat().st_size == 0:
        log.warning("No park-level CSV — park_model skipped.")
        return None

    df = pd.read_csv(PARK_CSV)
    log.info("Park CSV: %d rows from %d (chain, park) pairs",
             len(df), df.groupby(["chain", "park_slug"]).ngroups)

    rows = []
    for _, r in df.iterrows():
        try:
            d = datetime.fromisoformat(r["date"])
            when = d.replace(hour=int(r["hour"]))
            rows.append({**build_park_feature_row(when), "__target": float(r["wait_minutes"])})
        except Exception:
            continue

    park_df = pd.DataFrame(rows)
    Xp, yp = park_df[PARK_FEATURE_NAMES], park_df["__target"]
    sw = np.sqrt(yp / yp.mean())
    log.info("Stage 1: fitting park_model on %d rows…", len(Xp))
    model = HistGradientBoostingRegressor(
        max_iter=600, max_depth=6, learning_rate=0.05,
        min_samples_leaf=20, l2_regularization=0.5, random_state=42,
    )
    model.fit(Xp, yp, sample_weight=sw)
    log.info("  park_model in-sample MAE: %.2f min",
             mean_absolute_error(yp, model.predict(Xp)))
    return model


# ── Stage 2: unified per-ride model (Epic + Disney) ───────────────────────────

def _load_csv_to_records(csv_path: Path, slug_map: dict, resolver) -> list[tuple]:
    """Read a waits CSV and return list of (Attraction, datetime, early_entry, wait, date_str)."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []

    df = pd.read_csv(csv_path)
    log.info("  %s: %d rows", csv_path.name, len(df))

    records = []
    skipped = 0
    for _, r in df.iterrows():
        local_id = slug_map.get(r["attraction_slug"])
        if not local_id:
            skipped += 1
            continue
        a = resolver(local_id)
        if a is None:
            skipped += 1
            continue
        try:
            d = datetime.fromisoformat(r["date"])
            hour = int(r["hour"])
            wait = float(r["wait_minutes"])
        except Exception:
            skipped += 1
            continue
        when = d.replace(hour=hour)
        records.append((a, when, hour < 9, wait, r["date"]))

    log.info("    mapped %d records (%d skipped: unknown slug/id)", len(records), skipped)
    return records


def train_ride_model(park_model):
    log.info("Loading per-ride CSVs…")
    epic_records    = _load_csv_to_records(EPIC_CSV,   EPIC_SLUG_TO_LOCAL,   attraction_by_id)
    disney_records  = _load_csv_to_records(DISNEY_CSV, DISNEY_SLUG_TO_LOCAL, disney_attraction_by_id)

    all_records = epic_records + disney_records
    if not all_records:
        log.error("No per-ride training records — aborting.")
        return None, []

    log.info("Total: %d Epic + %d Disney = %d records",
             len(epic_records), len(disney_records), len(all_records))

    # Hold out 20% of distinct dates (stratified across all sources)
    all_dates = sorted(set(r[4] for r in all_records))
    random.seed(42)
    test_dates = set(random.sample(all_dates, max(1, len(all_dates) // 5)))
    log.info("Test set: %d / %d dates held out", len(test_dates), len(all_dates))

    # Batch park_avg predictions
    log.info("Batch-predicting park_avg for all %d rows…", len(all_records))
    if park_model is not None:
        park_feats = pd.DataFrame([build_park_feature_row(r[1]) for r in all_records])
        park_avgs = park_model.predict(park_feats[PARK_FEATURE_NAMES]).tolist()
        log.info("  park_avg: mean=%.1f  range=%.0f→%.0f",
                 np.mean(park_avgs), np.min(park_avgs), np.max(park_avgs))
    else:
        park_avgs = [0.0] * len(all_records)

    train_rows, test_rows = [], []
    for (a, when, early, wait, date_str), park_avg in zip(all_records, park_avgs):
        feat = build_ride_feature_row(a, when, early_entry=early, park_avg_pred=float(park_avg))
        feat["__target"] = wait
        feat["__date"] = date_str
        (test_rows if date_str in test_dates else train_rows).append(feat)

    train_df = pd.DataFrame(train_rows)
    test_df  = pd.DataFrame(test_rows)
    log.info("Train: %d rows  Test: %d rows", len(train_df), len(test_df))

    Xr = train_df[RIDE_FEATURE_NAMES]
    yr = train_df["__target"]
    sw = np.sqrt(yr / yr.mean())

    log.info("Stage 2: fitting ride_model…")
    model = HistGradientBoostingRegressor(
        max_iter=900, max_depth=7, learning_rate=0.04,
        min_samples_leaf=15, l2_regularization=0.3, random_state=42,
    )
    model.fit(Xr, yr, sample_weight=sw)
    log.info("  ride_model in-sample MAE: %.2f min",
             mean_absolute_error(yr, model.predict(Xr)))

    if not test_df.empty:
        preds = model.predict(test_df[RIDE_FEATURE_NAMES])
        mae_test = mean_absolute_error(test_df["__target"], preds)
        log.info("  ride_model held-out MAE: %.2f min  (n=%d)", mae_test, len(test_df))

        test_df = test_df.copy()
        test_df["__pred"] = preds
        for tier, grp in test_df.groupby("ride_tier"):
            log.info("    tier %d: n=%d  MAE=%.1f  mean_actual=%.1f",
                     int(tier), len(grp),
                     mean_absolute_error(grp["__target"], grp["__pred"]),
                     grp["__target"].mean())

    return model, sorted(test_dates)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    park_model = train_park_model()
    ride_model, test_dates = train_ride_model(park_model)

    if ride_model is None:
        log.error("Training failed — model not saved.")
        return

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "park_model": park_model,
        "ride_model": ride_model,
        "park_feature_names": PARK_FEATURE_NAMES,
        "ride_feature_names": RIDE_FEATURE_NAMES,
        "test_dates": test_dates,
        "version": 3,
        "includes_disney": True,
    }
    joblib.dump(bundle, MODEL_OUT)
    log.info("Saved v3 bundle → %s", MODEL_OUT)
    log.info("Done. Restart the backend to load the new model.")


if __name__ == "__main__":
    main()
