import { create } from "zustand";
import type {
  Attraction,
  CrowdForecast,
  Land,
  LandId,
  OptimizeResponse,
  PlannedItem,
  PriorityItem,
  Restaurant,
} from "../types";
import { api } from "../api/client";

/** Median wait + worst-case wait per attraction for the current target date. */
export interface AttractionDaySummary {
  median_wait: number;
  worst_case_median: number;
}

interface PlannerState {
  // Catalog
  lands: Record<LandId, Land> | null;
  attractions: Attraction[];
  restaurants: Restaurant[];
  loaded: boolean;
  catalogError: string | null;

  // Settings
  targetDate: string;        // YYYY-MM-DD
  earlyEntry: boolean;
  worstCaseMode: boolean;    // when true, timeline uses worst-case wait for height
  apiKey: string;

  // Crowd forecast for current date
  forecast: CrowdForecast | null;

  // Per-attraction summary for the current date (used by left-rail wait pills
  // and the timeline when worstCaseMode is on)
  daySummaries: Record<string, AttractionDaySummary>;

  // Manual itinerary
  plannedItems: PlannedItem[];

  // Optimizer-driven priorities
  priorities: PriorityItem[];
  optimizing: boolean;
  optimizeResult: OptimizeResponse | null;

  // Actions
  loadCatalog: () => Promise<void>;
  setDate: (d: string) => Promise<void>;
  setEarlyEntry: (v: boolean) => void;
  setWorstCaseMode: (v: boolean) => void;
  setApiKey: (k: string) => void;
  addPlannedItem: (a: Attraction, startMinute: number, waitMinutes: number, worstCaseWait?: number) => void;
  movePlannedItem: (id: string, startMinute: number) => void;
  removePlannedItem: (id: string) => void;
  togglePriority: (attractionId: string) => void;
  toggleMustDo: (attractionId: string) => void;
  setRank: (attractionId: string, rank: number) => void;
  runOptimize: () => Promise<void>;
  applyOptimizeResultToTimeline: () => void;
  refreshDaySummaries: () => Promise<void>;
}

const todaysDefault = "2026-05-25";  // Memorial Day Monday

export const usePlanner = create<PlannerState>((set, get) => ({
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
  daySummaries: {},
  plannedItems: [],
  priorities: [],
  optimizing: false,
  optimizeResult: null,

  loadCatalog: async () => {
    try {
      const [lands, attractions, restaurants, forecast] = await Promise.all([
        api.lands(),
        api.attractions(),
        api.restaurants(),
        api.crowdForecast(get().targetDate),
      ]);
      set({ lands, attractions, restaurants, forecast, loaded: true, catalogError: null });
      // kick off summary refresh in the background
      get().refreshDaySummaries();
    } catch (e: any) {
      set({ catalogError: e.message ?? String(e), loaded: false });
    }
  },

  setDate: async (d: string) => {
    set({ targetDate: d });
    try {
      const forecast = await api.crowdForecast(d);
      set({ forecast });
    } catch {/* ignore */}
    get().refreshDaySummaries();
  },

  setEarlyEntry: (v) => set({ earlyEntry: v }),
  setWorstCaseMode: (v) => set({ worstCaseMode: v }),

  setApiKey: (k) => {
    if (typeof window !== "undefined") localStorage.setItem("anthropic_api_key", k);
    set({ apiKey: k });
  },

  addPlannedItem: (a, startMinute, waitMinutes, worstCaseWait) => {
    const id = `${a.id}-${Date.now()}`;
    const wait = Math.max(0, Math.round(waitMinutes || 0));
    const duration = wait + a.duration_minutes;
    set(s => ({
      plannedItems: [...s.plannedItems, {
        id, attraction_id: a.id, name: a.name, land: a.land,
        start_minute: Math.max(0, Math.round(startMinute)),
        duration_minute: duration,
        wait_minutes: wait,
        worst_case_wait: worstCaseWait != null ? Math.round(worstCaseWait) : undefined,
      }],
    }));
  },

  movePlannedItem: (id, startMinute) => {
    set(s => ({
      plannedItems: s.plannedItems.map(p =>
        p.id === id ? { ...p, start_minute: Math.max(0, startMinute) } : p,
      ),
    }));
  },

  removePlannedItem: (id) => {
    set(s => ({ plannedItems: s.plannedItems.filter(p => p.id !== id) }));
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

  runOptimize: async () => {
    set({ optimizing: true });
    try {
      const result = await api.optimize({
        target_date: get().targetDate,
        early_entry: get().earlyEntry,
        priorities: get().priorities,
      });
      set({ optimizeResult: result, optimizing: false });
    } catch (e: any) {
      set({ optimizing: false, optimizeResult: null });
      alert(`Optimization failed: ${e.message ?? e}`);
    }
  },

  refreshDaySummaries: async () => {
    // Pull the day-curve for every ride/experience in parallel; cache the
    // median predicted wait and the median worst-case so the left-rail can
    // show a representative pill per attraction.
    const { attractions, targetDate, earlyEntry } = get();
    if (!attractions.length) return;
    const targets = attractions.filter(a => a.kind === "ride" || a.kind === "experience");
    const summaries: Record<string, AttractionDaySummary> = {};
    await Promise.all(
      targets.map(async a => {
        try {
          const curve = await api.dayCurve(a.id, targetDate, earlyEntry);
          const waits = curve.hours.map(h => h.wait_minutes).filter(n => Number.isFinite(n));
          const worst = curve.hours
            .map(h => h.worst_case_wait)
            .filter((n): n is number => n != null);
          const median = (arr: number[]) => {
            if (!arr.length) return 0;
            const s = [...arr].sort((x, y) => x - y);
            const m = Math.floor(s.length / 2);
            return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2);
          };
          summaries[a.id] = {
            median_wait: median(waits),
            worst_case_median: median(worst),
          };
        } catch {/* skip */}
      }),
    );
    set({ daySummaries: summaries });
  },

  applyOptimizeResultToTimeline: () => {
    const r = get().optimizeResult;
    if (!r) return;
    const dayStart = get().earlyEntry ? 8 : 9;
    const items: PlannedItem[] = r.items.map((it, idx) => {
      const start = new Date(it.start_time);
      const end = new Date(it.end_time);
      const startMin = start.getHours() * 60 + start.getMinutes() - dayStart * 60;
      const durMin = (end.getTime() - start.getTime()) / 60000;
      return {
        id: `${it.attraction_id}-opt-${idx}`,
        attraction_id: it.attraction_id,
        name: it.name,
        land: it.land,
        start_minute: Math.max(0, Math.round(startMin)),
        duration_minute: Math.max(15, Math.round(durMin)),
        wait_minutes: it.wait_minutes,
      };
    });
    set({ plannedItems: items });
  },
}));
