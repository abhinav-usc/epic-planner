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
    # Lightning Lane type: "single" = Individual LL (premium per-ride purchase),
    # "multi" = LL Multi Pass (day-pass tier), None = no LL available.
    ll_type: Optional[str] = None

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
    Attraction(
        id="meet_mario_luigi",
        name="Meet Mario and Luigi",
        land="super_nintendo_world",
        kind="experience",
        tier=2,
        duration_minutes=5,
        has_express=False,
        description="Character meet-and-greet with Mario and Luigi.",
    ),
    Attraction(
        id="meet_princess_peach",
        name="Meet Princess Peach",
        land="super_nintendo_world",
        kind="experience",
        tier=2,
        duration_minutes=5,
        has_express=False,
        description="Character meet-and-greet with Princess Peach.",
    ),
    Attraction(
        id="meet_donkey_kong",
        name="Meet Donkey Kong",
        land="super_nintendo_world",
        kind="experience",
        tier=2,
        duration_minutes=5,
        has_express=False,
        description="Character meet-and-greet with Donkey Kong.",
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
            "10:50", "11:40", "12:30", "13:20", "14:10",
            "15:20", "16:10", "17:00", "17:50", "18:40", "19:50",
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
        id="meet_toothless_hiccup",
        name="Meet Toothless & Hiccup",
        land="isle_of_berk",
        kind="experience",
        tier=2,
        duration_minutes=5,
        has_express=False,
        description="Standalone meet-and-greet with the live Hiccup actor (separate from the Toothless animatronic show).",
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
    Attraction(
        id="dark_universe_meet",
        name="Dark Universe Character Meet & Greet",
        land="dark_universe",
        kind="experience",
        tier=2,
        duration_minutes=5,
        has_express=False,
        description="Meet the classic Universal Monsters (Invisible Man, Frankenstein's Monster, etc.).",
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
    description: str = ""
    menu_highlights: list[str] = field(default_factory=list)
    url: str = ""
    wait_notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


_BASE_URL = "https://www.universalorlando.com/web/en/us/things-to-do/dining/"

RESTAURANTS: list[Restaurant] = [
    # ── Celestial Park ────────────────────────────────────────────────────────
    Restaurant(
        "the_atlantic", "The Atlantic", "celestial_park", "full", "Seafood", 75, True,
        popular_dish="Seared scallops",
        description="Upscale table-service seafood restaurant at the heart of Celestial Park. Reservations highly recommended — walk-ins are rarely available on busy days.",
        menu_highlights=[
            "Seared Scallops — Arborio rice, trumpet mushrooms, charred romanesco, Parmigiano-Reggiano",
            "Sea Bass — carrot mochi, sugar snap peas, lemongrass broth, star fruit",
            "Whole Roasted Branzino",
            "Atlantic Lobster Bisque",
            "Grand Atlantic Martini — dry gin, aperitif, gilded lemon twist",
        ],
        url=_BASE_URL + "atlantic",
        wait_notes="Reservations required; book 60+ days out. Walk-in availability rare on busy days. Avg dining time 75+ min. (Source: orlandoinformer.com)",
    ),
    Restaurant(
        "blue_dragon", "The Blue Dragon Pan-Asian Restaurant", "celestial_park", "full", "Pan-Asian", 70, True,
        popular_dish="Crispy duck bao",
        description="Full-service Pan-Asian restaurant with elegant décor and artisan cocktails. One of Celestial Park's two table-service options.",
        menu_highlights=[
            "Tonkotsu Ramen",
            "Crispy Duck Bao",
            "Khaosan Boba — milk tea, coffee boba, coffee foam",
            "Pan-Seared Miso Black Cod",
            "Lychee Mochi Ice Cream",
        ],
        url=_BASE_URL + "blue-dragon-pan-asian-restaurant",
        wait_notes="Full-service; reservations recommended. Walk-ins typically available mid-afternoon.",
    ),
    Restaurant(
        "pizza_moon", "Pizza Moon", "celestial_park", "quick", "Pizza", 30, False,
        popular_dish="Honey-pepperoni pizza",
        description="Counter-service pizza with galaxy-themed décor. Strong vegetarian and vegan options.",
        menu_highlights=[
            "Honey-Pepperoni Pizza",
            "Harvest Moon Pizza (vegan) — grilled artichoke, roasted tomatoes, peppers, Castelvetrano olives, arugula",
            "Margherita Pizza",
            "Celestial Cheesecake",
            "Cosmic Meatball Sub",
        ],
        url=_BASE_URL + "pizza-moon",
        wait_notes="Typically 10–20 min queue. Busier at lunch. Mobile ordering available via Universal app.",
    ),
    Restaurant(
        "comet_dogs", "Comet Dogs", "celestial_park", "quick", "Hot dogs", 20, False,
        popular_dish="The Comet Dog",
        description="Classic American hot dogs with cosmic-themed toppings. A quick and budget-friendly option in Celestial Park.",
        menu_highlights=[
            "The Comet Dog — chili & cheese",
            "Galaxy Dog — bacon jam",
            "Asteroid Dog — kimchi & spicy mustard",
            "Comet Chili",
            "Fresh-Cut Fries",
        ],
        url=_BASE_URL + "comet-dogs",
        wait_notes="Quick counter kiosk. Rarely more than 10–15 min wait.",
    ),
    Restaurant(
        "frosty_moon", "Frosty Moon", "celestial_park", "quick", "Ice cream", 15, False,
        popular_dish="Moon Pie sundae",
        description="Stellar-themed ice cream shop with constellation-inspired frozen treats.",
        menu_highlights=[
            "Moon Pie Sundae",
            "Stardust Soft Serve",
            "Galaxy Shake",
            "Constellation Waffle Cone",
            "Celestial Sorbet",
        ],
        url="",
        wait_notes="10–20 min on peak days.",
    ),
    Restaurant(
        "meteor_astropub", "Meteor Astropub", "celestial_park", "quick", "Gastropub", 40, False,
        popular_dish="Fish & chips with wasabi fries",
        description="Meteor-themed gastropub with elevated comfort food and craft cocktails. Good adult-friendly option without table-service waits.",
        menu_highlights=[
            "Fish & Chips — with wasabi fries",
            "Goat Cheese Grilled Cheese",
            "Meteor Smashburger",
            "Asteroid Wings",
            "Craft Beer & House Cocktail Selection",
        ],
        url=_BASE_URL + "meteor-astropub",
        wait_notes="15–30 min at lunch peak. Typically quiet after 2 PM. (Source: themeparkshark.com)",
    ),
    Restaurant(
        "celestiki", "Celestiki", "celestial_park", "quick", "Tiki/tropical", 30, False,
        popular_dish="Volcano Bowl",
        description="Open-air tiki bar with tropical bites and creative cocktails. Great for a mid-afternoon drink.",
        menu_highlights=[
            "Volcano Bowl — signature tiki cocktail",
            "Pulled Pork Sliders",
            "Fish Tacos",
            "Mahi Bites",
            "Cosmic Mai Tai",
        ],
        url="",
        wait_notes="Bar seating usually available. Food wait 10–15 min.",
    ),
    Restaurant(
        "star_sui_bao", "Star Sui Bao", "celestial_park", "quick", "Bao buns", 20, False,
        popular_dish="BBQ pork bao",
        description="Asian-inspired steamed bao counter with fresh housemade fillings. Great for a quick, satisfying lunch.",
        menu_highlights=[
            "BBQ Pork Bao",
            "Chicken Teriyaki Bao",
            "Veggie Mushroom Bao",
            "Sesame Balls",
            "Milk Tea",
        ],
        url="",
        wait_notes="One of the quicker options in Celestial Park. Rarely over 15 min.",
    ),
    Restaurant(
        "oak_star_tavern", "The Oak & Star Tavern", "celestial_park", "quick", "American tavern", 45, False,
        popular_dish="Cosmic chicken pot pie",
        description="Cozy American tavern with hearty park-going favorites and a warm, wood-paneled atmosphere.",
        menu_highlights=[
            "Cosmic Chicken Pot Pie",
            "Prime Rib Sandwich",
            "Mac & Cheese",
            "Tavern Salad",
            "Ale-Battered Onion Rings",
        ],
        url="",
        wait_notes="15–25 min typical queue at lunch.",
    ),
    Restaurant(
        "bar_zenith", "Bar Zenith", "celestial_park", "bar", "Cocktails", 30, False,
        popular_dish="Galaxy old fashioned",
        description="Sophisticated cocktail bar at the heart of Celestial Park. Perfect for a mid-afternoon drink with views of the fountains.",
        menu_highlights=[
            "Galaxy Old Fashioned",
            "Celestial G&T",
            "Nebula Negroni",
            "Starfield Spritz",
            "Non-Alcoholic Celestial Punch",
        ],
        url="",
        wait_notes="Walk-up bar; typically no wait. Limited seating.",
    ),
    Restaurant(
        "plastered_owl", "The Plastered Owl", "celestial_park", "bar", "Beer + dueling guitars", 60, False,
        popular_dish="Owl ale",
        description="Lively entertainment bar with live dueling guitar music and British-pub energy. Best experienced in the evenings.",
        menu_highlights=[
            "Owl Ale (house brew)",
            "Rotating Craft Taps",
            "Loaded Nachos",
            "Pretzels & Beer Cheese",
            "Classic Cocktail Menu",
        ],
        url="",
        wait_notes="Gets crowded evenings with live music. Arrive early for seating.",
    ),
    Restaurant(
        "lens_flare", "Lens Flare", "celestial_park", "bar", "Cocktails", 30, False,
        popular_dish="Solar flare margarita",
        description="Open-air cocktail bar with specialty drinks and views of Celestial Park's garden.",
        menu_highlights=[
            "Solar Flare Margarita",
            "Starlight Lemonade",
            "Aperol Spritz",
            "Frozen Cosmos",
        ],
        url="",
        wait_notes="Walk-up bar; minimal wait.",
    ),
    Restaurant(
        "moonship_chocolates", "Moonship Chocolates & Celestial Sweets", "celestial_park", "snack",
        "Chocolate/desserts", 10, False,
        popular_dish="Galaxy bonbons",
        description="Artisan chocolate and confectionery shop. Great for a sweet souvenir or midday treat.",
        menu_highlights=[
            "Galaxy Bonbons",
            "Astro Fudge",
            "Celestial Truffles",
            "Chocolate-Dipped Fruit",
            "Themed Candy Bars",
        ],
        url="",
        wait_notes="Snack shop; rarely has a line.",
    ),
    Restaurant(
        "north_star_wintry", "North Star Wintry Wonders", "celestial_park", "snack", "Frozen treats", 10, False,
        popular_dish="Stardust soft serve",
        description="Frozen treats kiosk near Celestial Park's north fountain.",
        menu_highlights=[
            "Stardust Soft Serve",
            "Constellation Waffle Cone",
            "Frozen Lemonade",
            "Dipped Waffle Cones",
        ],
        url="",
        wait_notes="5–10 min max.",
    ),
    Restaurant(
        "starbucks", "Starbucks Coffee", "celestial_park", "quick", "Coffee", 10, False,
        popular_dish="Standard Starbucks menu",
        description="Full-service Starbucks with standard menu plus some park-exclusive signature drinks.",
        menu_highlights=[
            "Standard Starbucks Menu",
            "Park-exclusive signature beverages",
            "Mobile order available via Starbucks app",
        ],
        url="",
        wait_notes="Mobile order recommended. In-person line 15–20 min on busy mornings.",
    ),

    # ── Super Nintendo World ──────────────────────────────────────────────────
    Restaurant(
        "toadstool_cafe", "Toadstool Cafe", "super_nintendo_world", "quick", "Mario-themed American", 40, True,
        popular_dish="Mario Burger",
        description="The most-visited quick-service in Super Nintendo World. Colorful Mario-themed décor with giant mushrooms and Nintendo references throughout. A must-eat for fans.",
        menu_highlights=[
            "Mario Burger — bacon, mushroom, American cheese",
            "Luigi Burger — pesto grilled chicken",
            "Bowser's Fireball Challenge — 1-lb meatball, mozzarella, mushroom marinara, Bowser puff pastry",
            "Mushroom Kingdom Pasta",
            "Princess Peach's Lemonade",
        ],
        url=_BASE_URL + "toadstool-cafe",
        wait_notes="Busiest QS in SNW. Expect 45–60 min+ at lunch peak (11:30 AM–1:30 PM). Join mobile waitlist via Universal app at park open. Best times: before 11:30 AM or after 2 PM. (Source: orlandoinformer.com, r/UniversalOrlando)",
    ),
    Restaurant(
        "yoshis_snack_island", "Yoshi's Snack Island", "super_nintendo_world", "snack", "Fruity snacks", 10,
        False,
        popular_dish="Yoshi fruit cup",
        description="Outdoor fruit and healthy snack kiosk near Yoshi's Adventure. Great for a quick refuel between rides.",
        menu_highlights=[
            "Yoshi Fruit Cup",
            "Power-Up Punch",
            "Star Bit Candy",
            "Themed Frozen Treats",
        ],
        url="",
        wait_notes="Minimal wait. Great for a quick healthy snack.",
    ),
    Restaurant(
        "bubbly_barrel", "The Bubbly Barrel", "super_nintendo_world", "quick", "Drinks", 15, False,
        popular_dish="Power-Up smoothie",
        description="Nintendo-themed drinks kiosk with Power-Up beverages and smoothies.",
        menu_highlights=[
            "Power-Up Smoothie",
            "Princess Peach Punch",
            "1-Up Lemonade",
            "Mushroom Kingdom Milk Tea",
        ],
        url="",
        wait_notes="5–10 min typical.",
    ),
    Restaurant(
        "turbo_boost_treats", "Turbo-Boost Treats", "super_nintendo_world", "snack", "Energy snacks", 10, False,
        popular_dish="Super Star popcorn",
        description="Nintendo-inspired snack cart with themed treats within Super Nintendo World.",
        menu_highlights=[
            "Super Star Popcorn",
            "Mushroom Cookies",
            "Power-Up Gummy Candy",
            "Star Bit Sundae",
        ],
        url="",
        wait_notes="Quick counter; minimal wait.",
    ),

    # ── Ministry of Magic ─────────────────────────────────────────────────────
    Restaurant(
        "cafe_la_sirene", "Café L'air De La Sirène", "ministry_of_magic", "quick", "French patisserie", 35,
        False,
        popular_dish="Butterbeer Crepe",
        description="Charming Parisian café set in 1920s Magical Paris. French patisserie classics with a wizarding twist. Indoor and outdoor seating with ornate carved marble décor.",
        menu_highlights=[
            "Butterbeer Crepe — shortbread cookie butter, Bavarian cream, Butterbeer drizzle, strawberries",
            "Baguette de Dinde — black pepper turkey, arugula, apple, Brie, mustard butter on warm baguette",
            "Quiche Lorraine — egg custard, bacon, Gruyère, caramelized onions, Mornay sauce",
            "Poulet à la Provençal — roasted half chicken, tomato-olive vinaigrette, roasted potatoes",
            "Café Noisette",
        ],
        url=_BASE_URL + "cafe-lair-de-la-sirene",
        wait_notes="Quick service but crowded 11 AM–2 PM. Off-peak hours have minimal waits. (Source: orlandoinformer.com, wdwnt.com)",
    ),
    Restaurant(
        "le_gobelet_noir", "Le Gobelet Noir", "ministry_of_magic", "quick", "French bistro", 45, False,
        popular_dish="Alchemist's Platter",
        description="Cozy dark French café with a wizarding spin on hearty bistro classics. One of the better hot-meal options in Ministry of Magic.",
        menu_highlights=[
            "Alchemist's Platter — smoked sausage, potato & cheese pierogies, pickled eggs, marinated beets, warm pretzel with German mustard & cheese fondue",
            "Vegan Lentil Stew — lentils, vegan bacon, root vegetables, artisan bread",
            "French Onion Soup",
            "Cauldron Cassoulet",
            "Dark Chocolate Crème Brûlée",
        ],
        url=_BASE_URL + "le-gobelet-noir",
        wait_notes="Less crowded than Café L'air. Good alternative if Café L'air is backed up. (Source: uofan.com)",
    ),
    Restaurant(
        "bar_moonshine", "Bar Moonshine", "ministry_of_magic", "bar", "Wizarding cocktails", 25, False,
        popular_dish="Moonshine martini",
        description="Intimate wizarding cocktail bar with magical-themed concoctions. A cozy spot for an afternoon drink away from the crowds.",
        menu_highlights=[
            "Moonshine Martini",
            "Felix Felicis Fizz",
            "Polyjuice Punch",
            "Gillywater (non-alcoholic)",
        ],
        url="",
        wait_notes="Walk-up bar; minimal wait.",
    ),
    Restaurant(
        "cosme_acajor", "Cosme Acajor Baguettes Magique", "ministry_of_magic", "quick", "Bakery", 15, False,
        popular_dish="Magique baguette",
        description="Grab-and-go magical bakery with fresh French baked goods. Ideal for breakfast before rides or a quick midday snack.",
        menu_highlights=[
            "Magique Baguette",
            "Pain de Campagne",
            "Almond Croissant",
            "Tarte au Citron",
            "Pain au Chocolat",
        ],
        url="",
        wait_notes="5–10 min walk-up. Best for breakfast before the lunch rush.",
    ),
    Restaurant(
        "biraubeurre_cart", "Bièraubeurre Cart", "ministry_of_magic", "cart", "Butterbeer", 5, False,
        popular_dish="Butterbeer (cold)",
        description="The iconic Butterbeer cart — a must for Harry Potter fans. Available cold, frozen, or hot (seasonal).",
        menu_highlights=[
            "Butterbeer (cold) — cream cheese foam top",
            "Butterbeer Frozen",
            "Butterbeer Hot (seasonal)",
            "Pumpkin Juice",
        ],
        url="",
        wait_notes="15–25 min wait typical; slightly shorter than the Hogsmeade Butterbeer carts. (Source: community reports)",
    ),

    # ── Isle of Berk ──────────────────────────────────────────────────────────
    Restaurant(
        "mead_hall", "Mead Hall", "isle_of_berk", "quick", "Viking feast", 50, False,
        popular_dish="Thawfest Platter",
        description="Viking longhouse-style feast hall with large communal tables and a boisterous atmosphere. One of the most Instagram-worthy dining spots in Epic Universe.",
        menu_highlights=[
            "Thawfest Platter — chicken drumsticks in wild berry BBQ glaze, grilled salmon, sausage, roasted vegetables, Nordic fries",
            "Stormfly's Catch of the Day — chocolate mousse fish on crispy rice",
            "Dragon Chicken Drumstick",
            "Non-Alcoholic Mead",
            "Apple Cider",
        ],
        url=_BASE_URL + "mead-hall",
        wait_notes="20–35 min queue on typical days; communal seating means tables turn over faster than the line suggests. (Source: disneyfoodblog.com, uofan.com)",
    ),
    Restaurant(
        "spit_fyre_grill", "Spit Fyre Grill", "isle_of_berk", "quick", "BBQ/grill", 35, False,
        popular_dish="Stoick's Steak Bowl",
        description="Open-fire BBQ counter inspired by Berk's dragon trainers. Build-your-own bowl concept with proteins and fresh toppings.",
        menu_highlights=[
            "Stoick's Steak Bowl",
            "Hiccup's Salmon Bowl",
            "Meatlug's Chicken Bowl",
            "Astrid's Shrimp Bowl",
            "Valka's Vegan Bowl",
        ],
        url=_BASE_URL + "spit-fyre-grill",
        wait_notes="Typically 15–25 min. Bowl concept means consistent, fast service. (Source: uofan.com)",
    ),
    Restaurant(
        "hooligans_grog", "Hooligan's Grog & Gruel", "isle_of_berk", "quick", "Stew + ale", 40, False,
        popular_dish="Mac & Cheese Cone",
        description="Rustic Viking stew-and-ale counter famous for its Mac & Cheese Cone — a unique, shareable street-food twist on a comfort classic.",
        menu_highlights=[
            "Dragon's Garden Pyre — mac & cheese, herb chicken, corn, avocado, Flamin' Hot Cheetos in a cone",
            "PB&J — BBQ harissa pulled pork, peanut bacon jam in a cone",
            "Classic Mac & Cheese Cone",
            "Hooligan Stew",
            "Viking Ale (or non-alcoholic mead)",
        ],
        url=_BASE_URL + "hooligans-grog-and-gruel",
        wait_notes="Fan favorite. Moderate 15–20 min waits on typical days. (Source: orlandoinformer.com, wdwnt.com)",
    ),

    # ── Dark Universe ─────────────────────────────────────────────────────────
    Restaurant(
        "das_stakehaus", "Das Stakehaus", "dark_universe", "quick", "Vampire steakhouse", 45, False,
        popular_dish="Bird on a Stake",
        description="Gothic vampire-themed quick-service set above ancient catacombs. Surprisingly excellent protein-forward meals with theatrical presentation.",
        menu_highlights=[
            "Fish on a Stake — blackened salmon",
            "Bird on a Stake — grilled chicken",
            "Bits & Pieces — wild mushroom brisket meatloaf",
            "Das Burger",
            "Forager Salad",
        ],
        url=_BASE_URL + "das-stakehaus",
        wait_notes="Under 20 min most of the day except 12–1 PM lunch rush. (Source: must-love-garlic.com, disneyfoodblog.com)",
    ),
    Restaurant(
        "burning_blade_tavern", "The Burning Blade Tavern", "dark_universe", "quick", "Gothic pub", 40, False,
        popular_dish="Burning Blade Burger",
        description="Trophy-decorated dark tavern with pub favorites and a gothic monster aesthetic. Known for its loaded potato and signature burger.",
        menu_highlights=[
            "Hunter's Garlic Stake — crispy garlic butter pretzel with garlic dipping sauce",
            "Burning Cheddar Bites — fried poppers, sriracha ranch",
            "Charred Loaded Potato — hickory char crust, Monterey Jack, sour cream, jalapeño bacon",
            "Burning Blade Burger — 4 oz black Angus, American cheese, caramelized onions, jalapeño bacon",
            "Bratwurst",
        ],
        url=_BASE_URL + "burning-blade-tavern",
        wait_notes="Typically 15–20 min. (Source: uofan.com)",
    ),
    Restaurant(
        "de_laceys_cottage", "De Lacey's Cottage", "dark_universe", "quick", "Cottage fare", 35, False,
        popular_dish="Warm Hearted Cinnamon Bites",
        description="Small cozy counter with cottage-style comfort food and sweet treats. Great for dessert or a light snack.",
        menu_highlights=[
            "Frank & Friends Pretzel — with white cheddar sauce",
            "Warm Hearted Cinnamon Bites — cinnamon sugar donut bites, cream cheese icing, streusel",
            "Cottage Pie",
            "Monster Mash Potatoes",
        ],
        url=_BASE_URL + "de-laceys-cottage",
        wait_notes="Small counter; rarely more than 10 min. Good for a quick dessert stop. (Source: disneyfoodblog.com)",
    ),
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


def ll_wait_minutes(standby_wait: int, ll_type: Optional[str]) -> int:
    """Return estimated in-queue wait when using Lightning Lane.

    Empirical reductions from TouringPlans / thrill-data historical data:
      LLSP (Single): guests typically wait 5–15 min in the LL queue.
                     Modelled as max(5, standby * 0.12).
      LLMP (Multi):  return windows fill up fast; typical LL queue 10–30 min.
                     Modelled as max(10, standby * 0.25).
    """
    if ll_type == "single":
        return max(5, int(round(standby_wait * 0.12)))
    if ll_type == "multi":
        return max(10, int(round(standby_wait * 0.25)))
    return standby_wait
