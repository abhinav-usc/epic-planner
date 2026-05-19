/** Walk-time tables mirroring backend/data/attractions_db.py and disney_db.py. */

function hubSpoke(spokes: Record<string, number>): Map<string, number> {
  const m = new Map<string, number>();
  for (const [a, ta] of Object.entries(spokes)) {
    for (const [b, tb] of Object.entries(spokes)) {
      m.set(`${a}→${b}`, a === b ? 0 : ta + tb);
    }
  }
  return m;
}

const EPIC_WALKS = hubSpoke({
  celestial_park: 0,
  super_nintendo_world: 5,
  ministry_of_magic: 5,
  isle_of_berk: 6,
  dark_universe: 5,
});

const MK_WALKS = hubSpoke({
  mk_main_street: 0,
  mk_fantasyland: 6,
  mk_tomorrowland: 5,
  mk_adventureland: 5,
  mk_liberty_square: 6,
  mk_frontierland: 7,
});

const EPCOT_WALKS = hubSpoke({
  ep_world_celebration: 0,
  ep_world_discovery: 5,
  ep_world_nature: 5,
  ep_world_showcase: 10,
});

const HS_WALKS = hubSpoke({
  hs_hollywood_boulevard: 0,
  hs_galaxys_edge: 8,
  hs_toy_story_land: 6,
  hs_sunset_boulevard: 5,
  hs_echo_lake: 4,
  hs_grand_avenue: 5,
  hs_animation_courtyard: 5,
});

const AK_WALKS = hubSpoke({
  ak_discovery_island: 0,
  ak_pandora: 7,
  ak_africa: 6,
  ak_asia: 7,
  ak_dinoland: 6,
});

// Disneyland Park — hub-spoke from main street + adjacency shortcuts
const DL_BASE = hubSpoke({
  dl_main_street: 0,
  dl_adventureland: 5,
  dl_new_orleans_sq: 7,
  dl_frontierland: 8,
  dl_fantasyland: 7,
  dl_tomorrowland: 5,
  dl_galaxys_edge: 10,
  dl_toontown: 8,
});
// Adjacency overrides
const DL_OVERRIDES: [string, string, number][] = [
  ["dl_adventureland", "dl_new_orleans_sq", 3],
  ["dl_new_orleans_sq", "dl_adventureland", 3],
  ["dl_new_orleans_sq", "dl_frontierland", 4],
  ["dl_frontierland", "dl_new_orleans_sq", 4],
  ["dl_frontierland", "dl_fantasyland", 5],
  ["dl_fantasyland", "dl_frontierland", 5],
  ["dl_fantasyland", "dl_tomorrowland", 6],
  ["dl_tomorrowland", "dl_fantasyland", 6],
  ["dl_galaxys_edge", "dl_frontierland", 5],
  ["dl_frontierland", "dl_galaxys_edge", 5],
  ["dl_toontown", "dl_fantasyland", 4],
  ["dl_fantasyland", "dl_toontown", 4],
];
const DL_WALKS = new Map(DL_BASE);
for (const [a, b, t] of DL_OVERRIDES) DL_WALKS.set(`${a}→${b}`, t);

// Universal Hollywood — two-level park
function ushWalk(from: string, to: string): number {
  if (from === to) return 0;
  const UPPER = new Set(["uh_upper_lot", "uh_springfield", "uh_dreamworks", "uh_studio_tour"]);
  const LOWER = new Set(["uh_lower_lot", "uh_wizarding_world"]);
  if (UPPER.has(from) && UPPER.has(to)) return 5;
  if (LOWER.has(from) && LOWER.has(to)) return 5;
  return 8; // cross-level escalator
}
const USH_LANDS = ["uh_upper_lot", "uh_springfield", "uh_dreamworks", "uh_studio_tour", "uh_lower_lot", "uh_wizarding_world"];
const USH_WALKS = new Map<string, number>();
for (const a of USH_LANDS) for (const b of USH_LANDS) USH_WALKS.set(`${a}→${b}`, ushWalk(a, b));

const PARK_WALKS: Record<string, Map<string, number>> = {
  epic_universe: EPIC_WALKS,
  magic_kingdom: MK_WALKS,
  epcot: EPCOT_WALKS,
  hollywood_studios: HS_WALKS,
  animal_kingdom: AK_WALKS,
  disneyland: DL_WALKS,
  universal_hollywood: USH_WALKS,
};

export function walkMinutes(parkId: string, fromLand: string, toLand: string): number {
  if (!fromLand || !toLand || fromLand === toLand) return 0;
  if (fromLand === "break" || toLand === "break") return 0;
  return PARK_WALKS[parkId]?.get(`${fromLand}→${toLand}`) ?? 5;
}
