export type LandId =
  | "celestial_park"
  | "super_nintendo_world"
  | "ministry_of_magic"
  | "isle_of_berk"
  | "dark_universe";

export interface Land {
  name: string;
  color: string;
  icon: string;
  description: string;
}

export type AttractionKind = "ride" | "show" | "restaurant" | "experience";

export interface Attraction {
  id: string;
  name: string;
  land: LandId;
  kind: AttractionKind;
  tier: number;
  duration_minutes: number;
  capacity_per_hour: number | null;
  has_single_rider: boolean;
  has_express: boolean;
  height_inches: number | null;
  queue_times_id: number | null;
  showtimes: string[] | null;
  description: string;
}

export interface Restaurant {
  id: string;
  name: string;
  land: LandId;
  service: string;
  cuisine: string;
  avg_meal_minutes: number;
  reservations: boolean;
  popular_dish: string;
}

export interface CrowdForecast {
  date: string;
  crowd_level: number;
  base_multiplier: number;
  holiday_label: string | null;
  novelty_multiplier: number;
  dow_multiplier: number;
  month_multiplier: number;
  hourly_multipliers: Record<string, number>;
}

export interface HourPrediction {
  hour: number;
  wait_minutes: number;
  crowd_multiplier: number;
}

export interface DayCurve {
  attraction_id: string;
  date: string;
  hours: HourPrediction[];
}

export interface PriorityItem {
  attraction_id: string;
  must_do: boolean;
  rank: number;
}

export interface ItineraryItem {
  attraction_id: string;
  name: string;
  land: LandId;
  start_time: string;
  end_time: string;
  wait_minutes: number;
  activity_minutes: number;
  walk_minutes_from_prev: number;
  notes: string[];
}

export interface OptimizeResponse {
  target_date: string;
  items: ItineraryItem[];
  total_wait_minutes: number;
  total_activity_minutes: number;
  feasible: boolean;
  warnings: string[];
}

/** UI-only: an item in the user's manual plan (before optimization). */
export interface PlannedItem {
  id: string;            // unique within the plan
  attraction_id: string;
  name: string;
  land: LandId;
  start_minute: number;  // minutes since park open (0 = 8 AM or 9 AM)
  duration_minute: number;
  wait_minutes: number;
}
