import type {
  Attraction,
  CrowdForecast,
  DayCurve,
  Land,
  LandId,
  OptimizeResponse,
  PriorityItem,
  Restaurant,
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
  async lands(): Promise<Record<LandId, Land>> {
    return jsonFetch("/api/lands");
  },
  async attractions(): Promise<Attraction[]> {
    return jsonFetch("/api/attractions");
  },
  async restaurants(): Promise<Restaurant[]> {
    return jsonFetch("/api/restaurants");
  },
  async crowdForecast(date: string): Promise<CrowdForecast> {
    return jsonFetch(`/api/crowd/forecast/${date}`);
  },
  async dayCurve(attractionId: string, date: string, earlyEntry = false): Promise<DayCurve> {
    return jsonFetch(`/api/attractions/${attractionId}/wait-times?target_date=${date}&early_entry=${earlyEntry}`);
  },
  async optimize(params: {
    target_date: string;
    early_entry: boolean;
    priorities: PriorityItem[];
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
};
