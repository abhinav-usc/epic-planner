"""
Universal Studios Hollywood catalog.

Attraction data sourced from Universal Studios Hollywood official site,
thrill-data.com, queue-times.com, and TouringPlans (2022-2025).

Note on Express Pass:
  Universal Hollywood uses a single Express Pass (not a two-tier system).
  We model this as ll_type="multi" so the existing LL reduction logic applies.
  Typical Express Pass benefit: ~65% wait reduction (less powerful than WDW LLMP).
"""
from __future__ import annotations

from typing import Optional

from backend.data.attractions_db import Attraction, Restaurant


# ─── Park metadata ─────────────────────────────────────────────────────────────

USH_PARKS = {
    "universal_hollywood": {
        "name": "Universal Studios Hollywood",
        "icon": "🎬",
        "description": "The Entertainment Capital of L.A. Harry Potter, Jurassic World, Minions, and the legendary tram tour.",
        "open_hour": 9,
        "close_hour": 20,
    },
}


# ─── Lands ─────────────────────────────────────────────────────────────────────

USH_LANDS = {
    "uh_wizarding_world":  {"name": "The Wizarding World of Harry Potter", "color": "#7C3AED", "icon": "⚡", "description": "Hogsmeade village, Hogwarts castle, Forbidden Journey, and Flight of the Hippogriff."},
    "uh_lower_lot":        {"name": "Lower Lot",                           "color": "#1F2937", "icon": "🦖", "description": "Jurassic World, Transformers, Revenge of the Mummy. High-density thrill zone."},
    "uh_upper_lot":        {"name": "Upper Lot",                           "color": "#F97316", "icon": "🎬", "description": "Simpsons, Despicable Me, WaterWorld. The main entrance level."},
    "uh_springfield":      {"name": "Springfield U.S.A.",                  "color": "#FBBF24", "icon": "🍩", "description": "Simpsons-themed Springfield with Moe's Tavern, Krusty Burger, and the Simpsons ride."},
    "uh_dreamworks":       {"name": "DreamWorks Theatre",                  "color": "#10B981", "icon": "🐉", "description": "Dragons! The DreamWorks Experience — immersive 4D dragon encounter."},
    "uh_studio_tour":      {"name": "Studio Tour",                         "color": "#6B7280", "icon": "🎥", "description": "Behind-the-scenes tram ride through working Universal back lot. King Kong, Jaws, Fast & Furious."},
}


# ─── Walk times ────────────────────────────────────────────────────────────────
# USH is a two-level park connected by escalators/elevators.
# Upper Lot → Lower Lot: ~8 min (escalators + walking).
# Within levels: 3-6 min.

def _ush_walk(from_land: str, to_land: str) -> int:
    CROSS_LEVEL = {
        ("uh_upper_lot", "uh_lower_lot"), ("uh_lower_lot", "uh_upper_lot"),
        ("uh_upper_lot", "uh_wizarding_world"), ("uh_wizarding_world", "uh_upper_lot"),
        ("uh_springfield", "uh_lower_lot"), ("uh_lower_lot", "uh_springfield"),
        ("uh_springfield", "uh_wizarding_world"), ("uh_wizarding_world", "uh_springfield"),
        ("uh_dreamworks", "uh_lower_lot"), ("uh_lower_lot", "uh_dreamworks"),
        ("uh_studio_tour", "uh_lower_lot"), ("uh_lower_lot", "uh_studio_tour"),
    }
    SAME_LEVEL_UPPER = {"uh_upper_lot", "uh_springfield", "uh_dreamworks", "uh_studio_tour"}
    SAME_LEVEL_LOWER = {"uh_lower_lot", "uh_wizarding_world"}

    if from_land == to_land:
        return 0
    if (from_land, to_land) in CROSS_LEVEL:
        return 8
    if from_land in SAME_LEVEL_UPPER and to_land in SAME_LEVEL_UPPER:
        return 5
    if from_land in SAME_LEVEL_LOWER and to_land in SAME_LEVEL_LOWER:
        return 5
    return 9


USH_WALK_PAIRS = {
    (a, b): _ush_walk(a, b)
    for a in USH_LANDS
    for b in USH_LANDS
}


def universal_hollywood_walk_minutes(from_land: str, to_land: str) -> int:
    return USH_WALK_PAIRS.get((from_land, to_land), 8)


# ─── Attractions ───────────────────────────────────────────────────────────────

USH_ATTRACTIONS: list[Attraction] = [

    # ── The Wizarding World of Harry Potter ───────────────────────────────────
    Attraction(
        id="uh_forbidden_journey",
        name="Harry Potter and the Forbidden Journey",
        land="uh_wizarding_world",
        kind="ride",
        tier=5,
        duration_minutes=5,
        capacity_per_hour=1700,
        has_single_rider=True,
        has_express=True,
        height_inches=48,
        description="KUKA-arm motion ride through Hogwarts castle with Dementors, Quidditch, and the whomping willow.",
    ),
    Attraction(
        id="uh_hippogriff",
        name="Flight of the Hippogriff",
        land="uh_wizarding_world",
        kind="ride",
        tier=3,
        duration_minutes=2,
        capacity_per_hour=1200,
        has_single_rider=False,
        has_express=True,
        height_inches=39,
        description="Outdoor steel coaster looping around Hagrid's hut with views of Hogsmeade.",
    ),

    # ── Lower Lot ─────────────────────────────────────────────────────────────
    Attraction(
        id="uh_jurassic_world",
        name="Jurassic World – The Ride",
        land="uh_lower_lot",
        kind="ride",
        tier=5,
        duration_minutes=6,
        capacity_per_hour=1600,
        has_single_rider=False,
        has_express=True,
        height_inches=42,
        description="River raft ride ending with the massive Mosasaurus drop. Rethemed from the classic Jurassic Park ride.",
    ),
    Attraction(
        id="uh_transformers",
        name="Transformers: The Ride-3D",
        land="uh_lower_lot",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=1800,
        has_single_rider=False,
        has_express=True,
        height_inches=40,
        description="High-tech motion-base ride battling Decepticons. Impressive screen and practical effects combo.",
    ),
    Attraction(
        id="uh_mummy",
        name="Revenge of the Mummy – The Ride",
        land="uh_lower_lot",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1600,
        has_single_rider=False,
        has_express=True,
        height_inches=48,
        description="Indoor roller coaster with sudden launches, backwards sections, and psychological scares.",
    ),

    # ── Upper Lot ─────────────────────────────────────────────────────────────
    Attraction(
        id="uh_despicable_me",
        name="Despicable Me: Minion Mayhem",
        land="uh_upper_lot",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=2200,
        has_single_rider=False,
        has_express=True,
        height_inches=40,
        description="Gru trains you to be a minion in this high-capacity 4D motion simulator.",
    ),

    # ── Springfield ───────────────────────────────────────────────────────────
    Attraction(
        id="uh_simpsons_ride",
        name="The Simpsons Ride",
        land="uh_springfield",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=2000,
        has_single_rider=False,
        has_express=True,
        height_inches=40,
        description="High-capacity dome simulator taking you on a wild ride through Springfield with Sideshow Bob.",
    ),
    Attraction(
        id="uh_fast_furious",
        name="Fast & Furious – Supercharged",
        land="uh_upper_lot",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=3000,
        has_single_rider=False,
        has_express=True,
        description="Tram-based extension of the Studio Tour with screen illusions and vibration effects.",
    ),

    # ── DreamWorks ────────────────────────────────────────────────────────────
    Attraction(
        id="uh_dreamworks_theatre",
        name="DreamWorks Theatre featuring Kung Fu Panda",
        land="uh_dreamworks",
        kind="show",
        tier=3,
        duration_minutes=15,
        capacity_per_hour=None,
        has_express=False,
        showtimes=["10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
                   "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
                   "16:00", "16:30", "17:00"],
        description="Immersive 4D show in a purpose-built theatre. Kung Fu Panda battles a villain in the Spirit Realm.",
    ),

    # ── Studio Tour ───────────────────────────────────────────────────────────
    Attraction(
        id="uh_studio_tour",
        name="Studio Tour",
        land="uh_studio_tour",
        kind="experience",
        tier=4,
        duration_minutes=55,
        capacity_per_hour=3000,
        has_single_rider=False,
        has_express=True,
        description="Iconic tram tour of the working back lot. King Kong 360, Jaws, Norman Bates' house, Fast & Furious.",
    ),

    # ── Shows ─────────────────────────────────────────────────────────────────
    Attraction(
        id="uh_waterworld",
        name="WaterWorld",
        land="uh_upper_lot",
        kind="show",
        tier=3,
        duration_minutes=20,
        capacity_per_hour=None,
        has_express=False,
        showtimes=["11:00", "13:00", "15:00", "17:00", "19:00"],
        description="Live stunt show set in the WaterWorld universe — jet skis, explosions, and a crashing seaplane.",
    ),
    Attraction(
        id="uh_special_effects",
        name="Special Effects Show",
        land="uh_upper_lot",
        kind="show",
        tier=2,
        duration_minutes=25,
        capacity_per_hour=None,
        has_express=False,
        showtimes=["10:30", "12:30", "14:30", "16:30"],
        description="Behind-the-scenes of Hollywood movie magic — sound effects, props, and film tricks.",
    ),
]

# ── Express Pass types (Universal doesn't have a two-tier system) ───────────────
# Model all Express Pass eligible rides as "multi" — same as LLMP.
_USH_EXPRESS_ELIGIBLE = {
    "uh_forbidden_journey", "uh_hippogriff", "uh_jurassic_world",
    "uh_transformers", "uh_mummy", "uh_despicable_me",
    "uh_simpsons_ride", "uh_fast_furious", "uh_studio_tour",
}
for _a in USH_ATTRACTIONS:
    _a.ll_type = "multi" if _a.id in _USH_EXPRESS_ELIGIBLE else None


# ─── Restaurants ───────────────────────────────────────────────────────────────

USH_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        id="uh_three_broomsticks",
        name="Three Broomsticks",
        land="uh_wizarding_world",
        service="quick",
        cuisine="British / Wizarding World",
        avg_meal_minutes=25,
        reservations=False,
        popular_dish="Great Feast (turkey leg, chicken, etc.)",
        description="Main dining hall in the Wizarding World with HP-themed fare. Beautiful hall interior.",
        menu_highlights=["Great Feast", "Butterbeer (frozen/cold)", "Pumpkin juice", "Shepherd's pie"],
        url="",
        wait_notes="Busiest 12–2 pm. Go at 11 am or after 2 pm.",
    ),
    Restaurant(
        id="uh_krusty_burger",
        name="Krusty Burger",
        land="uh_springfield",
        service="quick",
        cuisine="American burgers",
        avg_meal_minutes=15,
        reservations=False,
        popular_dish="The Clogger (double burger)",
        description="Simpsons-themed burger joint. Reasonable prices, good atmosphere.",
        menu_highlights=["Clogger burger", "Cletus' Chicken Shack (adjacent)", "Duff Beer"],
        url="",
        wait_notes="Moderate lines at lunch. Fast service.",
    ),
    Restaurant(
        id="uh_mels_diner",
        name="Mel's Diner",
        land="uh_upper_lot",
        service="quick",
        cuisine="American diner",
        avg_meal_minutes=20,
        reservations=False,
        popular_dish="Burgers and shakes",
        description="1950s-themed diner at the main entrance. Good for classic American fare.",
        menu_highlights=["Classic burger", "Milkshakes", "Hot dogs"],
        url="",
        wait_notes="Busy at lunch. Try for breakfast or late afternoon.",
    ),
    Restaurant(
        id="uh_jurassic_cantina",
        name="Jurassic Café",
        land="uh_lower_lot",
        service="quick",
        cuisine="Mexican / Tex-Mex",
        avg_meal_minutes=20,
        reservations=False,
        popular_dish="Dinosaur nachos",
        description="Themed quick-service adjacent to Jurassic World in the Lower Lot.",
        menu_highlights=["Nachos", "Burrito bowl", "Lemonade"],
        url="",
        wait_notes="Less crowded than Upper Lot options. Good midday choice.",
    ),
]


# ─── Public accessors ──────────────────────────────────────────────────────────

def universal_hollywood_lands() -> dict:
    return USH_LANDS


def universal_hollywood_attractions() -> list[dict]:
    return [a.to_dict() for a in USH_ATTRACTIONS]


def universal_hollywood_restaurants() -> list[dict]:
    return [r.to_dict() for r in USH_RESTAURANTS]


def universal_hollywood_attraction_by_id(attraction_id: str) -> Optional[Attraction]:
    for a in USH_ATTRACTIONS:
        if a.id == attraction_id:
            return a
    return None
