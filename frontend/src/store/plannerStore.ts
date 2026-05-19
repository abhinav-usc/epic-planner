import { create } from "zustand";
import type {
  Attraction,
  CrowdForecast,
  DayCurve,
  FoodBreakConfig,
  Land,
  LandId,
  LivePollResponse,
  LLPlanResponse,
  OptimizeResponse,
  ParkId,
  PlannedItem,
  PlannedKind,
  PriorityItem,
  Restaurant,
  ShoppingBreakConfig,
} from "../types";
import { api } from "../api/client";

/** Median wait + worst-case wait per attraction for the current target date. */
export interface AttractionDaySummary {
  median_wait: number;
  worst_case_median: number;
}

// Minutes a queue typically forms before a stage show.
export const SHOW_QUEUE_MINUTES = 15;

interface PlaceResult {
  ok: boolean;
  /** Final start_minute (may be snapped from requested if collision). */
  start_minute: number;
  /** Why we couldn't place it (only set when ok=false). */
  reason?: string;
  /** Reason note if we snapped — visible to caller for toast/log. */
  snapped?: string;
}

interface PlannerState {
  // Park
  currentPark: ParkId;

  // Catalog
  lands: Record<LandId, Land> | null;
  attractions: Attraction[];
  restaurants: Restaurant[];
  loaded: boolean;
  catalogError: string | null;

  // Settings
  targetDate: string;
  earlyEntry: boolean;
  worstCaseMode: boolean;
  apiKey: string;

  // Crowd forecast for current date
  forecast: CrowdForecast | null;

  // Full per-hour wait curves cached per attraction. Used both for the
  // left-rail pills and to instantly recompute wait when a bar moves.
  dayCurves: Record<string, DayCurve>;
  daySummaries: Record<string, AttractionDaySummary>;

  // Manual itinerary
  plannedItems: PlannedItem[];
  placementNote: string | null;  // transient note: "snapped to next free slot", etc.

  // Optimizer-driven priorities
  priorities: PriorityItem[];
  ropeDropLand: string | null;
  arrivalHour: number | null;  // null = use park open time
  breakMinutes: number;
  foodBreaks: FoodBreakConfig[];
  shoppingBreaks: ShoppingBreakConfig[];
  useLlMulti: boolean;           // user has Lightning Lane Multi Pass
  llSingleIds: string[];         // ride IDs user purchased LLSP for
  landHopping: boolean;          // greedy global scheduler (ignore land clustering)
  optimizing: boolean;
  optimizeResult: OptimizeResponse | null;

  // Lightning Lane Multi Pass booking plan, recomputed when plan changes.
  llPlan: LLPlanResponse | null;
  llPlanLoading: boolean;

  // Manual wait time overrides: attraction_id → user-specified wait minutes.
  // Overrides persist in localStorage and take priority over model predictions.
  waitOverrides: Record<string, number>;

  // Live mode: poll queue-times.com every 5 min, calibrate predictions, auto re-optimize.
  liveMode: boolean;
  liveData: LivePollResponse | null;
  liveLastFetchedAt: string | null;  // ISO; null until first successful poll

  // Actions
  switchPark: (parkId: ParkId) => Promise<void>;
  loadCatalog: () => Promise<void>;
  setDate: (d: string) => Promise<void>;
  setEarlyEntry: (v: boolean) => void;
  setWorstCaseMode: (v: boolean) => void;
  setApiKey: (k: string) => void;
  setPlacementNote: (s: string | null) => void;
  setRopeDropLand: (land: string | null) => void;
  setArrivalHour: (hour: number | null) => void;
  setBreakMinutes: (min: number) => void;
  addFoodBreak: () => void;
  removeFoodBreak: (index: number) => void;
  updateFoodBreak: (index: number, patch: Partial<FoodBreakConfig>) => void;
  toggleShoppingBreak: (land: LandId) => void;
  setShoppingBreakDuration: (land: LandId, duration: number) => void;
  setUseLlMulti: (v: boolean) => void;
  toggleLlSingle: (rideId: string) => void;
  /** Add a pre-booked LLSP reservation — creates a locked block on the timeline. */
  addLlReservation: (a: Attraction, windowStartMinute: number) => void;
  removeLlReservation: (id: string) => void;
  setLandHopping: (v: boolean) => void;
  setShowtime: (attractionId: string, showtime: string | null) => void;
  /** Place an attraction at a requested minute. Snaps for shows, prevents
   *  overlap, recomputes wait from cached day curve. Returns a PlaceResult. */
  placeAttraction: (a: Attraction, requestedMinute: number) => PlaceResult;
  /** Move an existing planned item. Snaps for shows, prevents overlap, and
   *  for rides/experiences recomputes wait + worst-case from the new time. */
  moveItem: (id: string, requestedMinute: number) => PlaceResult;
  addBreak: (kind: "break_food" | "break_shop", durationMin: number, requestedMinute?: number) => PlaceResult;
  /** Update a break's duration in-place. Clamps to [5, time-until-next-item-or-close]. */
  setBreakDuration: (id: string, durationMin: number) => void;
  removePlannedItem: (id: string) => void;
  toggleDone: (id: string) => void;
  clearTimeline: () => void;
  /** Replace the current plan with a previously-saved snapshot. */
  loadPlanItems: (items: PlannedItem[], earlyEntry: boolean) => void;
  togglePriority: (attractionId: string) => void;
  toggleMustDo: (attractionId: string) => void;
  setRank: (attractionId: string, rank: number) => void;
  runOptimize: () => Promise<void>;
  applyOptimizeResultToTimeline: () => void;
  refreshDayCurves: () => Promise<void>;
  /** Recompute the Lightning Lane booking plan from current state. */
  refreshLlPlan: () => Promise<void>;
  /** Set or clear a manual wait override for an attraction. Pass null to clear. */
  setWaitOverride: (attractionId: string, wait: number | null) => void;
  /** Toggle live polling mode on/off. When on, queue-times is polled every 5 min. */
  setLiveMode: (on: boolean) => void;
  /** Fetch the latest live snapshot now (also called by the live-mode interval). */
  pollLive: () => Promise<void>;
}

// Default to today (local time) — formatted as YYYY-MM-DD.
const todaysDefault = (() => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
})();
const PARK_OPEN_HOUR_DEFAULT = 9;
const PARK_OPEN_HOUR_EARLY = 8;
const PARK_CLOSE_HOURS: Record<string, number> = {
  epic_universe: 21,
  magic_kingdom: 22,
  epcot: 21,
  hollywood_studios: 21,
  animal_kingdom: 18,
  disneyland: 23,
};
function parkCloseHour(park: ParkId) { return PARK_CLOSE_HOURS[park] ?? 21; }
function openHour(earlyEntry: boolean) { return earlyEntry ? PARK_OPEN_HOUR_EARLY : PARK_OPEN_HOUR_DEFAULT; }
function closeMinute(earlyEntry: boolean, park: ParkId = "epic_universe") { return (parkCloseHour(park) - openHour(earlyEntry)) * 60; }

/** Linearly interpolate the predicted wait at an arbitrary minute. */
function waitAt(curve: DayCurve | undefined, minuteSinceOpen: number, parkOpen: number): { wait: number; worst?: number } {
  if (!curve || !curve.hours.length) return { wait: 30 };
  const hourOfDay = parkOpen + minuteSinceOpen / 60;
  // Find the two surrounding hours in the curve.
  const sorted = [...curve.hours].sort((a, b) => a.hour - b.hour);
  let lo = sorted[0], hi = sorted[sorted.length - 1];
  for (let i = 0; i < sorted.length - 1; i++) {
    if (sorted[i].hour <= hourOfDay && sorted[i + 1].hour >= hourOfDay) {
      lo = sorted[i];
      hi = sorted[i + 1];
      break;
    }
  }
  if (lo.hour === hi.hour) return { wait: Math.round(lo.wait_minutes), worst: lo.worst_case_wait ?? undefined };
  const t = Math.max(0, Math.min(1, (hourOfDay - lo.hour) / (hi.hour - lo.hour)));
  const wait = Math.round(lo.wait_minutes * (1 - t) + hi.wait_minutes * t);
  let worst: number | undefined;
  if (lo.worst_case_wait != null && hi.worst_case_wait != null) {
    worst = Math.round(lo.worst_case_wait * (1 - t) + hi.worst_case_wait * t);
  }
  return { wait, worst };
}

/** Convert a showtime "HH:MM" to a minute-since-open offset for the date. */
function showtimeToMinute(hhmm: string, parkOpen: number): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m - parkOpen * 60;
}

/** Find a valid free slot near `requested`. Allows items to START up to closeMin
 *  (items can finish after close — guests can queue until the park closes).
 *  Picks the FREE slot closest to the requested position. */
function findFreeSlot(
  items: PlannedItem[],
  requested: number,
  duration: number,
  excludeId: string | null,
  closeMin: number,
): { ok: boolean; start: number; snapped: boolean } {
  // Allow starting up to close — rides started at close are normal park behaviour.
  const maxStart = closeMin;
  const target = Math.max(0, Math.min(maxStart, requested));
  const wasClamped = target !== requested;

  const ranges = items
    .filter(i => i.id !== excludeId)
    .map(i => [i.start_minute, i.start_minute + i.duration_minute] as [number, number])
    .sort((a, b) => a[0] - b[0]);

  function overlapsAt(start: number): boolean {
    if (start < 0 || start > maxStart) return true;
    const end = start + duration;
    return ranges.some(([a, b]) => start < b && a < end);
  }

  if (!overlapsAt(target)) {
    return { ok: true, start: target, snapped: wasClamped };
  }

  // Build candidate free positions: right after each block end and right before each block start.
  const candidates = new Set<number>([0, maxStart]);
  for (const [a, b] of ranges) {
    candidates.add(b);             // place immediately after this item
    candidates.add(a - duration);  // place ending immediately before this item
  }

  let best: number | null = null;
  let bestDist = Infinity;
  for (const c of candidates) {
    const clamped = Math.max(0, Math.min(maxStart, c));
    if (overlapsAt(clamped)) continue;
    const dist = Math.abs(clamped - target);
    if (dist < bestDist) { best = clamped; bestDist = dist; }
  }

  if (best !== null) return { ok: true, start: best, snapped: true };
  return { ok: false, start: target, snapped: false };
}

/** Snap a proposed minute to the nearest showtime for a show attraction. */
function snapShowtime(a: Attraction, requested: number, parkOpen: number): number | null {
  if (!a.showtimes || a.showtimes.length === 0) return null;
  const offsets = a.showtimes.map(t => showtimeToMinute(t, parkOpen));
  // Closest showtime to the requested center of the block
  let best = offsets[0];
  let bestDist = Math.abs(offsets[0] - requested);
  for (const m of offsets) {
    const d = Math.abs(m - requested);
    if (d < bestDist) { best = m; bestDist = d; }
  }
  return best;
}

export const usePlanner = create<PlannerState>((set, get) => ({
  currentPark: "epic_universe",

  lands: null,
  attractions: [],
  restaurants: [],
  loaded: false,
  catalogError: null,

  targetDate: todaysDefault,
  earlyEntry: false,
  worstCaseMode: false,
  apiKey: typeof window !== "undefined" ? localStorage.getItem("anthropic_api_key") || "" : "",

  forecast: null,
  dayCurves: {},
  daySummaries: {},
  plannedItems: [],
  placementNote: null,
  priorities: [],
  ropeDropLand: null,
  arrivalHour: null,
  breakMinutes: 60,
  foodBreaks: [
    { duration_minutes: 30, earliest_hour: 10, latest_hour: 11 },
    { duration_minutes: 60, earliest_hour: 12, latest_hour: 13 },
    { duration_minutes: 30, earliest_hour: 15, latest_hour: 16 },
  ],
  shoppingBreaks: [],
  useLlMulti: false,
  llSingleIds: [],
  landHopping: false,
  optimizing: false,
  optimizeResult: null,
  llPlan: null,
  llPlanLoading: false,
  waitOverrides: typeof window !== "undefined"
    ? JSON.parse(localStorage.getItem("wait_overrides") || "{}")
    : {},
  liveMode: false,
  liveData: null,
  liveLastFetchedAt: null,

  switchPark: async (parkId) => {
    set({ currentPark: parkId, loaded: false, attractions: [], restaurants: [], lands: null,
          plannedItems: [], priorities: [], dayCurves: {}, daySummaries: {}, optimizeResult: null });
    await get().loadCatalog();
  },

  loadCatalog: async () => {
    const park = get().currentPark;
    try {
      const [lands, attractions, restaurants, forecast] = await Promise.all([
        api.lands(park),
        api.attractions(park),
        api.restaurants(park),
        api.crowdForecast(get().targetDate),
      ]);
      set({ lands, attractions, restaurants, forecast, loaded: true, catalogError: null });
      get().refreshDayCurves();
    } catch (e: any) {
      set({ catalogError: e.message ?? String(e), loaded: false });
    }
  },

  setDate: async (d: string) => {
    set({ targetDate: d }); // keep plannedItems — waits recomputed below
    try {
      const forecast = await api.crowdForecast(d);
      set({ forecast });
    } catch {/* ignore */}
    await get().refreshDayCurves();
    // Recompute wait times for ride/experience items against the new date's curves.
    const { plannedItems, dayCurves, earlyEntry } = get();
    const parkOpen = openHour(earlyEntry);
    if (plannedItems.length > 0) {
      const updated = plannedItems.map(item => {
        if (item.kind !== "ride" && item.kind !== "experience") return item;
        const { wait, worst } = waitAt(dayCurves[item.attraction_id], item.start_minute, parkOpen);
        return {
          ...item,
          wait_minutes: wait,
          worst_case_wait: worst,
          duration_minute: wait + item.ride_minutes,
        };
      });
      set({ plannedItems: updated });
    }
  },

  setEarlyEntry: (v) => set({ earlyEntry: v }),
  setWorstCaseMode: (v) => set({ worstCaseMode: v }),
  setPlacementNote: (s) => set({ placementNote: s }),

  setApiKey: (k) => {
    if (typeof window !== "undefined") localStorage.setItem("anthropic_api_key", k);
    set({ apiKey: k });
  },

  placeAttraction: (a, requestedMinute) => {
    const { plannedItems, dayCurves, earlyEntry, currentPark } = get();
    const parkOpen = openHour(earlyEntry);
    const close = closeMinute(earlyEntry, currentPark);

    let kind: PlannedKind = a.kind;
    let start = Math.max(0, Math.round(requestedMinute));
    let wait = 0;
    let worst: number | undefined;
    let rideMin = a.duration_minutes;
    let showtimeMinute: number | undefined;
    let snapNote = "";

    if (a.kind === "show") {
      const showtime = snapShowtime(a, requestedMinute, parkOpen);
      if (showtime == null) {
        return { ok: false, start_minute: start, reason: "No showtimes for this show" };
      }
      // Block covers queue (wait) + show duration; queue ends right at showtime.
      wait = SHOW_QUEUE_MINUTES;
      start = Math.max(0, showtime - wait);
      showtimeMinute = showtime;
      snapNote = `Snapped to ${a.showtimes![Math.max(0, a.showtimes!.findIndex(t => showtimeToMinute(t, parkOpen) === showtime))]} showtime`;
    } else {
      // Ride/experience: use manual override if set, else predicted wait.
      const { waitOverrides } = get();
      if (a.id in waitOverrides) {
        wait = waitOverrides[a.id];
      } else {
        const { wait: w, worst: wc } = waitAt(dayCurves[a.id], start, parkOpen);
        wait = w;
        worst = wc;
      }
    }

    const duration = wait + rideMin;
    const placement = findFreeSlot(plannedItems, start, duration, null, close);
    if (!placement.ok) {
      return { ok: false, start_minute: start, reason: "No free slot fits this attraction" };
    }

    // For shows, if we had to snap away from the chosen showtime due to overlap,
    // try the *next* available showtime instead.
    if (a.kind === "show" && placement.snapped) {
      const offsets = (a.showtimes || []).map(t => showtimeToMinute(t, parkOpen)).sort((x, y) => x - y);
      let placed = false;
      for (const st of offsets) {
        const tryStart = Math.max(0, st - wait);
        const f = findFreeSlot(plannedItems, tryStart, duration, null, close);
        if (f.ok && !f.snapped) {
          showtimeMinute = st;
          start = tryStart;
          placement.start = tryStart;
          placement.snapped = false;
          snapNote = `Snapped to ${a.showtimes![offsets.indexOf(st)]} showtime (next available)`;
          placed = true;
          break;
        }
      }
      if (!placed) {
        return { ok: false, start_minute: start, reason: "All showtimes conflict with existing plan" };
      }
    }

    const id = `${a.id}-${Date.now()}`;
    const newItem: PlannedItem = {
      id,
      attraction_id: a.id,
      name: a.name,
      land: a.land,
      kind,
      start_minute: placement.start,
      duration_minute: duration,
      ride_minutes: rideMin,
      wait_minutes: wait,
      worst_case_wait: worst,
      showtime_minute: showtimeMinute,
    };
    const chosenShowtime = a.kind === "show" && showtimeMinute !== undefined
      ? (a.showtimes?.find(t => showtimeToMinute(t, parkOpen) === showtimeMinute) ?? null)
      : null;
    set(s => {
      const alreadyPrioritized = s.priorities.some(p => p.attraction_id === a.id);
      const newPriorities = alreadyPrioritized
        ? s.priorities
        : [...s.priorities, { attraction_id: a.id, must_do: false, rank: s.priorities.length + 1, chosen_showtime: chosenShowtime }];
      return {
        plannedItems: [...s.plannedItems, newItem],
        priorities: newPriorities,
        placementNote: placement.snapped
          ? `Placed at ${formatMin(placement.start, parkOpen)} (snapped past conflict)`
          : (snapNote || null),
      };
    });
    return { ok: true, start_minute: placement.start, snapped: snapNote || (placement.snapped ? "conflict" : undefined) };
  },

  moveItem: (id, requestedMinute) => {
    const { plannedItems, dayCurves, earlyEntry, attractions, currentPark } = get();
    const parkOpen = openHour(earlyEntry);
    const close = closeMinute(earlyEntry, currentPark);
    const item = plannedItems.find(p => p.id === id);
    if (!item) return { ok: false, start_minute: 0, reason: "Item not found" };

    let newStart = Math.max(0, Math.round(requestedMinute));
    let newWait = item.wait_minutes;
    let newWorst = item.worst_case_wait;
    let newShowtime = item.showtime_minute;

    if (item.kind === "show") {
      const a = attractions.find(x => x.id === item.attraction_id);
      if (a) {
        const showtime = snapShowtime(a, newStart + item.wait_minutes, parkOpen);
        if (showtime != null) {
          newShowtime = showtime;
          newStart = Math.max(0, showtime - item.wait_minutes);
        }
      }
    } else if (item.kind === "ride" || item.kind === "experience") {
      const { waitOverrides } = get();
      if (item.attraction_id in waitOverrides) {
        newWait = waitOverrides[item.attraction_id];
      } else {
        const { wait, worst } = waitAt(dayCurves[item.attraction_id], newStart, parkOpen);
        newWait = wait;
        newWorst = worst;
      }
    }

    const newDuration = newWait + item.ride_minutes;
    const placement = findFreeSlot(plannedItems, newStart, newDuration, id, close);
    if (!placement.ok) {
      return { ok: false, start_minute: newStart, reason: "Can't fit at requested time" };
    }

    set(s => ({
      plannedItems: s.plannedItems.map(p =>
        p.id === id ? {
          ...p,
          start_minute: placement.start,
          duration_minute: newDuration,
          wait_minutes: newWait,
          worst_case_wait: newWorst,
          showtime_minute: newShowtime,
        } : p,
      ),
      placementNote: placement.snapped
        ? `Snapped past conflict to ${formatMin(placement.start, parkOpen)}`
        : null,
    }));
    return { ok: true, start_minute: placement.start, snapped: placement.snapped ? "conflict" : undefined };
  },

  addBreak: (kind, durationMin, requestedMinute) => {
    const { plannedItems, earlyEntry, currentPark } = get();
    const parkOpen = openHour(earlyEntry);
    const close = closeMinute(earlyEntry, currentPark);
    // Default: place at noon if no requested minute
    const requested = requestedMinute ?? ((12 - parkOpen) * 60);
    const placement = findFreeSlot(plannedItems, requested, durationMin, null, close);
    if (!placement.ok) {
      return { ok: false, start_minute: requested, reason: "No room for a break" };
    }
    const isFood = kind === "break_food";
    const id = `${kind}-${Date.now()}`;
    const newItem: PlannedItem = {
      id,
      attraction_id: id,
      name: isFood ? "Food break" : "Shopping break",
      land: "break",
      kind,
      start_minute: placement.start,
      duration_minute: durationMin,
      ride_minutes: durationMin,
      wait_minutes: 0,
    };
    set(s => ({ plannedItems: [...s.plannedItems, newItem] }));
    return { ok: true, start_minute: placement.start, snapped: placement.snapped ? "conflict" : undefined };
  },

  setBreakDuration: (id, durationMin) => {
    const { plannedItems, earlyEntry, currentPark } = get();
    const close = closeMinute(earlyEntry, currentPark);
    const me = plannedItems.find(p => p.id === id);
    if (!me) return;
    // Don't extend into the next block.
    const nextStart = plannedItems
      .filter(p => p.id !== id && p.start_minute > me.start_minute)
      .reduce<number>((min, p) => Math.min(min, p.start_minute), close);
    const maxEnd = Math.min(close, nextStart);
    const maxDuration = Math.max(5, maxEnd - me.start_minute);
    const clamped = Math.max(5, Math.min(maxDuration, Math.round(durationMin)));
    set(s => ({
      plannedItems: s.plannedItems.map(p =>
        p.id === id ? { ...p, duration_minute: clamped, ride_minutes: clamped } : p,
      ),
    }));
  },

  removePlannedItem: (id) => {
    set(s => {
      const item = s.plannedItems.find(p => p.id === id);
      const remaining = s.plannedItems.filter(p => p.id !== id);
      if (!item || item.kind === "break_food" || item.kind === "break_shop") {
        return { plannedItems: remaining };
      }
      const stillPlanned = remaining.some(p => p.attraction_id === item.attraction_id);
      if (stillPlanned) return { plannedItems: remaining };
      const newPriorities = s.priorities
        .filter(p => p.attraction_id !== item.attraction_id)
        .map((p, i) => ({ ...p, rank: i + 1 }));
      return { plannedItems: remaining, priorities: newPriorities };
    });
  },

  toggleDone: (id) => {
    set(s => ({
      plannedItems: s.plannedItems.map(p =>
        p.id === id ? { ...p, done: !p.done } : p
      ),
    }));
  },

  clearTimeline: () => set({ plannedItems: [], priorities: [] }),

  loadPlanItems: (items, earlyEntry) => {
    const seen = new Set<string>();
    const priorities: PriorityItem[] = [];
    for (const item of items) {
      if (item.kind === "break_food" || item.kind === "break_shop") continue;
      if (seen.has(item.attraction_id)) continue;
      seen.add(item.attraction_id);
      priorities.push({ attraction_id: item.attraction_id, must_do: false, rank: priorities.length + 1 });
    }
    set({ plannedItems: items, earlyEntry, priorities });
  },

  togglePriority: (attractionId) => {
    const existing = get().priorities.find(p => p.attraction_id === attractionId);
    if (existing) {
      set(s => ({ priorities: s.priorities.filter(p => p.attraction_id !== attractionId) }));
    } else {
      const nextRank = (get().priorities.length || 0) + 1;
      set(s => ({ priorities: [...s.priorities, { attraction_id: attractionId, must_do: false, rank: nextRank }] }));
    }
  },

  toggleMustDo: (attractionId) => {
    set(s => ({
      priorities: s.priorities.map(p =>
        p.attraction_id === attractionId ? { ...p, must_do: !p.must_do } : p,
      ),
    }));
  },

  setRank: (attractionId, rank) => {
    set(s => ({
      priorities: s.priorities.map(p =>
        p.attraction_id === attractionId ? { ...p, rank } : p,
      ),
    }));
  },

  setRopeDropLand: (land) => set({ ropeDropLand: land }),
  setArrivalHour: (hour) => set({ arrivalHour: hour }),
  setBreakMinutes: (min) => set({ breakMinutes: min }),

  addFoodBreak: () => set(s => ({
    foodBreaks: [...s.foodBreaks, { duration_minutes: 30, earliest_hour: 13, latest_hour: 14 }],
  })),
  removeFoodBreak: (index) => set(s => ({
    foodBreaks: s.foodBreaks.filter((_, i) => i !== index),
  })),
  updateFoodBreak: (index, patch) => set(s => ({
    foodBreaks: s.foodBreaks.map((fb, i) => i === index ? { ...fb, ...patch } : fb),
  })),
  toggleShoppingBreak: (land) => set(s => {
    const exists = s.shoppingBreaks.find(sb => sb.land === land);
    return {
      shoppingBreaks: exists
        ? s.shoppingBreaks.filter(sb => sb.land !== land)
        : [...s.shoppingBreaks, { land, duration_minutes: 15 }],
    };
  }),
  setShoppingBreakDuration: (land, duration) => set(s => ({
    shoppingBreaks: s.shoppingBreaks.map(sb => sb.land === land ? { ...sb, duration_minutes: duration } : sb),
  })),
  setUseLlMulti: (v) => set({ useLlMulti: v }),
  setLandHopping: (v) => set({ landHopping: v }),
  toggleLlSingle: (rideId) => set(s => ({
    llSingleIds: s.llSingleIds.includes(rideId)
      ? s.llSingleIds.filter(id => id !== rideId)
      : [...s.llSingleIds, rideId],
  })),
  addLlReservation: (a, windowStartMinute) => {
    const { dayCurves, earlyEntry, currentPark } = get();
    const curve = dayCurves[a.id];
    const parkOpen = openHour(earlyEntry);
    const { wait } = waitAt(curve, windowStartMinute, parkOpen);
    // Use LLSP queue time (~12% of standby, min 5 min).
    const llWait = Math.max(5, Math.round(wait * 0.12));
    const duration = llWait + a.duration_minutes;
    const id = `llr_${a.id}_${Date.now()}`;
    const item: PlannedItem = {
      id,
      attraction_id: a.id,
      name: a.name,
      land: a.land,
      kind: a.kind,
      start_minute: windowStartMinute,
      duration_minute: duration,
      wait_minutes: llWait,
      ride_minutes: a.duration_minutes,
      locked: true,
      ll_window_end: windowStartMinute + 60,
    };
    set(s => ({ plannedItems: [...s.plannedItems, item] }));
  },
  removeLlReservation: (id) => set(s => ({
    plannedItems: s.plannedItems.filter(p => p.id !== id),
  })),
  setShowtime: (attractionId, showtime) => {
    set(s => ({
      priorities: s.priorities.map(p =>
        p.attraction_id === attractionId ? { ...p, chosen_showtime: showtime } : p,
      ),
    }));
  },

  runOptimize: async () => {
    set({ optimizing: true });
    try {
      const { targetDate, earlyEntry, priorities, ropeDropLand, arrivalHour, breakMinutes, foodBreaks, shoppingBreaks, currentPark, useLlMulti, llSingleIds, landHopping, plannedItems } = get();
      // Exclude rides the user has already done from the priority list passed to the optimizer.
      const doneIds = new Set(plannedItems.filter(p => p.done).map(p => p.attraction_id));
      const activePriorities = priorities.filter(p => !doneIds.has(p.attraction_id));
      // Pass pre-booked LLSP reservations as fixed constraints.
      const lockedItems = plannedItems.filter(p => p.locked);
      const ll_reservations = lockedItems.map(p => ({
        attraction_id: p.attraction_id,
        window_start_minute: p.start_minute,
      }));
      const result = await api.optimize({
        target_date: targetDate,
        early_entry: earlyEntry,
        priorities: activePriorities,
        rope_drop_land: ropeDropLand,
        arrival_hour: arrivalHour ?? undefined,
        break_minutes: breakMinutes,
        food_breaks: foodBreaks,
        shopping_breaks: shoppingBreaks,
        park_id: currentPark,
        use_ll_multi: useLlMulti,
        ll_single_ids: llSingleIds,
        ll_reservations,
        land_hopping: landHopping,
      });
      set({ optimizeResult: result, optimizing: false });
    } catch (e: any) {
      set({ optimizing: false, optimizeResult: null });
      alert(`Optimization failed: ${e.message ?? e}`);
    }
  },

  refreshDayCurves: async () => {
    const { attractions, targetDate, earlyEntry, currentPark, liveMode } = get();
    if (!attractions.length) return;
    const targets = attractions.filter(a => a.kind === "ride" || a.kind === "experience");
    if (!targets.length) return;

    const med = (arr: number[]) => {
      if (!arr.length) return 0;
      const s = [...arr].sort((x, y) => x - y);
      const m = Math.floor(s.length / 2);
      return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
    };

    try {
      // Single batch request for all attractions — much faster than one request each.
      const batch = await api.dayCurvesBatch(targets.map(a => a.id), targetDate, earlyEntry, currentPark, liveMode);
      const curves: Record<string, DayCurve> = {};
      const summaries: Record<string, AttractionDaySummary> = {};
      for (const [id, curve] of Object.entries(batch)) {
        curves[id] = curve;
        const waits = curve.hours.map(h => h.wait_minutes).filter(n => Number.isFinite(n));
        const worst = curve.hours.map(h => h.worst_case_wait).filter((n): n is number => n != null);
        summaries[id] = { median_wait: med(waits), worst_case_median: med(worst) };
      }
      set({ dayCurves: curves, daySummaries: summaries });
    } catch {
      // Fallback: individual requests if batch fails
      const curves: Record<string, DayCurve> = {};
      const summaries: Record<string, AttractionDaySummary> = {};
      await Promise.all(
        targets.map(async a => {
          try {
            const curve = await api.dayCurve(a.id, targetDate, earlyEntry, currentPark, liveMode);
            curves[a.id] = curve;
            const waits = curve.hours.map(h => h.wait_minutes).filter(n => Number.isFinite(n));
            const worst = curve.hours.map(h => h.worst_case_wait).filter((n): n is number => n != null);
            summaries[a.id] = { median_wait: med(waits), worst_case_median: med(worst) };
          } catch {/* skip */}
        }),
      );
      set({ dayCurves: curves, daySummaries: summaries });
    }
  },

  setWaitOverride: (attractionId, wait) => {
    set(s => {
      const next = wait === null
        ? Object.fromEntries(Object.entries(s.waitOverrides).filter(([k]) => k !== attractionId))
        : { ...s.waitOverrides, [attractionId]: wait };
      if (typeof window !== "undefined") localStorage.setItem("wait_overrides", JSON.stringify(next));
      // Update all existing planned items for this attraction
      const updatedItems = s.plannedItems.map(item => {
        if (item.attraction_id !== attractionId || item.kind === "break_food" || item.kind === "break_shop") return item;
        const newWait = wait ?? item.wait_minutes;
        return { ...item, wait_minutes: newWait, duration_minute: newWait + item.ride_minutes };
      });
      return { waitOverrides: next, plannedItems: updatedItems };
    });
  },

  setLiveMode: (on) => {
    set({ liveMode: on });
    if (on) {
      void get().pollLive();
    }
  },

  pollLive: async () => {
    const { currentPark } = get();
    try {
      const data = await api.livePoll(currentPark);
      set({ liveData: data, liveLastFetchedAt: data.fetched_at });
      // Re-fetch dayCurves with live calibration applied. This triggers the
      // LL plan refresh via the existing useEffect on plannedItems/dayCurves.
      await get().refreshDayCurves();
    } catch (e) {
      // Silent fail — leave liveData stale; next poll may succeed.
    }
  },

  refreshLlPlan: async () => {
    const { plannedItems, priorities, targetDate, earlyEntry, currentPark, attractions, arrivalHour, useLlMulti } = get();
    if (!useLlMulti) {
      set({ llPlan: null, llPlanLoading: false });
      return;
    }
    const mustDo = new Set(priorities.filter(p => p.must_do).map(p => p.attraction_id));
    const aById = new Map(attractions.map(a => [a.id, a]));
    // Locked items = pre-booked LLSP — exclude from LLMP plan.
    const lockedIds = new Set(plannedItems.filter(p => p.locked).map(p => p.attraction_id));
    const rides = plannedItems
      .filter(item => item.kind === "ride" && !item.done && !item.locked)
      .map(item => ({ item, a: aById.get(item.attraction_id) }))
      .filter((x): x is { item: PlannedItem; a: Attraction } => !!x.a && x.a.ll_type === "multi")
      .map(({ item }) => ({
        attraction_id: item.attraction_id,
        planned_minute: item.start_minute + (item.wait_minutes ?? 0),
        must_do: mustDo.has(item.attraction_id),
      }));

    if (rides.length === 0) {
      set({ llPlan: null, llPlanLoading: false });
      return;
    }

    // Arrival minute: if user set arrivalHour, derive minutes-since-park-open.
    // Otherwise default to 0 (book at park open / 7am pre-open if available).
    const open = openHour(earlyEntry);
    const arrival_minute = arrivalHour != null && arrivalHour > open
      ? (arrivalHour - open) * 60
      : 0;

    set({ llPlanLoading: true });
    try {
      const plan = await api.llPlan({
        target_date: targetDate,
        park: currentPark,
        early_entry: earlyEntry,
        rides,
        arrival_minute,
        ll_reserved_ids: [...lockedIds],
      });
      set({ llPlan: plan, llPlanLoading: false });
    } catch {
      set({ llPlanLoading: false });
    }
  },

  applyOptimizeResultToTimeline: () => {
    const r = get().optimizeResult;
    if (!r) return;
    const earlyEntry = get().earlyEntry;
    const dayStart = openHour(earlyEntry);
    const attractions = get().attractions;
    // Preserve locked (LLSP pre-booked) items from the current plan.
    const lockedById = new Map(
      get().plannedItems.filter(p => p.locked).map(p => [p.attraction_id, p])
    );
    const items: PlannedItem[] = r.items.map((it, idx) => {
      const start = new Date(it.start_time);
      const end = new Date(it.end_time);
      const startMin = start.getHours() * 60 + start.getMinutes() - dayStart * 60;
      const durMin = (end.getTime() - start.getTime()) / 60000;

      // Break items injected by the backend — map directly to break PlannedItems.
      if (it.attraction_id.startsWith("break_")) {
        const isFood = it.attraction_id.startsWith("break_food");
        const kind: PlannedKind = isFood ? "break_food" : "break_shop";
        return {
          id: `${it.attraction_id}-opt-${idx}`,
          attraction_id: it.attraction_id,
          name: it.name,
          land: (it.land === "break" ? "break" : it.land) as PlannedItem["land"],
          kind,
          start_minute: Math.max(0, Math.round(startMin)),
          duration_minute: Math.max(15, Math.round(durMin)),
          wait_minutes: 0,
          ride_minutes: Math.max(15, Math.round(durMin)),
        };
      }

      const a = attractions.find(x => x.id === it.attraction_id);
      const kind: PlannedKind = a?.kind ?? "ride";
      const rideMinutes = a?.duration_minutes ?? Math.max(0, Math.round(durMin) - it.wait_minutes);
      const lockedSource = lockedById.get(it.attraction_id);
      return {
        id: lockedSource ? lockedSource.id : `${it.attraction_id}-opt-${idx}`,
        attraction_id: it.attraction_id,
        name: it.name,
        land: it.land,
        kind,
        start_minute: Math.max(0, Math.round(startMin)),
        duration_minute: Math.max(15, Math.round(durMin)),
        wait_minutes: it.wait_minutes,
        ride_minutes: rideMinutes,
        walk_minutes_from_prev: it.walk_minutes_from_prev ?? 0,
        ...(lockedSource && { locked: true, ll_window_end: lockedSource.ll_window_end }),
      };
    });
    set({ plannedItems: items });
  },
}));

function formatMin(minSinceOpen: number, parkOpen: number): string {
  const total = parkOpen * 60 + minSinceOpen;
  const h = Math.floor(total / 60) % 24;
  const m = total % 60;
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${m.toString().padStart(2, "0")} ${ampm}`;
}
