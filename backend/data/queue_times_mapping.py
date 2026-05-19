"""Mapping from queue-times.com ride IDs to our internal attraction IDs.

Built by inspecting queue-times' live data for each park. Manual map (numeric
IDs are stable; names sometimes shift with branding/overlays).

queue-times park IDs:
  Disneyland Park             = 16
  Magic Kingdom               = 6
  EPCOT                       = 5
  Hollywood Studios           = 7
  Animal Kingdom              = 8
  Epic Universe (Universal)   = 334
"""
from __future__ import annotations


QT_PARK_IDS: dict[str, int] = {
    "disneyland":         16,
    "magic_kingdom":      6,
    "epcot":              5,
    "hollywood_studios":  7,
    "animal_kingdom":     8,
    "epic_universe":      334,
}


# Per-park: queue-times ride ID → our local attraction_id.
# Only rides we predict waits for are mapped; walkthrough attractions and
# secondary entries (single-rider lines, monorails) are intentionally omitted.

DISNEYLAND_QT_TO_LOCAL: dict[int, str] = {
    326:   "dl_indiana_jones",
    296:   "dl_jungle_cruise",
    13958: "dl_haunted_mansion",
    289:   "dl_pirates",
    323:   "dl_big_thunder",
    14168: "dl_tianas_bayou",
    279:   "dl_matterhorn",
    281:   "dl_peter_pan",
    307:   "dl_small_world",
    332:   "dl_roger_rabbit",
    306:   "dl_winnie_pooh",
    275:   "dl_dumbo",
    285:   "dl_alice",
    282:   "dl_pinocchio",
    283:   "dl_snow_white",
    284:   "dl_space_mountain",       # appears as "Hyperspace Mountain" overlay sometimes
    273:   "dl_buzz_lightyear",
    286:   "dl_star_tours",
    317:   "dl_autopia",
    276:   "dl_finding_nemo",
    11526: "dl_runaway_railway",
    327:   "dl_mickeys_house",
    6340:  "dl_rise_resistance",
    6339:  "dl_smugglers_run",
}


# Epic Universe + WDW park mappings will be filled in when those parks need live mode.
EPIC_UNIVERSE_QT_TO_LOCAL: dict[int, str] = {}
MAGIC_KINGDOM_QT_TO_LOCAL: dict[int, str] = {}
EPCOT_QT_TO_LOCAL: dict[int, str] = {}
HOLLYWOOD_STUDIOS_QT_TO_LOCAL: dict[int, str] = {}
ANIMAL_KINGDOM_QT_TO_LOCAL: dict[int, str] = {}


PARK_MAPPINGS: dict[str, dict[int, str]] = {
    "disneyland":        DISNEYLAND_QT_TO_LOCAL,
    "epic_universe":     EPIC_UNIVERSE_QT_TO_LOCAL,
    "magic_kingdom":     MAGIC_KINGDOM_QT_TO_LOCAL,
    "epcot":             EPCOT_QT_TO_LOCAL,
    "hollywood_studios": HOLLYWOOD_STUDIOS_QT_TO_LOCAL,
    "animal_kingdom":    ANIMAL_KINGDOM_QT_TO_LOCAL,
}


def to_local_id(park: str, qt_id: int) -> str | None:
    return PARK_MAPPINGS.get(park, {}).get(qt_id)


def queue_times_park_id(park: str) -> int | None:
    return QT_PARK_IDS.get(park)
