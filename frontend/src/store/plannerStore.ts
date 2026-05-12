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
  apiKey: string;

  // Crowd forecast for current date
  forecast: CrowdForecast | null;

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
  setApiKey: (k: string) => void;
  addPlannedItem: (a: Attraction, startMinute: number, waitMinutes: number) => void;
  movePlannedItem: (id: string, startMinute: number) => void;
  removePlannedItem: (id: string) => void;
  togglePriority: (attractionId: string) => void;
  toggleMustDo: (attractionId: string) => void;
  setRank: (attractionId: string, rank: number) => void;
  runOptimize: () => Promise<void>;
  applyOptimizeResultToTimeline: () => void;
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
  apiKey: typeof window !== "undefined" ? localStorage.getItem("anthropic_api_key") || "" : "",

  forecast: null,
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
  },

  setEarlyEntry: (v) => set({ earlyEntry: v }),

  setApiKey: (k) => {
    if (typeof window !== "undefined") localStorage.setItem("anthropic_api_key", k);
    set({ apiKey: k });
  },

  addPlannedItem: (a, startMinute, waitMinutes) => {
    const id = `${a.id}-${Date.now()}`;
    const duration = waitMinutes + a.duration_minutes;
    set(s => ({
      plannedItems: [...s.plannedItems, {
        id, attraction_id: a.id, name: a.name, land: a.land,
        start_minute: startMinute, duration_minute: duration, wait_minutes: waitMinutes,
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
