"""
Disney World park catalogs.

Four parks: Magic Kingdom, EPCOT, Hollywood Studios, Animal Kingdom.
Attraction data sourced from official Disney World website, TouringPlans,
queue-times.com, and Touring Plans wait time data (2024-2025).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

from backend.data.attractions_db import Attraction, Restaurant


# ─── Park metadata ─────────────────────────────────────────────────────────────

DISNEY_PARKS = {
    "magic_kingdom": {
        "name": "Magic Kingdom",
        "icon": "🏰",
        "description": "The Most Magical Place on Earth. Cinderella Castle, classic rides, and Disney Characters.",
        "open_hour": 9,
        "close_hour": 22,
    },
    "epcot": {
        "name": "EPCOT",
        "icon": "🌍",
        "description": "Future World meets World Showcase. Innovation, culture, food, and immersive storytelling.",
        "open_hour": 9,
        "close_hour": 21,
    },
    "hollywood_studios": {
        "name": "Hollywood Studios",
        "icon": "🎬",
        "description": "Star Wars, Toy Story, Tower of Terror — Hollywood thrills and cinematic magic.",
        "open_hour": 9,
        "close_hour": 21,
    },
    "animal_kingdom": {
        "name": "Animal Kingdom",
        "icon": "🌿",
        "description": "Pandora, Africa, Asia — live animals and immersive adventure.",
        "open_hour": 8,
        "close_hour": 18,
    },
}


# ─── Lands ─────────────────────────────────────────────────────────────────────

MK_LANDS = {
    "mk_main_street":   {"name": "Main Street, U.S.A.", "color": "#D97706", "icon": "🏛️",  "description": "Turn-of-the-century America, shops, and the Town Square."},
    "mk_fantasyland":   {"name": "Fantasyland",          "color": "#EC4899", "icon": "🏰", "description": "Classic fairy-tale rides including Peter Pan and Seven Dwarfs Mine Train."},
    "mk_tomorrowland":  {"name": "Tomorrowland",         "color": "#06B6D4", "icon": "🚀", "description": "Sci-fi future with TRON Lightcycle/Run and Space Mountain."},
    "mk_adventureland": {"name": "Adventureland",        "color": "#16A34A", "icon": "🗺️", "description": "Pirates, jungle, and tropical adventure."},
    "mk_liberty_square":{"name": "Liberty Square",       "color": "#92400E", "icon": "🔔", "description": "Colonial America, the Haunted Mansion, and the Hall of Presidents."},
    "mk_frontierland":  {"name": "Frontierland",         "color": "#B45309", "icon": "🤠", "description": "Wild West with Big Thunder Mountain Railroad and Tiana's Bayou Adventure."},
}

EPCOT_LANDS = {
    "ep_world_discovery":   {"name": "World Discovery",   "color": "#7C3AED", "icon": "🔬", "description": "Science and innovation: Guardians of the Galaxy, Test Track, Mission: SPACE."},
    "ep_world_nature":      {"name": "World Nature",      "color": "#059669", "icon": "🌊", "description": "Soarin', The Seas with Nemo, Living with the Land."},
    "ep_world_celebration": {"name": "World Celebration", "color": "#2563EB", "icon": "✨", "description": "Spaceship Earth, Journey Into Imagination, and EPCOT's signature icon."},
    "ep_world_showcase":    {"name": "World Showcase",    "color": "#DC2626", "icon": "🌐", "description": "11 international pavilions around World Showcase Lagoon: Frozen Ever After, Remy's Ratatouille Adventure."},
}

HS_LANDS = {
    "hs_galaxys_edge":         {"name": "Star Wars: Galaxy's Edge",   "color": "#1F2937", "icon": "⭐", "description": "Batuu: Rise of the Resistance and Millennium Falcon: Smugglers Run."},
    "hs_toy_story_land":       {"name": "Toy Story Land",             "color": "#FBBF24", "icon": "🧸", "description": "Shrink down to toy size: Slinky Dog Dash, Toy Story Mania!, Alien Swirling Saucers."},
    "hs_sunset_boulevard":     {"name": "Sunset Boulevard",           "color": "#F97316", "icon": "🎸", "description": "Tower of Terror, Rock 'n' Roller Coaster, and Beauty and the Beast."},
    "hs_echo_lake":            {"name": "Echo Lake",                  "color": "#06B6D4", "icon": "🎭", "description": "Indiana Jones Stunt Spectacular, Star Tours."},
    "hs_grand_avenue":         {"name": "Grand Avenue",               "color": "#6B7280", "icon": "🏙️", "description": "Muppet*Vision 3D, Baseline Tap House."},
    "hs_animation_courtyard":  {"name": "Animation Courtyard",        "color": "#8B5CF6", "icon": "🎨", "description": "Mickey & Minnie's Runaway Railway, Disney Junior Dance Party."},
    "hs_hollywood_boulevard":  {"name": "Hollywood Boulevard",        "color": "#D97706", "icon": "🎬", "description": "Main entrance boulevard, The Great Movie Ride site, shops and dining."},
}

AK_LANDS = {
    "ak_pandora":        {"name": "Pandora – The World of Avatar", "color": "#10B981", "icon": "🪐", "description": "Avatar Flight of Passage, Na'vi River Journey — bioluminescent wonder."},
    "ak_africa":         {"name": "Africa",                        "color": "#D97706", "icon": "🦁", "description": "Kilimanjaro Safaris, Festival of the Lion King, Gorilla Falls."},
    "ak_asia":           {"name": "Asia",                          "color": "#EF4444", "icon": "🐯", "description": "Expedition Everest, Kali River Rapids, Maharajah Jungle Trek."},
    "ak_discovery_island":{"name": "Discovery Island",             "color": "#8B5CF6", "icon": "🌳", "description": "The Tree of Life, It's Tough to Be a Bug!, central hub."},
    "ak_dinoland":       {"name": "DinoLand U.S.A.",               "color": "#6B7280", "icon": "🦕", "description": "DINOSAUR, TriceraTop Spin, Finding Nemo show."},
}

ALL_DISNEY_LANDS: dict[str, dict] = {
    **MK_LANDS, **EPCOT_LANDS, **HS_LANDS, **AK_LANDS,
}


# ─── Walk times ────────────────────────────────────────────────────────────────

def _hub_spoke_walks(hub: str, spokes: dict[str, int]) -> dict[tuple[str, str], int]:
    """Build walk-time matrix from a hub with spoke distances."""
    times: dict[tuple[str, str], int] = {}
    for a, t_a in spokes.items():
        for b, t_b in spokes.items():
            if a == b:
                times[(a, b)] = 0
            elif a == hub or b == hub:
                times[(a, b)] = t_a + t_b
            else:
                times[(a, b)] = t_a + t_b
    return times


MK_HUB = "mk_main_street"
MK_WALK = _hub_spoke_walks(MK_HUB, {
    "mk_main_street": 0,
    "mk_fantasyland": 6,
    "mk_tomorrowland": 5,
    "mk_adventureland": 5,
    "mk_liberty_square": 6,
    "mk_frontierland": 7,
})

# EPCOT: Discovery side (hub) + World Showcase loop
# Walking from World Discovery to far end of World Showcase ≈ 20 min
EPCOT_HUB = "ep_world_celebration"
EPCOT_WALK = _hub_spoke_walks(EPCOT_HUB, {
    "ep_world_celebration": 0,
    "ep_world_discovery": 5,
    "ep_world_nature": 5,
    "ep_world_showcase": 10,
})

HS_HUB = "hs_hollywood_boulevard"
HS_WALK = _hub_spoke_walks(HS_HUB, {
    "hs_hollywood_boulevard": 0,
    "hs_galaxys_edge": 8,
    "hs_toy_story_land": 6,
    "hs_sunset_boulevard": 5,
    "hs_echo_lake": 4,
    "hs_grand_avenue": 5,
    "hs_animation_courtyard": 5,
})

AK_HUB = "ak_discovery_island"
AK_WALK = _hub_spoke_walks(AK_HUB, {
    "ak_discovery_island": 0,
    "ak_pandora": 7,
    "ak_africa": 6,
    "ak_asia": 7,
    "ak_dinoland": 6,
})

DISNEY_WALK_TABLES: dict[str, dict[tuple[str, str], int]] = {
    "magic_kingdom": MK_WALK,
    "epcot": EPCOT_WALK,
    "hollywood_studios": HS_WALK,
    "animal_kingdom": AK_WALK,
}


def disney_walk_minutes(park_id: str, from_land: str, to_land: str) -> int:
    table = DISNEY_WALK_TABLES.get(park_id, {})
    return table.get((from_land, to_land), 8)


# ─── Attractions ───────────────────────────────────────────────────────────────

MK_ATTRACTIONS: list[Attraction] = [
    # ── Fantasyland ───────────────────────────────────────────────────────────
    Attraction(
        id="mk_seven_dwarfs",
        name="Seven Dwarfs Mine Train",
        land="mk_fantasyland",
        kind="ride",
        tier=5,
        duration_minutes=4,
        capacity_per_hour=1100,
        has_single_rider=False,
        has_express=True,
        height_inches=38,
        description="Family-style mine coaster with swinging cars and beloved dwarfs scenes inside.",
    ),
    Attraction(
        id="mk_peter_pan",
        name="Peter Pan's Flight",
        land="mk_fantasyland",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1200,
        has_express=True,
        description="Iconic flying-ship dark ride over Neverland. Perennially long waits for a slow loader.",
    ),
    Attraction(
        id="mk_little_mermaid",
        name="Under the Sea – Journey of The Little Mermaid",
        land="mk_fantasyland",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=2000,
        has_express=True,
        description="Clamshell omnimover through Ariel's undersea world.",
    ),
    Attraction(
        id="mk_winnie_pooh",
        name="The Many Adventures of Winnie the Pooh",
        land="mk_fantasyland",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=1600,
        has_express=True,
        description="Gentle dark ride through the Hundred Acre Wood.",
    ),
    Attraction(
        id="mk_small_world",
        name="it's a small world",
        land="mk_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=10,
        capacity_per_hour=2800,
        has_express=False,
        description="Gentle boat ride celebrating children of the world with a catchy theme song.",
    ),
    Attraction(
        id="mk_dumbo",
        name="Dumbo the Flying Elephant",
        land="mk_fantasyland",
        kind="ride",
        tier=2,
        duration_minutes=2,
        capacity_per_hour=900,
        has_express=True,
        description="Twin-spinner with interactive queue playground. Classic for young children.",
    ),
    Attraction(
        id="mk_enchanted_tales",
        name="Enchanted Tales with Belle",
        land="mk_fantasyland",
        kind="experience",
        tier=3,
        duration_minutes=20,
        capacity_per_hour=600,
        has_express=True,
        description="Interactive storytelling experience where guests audition to act out Beauty and the Beast.",
    ),
    Attraction(
        id="mk_philharmagic",
        name="Mickey's PhilharMagic",
        land="mk_fantasyland",
        kind="show",
        tier=3,
        duration_minutes=12,
        capacity_per_hour=2400,
        has_express=True,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30", "17:00", "17:30", "18:00", "18:30",
        ],
        description="4D concert film starring Donald Duck. Wafts of smells and water effects.",
    ),
    Attraction(
        id="mk_princess_hall",
        name="Princess Fairytale Hall",
        land="mk_fantasyland",
        kind="experience",
        tier=2,
        duration_minutes=15,
        has_express=True,
        description="Meet Disney Princesses (Cinderella, Elena, Rapunzel, or Tiana) for photos and autographs.",
    ),

    # ── Tomorrowland ─────────────────────────────────────────────────────────
    Attraction(
        id="mk_tron",
        name="TRON Lightcycle / Run",
        land="mk_tomorrowland",
        kind="ride",
        tier=5,
        duration_minutes=3,
        capacity_per_hour=1800,
        has_single_rider=False,
        has_express=True,
        height_inches=48,
        description="Motorcycle-style launched coaster under a sweeping canopy. Fastest coaster at any Disney park.",
    ),
    Attraction(
        id="mk_space_mountain",
        name="Space Mountain",
        land="mk_tomorrowland",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1800,
        has_express=True,
        height_inches=44,
        description="Classic indoor roller coaster through simulated outer space. Remains a Disney icon.",
    ),
    Attraction(
        id="mk_buzz_lightyear",
        name="Buzz Lightyear's Space Ranger Spin",
        land="mk_tomorrowland",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=1600,
        has_express=True,
        description="Interactive dark ride. Shoot targets to earn points and save the universe.",
    ),
    Attraction(
        id="mk_laugh_floor",
        name="Monsters, Inc. Laugh Floor",
        land="mk_tomorrowland",
        kind="show",
        tier=2,
        duration_minutes=20,
        has_express=True,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30", "17:00",
        ],
        description="Live interactive comedy show with audience participation and projected monster characters.",
    ),

    # ── Adventureland ─────────────────────────────────────────────────────────
    Attraction(
        id="mk_pirates",
        name="Pirates of the Caribbean",
        land="mk_adventureland",
        kind="ride",
        tier=3,
        duration_minutes=16,
        capacity_per_hour=3400,
        has_express=True,
        description="Classic boat ride through swashbuckling Caribbean pirate scenes. A Disney original.",
    ),
    Attraction(
        id="mk_jungle_cruise",
        name="Jungle Cruise",
        land="mk_adventureland",
        kind="ride",
        tier=3,
        duration_minutes=10,
        capacity_per_hour=2000,
        has_express=True,
        description="Boat tour of the exotic rivers of the world with animatronic animals and famously bad skipper puns.",
    ),
    Attraction(
        id="mk_magic_carpets",
        name="Magic Carpets of Aladdin",
        land="mk_adventureland",
        kind="ride",
        tier=2,
        duration_minutes=2,
        capacity_per_hour=900,
        has_express=True,
        description="Flying carpet spinner with Aladdin theming. Short waits, great for young children.",
    ),
    Attraction(
        id="mk_tiki_room",
        name="Walt Disney's Enchanted Tiki Room",
        land="mk_adventureland",
        kind="show",
        tier=2,
        duration_minutes=13,
        has_express=False,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30", "17:00", "17:30",
        ],
        description="Original 1963 Audio-Animatronic show. Tropical birds perform 'In the Tiki, Tiki, Tiki Room.'",
    ),

    # ── Liberty Square ────────────────────────────────────────────────────────
    Attraction(
        id="mk_haunted_mansion",
        name="Haunted Mansion",
        land="mk_liberty_square",
        kind="ride",
        tier=4,
        duration_minutes=9,
        capacity_per_hour=2600,
        has_express=True,
        description="Iconic Doom Buggy tour through a haunted manor. 999 happy haunts.",
    ),
    Attraction(
        id="mk_hall_presidents",
        name="Hall of Presidents",
        land="mk_liberty_square",
        kind="show",
        tier=2,
        duration_minutes=22,
        has_express=False,
        showtimes=[
            "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
        ],
        description="Audio-Animatronic tribute to all U.S. Presidents with narrated film.",
    ),

    # ── Frontierland ──────────────────────────────────────────────────────────
    Attraction(
        id="mk_big_thunder",
        name="Big Thunder Mountain Railroad",
        land="mk_frontierland",
        kind="ride",
        tier=4,
        duration_minutes=4,
        capacity_per_hour=2600,
        has_express=True,
        height_inches=40,
        description="The wildest ride in the wilderness! Runaway mine train coaster through a haunted mesa.",
    ),
    Attraction(
        id="mk_tianas_bayou",
        name="Tiana's Bayou Adventure",
        land="mk_frontierland",
        kind="ride",
        tier=5,
        duration_minutes=10,
        capacity_per_hour=1800,
        has_express=True,
        height_inches=40,
        description="Flume ride through the Louisiana bayou featuring Tiana's big drop finale. Replaced Splash Mountain.",
    ),
    Attraction(
        id="mk_country_bears",
        name="Country Bear Jamboree",
        land="mk_frontierland",
        kind="show",
        tier=2,
        duration_minutes=16,
        has_express=False,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00",
        ],
        description="Classic Audio-Animatronic variety show featuring the Country Bear musicians.",
    ),
]

EPCOT_ATTRACTIONS: list[Attraction] = [
    # ── World Discovery ───────────────────────────────────────────────────────
    Attraction(
        id="ep_guardians",
        name="Guardians of the Galaxy: Cosmic Rewind",
        land="ep_world_discovery",
        kind="ride",
        tier=5,
        duration_minutes=4,
        capacity_per_hour=2000,
        has_express=True,
        height_inches=42,
        description="World's first reverse-launch indoor coaster. Guardians of the Galaxy-themed chase through space.",
    ),
    Attraction(
        id="ep_test_track",
        name="Test Track",
        land="ep_world_discovery",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=1600,
        has_single_rider=True,
        has_express=True,
        height_inches=40,
        description="Design a virtual concept car, then test it at highway speeds. SimCar by Chevrolet.",
    ),
    Attraction(
        id="ep_mission_space",
        name="Mission: SPACE (Orange – Intense)",
        land="ep_world_discovery",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=1400,
        has_express=True,
        height_inches=44,
        description="Centrifuge-based astronaut training sim. Orange mission: Mars landing with G-forces.",
    ),

    # ── World Nature ──────────────────────────────────────────────────────────
    Attraction(
        id="ep_soarin",
        name="Soarin' Around the World",
        land="ep_world_nature",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=2400,
        has_express=True,
        height_inches=40,
        description="Hang-glider simulator soaring over world landmarks. Beloved for its scent and wide-angle screen.",
    ),
    Attraction(
        id="ep_living_land",
        name="Living with the Land",
        land="ep_world_nature",
        kind="ride",
        tier=2,
        duration_minutes=15,
        capacity_per_hour=2400,
        has_express=True,
        description="Greenhouse boat tour showing sustainable agriculture research inside EPCOT.",
    ),
    Attraction(
        id="ep_nemo_seas",
        name="The Seas with Nemo & Friends",
        land="ep_world_nature",
        kind="ride",
        tier=2,
        duration_minutes=5,
        capacity_per_hour=2700,
        has_express=True,
        description="Clamshell ride through an aquarium and animated Nemo/friends underwater scenes.",
    ),
    Attraction(
        id="ep_turtle_talk",
        name="Turtle Talk with Crush",
        land="ep_world_nature",
        kind="show",
        tier=3,
        duration_minutes=18,
        has_express=True,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30", "17:00",
        ],
        description="Live interactive digital show where Crush the sea turtle chats with the audience.",
    ),

    # ── World Celebration ─────────────────────────────────────────────────────
    Attraction(
        id="ep_spaceship_earth",
        name="Spaceship Earth",
        land="ep_world_celebration",
        kind="ride",
        tier=2,
        duration_minutes=15,
        capacity_per_hour=2800,
        has_express=True,
        description="Iconic slow omnimover ride through the history of human communication inside the geodesic sphere.",
    ),
    Attraction(
        id="ep_figment",
        name="Journey Into Imagination with Figment",
        land="ep_world_celebration",
        kind="ride",
        tier=2,
        duration_minutes=6,
        capacity_per_hour=2000,
        has_express=True,
        description="Quirky dark ride with Figment the purple dragon exploring imagination. Beloved cult classic.",
    ),

    # ── World Showcase ────────────────────────────────────────────────────────
    Attraction(
        id="ep_remy",
        name="Remy's Ratatouille Adventure",
        land="ep_world_showcase",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=2800,
        has_express=True,
        description="Trackless dark ride shrinking you to rat-size in Gusteau's kitchen. Family-friendly thrill.",
    ),
    Attraction(
        id="ep_frozen",
        name="Frozen Ever After",
        land="ep_world_showcase",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=2500,
        has_express=True,
        description="Boat ride through Arendelle. Beloved scenes with Elsa, Anna, Sven, and Kristoff.",
    ),
    Attraction(
        id="ep_gran_fiesta",
        name="Gran Fiesta Tour Starring The Three Caballeros",
        land="ep_world_showcase",
        kind="ride",
        tier=1,
        duration_minutes=8,
        capacity_per_hour=2000,
        has_express=False,
        description="Gentle boat ride through Mexican pavilion with festive Three Caballeros musical journey.",
    ),
    Attraction(
        id="ep_reflections_china",
        name="Reflections of China",
        land="ep_world_showcase",
        kind="show",
        tier=2,
        duration_minutes=14,
        has_express=False,
        showtimes=[
            "11:00", "12:00", "13:00", "14:00", "15:00", "16:00",
        ],
        description="Circle-vision 360° film touring China's landscapes, culture, and history. Stand-up theater.",
    ),
]

HS_ATTRACTIONS: list[Attraction] = [
    # ── Galaxy's Edge ─────────────────────────────────────────────────────────
    Attraction(
        id="hs_rise_resistance",
        name="Star Wars: Rise of the Resistance",
        land="hs_galaxys_edge",
        kind="ride",
        tier=5,
        duration_minutes=18,
        capacity_per_hour=1500,
        has_express=True,
        height_inches=40,
        description="Epic multi-ride immersive experience. Captured by the First Order, then rescued by the Resistance. A bucket list attraction.",
    ),
    Attraction(
        id="hs_smugglers_run",
        name="Millennium Falcon: Smugglers Run",
        land="hs_galaxys_edge",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=1800,
        has_express=True,
        height_inches=38,
        description="Pilot the Millennium Falcon on a smuggling mission. Your role (pilot/gunner/engineer) affects the ride.",
    ),

    # ── Toy Story Land ────────────────────────────────────────────────────────
    Attraction(
        id="hs_slinky_dog",
        name="Slinky Dog Dash",
        land="hs_toy_story_land",
        kind="ride",
        tier=4,
        duration_minutes=3,
        capacity_per_hour=1400,
        has_express=True,
        height_inches=38,
        description="Family-friendly launched coaster with Andy's Slinky Dog theming. A perpetual high-demand ride.",
    ),
    Attraction(
        id="hs_toy_story_mania",
        name="Toy Story Mania!",
        land="hs_toy_story_land",
        kind="ride",
        tier=4,
        duration_minutes=7,
        capacity_per_hour=2800,
        has_single_rider=False,
        has_express=True,
        description="Interactive 4D carnival game dark ride shooting at Toy Story-themed targets.",
    ),
    Attraction(
        id="hs_alien_saucers",
        name="Alien Swirling Saucers",
        land="hs_toy_story_land",
        kind="ride",
        tier=2,
        duration_minutes=2,
        capacity_per_hour=900,
        has_express=True,
        description="Spinning-cup ride with little green alien theming from Toy Story's Pizza Planet.",
    ),

    # ── Sunset Boulevard ──────────────────────────────────────────────────────
    Attraction(
        id="hs_tower_of_terror",
        name="The Twilight Zone Tower of Terror",
        land="hs_sunset_boulevard",
        kind="ride",
        tier=5,
        duration_minutes=5,
        capacity_per_hour=1500,
        has_express=True,
        height_inches=40,
        description="Random freefall drop in a haunted Hollywood hotel elevator. Classic Disney thrill.",
    ),
    Attraction(
        id="hs_rock_n_roller",
        name="Rock 'n' Roller Coaster Starring Aerosmith",
        land="hs_sunset_boulevard",
        kind="ride",
        tier=5,
        duration_minutes=2,
        capacity_per_hour=1400,
        has_single_rider=True,
        has_express=True,
        height_inches=48,
        description="Multi-inversion launched indoor coaster at 0 to 60 in 2.8 seconds. Loud Aerosmith rock soundtrack.",
    ),
    Attraction(
        id="hs_beauty_beast_show",
        name="Beauty and the Beast Live on Stage",
        land="hs_sunset_boulevard",
        kind="show",
        tier=3,
        duration_minutes=30,
        has_express=False,
        showtimes=[
            "10:30", "12:00", "13:30", "15:00", "16:30",
        ],
        description="Broadway-style stage show retelling Beauty and the Beast with elaborate costumes.",
    ),
    Attraction(
        id="hs_fantasmic",
        name="Fantasmic!",
        land="hs_sunset_boulevard",
        kind="show",
        tier=5,
        duration_minutes=30,
        has_express=True,
        showtimes=["21:00", "21:30"],
        description="Epic outdoor nighttime spectacular on a Hollywood Hills stage with fireworks, water screens, and 50 Disney characters.",
    ),

    # ── Echo Lake ─────────────────────────────────────────────────────────────
    Attraction(
        id="hs_indiana_jones",
        name="Indiana Jones Epic Stunt Spectacular!",
        land="hs_echo_lake",
        kind="show",
        tier=3,
        duration_minutes=30,
        has_express=False,
        showtimes=[
            "10:00", "12:00", "14:00", "16:00",
        ],
        description="Live action stunt show demonstrating filmmaking secrets from Raiders of the Lost Ark.",
    ),
    Attraction(
        id="hs_star_tours",
        name="Star Tours – The Adventures Continue",
        land="hs_echo_lake",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=2000,
        has_express=True,
        height_inches=40,
        description="Flight simulator with randomized Star Wars destinations and spy missions.",
    ),

    # ── Grand Avenue ──────────────────────────────────────────────────────────
    Attraction(
        id="hs_muppets",
        name="Muppet*Vision 3D",
        land="hs_grand_avenue",
        kind="show",
        tier=3,
        duration_minutes=16,
        has_express=True,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30", "17:00",
        ],
        description="Classic 4D Muppet film with in-theater special effects. A timeless, hilarious show.",
    ),

    # ── Animation Courtyard ───────────────────────────────────────────────────
    Attraction(
        id="hs_runaway_railway",
        name="Mickey & Minnie's Runaway Railway",
        land="hs_animation_courtyard",
        kind="ride",
        tier=4,
        duration_minutes=5,
        capacity_per_hour=2800,
        has_express=True,
        description="Trackless dark ride inside a Mickey Mouse cartoon. Genuinely funny and unexpected.",
    ),
]

AK_ATTRACTIONS: list[Attraction] = [
    # ── Pandora ───────────────────────────────────────────────────────────────
    Attraction(
        id="ak_flight_of_passage",
        name="Avatar Flight of Passage",
        land="ak_pandora",
        kind="ride",
        tier=5,
        duration_minutes=5,
        capacity_per_hour=1600,
        has_express=True,
        height_inches=44,
        description="Banshee motorcycle simulator soaring over Pandora's bioluminescent landscape. The most-demanded ride at Animal Kingdom.",
    ),
    Attraction(
        id="ak_navi_river",
        name="Na'vi River Journey",
        land="ak_pandora",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=2200,
        has_express=True,
        description="Gentle boat ride through glowing Pandoran rainforest leading to the Shaman of Songs animatronic.",
    ),

    # ── Africa ────────────────────────────────────────────────────────────────
    Attraction(
        id="ak_kilimanjaro",
        name="Kilimanjaro Safaris",
        land="ak_africa",
        kind="ride",
        tier=4,
        duration_minutes=22,
        capacity_per_hour=3200,
        has_express=True,
        description="Open-vehicle safari across 110 acres of African savanna with free-roaming animals.",
    ),
    Attraction(
        id="ak_lion_king",
        name="Festival of the Lion King",
        land="ak_africa",
        kind="show",
        tier=5,
        duration_minutes=30,
        has_express=True,
        showtimes=[
            "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
        ],
        description="Broadway-caliber live musical celebration with acrobats, singers, and lion puppets. A must-see.",
    ),
    Attraction(
        id="ak_gorilla_falls",
        name="Gorilla Falls Exploration Trail",
        land="ak_africa",
        kind="experience",
        tier=2,
        duration_minutes=30,
        has_express=False,
        description="Walking trail through African flora and fauna — gorillas, hippos, birds, and naked mole rats.",
    ),

    # ── Asia ──────────────────────────────────────────────────────────────────
    Attraction(
        id="ak_expedition_everest",
        name="Expedition Everest – Legend of the Forbidden Mountain",
        land="ak_asia",
        kind="ride",
        tier=5,
        duration_minutes=4,
        capacity_per_hour=2000,
        has_single_rider=True,
        has_express=True,
        height_inches=44,
        description="Runaway train coaster up and inside Mount Everest. Backwards drop when the Yeti destroys the track.",
    ),
    Attraction(
        id="ak_kali_rapids",
        name="Kali River Rapids",
        land="ak_asia",
        kind="ride",
        tier=3,
        duration_minutes=5,
        capacity_per_hour=1800,
        has_express=True,
        height_inches=38,
        description="Circular raft river ride through logging deforestation scenery. You will get soaked.",
    ),
    Attraction(
        id="ak_maharajah_trek",
        name="Maharajah Jungle Trek",
        land="ak_asia",
        kind="experience",
        tier=2,
        duration_minutes=30,
        has_express=False,
        description="Walking trail through Southeast Asian ruins with tigers, giant fruit bats, and Komodo dragons.",
    ),
    Attraction(
        id="ak_up_show",
        name="UP! A Great Bird Adventure",
        land="ak_asia",
        kind="show",
        tier=3,
        duration_minutes=25,
        has_express=False,
        showtimes=[
            "10:00", "11:30", "13:00", "14:30", "16:00",
        ],
        description="Outdoor live bird show featuring Russell and Dug from UP! alongside exotic free-flying birds.",
    ),

    # ── Discovery Island ──────────────────────────────────────────────────────
    Attraction(
        id="ak_tough_bug",
        name="It's Tough to Be a Bug!",
        land="ak_discovery_island",
        kind="show",
        tier=3,
        duration_minutes=9,
        has_express=True,
        showtimes=[
            "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
            "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
            "16:00", "16:30",
        ],
        description="4D film inside the Tree of Life with Flik from A Bug's Life. Stinging effects! Not for the squeamish.",
    ),

    # ── DinoLand USA ──────────────────────────────────────────────────────────
    Attraction(
        id="ak_dinosaur",
        name="DINOSAUR",
        land="ak_dinoland",
        kind="ride",
        tier=4,
        duration_minutes=4,
        capacity_per_hour=2000,
        has_express=True,
        height_inches=40,
        description="Time-rover dark ride to the Cretaceous period to rescue an Iguanodon before the asteroid hits.",
    ),
    Attraction(
        id="ak_triceratop_spin",
        name="TriceraTop Spin",
        land="ak_dinoland",
        kind="ride",
        tier=2,
        duration_minutes=2,
        capacity_per_hour=900,
        has_express=True,
        description="Flying-spinner ride with triceratops theming. Short wait, fun for young children.",
    ),
    Attraction(
        id="ak_nemo_show",
        name="Finding Nemo: The Big Blue… and Beyond!",
        land="ak_dinoland",
        kind="show",
        tier=3,
        duration_minutes=30,
        has_express=False,
        showtimes=[
            "10:30", "12:00", "13:30", "15:00", "16:30",
        ],
        description="New live musical show featuring Finding Nemo characters on stage with puppets and projection effects.",
    ),
]

ALL_DISNEY_ATTRACTIONS: list[Attraction] = (
    MK_ATTRACTIONS + EPCOT_ATTRACTIONS + HS_ATTRACTIONS + AK_ATTRACTIONS
)

PARK_ATTRACTIONS: dict[str, list[Attraction]] = {
    "magic_kingdom":    MK_ATTRACTIONS,
    "epcot":            EPCOT_ATTRACTIONS,
    "hollywood_studios": HS_ATTRACTIONS,
    "animal_kingdom":   AK_ATTRACTIONS,
}


# ─── Lightning Lane types ──────────────────────────────────────────────────────
# Source: Disney World app, allears.net, touringplans.com (verified 2025-2026).
# "single" = Lightning Lane Single Pass (individual per-ride purchase, highest demand).
# "multi"  = Lightning Lane Multi Pass (day-pass tier, most rides).
# Absent   = no Lightning Lane offered (walking trails, low-demand shows, etc.).

_DISNEY_LL_TYPES: dict[str, str] = {
    # ── Magic Kingdom ── LLSP (premium individual rides) ──────────────────────
    "mk_seven_dwarfs":      "single",   # ~$12-18; perennial top-demand
    "mk_tron":              "single",   # ~$15-20; fastest MK coaster, huge standby
    "mk_tianas_bayou":      "single",   # ~$12-18; flume ride, long waits since 2024

    # ── Magic Kingdom ── LLMP ─────────────────────────────────────────────────
    "mk_peter_pan":         "multi",
    "mk_little_mermaid":    "multi",
    "mk_winnie_pooh":       "multi",
    "mk_dumbo":             "multi",
    "mk_enchanted_tales":   "multi",
    "mk_philharmagic":      "multi",
    "mk_space_mountain":    "multi",
    "mk_buzz_lightyear":    "multi",
    "mk_laugh_floor":       "multi",
    "mk_pirates":           "multi",
    "mk_jungle_cruise":     "multi",
    "mk_magic_carpets":     "multi",
    "mk_haunted_mansion":   "multi",
    "mk_big_thunder":       "multi",
    # mk_small_world, mk_tiki_room, mk_hall_presidents, mk_country_bears → no LL
    # mk_princess_hall → character meet, no LL

    # ── EPCOT ── LLSP ─────────────────────────────────────────────────────────
    "ep_guardians":         "single",   # ~$12-18; virtual queue / LLSP, no standby

    # ── EPCOT ── LLMP ─────────────────────────────────────────────────────────
    "ep_test_track":        "multi",
    "ep_mission_space":     "multi",
    "ep_soarin":            "multi",
    "ep_living_land":       "multi",
    "ep_nemo_seas":         "multi",
    "ep_turtle_talk":       "multi",
    "ep_spaceship_earth":   "multi",
    "ep_figment":           "multi",
    "ep_remy":              "multi",
    "ep_frozen":            "multi",
    # ep_gran_fiesta, ep_reflections_china → no LL (low demand / film)

    # ── Hollywood Studios ── LLSP ─────────────────────────────────────────────
    "hs_rise_resistance":   "single",   # ~$15-25; most sought-after HS ride

    # ── Hollywood Studios ── LLMP ─────────────────────────────────────────────
    "hs_smugglers_run":     "multi",
    "hs_slinky_dog":        "multi",
    "hs_toy_story_mania":   "multi",
    "hs_alien_saucers":     "multi",
    "hs_tower_of_terror":   "multi",
    "hs_rock_n_roller":     "multi",
    "hs_runaway_railway":   "multi",
    "hs_star_tours":        "multi",
    "hs_muppets":           "multi",
    "hs_fantasmic":         "multi",    # Fantasmic Dining / LL preference package
    # hs_indiana_jones, hs_beauty_beast_show → shows, no LL

    # ── Animal Kingdom ── LLSP ────────────────────────────────────────────────
    "ak_flight_of_passage": "single",   # ~$15-20; highest demand in AK

    # ── Animal Kingdom ── LLMP ────────────────────────────────────────────────
    "ak_navi_river":        "multi",
    "ak_kilimanjaro":       "multi",
    "ak_lion_king":         "multi",
    "ak_expedition_everest":"multi",
    "ak_kali_rapids":       "multi",
    "ak_tough_bug":         "multi",
    "ak_dinosaur":          "multi",
    "ak_triceratop_spin":   "multi",
    # ak_gorilla_falls, ak_maharajah_trek → walking trails, no LL
    # ak_up_show, ak_nemo_show → shows, no LL
}

for _a in ALL_DISNEY_ATTRACTIONS:
    _ll = _DISNEY_LL_TYPES.get(_a.id)
    if _ll:
        _a.ll_type = _ll


# ─── Restaurants ───────────────────────────────────────────────────────────────

MK_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        "mk_be_our_guest", "Be Our Guest Restaurant", "mk_fantasyland", "full", "French", 75, True,
        popular_dish="Braised Pork",
        description="Dinner table-service in the Beast's enchanted castle ballroom. Reservations essential; walk-up lunch counter too.",
        menu_highlights=["Braised Pork", "Pan-seared Chicken", "Grey Stuff Dessert", "The Master's Filet", "French Onion Soup"],
        url="", wait_notes="Reservations book out weeks ahead. Walk-up breakfast/lunch counter (no ADR needed) opens at park open.",
    ),
    Restaurant(
        "mk_cinderellas_table", "Cinderella's Royal Table", "mk_fantasyland", "full", "American", 80, True,
        popular_dish="Herb-crusted Beef Tenderloin",
        description="Princess character dining inside Cinderella Castle. A truly magical experience. Books out 60+ days.",
        menu_highlights=["Herb-crusted Beef Tenderloin", "Roasted Chicken", "Princess character photos included", "Royal Apple Dessert"],
        url="", wait_notes="Book the moment your ADR window opens (60 days for guests). Nearly impossible as walk-in.",
    ),
    Restaurant(
        "mk_columbia_harbour", "Columbia Harbour House", "mk_liberty_square", "quick", "American seafood", 35, False,
        popular_dish="Lobster Roll",
        description="Quick-service seafood and American fare in Liberty Square. Two-story interior with reasonable waits.",
        menu_highlights=["Lobster Roll", "Fried Shrimp Platter", "Clam Chowder", "New England Fish Fry", "Vegetarian Chili"],
        url="", wait_notes="Waits stay manageable (15-25 min) even at lunch. Upstairs seating usually available.",
    ),
    Restaurant(
        "mk_friar_nook", "The Friar's Nook", "mk_fantasyland", "snack", "Snacks", 10, False,
        popular_dish="Loaded Mac & Cheese Tots",
        description="Walk-up snack window with loaded tots and frozen treats. Highly Instagrammable.",
        menu_highlights=["Loaded Mac & Cheese Tots", "Pickle-brined Fried Chicken", "Frozen Sour Apple Lemonade"],
        url="", wait_notes="Popular; 10-20 min on busy days.",
    ),
    Restaurant(
        "mk_sleepy_hollow", "Sleepy Hollow", "mk_liberty_square", "snack", "Waffles/snacks", 10, False,
        popular_dish="Funnel Cake Waffle Sandwich",
        description="Famous for the breakfast waffle sandwich and funnel cakes. Walk-up window by the castle bridge.",
        menu_highlights=["Waffle Sandwich (Nutella & fruit)", "Fresh Funnel Cake", "Ice Cream Waffle Sandwich"],
        url="", wait_notes="Can get busy. 15-25 min waits at peak.",
    ),
]

EPCOT_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        "ep_space220", "Space 220 Restaurant", "ep_world_discovery", "full", "American fusion", 90, True,
        popular_dish="Lobster Thermidor",
        description="Fine dining 220 miles above Earth. Elevator ride to a fake space station, panoramic Earth views. Extremely popular.",
        menu_highlights=["Lobster Thermidor", "Smoked Duck", "Celeste — butter poached lobster", "Shooting Star dessert"],
        url="", wait_notes="ADR required. Walk-up lounge (Space 220 Lounge) is first-come; arrive 15-20 min before open.",
    ),
    Restaurant(
        "ep_garden_grill", "Garden Grill Restaurant", "ep_world_nature", "full", "American", 75, True,
        popular_dish="Rotisserie Turkey",
        description="Rotating character dining over Living with the Land greenhouse. Farm-to-table American food.",
        menu_highlights=["Rotisserie Turkey", "Farmstead Beef", "Cast-Iron Mac & Cheese", "Mickey character appearances"],
        url="", wait_notes="Character dining; reservations recommended. Rotating floor makes some guests dizzy.",
    ),
    Restaurant(
        "ep_les_halles", "Les Halles Boulangerie-Patisserie", "ep_world_showcase", "quick", "French bakery", 30, False,
        popular_dish="Croque Monsieur",
        description="Paris-style bakery in the France pavilion. Arguably the best quick-service in all of EPCOT.",
        menu_highlights=["Croque Monsieur", "Quiche Lorraine", "Croissant", "Napoleon", "Café au Lait"],
        url="", wait_notes="One of EPCOT's most popular QS. 20-35 min line at lunch.",
    ),
    Restaurant(
        "ep_regal_eagle", "Regal Eagle Smokehouse: Craft Drafts & Barbecue", "ep_world_discovery", "quick", "BBQ", 40, False,
        popular_dish="Pulled Pork Platter",
        description="American BBQ counter with craft beer in the American Adventure pavilion. Large portions.",
        menu_highlights=["Pulled Pork Platter", "Smoked Chicken", "Brisket Sandwich", "BBQ Jackfruit (vegan)", "Craft Beer"],
        url="", wait_notes="Typically 15-25 min. Large dining area means more seating.",
    ),
    Restaurant(
        "ep_sunshine_seasons", "Sunshine Seasons", "ep_world_nature", "quick", "International", 30, False,
        popular_dish="Grilled Salmon",
        description="Large food court under the geodesic dome of The Land pavilion. Multiple stations.",
        menu_highlights=["Grilled Salmon", "Wood-Fired Rotisserie Chicken", "Asian Noodle Bowl", "Fresh Salads"],
        url="", wait_notes="Good for large groups — different stations allow splitting up. 10-20 min.",
    ),
]

HS_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        "hs_50s_prime_time", "50's Prime Time Café", "hs_echo_lake", "full", "American", 75, True,
        popular_dish="Pot Roast",
        description="1950s TV kitchen table-service where waitstaff plays your 'Mom' and scolds you for elbows on the table.",
        menu_highlights=["Mom's Pot Roast", "Peanut Butter & Jelly Milkshake", "Mashed Potatoes", "Fried Chicken"],
        url="", wait_notes="Unique experience; reservations recommended. Walk-up lunch can be available.",
    ),
    Restaurant(
        "hs_sci_fi_dine_in", "Sci-Fi Dine-In Theater Restaurant", "hs_grand_avenue", "full", "American", 70, True,
        popular_dish="Angus Beef Burger",
        description="Eat in a 1950s-style car at a drive-in theater playing vintage sci-fi B-movies.",
        menu_highlights=["Angus Beef Burger", "Grilled Chicken Sandwich", "Cosmic Brownie Shake", "All-Beef Hot Dog"],
        url="", wait_notes="Very atmospheric; table-service, reservations needed. Walk-up available on less busy days.",
    ),
    Restaurant(
        "hs_docking_bay_7", "Docking Bay 7 Food and Cargo", "hs_galaxys_edge", "quick", "Alien/fusion", 35, False,
        popular_dish="Smoked Kaadu Ribs",
        description="Main quick-service inside Black Spire Outpost on Batuu. The best dining experience in Galaxy's Edge.",
        menu_highlights=["Smoked Kaadu Ribs (pork)", "Fried Endorian Tip Yip (chicken)", "Yobshrimp Noodle Salad", "Batuu-bon dessert"],
        url="", wait_notes="20-35 min at lunch. The Outpost Popcorn stand nearby has nearly no wait.",
    ),
    Restaurant(
        "hs_woodys_lunch_box", "Woody's Lunch Box", "hs_toy_story_land", "quick", "American comfort", 30, False,
        popular_dish="Totchos",
        description="Walk-up counter in Toy Story Land famous for Totchos (tot nachos) and the Monte Cristo sandwich.",
        menu_highlights=["Totchos (loaded tater tots)", "Lunch Box Tart (Pop-Tart-style)", "BBQ Brisket Melt", "Chocolate PB Shake"],
        url="", wait_notes="Long lines (30-45 min) at peak — a victim of its own popularity. Go early or late.",
    ),
]

AK_RESTAURANTS: list[Restaurant] = [
    Restaurant(
        "ak_tiffins", "Tiffins Restaurant", "ak_discovery_island", "full", "Global", 85, True,
        popular_dish="Whole-Roasted Sustainable Fish",
        description="Animal Kingdom's only full table-service. Global cuisine celebrating adventure and travel. Art-filled dining rooms.",
        menu_highlights=["Whole-Roasted Fish", "Braised Sustainable Grouper", "Lamb Chops", "Mango Brûlée", "Exotic Cocktail Menu"],
        url="", wait_notes="ADR strongly recommended. Walk-up sometimes available at off-peak hours.",
    ),
    Restaurant(
        "ak_flame_tree", "Flame Tree Barbecue", "ak_discovery_island", "quick", "BBQ", 35, False,
        popular_dish="Half Slab St. Louis Ribs",
        description="Animal Kingdom's most beloved quick-service. Open-air BBQ with Discovery River views.",
        menu_highlights=["Half Slab St. Louis Ribs", "Pulled Pork Sandwich", "BBQ Chicken", "Smoked Turkey Leg"],
        url="", wait_notes="Can have 20-30 min waits. Outdoor seating along the river. Go early.",
    ),
    Restaurant(
        "ak_satuli_canteen", "Satu'li Canteen", "ak_pandora", "quick", "Na'vi/fusion", 40, False,
        popular_dish="Cheeseburger Pod",
        description="EPCOT-worthy quick-service inside Pandora. Build-your-own bowls with alien grain bases.",
        menu_highlights=["Cheeseburger Steamed Pod", "Slow-roasted Beef Bowl", "Healthy Romaine Bowl", "Blueberry Cream Cheese Mousse"],
        url="", wait_notes="Busy due to Pandora demand. Mobile order strongly recommended. 20-40 min walk-up.",
    ),
    Restaurant(
        "ak_tusker_house", "Tusker House Restaurant", "ak_africa", "full", "African fusion", 75, True,
        popular_dish="Peri Peri Rotisserie Chicken",
        description="Character dining breakfast/lunch/dinner with Donald Duck and friends in Harambe. African-inspired buffet.",
        menu_highlights=["Peri Peri Rotisserie Chicken", "Durban-style Spit Roasted Chicken", "Bobotie (Cape Malay meat curry)", "Mickey-shaped waffles (breakfast)"],
        url="", wait_notes="Character dining; book ADR. Donald, Daisy, Mickey, Goofy all appear.",
    ),
]

ALL_DISNEY_RESTAURANTS: list[Restaurant] = (
    MK_RESTAURANTS + EPCOT_RESTAURANTS + HS_RESTAURANTS + AK_RESTAURANTS
)

PARK_RESTAURANTS: dict[str, list[Restaurant]] = {
    "magic_kingdom":     MK_RESTAURANTS,
    "epcot":             EPCOT_RESTAURANTS,
    "hollywood_studios": HS_RESTAURANTS,
    "animal_kingdom":    AK_RESTAURANTS,
}


# ─── Helpers ───────────────────────────────────────────────────────────────────

def disney_lands(park_id: str) -> dict:
    if park_id == "magic_kingdom":
        return MK_LANDS
    if park_id == "epcot":
        return EPCOT_LANDS
    if park_id == "hollywood_studios":
        return HS_LANDS
    if park_id == "animal_kingdom":
        return AK_LANDS
    return {}


def disney_attractions(park_id: str) -> list[dict]:
    return [a.to_dict() for a in PARK_ATTRACTIONS.get(park_id, [])]


def disney_restaurants(park_id: str) -> list[dict]:
    return [r.to_dict() for r in PARK_RESTAURANTS.get(park_id, [])]


def disney_attraction_by_id(attraction_id: str) -> Optional[Attraction]:
    for a in ALL_DISNEY_ATTRACTIONS:
        if a.id == attraction_id:
            return a
    return None
