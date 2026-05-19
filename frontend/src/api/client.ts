import type {
  Attraction,
  CrowdForecast,
  DayCurve,
  FeasibilityResult,
  FoodBreakConfig,
  HistoryDateSummary,
  HistoryDayDetail,
  Land,
  LandId,
  LivePollResponse,
  LLPlanResponse,
  OptimizeResponse,
  ParkId,
  PriorityItem,
  Restaurant,
  ShoppingBreakConfig,
} from "../types";

const apiKey = () => localStorage.getItem("anthropic_api_key") || "";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return (await res.json()) as T;
}

export const api = {
  async parks(): Promise<Record<ParkId, { name: string; icon: string; description: string; open_hour: number; close_hour: number }>> {
    return jsonFetch("/api/parks");
  },
  async lands(park: ParkId = "epic_universe"): Promise<Record<LandId, Land>> {
    return jsonFetch(`/api/lands?park=${park}`);
  },
  async attractions(park: ParkId = "epic_universe"): Promise<Attraction[]> {
    return jsonFetch(`/api/attractions?park=${park}`);
  },
  async restaurants(park: ParkId = "epic_universe"): Promise<Restaurant[]> {
    return jsonFetch(`/api/restaurants?park=${park}`);
  },
  async crowdForecast(date: string): Promise<CrowdForecast> {
    return jsonFetch(`/api/crowd/forecast/${date}`);
  },
  async dayCurve(attractionId: string, date: string, earlyEntry = false, park: ParkId = "epic_universe", liveCalibration = false): Promise<DayCurve> {
    return jsonFetch(`/api/attractions/${attractionId}/wait-times?target_date=${date}&early_entry=${earlyEntry}&park=${park}&live_calibration=${liveCalibration}`);
  },
  async dayCurvesBatch(attractionIds: string[], date: string, earlyEntry = false, park: ParkId = "epic_universe", liveCalibration = false): Promise<Record<string, DayCurve>> {
    return jsonFetch("/api/day-curves-batch", {
      method: "POST",
      body: JSON.stringify({ attraction_ids: attractionIds, target_date: date, early_entry: earlyEntry, park, live_calibration: liveCalibration }),
    });
  },
  async livePoll(park: ParkId): Promise<LivePollResponse> {
    return jsonFetch("/api/live/poll", {
      method: "POST",
      body: JSON.stringify({ park }),
    });
  },
  async optimize(params: {
    target_date: string;
    early_entry: boolean;
    priorities: PriorityItem[];
    rope_drop_land?: string | null;
    arrival_hour?: number;
    break_minutes?: number;
    food_breaks?: FoodBreakConfig[];
    shopping_breaks?: ShoppingBreakConfig[];
    park_id?: ParkId;
    use_ll_multi?: boolean;
    ll_single_ids?: string[];
    ll_reservations?: { attraction_id: string; window_start_minute: number }[];
    land_hopping?: boolean;
  }): Promise<OptimizeResponse> {
    return jsonFetch("/api/optimize", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },
  async aiChat(prompt: string, context?: any): Promise<{ reply: string }> {
    return jsonFetch("/api/ai/chat", {
      method: "POST",
      headers: { "X-Anthropic-Key": apiKey() },
      body: JSON.stringify({ prompt, context }),
    });
  },
  async aiEvaluate(items: any[], target_date: string, crowd_label?: string | null): Promise<{ reply: string }> {
    return jsonFetch("/api/ai/evaluate", {
      method: "POST",
      headers: { "X-Anthropic-Key": apiKey() },
      body: JSON.stringify({ items, target_date, crowd_label }),
    });
  },
  async aiResearch(topic: string, kind = "restaurant"): Promise<{ reply: string }> {
    return jsonFetch("/api/ai/research", {
      method: "POST",
      headers: { "X-Anthropic-Key": apiKey() },
      body: JSON.stringify({ topic, kind }),
    });
  },
  async historyDates(park = "epic_universe"): Promise<HistoryDateSummary[]> {
    return jsonFetch(`/api/history/dates?park=${park}`);
  },
  async historyDay(date: string, park = "epic_universe"): Promise<HistoryDayDetail> {
    return jsonFetch(`/api/history/day/${date}?park=${park}`);
  },
  async feasibility(params: {
    items: {
      name: string; land: string;
      start_minute: number; wait_minutes: number;
      ride_minutes: number; duration_minute: number; kind: string;
    }[];
    park_open_hour: number;
    arrival_minute?: number;
  }): Promise<FeasibilityResult> {
    return jsonFetch("/api/history/feasibility", { method: "POST", body: JSON.stringify(params) });
  },
  async llPlan(params: {
    target_date: string;
    park: ParkId;
    early_entry: boolean;
    rides: { attraction_id: string; planned_minute: number; must_do: boolean }[];
    arrival_minute?: number;
    ll_reserved_ids?: string[];
  }): Promise<LLPlanResponse> {
    return jsonFetch("/api/ll-plan", {
      method: "POST",
      body: JSON.stringify(params),
    });
  },
  async dataFreshness(): Promise<{
    latest_epic_date: string | null;
    latest_park_date: string | null;
    epic_age_days: number | null;
    park_age_days: number | null;
    needs_refresh: boolean;
    refresh_running: boolean;
  }> {
    return jsonFetch("/api/data/freshness");
  },
  async dataRefresh(): Promise<{ started: boolean; reason: string }> {
    return jsonFetch("/api/data/refresh", { method: "POST" });
  },
};
