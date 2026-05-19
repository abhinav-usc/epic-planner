// Epic Universe park ID
export type EpicParkId = "epic_universe";

// Disney WDW park IDs
export type DisneyParkId =
  | "magic_kingdom"
  | "epcot"
  | "hollywood_studios"
  | "animal_kingdom";

// Disneyland Resort
export type DisneylandParkId = "disneyland";

export type ParkId = EpicParkId | DisneyParkId | DisneylandParkId;

export type LandId =
  // Epic Universe
  | "celestial_park"
  | "super_nintendo_world"
  | "ministry_of_magic"
  | "isle_of_berk"
  | "dark_universe"
  // Magic Kingdom
  | "mk_main_street"
  | "mk_fantasyland"
  | "mk_tomorrowland"
  | "mk_adventureland"
  | "mk_liberty_square"
  | "mk_frontierland"
  // EPCOT
  | "ep_world_discovery"
  | "ep_world_nature"
  | "ep_world_celebration"
  | "ep_world_showcase"
  // Hollywood Studios
  | "hs_galaxys_edge"
  | "hs_toy_story_land"
  | "hs_sunset_boulevard"
  | "hs_echo_lake"
  | "hs_grand_avenue"
  | "hs_animation_courtyard"
  | "hs_hollywood_boulevard"
  // Animal Kingdom
  | "ak_pandora"
  | "ak_africa"
  | "ak_asia"
  | "ak_discovery_island"
  | "ak_dinoland"
  // Disneyland Park
  | "dl_main_street"
  | "dl_adventureland"
  | "dl_new_orleans_sq"
  | "dl_frontierland"
  | "dl_fantasyland"
  | "dl_tomorrowland"
  | "dl_galaxys_edge"
  | "dl_toontown";

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
  ll_type?: "single" | "multi" | null;
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
  description: string;
  menu_highlights: string[];
  url: string;
  wait_notes: string;
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
  ll_return_minutes: number | null;  // 0 = LLSP (immediate), >0 = LLMP return window, null = no LL
  worst_case_wait: number | null;
  worst_case_n: number;
  crowd_multiplier: number;
}

export interface DayCurve {
  attraction_id: string;
  date: string;
  hours: HourPrediction[];
  source?: "actual" | "predicted";
}

export interface PriorityItem {
  attraction_id: string;
  must_do: boolean;
  rank: number;
  chosen_showtime?: string | null;  // "HH:MM" for shows
}

export interface FoodBreakConfig {
  duration_minutes: number;
  earliest_hour: number;
  latest_hour: number;
  /** If set, the break is pinned to this exact start (minutes since park open, 15-min grid). */
  start_minute?: number;
  /** If set together with start_minute, duration = end_minute - start_minute. */
  end_minute?: number;
}

export interface ShoppingBreakConfig {
  land: LandId;
  duration_minutes: number;
}

export interface ItineraryItem {
  attraction_id: string;
  name: string;
  land: LandId | "break";
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

export interface HistoryDateSummary {
  date: string;
  attraction_count: number;
  avg_wait: number;
  peak_wait: number;
}

export interface HistoryAttractionDay {
  slug: string;
  name: string;
  land: string;
  color: string;
  hours: { hour: number; wait_minutes: number | null }[];
  avg_wait: number;
  peak_wait: number;
}

export interface HistoryDayDetail {
  date: string;
  attractions: HistoryAttractionDay[];
}

export interface FeasibilityDateResult {
  date: string;
  passed: boolean;
  total_minutes: number;
  overrun: number;
}

export interface FeasibilityRideStat {
  name: string;
  planned_wait: number;
  avg_actual_wait: number;
  days_with_data: number;
}

export interface FeasibilityResult {
  days_checked: number;
  days_passed: number;
  pass_rate: number | null;
  planned_end_minutes: number;
  avg_actual_end_minutes: number;
  avg_overrun_minutes: number;
  slack_minutes: number;
  ride_stats: FeasibilityRideStat[];
  sample_failures: FeasibilityDateResult[];
  all_results: FeasibilityDateResult[];
  error?: string;
}

export interface LiveCalibration {
  park_wide_factor: number;
  by_ride_factor: Record<string, number>;
  samples_used: number;
  minutes_of_history: number;
}

export interface LiveRideWait {
  attraction_id: string;
  wait_minutes: number;
  is_open: boolean;
}

export interface LivePollResponse {
  park: ParkId;
  fetched_at: string;
  rides: LiveRideWait[];
  calibration: LiveCalibration;
}

export interface LLBooking {
  attraction_id: string;
  attraction_name: string;
  book_at_minute: number;          // 0 = at park open
  predicted_return_minute: number; // earliest available return time (from park open)
  savings_minutes: number;
  priority: "urgent" | "normal" | "skip";
  reason: string;
}

export interface LLPlanResponse {
  bookings: LLBooking[];
  park_open_minute: number;
  park_close_minute: number;
  day_crowd_multiplier: number;
}

export interface SavedPlan {
  id: string;
  date: string;
  name: string;
  savedAt: string;       // ISO timestamp
  earlyEntry: boolean;
  items: PlannedItem[];  // snapshot of the full planned item list
}

export type PlannedKind = AttractionKind | "break_food" | "break_shop";

/** UI-only: an item in the user's manual plan (before optimization). */
export interface PlannedItem {
  id: string;            // unique within the plan
  attraction_id: string;
  name: string;
  land: LandId | "break";
  kind: PlannedKind;
  start_minute: number;  // minutes since park open (0 = 8 AM or 9 AM)
  duration_minute: number;
  wait_minutes: number;
  ride_minutes: number;  // visible ride/show duration (block - wait)
  worst_case_wait?: number;  // historical 90th-percentile wait
  showtime_minute?: number;  // for shows: the actual show start time
  walk_minutes_from_prev?: number;  // minutes to walk from previous item's land
  done?: boolean;        // user marked this ride/show as completed during trip
  locked?: boolean;      // pre-booked LLSP — fixed time slot, optimizer works around it
  ll_window_end?: number; // end of the 60-min return window (minutes since open)
}
