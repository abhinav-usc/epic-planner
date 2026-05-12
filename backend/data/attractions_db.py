"""
Epic Universe attraction catalog.

Verified May 2026 from: Wikipedia, queue-times.com (park ID 334),
orlando-themeparks.com, orlandoinformer.com, discoveruniversal.com,
Frommer's, WDWNT, BlogMickey, Inside the Magic.

Park opened May 22, 2025.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# ─── Lands ────────────────────────────────────────────────────────────────────

LANDS = {
    "celestial_park": {
        "name": "Celestial Park",
        "color": "#4F46E5",  # indigo
        "icon": "🌌",
        "description": "Central hub. Gardens, fountains, and the Stardust Racers coaster.",
    },
    "super_nintendo_world": {
        "name": "Super Nintendo World",
        "color": "#DC2626",  # red
        "icon": "🎮",
        "description": "Interactive Mushroom Kingdom with Power-Up Bands.",
    },
    "ministry_of_magic": {
        "name": "The Wizarding World of Harry Potter: Ministry of Magic",
        "color": "#7C3AED",  # purple
        "icon": "⚡",
        "description": "1920s Paris and the British Ministry of Magic.",
    },
    "isle_of_berk": {
        "name": "How to Train Your Dragon: Isle of Berk",
        "color": "#059669",  # emerald
        "icon": "🐉",
        "description": "Living Viking village with flying dragons.",
    },
    "dark_universe": {
        "name": "Dark Universe",
        "color": "#9333EA",  # violet-dark
        "icon": "🧛",
        "description": "Darkmoor Village. Universal's classic monsters. Music by Danny Elfman.",
    },
}


# ─── Attraction model ─────────────────────────────────────────────────────────

@dataclass
class Attraction:
    id: str
    name: str
    land: str
    kind: str  # "ride" | "show" | "restaurant" | "experience"
    tier: int  # 1=A-ticket … 5=E-ticket. Restaurants/shows = priority weight.
    duration_minutes: int  # ride duration or show duration or typical meal time
    capacity_per_hour: Optional[int] = None  # riders/hr (rides only)
    has_single_rider: bool = False
    has_express: bool = True
    height_inches: Optional[int] = None
    queue_times_id: Optional[int] = None  # queue-times.com ride id
    showtimes: Optional[list[str]] = None  # "HH:MM" strings for fixed-time shows
    description: str = ""
    walking_thrill: bool = False  # can be done while walking past (atmospheric)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ─── Catalog ──────────────────────────────────────────────────────────────────

ATTRACTIONS: list[Attraction] = [
    # ── Celestial Park ────────────────────────────────────────────────────────
    Attraction(
        id="stardust_racers",
        name="Stardust Racers",
        land="celestial_park",
        kind="ride",
        tier=5,
        duration_minutes=2,
        capacity_per_hour=1400,
        has_single_rider=False,
        has_express=True,
        height_inches=54,
        description="Dual-launched racing coaster by Mack Rides. Two trains race side-by-side.",
    ),
    Attraction(
        id="constellation_carousel",
        name="Constellation Carousel",
        land="celestial_park",
        kind="ride",
        tier=2,
        duration_minutes=3,
        capacity_per_hour=900,
        has_express=False,
        description="Themed carousel with constellation creatures.",
    ),
    Attraction(
        id="astronomica",
        name="Astronomica",
        land="celestial_park",
        kind="experience",
        tier=1,
        duration_minutes=20,
        has_express=False,
        description="Children's interactive splash pad and play area.",
    ),

    # ── Super Nintendo World ──────────────────────────────────────────────────
    Attraction(
        id="mario_kart",
        name="Mario Kart: Bowser's Challenge",
        land="super_nintendo_world",
        kind="ride",
        tier=5,
        duration_minutes=5,
        capacity_per_hour=1200,
        has_single_rider=True,
        height_inches=40,
        queue_times_id=14683,
        description="AR dark ride. Throw shells at Team Bowser as you race.",
    ),
    Attraction(
        id="mine_cart_madness",
        name="Mine-Cart Madness",
        land="super_nintendo_world",
        kind="ride",
        tier=5,
        duration_minutes=3,
        capacity_per_hour=1100,
        height_inches=42,
        queue_times_id=14686,
        description="Donkey Kong-themed boom coaster by Setpoint. Carts appear to leap broken tracks.",
    ),
    Attraction(
        id="yoshis_adventure",
        name="Yoshi's Adventure",
        land="super_nintendo_world",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=1400,
        description="Family omnimover ride searching for eggs.",
    ),
    Attraction(
        id="bowser_jr_showdown",
        name="Bowser Jr. Shadow Showdown",
        land="super_nintendo_world",
        kind="experience",
        tier=2,
        duration_minutes=10,
        queue_times_id=14682,
        description="Interactive Power-Up Band challenge against Bowser Jr.",
    ),

    # ── Ministry of Magic ─────────────────────────────────────────────────────
    Attraction(
        id="battle_at_ministry",
        name="Harry Potter and the Battle at the Ministry",
        land="ministry_of_magic",
        kind="ride",
        tier=5,
        duration_minutes=7,
        capacity_per_hour=1800,
        has_single_rider=True,
        height_inches=42,
        description="Flying-theater dark ride. Trial in the Ministry courtroom goes wrong.",
    ),
    Attraction(
        id="le_cirque_arcanus",
        name="Le Cirque Arcanus",
        land="ministry_of_magic",
        kind="show",
        tier=4,
        duration_minutes=20,
        has_express=False,
        showtimes=[
            "11:45", "12:35", "13:25", "14:15", "15:15", "16:05",
            "16:55", "17:45", "18:35", "19:25", "20:15", "21:05",
        ],
        description="Indoor live theater. Ringmaster Skender and fantastic beasts. ~20 min including pre-show.",
    ),

    # ── Isle of Berk ──────────────────────────────────────────────────────────
    Attraction(
        id="hiccups_wing_gliders",
        name="Hiccup's Wing Gliders",
        land="isle_of_berk",
        kind="ride",
        tier=4,
        duration_minutes=2,
        capacity_per_hour=1200,
        height_inches=40,
        description="Launched family coaster by Intamin. Soar with Toothless.",
    ),
    Attraction(
        id="dragon_racers_rally",
        name="Dragon Racer's Rally",
        land="isle_of_berk",
        kind="ride",
        tier=3,
        duration_minutes=2,
        capacity_per_hour=600,
        height_inches=48,
        description="Sky Fly flat ride by Gerstlauer. Pilot your own dragon glider.",
    ),
    Attraction(
        id="fyre_drill",
        name="Fyre Drill",
        land="isle_of_berk",
        kind="ride",
        tier=2,
        duration_minutes=4,
        capacity_per_hour=900,
        description="Interactive boat ride by Mack. You will get wet.",
    ),
    Attraction(
        id="untrainable_dragon",
        name="The Untrainable Dragon",
        land="isle_of_berk",
        kind="show",
        tier=4,
        duration_minutes=25,
        has_express=False,
        showtimes=[
            "12:10", "13:00", "13:50", "14:40", "15:30",
            "16:40", "17:30", "18:20", "19:10", "20:00",
        ],
        description="Musical stage show with flying Toothless (27 ft wingspan) and live actors.",
    ),
    Attraction(
        id="meet_toothless",
        name="Meet Toothless and Friends",
        land="isle_of_berk",
        kind="experience",
        tier=2,
        duration_minutes=10,
        queue_times_id=14685,
        description="Animatronic Toothless plus Hiccup and Astrid character meet.",
    ),
    Attraction(
        id="viking_training_camp",
        name="Viking Training Camp",
        land="isle_of_berk",
        kind="experience",
        tier=1,
        duration_minutes=20,
        has_express=False,
        description="Children's playground with Viking obstacles.",
    ),

    # ── Dark Universe ─────────────────────────────────────────────────────────
    Attraction(
        id="monsters_unchained",
        name="Monsters Unchained: The Frankenstein Experiment",
        land="dark_universe",
        kind="ride",
        tier=5,
        duration_minutes=4,
        capacity_per_hour=1500,
        has_single_rider=True,
        height_inches=48,
        description="KUKA-arm dark ride. Dr. Victoria Frankenstein's experiment goes wrong.",
    ),
    Attraction(
        id="curse_of_werewolf",
        name="Curse of the Werewolf",
        land="dark_universe",
        kind="ride",
        tier=4,
        duration_minutes=2,
        capacity_per_hour=900,
        has_single_rider=True,
        height_inches=48,
        description="Launched spinning coaster by Mack Rides.",
    ),
    Attraction(
        id="darkmoor_monster_makeup",
        name="Darkmoor Monster Makeup Experience",
        land="dark_universe",
        kind="experience",
        tier=2,
        duration_minutes=30,
        has_express=False,
        description="Become a classic monster via professional makeup.",
    ),
]


# ─── Restaurants ──────────────────────────────────────────────────────────────

@dataclass
class Restaurant:
    id: str
    name: str
    land: str
    service: str  # "quick" | "full" | "bar" | "snack" | "cart"
    cuisine: str
    avg_meal_minutes: int
    reservations: bool = False
    popular_dish: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


RESTAURANTS: list[Restaurant] = [
    # Celestial Park
    Restaurant("the_atlantic", "The Atlantic", "celestial_park", "full", "Seafood", 75, True,
               "Whole roasted branzino"),
    Restaurant("blue_dragon", "The Blue Dragon Pan-Asian Restaurant", "celestial_park", "full", "Pan-Asian", 70, True,
               "Crispy duck bao"),
    Restaurant("pizza_moon", "Pizza Moon", "celestial_park", "quick", "Pizza", 30, False, "Honey-pepperoni"),
    Restaurant("comet_dogs", "Comet Dogs", "celestial_park", "quick", "Hot dogs", 20, False, "The Comet Dog"),
    Restaurant("frosty_moon", "Frosty Moon", "celestial_park", "quick", "Ice cream", 15, False, "Moon Pie sundae"),
    Restaurant("meteor_astropub", "Meteor Astropub", "celestial_park", "quick", "Gastropub", 40, False, "Smashburger"),
    Restaurant("celestiki", "Celestiki", "celestial_park", "quick", "Tiki/tropical", 30, False, "Volcano Bowl"),
    Restaurant("star_sui_bao", "Star Sui Bao", "celestial_park", "quick", "Bao buns", 20, False, "BBQ pork bao"),
    Restaurant("oak_star_tavern", "The Oak & Star Tavern", "celestial_park", "quick", "American tavern", 45, False,
               "Cosmic chicken pot pie"),
    Restaurant("bar_zenith", "Bar Zenith", "celestial_park", "bar", "Cocktails", 30, False, "Galaxy old fashioned"),
    Restaurant("plastered_owl", "The Plastered Owl", "celestial_park", "bar", "Beer + dueling guitars", 60, False,
               "Owl ale"),
    Restaurant("lens_flare", "Lens Flare", "celestial_park", "bar", "Cocktails", 30, False, "Solar flare margarita"),
    Restaurant("moonship_chocolates", "Moonship Chocolates & Celestial Sweets", "celestial_park", "snack",
               "Chocolate/desserts", 10, False, "Galaxy bonbons"),
    Restaurant("north_star_wintry", "North Star Wintry Wonders", "celestial_park", "snack", "Frozen treats", 10, False,
               "Stardust soft serve"),
    Restaurant("starbucks", "Starbucks Coffee", "celestial_park", "quick", "Coffee", 10, False, ""),

    # Super Nintendo World
    Restaurant("toadstool_cafe", "Toadstool Cafe", "super_nintendo_world", "quick", "Mario-themed American", 40, True,
               "Mushroom Burger"),
    Restaurant("yoshis_snack_island", "Yoshi's Snack Island", "super_nintendo_world", "snack", "Fruity snacks", 10,
               False, "Yoshi fruit cup"),
    Restaurant("bubbly_barrel", "The Bubbly Barrel", "super_nintendo_world", "quick", "Drinks", 15, False,
               "Power-Up smoothie"),
    Restaurant("turbo_boost_treats", "Turbo-Boost Treats", "super_nintendo_world", "snack", "Energy snacks", 10, False,
               "Super Star popcorn"),

    # Ministry of Magic
    Restaurant("cafe_la_sirene", "Café L'air De La Sirène", "ministry_of_magic", "quick", "French patisserie", 35,
               False, "Croque-mer"),
    Restaurant("le_gobelet_noir", "Le Gobelet Noir", "ministry_of_magic", "quick", "French bistro", 45, False,
               "Cauldron cassoulet"),
    Restaurant("bar_moonshine", "Bar Moonshine", "ministry_of_magic", "bar", "Wizarding cocktails", 25, False,
               "Moonshine martini"),
    Restaurant("cosme_acajor", "Cosme Acajor Baguettes Magique", "ministry_of_magic", "quick", "Bakery", 15, False,
               "Magique baguette"),
    Restaurant("biraubeurre_cart", "Bièraubeurre Cart", "ministry_of_magic", "cart", "Butterbeer", 5, False,
               "Butterbeer (cold)"),

    # Isle of Berk
    Restaurant("mead_hall", "Mead Hall", "isle_of_berk", "quick", "Viking feast", 50, False, "Mead Hall platter"),
    Restaurant("spit_fyre_grill", "Spit Fyre Grill", "isle_of_berk", "quick", "BBQ/grill", 35, False,
               "Spit-roasted chicken"),
    Restaurant("hooligans_grog", "Hooligan's Grog & Gruel", "isle_of_berk", "quick", "Stew + ale", 40, False,
               "Hooligan stew"),

    # Dark Universe
    Restaurant("das_stakehaus", "Das Stakehaus", "dark_universe", "quick", "Vampire steakhouse", 45, False,
               "Wooden-staked steak"),
    Restaurant("burning_blade_tavern", "The Burning Blade Tavern", "dark_universe", "quick", "Gothic pub", 40, False,
               "Burning Blade burger"),
    Restaurant("de_laceys_cottage", "De Lacey's Cottage", "dark_universe", "quick", "Cottage fare", 35, False,
               "Cottage pie"),
]


# ─── Lookups ──────────────────────────────────────────────────────────────────

def all_attractions() -> list[dict]:
    return [a.to_dict() for a in ATTRACTIONS]


def all_restaurants() -> list[dict]:
    return [r.to_dict() for r in RESTAURANTS]


def attraction_by_id(attraction_id: str) -> Optional[Attraction]:
    for a in ATTRACTIONS:
        if a.id == attraction_id:
            return a
    return None


def restaurant_by_id(restaurant_id: str) -> Optional[Restaurant]:
    for r in RESTAURANTS:
        if r.id == restaurant_id:
            return r
    return None


def attractions_by_land(land_id: str) -> list[Attraction]:
    return [a for a in ATTRACTIONS if a.land == land_id]


# ─── Walk-time matrix ─────────────────────────────────────────────────────────
# Approximate minutes to walk between lands. Celestial Park is the hub, so all
# inter-land trips pass through it. Numbers come from Universal's published map
# (Celestial Park is ~12 acres; each themed land is across a portal ~3-5 min
# from the hub).

WALK_TIMES: dict[tuple[str, str], int] = {}
LAND_TO_HUB = {
    "celestial_park": 0,
    "super_nintendo_world": 5,
    "ministry_of_magic": 5,
    "isle_of_berk": 6,
    "dark_universe": 5,
}
for a, _t_a in LAND_TO_HUB.items():
    for b, _t_b in LAND_TO_HUB.items():
        if a == b:
            WALK_TIMES[(a, b)] = 0
        elif a == "celestial_park" or b == "celestial_park":
            WALK_TIMES[(a, b)] = LAND_TO_HUB[a] + LAND_TO_HUB[b]
        else:
            # Cross-land trips pass through the hub (Celestial Park)
            WALK_TIMES[(a, b)] = LAND_TO_HUB[a] + LAND_TO_HUB[b]


def walk_minutes(from_land: str, to_land: str) -> int:
    return WALK_TIMES.get((from_land, to_land), 8)
