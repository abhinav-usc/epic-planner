"""
Disneyland Park (Anaheim) catalog.

Attraction data sourced from official Disneyland website, TouringPlans,
thrill-data.com, and queue-times.com (2022-2025).

Lightning Lane notes (verified 2026):
  - LLSP (Single Pass, per-ride purchase): Rise of the Resistance only
  - LLMP (Multi Pass): Indiana Jones, Haunted Mansion, Pirates, Matterhorn,
      Big Thunder, Tiana's Bayou, Space Mountain, Smugglers Run, Peter Pan,
      Roger Rabbit, and others
"""
from __future__ import annotations

from typing import Optional

from backend.data.attractions_db import Attraction, Restaurant


# ─── Park metadata ─────────────────────────────────────────────────────────────

DISNEYLAND_PARKS = {
    "disneyland": {
        "name": "Disneyland Park",
        "icon": "🏰",
        "description": "The original Magic Kingdom. Haunted Mansion, Indiana Jones, Galaxy's Edge, and more.",
        "open_hour": 9,
        "close_hour": 23,
    },
}


# ─── Lands ─────────────────────────────────────────────────────────────────────

DL_LANDS = {
    "dl_main_street":      {"name": "Main Street, U.S.A.",         "color": "#D97706", "icon": "🏛️",  "description": "Turn-of-the-century Americana. Town Square, shops, and Sleeping Beauty Castle ahead."},
    "dl_adventureland":    {"name": "Adventureland",                "color": "#16A34A", "icon": "🗺️",  "description": "Tropical adventure: Indiana Jones, Jungle Cruise, Tarzan's Treehouse."},
    "dl_new_orleans_sq":   {"name": "New Orleans Square",           "color": "#7C3AED", "icon": "⚜️",  "description": "Haunted Mansion and Pirates of the Caribbean — the best versions at any Disney park."},
    "dl_frontierland":     {"name": "Frontierland",                 "color": "#B45309", "icon": "🤠",  "description": "Wild West: Big Thunder Mountain, Tiana's Bayou Adventure, shooting gallery."},
    "dl_fantasyland":      {"name": "Fantasyland",                  "color": "#EC4899", "icon": "🏰",  "description": "Classic fairy tales: Peter Pan, It's a Small World, Matterhorn, Roger Rabbit."},
    "dl_tomorrowland":     {"name": "Tomorrowland",                 "color": "#06B6D4", "icon": "🚀",  "description": "Retro-futuristic: Space Mountain, Buzz Lightyear, Star Tours, Autopia."},
    "dl_galaxys_edge":     {"name": "Star Wars: Galaxy's Edge",     "color": "#1F2937", "icon": "⭐",  "description": "Batuu: Rise of the Resistance and Millennium Falcon: Smugglers Run."},
    "dl_toontown":         {"name": "Mickey's Toontown",            "color": "#FBBF24", "icon": "🎭",  "description": "Fully renovated animated town: Mickey's Toontown, CenTOONial Park."},
}


# ─── Walk times (hub-and-spoke, hub = Main Street) ─────────────────────────────
# Disneyland is roughly circular; spokes from main entrance.

def _hub_spoke_walks(spokes: dict[str, int]) -> dict[tuple[str, str], int]:
    times: dict[tuple[str, str], int] = {}
    for a, t_a in spokes.items():
        for b, t_b in spokes.items():
            times[(a, b)] = 0 if a == b else t_a + t_b
    return times


DL_WALK = _hub_spoke_walks({
    "dl_main_street":   0,
    "dl_adventureland": 5,
    "dl_new_orleans_sq":7,
    "dl_frontierland":  8,
    "dl_fantasyland":   7,
    "dl_tomorrowland":  5,
    "dl_galaxys_edge":  10,
    "dl_toontown":      8,
})
# Adjacency shortcuts (overwrite hub-spoke sum where lands are actually adjacent)
DL_WALK[("dl_adventureland", "dl_new_orleans_sq")] = 3
DL_WALK[("dl_new_orleans_sq", "dl_adventureland")] = 3
DL_WALK[("dl_new_orleans_sq", "dl_frontierland")]  = 4
DL_WALK[("dl_frontierland", "dl_new_orleans_sq")]  = 4
DL_WALK[("dl_frontierland", "dl_fantasyland")]     = 5
DL_WALK[("dl_fantasyland", "dl_frontierland")]     = 5
DL_WALK[("dl_fantasyland", "dl_tomorrowland")]     = 6
DL_WALK[("dl_tomorrowland", "dl_fantasyland")]     = 6
DL_WALK[("dl_galaxys_edge", "dl_frontierland")]    = 5
DL_WALK[("dl_frontierland", "dl_galaxys_edge")]    = 5
DL_WALK[("dl_toontown", "dl_fantasyland")]         = 4
DL_WALK[("dl_fantasyland", "dl_toontown")]         = 4


def disneyland_walk_minutes(from_land: str, to_land: str) -> int:
    return DL_WALK.get((from_land, to_land), 8)


# ─── Attractions ───────────────────────────────────────────────────────────────

DL_ATTRACTIONS: list[Attraction] = [

    # ── Galaxy's Edge ─────────────────────────────────────────────────────────
    Attraction(
        id="dl_rise_resistance",
        name="Star Wars: Rise of the Resistance",
        land="dl_galaxys_edge",
        kind="ride",
        tier=5,
        duration_minutes=18,
        capacity_per_hour=1750,
        has_single_rider=False,
        has_express=True,
        height_inches=40,
        description="Immersive mega-attraction: captured by the First Order, then rescued. Best ride in any Disney park.",
    ),
    Attraction(
        id="dl_smugglers_run",
        name="Millennium Falcon: Smugglers Run",
        land="dl_galaxys_edge",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=1680,
        has_single_rider=False,
        has_express=True,
        height_inches=38,
        description="Interactive cockpit experience piloting (or shooting from) the Millennium Falcon.",
    ),

    # ── Adventureland ─────────────────────────────────────────────────────────
    Attraction(
        id="dl_indiana_jones",
        name="Indiana Jones Adventure",
        land="dl_adventureland",
        kind="ride",
        tier=5,
        duration_minutes=4,
        capacity_per_hour=2000,
        has_single_rider=False,
        has_express=True,
        height_inches=46,
        description="EMV jeep ride through the Temple of the Forbidden Eye. A Disneyland original icon.",
    ),
    Attraction(
        id="dl_jungle_cruise",
        name="Jungle Cruise",
        land="dl_adventureland",
        kind="ride",
        tier=3,
        duration_minutes=10,
        capacity_per_hour=1800,
        has_express=True,
        description="Satirical safari boat ride through Africa, Asia, and the Amazon. Newly refreshed skipper puns.",
    ),
    Attraction(
        id="dl_tarzan_treehouse",
        name="Tarzan's Treehouse",
        land="dl_adventureland",
        kind="experience",
        tier=1,
        duration_minutes=15,
        capacity_per_hour=None,
        description="Walk-through treehouse attraction based on the 1999 animated film.",
    ),

    # ── New Orleans Square ─────────────────────────────────────────────────────
    Attraction(
        id="dl_haunted_mansion",
        name="Haunted Mansion",
        land="dl_new_orleans_sq",
        kind="ride",
        tier=4,
        duration_minutes=9,
        capacity_per_hour=2400,
        has_express=True,
        description="The definitive Haunted Mansion — 999 happy haunts, stretching room, the Hatbox Ghost.",
    ),
    Attraction(
        id="dl_pirates",
        name="Pirates of the Caribbean",
        land="dl_new_orleans_sq",
        kind="ride",
        tier=4,
        duration_minutes=16,
        capacity_per_hour=3000,
        has_express=True,
        description="The original and longest version of this classic boat ride — three drops and 15+ minutes.",
    ),

    # ── Frontierland ──────────────────────────────────────────────────────────
    Attraction(
        id="dl_big_thunder",
        name="Big Thunder Mountain Railroad",
        land="dl_frontierland",
        kind="ride",
        tier=3,
        duration_minutes=4,
        capacity_per_hour=2400,
        has_express=True,
        height_inches=40,
        description="Runaway mine train through a haunted gold-mining town. Often lower waits than WDW's version.",
    ),
    Attraction(
        id="dl_tianas_bayou",
        name="Tiana's Bayou Adventure",
        land="dl_frontierland",
        kind="ride",
        tier=4,
        duration_minutes=11,
        capacity_per_hour=2400,
        has_express=True,
        height_inches=40,
        description="Log flume through the Louisiana bayou. Replaced Splash Mountain — biggest drop in the park.",
    ),

    # ── Fantasyland ───────────────────────────────────────────────────────────
    Attraction(
        id="dl_matterhorn",
        name="Matterhorn Bobsleds",
        land="dl_fantasyland",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1600,
        has_single_rider=True,
        has_express=True,
        height_inches=42,
        description="Twin-track steel coaster through the Matterhorn peak with the Abominable Snowman inside. Disneyland classic.",
    ),
    Attraction(
        id="dl_peter_pan",
        name="Peter Pan's Flight",
        land="dl_fantasyland",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1200,
        has_express=True,
        description="Iconic flying galleon over London and Neverland. Consistently one of the longest wait-time rides.",
    ),
    Attraction(
        id="dl_small_world",
        name="it's a small world",
        land="dl_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=15,
        capacity_per_hour=2800,
        has_express=False,
        description="The original and longest version: 15 minutes through the world's cultures.",
    ),
    Attraction(
        id="dl_roger_rabbit",
        name="Roger Rabbit's Car Toon Spin",
        land="dl_toontown",
        kind="ride",
        tier=3,
        duration_minutes=4,
        capacity_per_hour=1200,
        has_express=True,
        description="Spinning dark ride through Toontown with Roger Rabbit and the Dip.",
    ),
    Attraction(
        id="dl_winnie_pooh",
        name="The Many Adventures of Winnie the Pooh",
        land="dl_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=4,
        capacity_per_hour=1600,
        has_express=True,
        description="Bouncy pot dark ride through the Hundred Acre Wood.",
    ),
    Attraction(
        id="dl_dumbo",
        name="Dumbo the Flying Elephant",
        land="dl_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=2,
        capacity_per_hour=900,
        has_express=True,
        description="Classic spinner with the beloved elephant.",
    ),
    Attraction(
        id="dl_alice",
        name="Alice in Wonderland",
        land="dl_fantasyland",
        kind="ride",
        tier=3,
        duration_minutes=4,
        capacity_per_hour=1200,
        has_express=True,
        description="Dark ride through Wonderland unique to Disneyland — not at WDW.",
    ),
    Attraction(
        id="dl_pinocchio",
        name="Pinocchio's Daring Journey",
        land="dl_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=3,
        capacity_per_hour=1600,
        has_express=True,
        description="Classic dark ride through the story of Pinocchio.",
    ),
    Attraction(
        id="dl_snow_white",
        name="Snow White's Enchanted Wish",
        land="dl_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=3,
        capacity_per_hour=1500,
        has_express=True,
        description="Renovated dark ride through Snow White's story — stunning new effects.",
    ),

    # ── Tomorrowland ─────────────────────────────────────────────────────────
    Attraction(
        id="dl_space_mountain",
        name="Space Mountain",
        land="dl_tomorrowland",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1800,
        has_express=True,
        height_inches=40,
        description="Indoor roller coaster through a simulated outer space voyage. Darker and faster than the WDW version.",
    ),
    Attraction(
        id="dl_buzz_lightyear",
        name="Buzz Lightyear Astro Blasters",
        land="dl_tomorrowland",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=1600,
        has_express=True,
        description="Rotating omnimover with laser blasters — shoot targets to defeat Zurg.",
    ),
    Attraction(
        id="dl_star_tours",
        name="Star Tours – The Adventures Continue",
        land="dl_tomorrowland",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=2000,
        has_express=True,
        height_inches=40,
        description="Motion-simulator with hundreds of possible Star Wars storyline combinations.",
    ),
    Attraction(
        id="dl_autopia",
        name="Autopia",
        land="dl_tomorrowland",
        kind="ride",
        tier=1,
        duration_minutes=7,
        capacity_per_hour=1200,
        has_express=False,
        height_inches=54,
        description="Guided car ride through a stylized freeway. Newly refreshed with smart-car theme.",
    ),
    Attraction(
        id="dl_finding_nemo",
        name="Finding Nemo Submarine Voyage",
        land="dl_tomorrowland",
        kind="ride",
        tier=2,
        duration_minutes=14,
        capacity_per_hour=1800,
        has_express=False,
        description="Submarine voyage with underwater scenes animated to the film's characters.",
    ),

    # ── Toontown ─────────────────────────────────────────────────────────────
    Attraction(
        id="dl_runaway_railway",
        name="Mickey & Minnie's Runaway Railway",
        land="dl_toontown",
        kind="ride",
        tier=5,
        duration_minutes=5,
        capacity_per_hour=1500,
        has_express=True,
        description="Trackless dark ride into a Mickey Mouse cartoon. Opened Jan 2023 in the El CapiTOON Theater. Routinely 60-120 min standby — one of DL's longest waits.",
    ),
    Attraction(
        id="dl_mickeys_house",
        name="Mickey's House and Meet Mickey",
        land="dl_toontown",
        kind="experience",
        tier=2,
        duration_minutes=20,
        capacity_per_hour=300,
        has_express=False,
        description="Walk through Mickey's house and meet Mickey Mouse himself.",
    ),

    # ── Shows ─────────────────────────────────────────────────────────────────
    Attraction(
        id="dl_fantasmic",
        name="Fantasmic!",
        land="dl_frontierland",
        kind="show",
        tier=4,
        duration_minutes=25,
        capacity_per_hour=None,
        has_express=False,
        showtimes=["21:00", "22:30"],
        description="Nighttime spectacular on the Rivers of America — Mickey battles villains with water, fire, and projection.",
    ),
    Attraction(
        id="dl_world_color",
        name="World of Color – One",
        land="dl_fantasyland",
        kind="show",
        tier=3,
        duration_minutes=25,
        capacity_per_hour=None,
        has_express=False,
        showtimes=["21:00", "22:00"],
        description="Water projection show at Paradise Pier (DCA side) visible from multiple viewpoints.",
    ),
    Attraction(
        id="dl_fireworks",
        name="Fireworks",
        land="dl_main_street",
        kind="show",
        tier=5,
        duration_minutes=20,
        capacity_per_hour=None,
        has_express=False,
        showtimes=["21:30"],
        description="Nightly fireworks spectacular above Sleeping Beauty Castle. Best viewed from Main Street or the hub.",
    ),
]

# ── LL types ──────────────────────────────────────────────────────────────────
_DL_LL_TYPES: dict[str, str] = {
    # LLSP (Individual — premium, per-ride purchase, ~$29-35 as of 2026)
    "dl_rise_resistance":  "single",
    # LLMP (Multi Pass — day pass covers all of these)
    "dl_indiana_jones":    "multi",
    "dl_smugglers_run":    "multi",
    "dl_matterhorn":       "multi",
    "dl_haunted_mansion":  "multi",
    "dl_pirates":          "multi",
    "dl_big_thunder":      "multi",
    "dl_tianas_bayou":     "multi",
    "dl_peter_pan":        "multi",
    "dl_space_mountain":   "multi",
    "dl_buzz_lightyear":   "multi",
    "dl_star_tours":       "multi",
    "dl_roger_rabbit":     "multi",
    "dl_runaway_railway":  "multi",
    "dl_small_world":      "multi",
    "dl_alice":            "multi",
    "dl_winnie_pooh":      "multi",
    "dl_snow_white":       "multi",
    "dl_finding_nemo":     "multi",
}
for _a in DL_ATTRACTIONS:
    _a.ll_type = _DL_LL_TYPES.get(_a.id)


# ─── Restaurants ───────────────────────────────────────────────────────────────

DL_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        id="dl_blue_bayou",
        name="Blue Bayou Restaurant",
        land="dl_new_orleans_sq",
        service="table",
        cuisine="Cajun / Creole",
        avg_meal_minutes=75,
        reservations=True,
        popular_dish="Monte Cristo sandwich",
        description="Iconic sit-down restaurant inside Pirates of the Caribbean with bayou atmosphere.",
        menu_highlights=["Monte Cristo sandwich", "Bayou gumbo", "Jambalaya"],
        url="https://disneyland.disney.go.com/dining/disneyland/blue-bayou-restaurant/",
        wait_notes="Reservations strongly recommended. Book 60 days out.",
    ),
    Restaurant(
        id="dl_bengal_bbq",
        name="Bengal Barbecue",
        land="dl_adventureland",
        service="quick",
        cuisine="BBQ skewers",
        avg_meal_minutes=15,
        reservations=False,
        popular_dish="Bacon-wrapped asparagus skewer",
        description="Popular outdoor skewer stand near Indiana Jones. Often has a long line at lunch.",
        menu_highlights=["Bacon-wrapped asparagus", "Tiger Tail (pork loin)", "Outback Vegetable skewer"],
        url="",
        wait_notes="Peak hour queues 20-30 min. Go off-peak.",
    ),
    Restaurant(
        id="dl_carnation_cafe",
        name="Carnation Café",
        land="dl_main_street",
        service="table",
        cuisine="American",
        avg_meal_minutes=60,
        reservations=True,
        popular_dish="Walt's Chili",
        description="Classic Main Street café with a historical menu from Walt Disney's era.",
        menu_highlights=["Walt's Chili", "Classic pot roast", "Fried chicken"],
        url="",
        wait_notes="Reservations help. Often walk-up available early morning.",
    ),
    Restaurant(
        id="dl_plaza_inn",
        name="Plaza Inn",
        land="dl_main_street",
        service="quick",
        cuisine="American comfort food",
        avg_meal_minutes=25,
        reservations=False,
        popular_dish="Fried chicken",
        description="Victorian-style cafeteria in the heart of Main Street. Famous fried chicken.",
        menu_highlights=["Fried chicken", "Pasta", "Rotisserie chicken"],
        url="",
        wait_notes="Busy at lunch. Lines move fast.",
    ),
    Restaurant(
        id="dl_ronto_roasters",
        name="Ronto Roasters",
        land="dl_galaxys_edge",
        service="quick",
        cuisine="Star Wars-themed",
        avg_meal_minutes=15,
        reservations=False,
        popular_dish="Ronto Wrap",
        description="Galaxy's Edge quick-service with spit-roasted meats. Atmospheric theming.",
        menu_highlights=["Ronto Wrap", "Roasted Ronto Wrap (breakfast)", "Milk (Blue or Green)"],
        url="",
        wait_notes="Moderate lines most of the day. Fastest early morning.",
    ),
    Restaurant(
        id="dl_river_belle",
        name="River Belle Terrace",
        land="dl_frontierland",
        service="quick",
        cuisine="American Southern",
        avg_meal_minutes=20,
        reservations=False,
        popular_dish="Mickey waffle breakfast",
        description="Outdoor terrace with views of the Rivers of America. Great for Fantasmic watching.",
        menu_highlights=["Mickey waffles", "Pulled pork sandwich", "Corn on the cob"],
        url="",
        wait_notes="Very popular during Fantasmic nights — arrive early for outdoor seating.",
    ),
]


# ─── Public accessors ──────────────────────────────────────────────────────────

def disneyland_lands() -> dict:
    return DL_LANDS


def disneyland_attractions() -> list[dict]:
    return [a.to_dict() for a in DL_ATTRACTIONS]


def disneyland_restaurants() -> list[dict]:
    return [r.to_dict() for r in DL_RESTAURANTS]


def disneyland_attraction_by_id(attraction_id: str) -> Optional[Attraction]:
    for a in DL_ATTRACTIONS:
        if a.id == attraction_id:
            return a
    return None
