import { useMemo, useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import {
  IconSparkles, IconDeviceGamepad2, IconWand, IconGhost2, IconFlame,
  IconSearch, IconStar, IconPlus, IconLayoutSidebarLeftCollapse, IconLayoutSidebarLeftExpand,
  IconClock, IconToolsKitchen2, IconRollercoaster, IconTheater, IconDiamond, IconCategory,
  type Icon,
} from "@tabler/icons-react";
import { usePlanner } from "../store/plannerStore";
import type { Attraction, LandId, Restaurant } from "../types";


const SERVICE_BADGE: Record<string, string> = {
  full:  "bg-indigo-500/20 text-indigo-300",
  quick: "bg-emerald-500/20 text-emerald-300",
  bar:   "bg-violet-500/20 text-violet-300",
  snack: "bg-amber-500/20 text-amber-300",
  cart:  "bg-slate-500/20 text-slate-300",
};

interface SidebarProps {
  onAttractionClick: (a: Attraction) => void;
  onRestaurantClick: (r: Restaurant) => void;
  selectedId: string | null;
  open: boolean;
  onToggle: () => void;
  mobileOpen?: boolean;
}

const LAND_ICONS: Partial<Record<LandId, Icon>> = {
  // Epic Universe
  celestial_park: IconSparkles,
  super_nintendo_world: IconDeviceGamepad2,
  ministry_of_magic: IconWand,
  isle_of_berk: IconFlame,
  dark_universe: IconGhost2,
  // Magic Kingdom
  mk_main_street: IconCategory,
  mk_fantasyland: IconWand,
  mk_tomorrowland: IconRollercoaster,
  mk_adventureland: IconCategory,
  mk_liberty_square: IconCategory,
  mk_frontierland: IconCategory,
  // EPCOT
  ep_world_discovery: IconSparkles,
  ep_world_nature: IconCategory,
  ep_world_celebration: IconCategory,
  ep_world_showcase: IconCategory,
  // Hollywood Studios
  hs_galaxys_edge: IconSparkles,
  hs_toy_story_land: IconCategory,
  hs_sunset_boulevard: IconFlame,
  hs_echo_lake: IconCategory,
  hs_grand_avenue: IconTheater,
  hs_animation_courtyard: IconTheater,
  hs_hollywood_boulevard: IconCategory,
  // Animal Kingdom
  ak_pandora: IconSparkles,
  ak_africa: IconCategory,
  ak_asia: IconCategory,
  ak_discovery_island: IconCategory,
  ak_dinoland: IconCategory,
};

function waitPillClasses(min: number): string {
  if (min <= 0) return "bg-bg-hover text-ink-muted";
  if (min <= 20) return "chip-ok";
  if (min <= 60) return "chip-warn";
  return "chip-bad";
}

function ShowtimePicker({ a, onClose }: { a: Attraction; onClose: () => void }) {
  const { earlyEntry, placeAttraction, priorities, setShowtime } = usePlanner();
  const pri = priorities.find(p => p.attraction_id === a.id);

  return (
    <div className="mt-1 mb-1 card p-2 space-y-1">
      <div className="text-[10px] text-ink-secondary font-medium flex items-center justify-between">
        <span>Pick a showtime</span>
        <button onClick={onClose} className="text-ink-muted hover:text-ink-primary">✕</button>
      </div>
      {(a.showtimes ?? []).map(st => {
        const [hh, mm] = st.split(":").map(Number);
        const openH = earlyEntry ? 8 : 9;
        const startMin = (hh - openH) * 60 + mm - 15; // queue 15min before
        const isChosen = pri?.chosen_showtime === st;
        return (
          <button
            key={st}
            onClick={() => {
              setShowtime(a.id, st);
              placeAttraction(a, startMin);
              onClose();
            }}
            className={clsx(
              "w-full text-left px-2 py-1 rounded text-[11px] transition-colors",
              isChosen
                ? "bg-accent text-bg-base font-medium"
                : "bg-bg-hover hover:bg-bg-card text-ink-primary",
            )}
          >
            <IconClock size={10} stroke={1.5} className="inline mr-1" />
            {st}
          </button>
        );
      })}
    </div>
  );
}

function AttractionRow({ a, color, selected, onSelect }: {
  a: Attraction; color: string; selected: boolean; onSelect: () => void;
}) {
  const { priorities, togglePriority, toggleMustDo, daySummaries, worstCaseMode } = usePlanner();
  const [showPicker, setShowPicker] = useState(false);
  const pri = priorities.find(p => p.attraction_id === a.id);
  const summary = daySummaries[a.id];
  const pillWait = summary
    ? (worstCaseMode ? summary.worst_case_median : summary.median_wait)
    : 0;

  const isShow = a.kind === "show" && (a.showtimes?.length ?? 0) > 0;

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `attr-${a.id}`,
    data: { attraction: a },
  });

  const showPill = (a.kind === "ride" || a.kind === "experience") && summary && pillWait > 0;

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isShow) {
      setShowPicker(v => !v);
    } else {
      onSelect();
    }
  };

  return (
    <>
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={handleClick}
      style={{ borderLeft: `2px solid ${color}` }}
      className={clsx(
        "card row-item cursor-grab active:cursor-grabbing transition-colors group",
        "hover:bg-bg-hover",
        selected && "ring-1 ring-accent",
        isDragging && "opacity-30",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className={clsx("text-[12px] leading-snug truncate", selected ? "font-medium" : "font-normal")}>
            {a.name}
          </div>
          <div className="text-[10px] text-ink-secondary mt-1 flex items-center gap-1 capitalize">
            <span>{a.kind}</span>
            {a.tier >= 4 && <span className="text-accent normal-case">· E-ticket</span>}
            {a.has_single_rider && <span className="normal-case">· Single rider</span>}
            {a.ll_type === "single" && <span className="text-purple-400 normal-case">· ⚡ LLSP</span>}
            {a.ll_type === "multi" && <span className="text-purple-400 normal-case">· ⚡ LLMP</span>}
            {a.showtimes && <span className="normal-case">· {a.showtimes.length} showtimes</span>}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {showPill && (
            <span className={clsx("chip", waitPillClasses(pillWait))} title="Median predicted wait for this day">
              {pillWait}m
            </span>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); toggleMustDo(a.id); if (!pri) togglePriority(a.id); }}
            onPointerDown={(e) => e.stopPropagation()}
            className={clsx(
              "text-[10px] w-5 h-5 rounded flex items-center justify-center transition-opacity",
              pri?.must_do
                ? "bg-accent text-bg-base"
                : "bg-bg-hover text-ink-secondary opacity-0 group-hover:opacity-100",
            )}
            title="Must-do (rope drop priority)"
          >
            <IconStar size={10} stroke={2} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); togglePriority(a.id); }}
            onPointerDown={(e) => e.stopPropagation()}
            className={clsx(
              "text-[10px] w-5 h-5 rounded flex items-center justify-center transition-opacity",
              pri && !pri.must_do
                ? "bg-bg-hover text-ink-primary"
                : "bg-bg-hover text-ink-secondary opacity-0 group-hover:opacity-100",
            )}
            title="Add to priorities"
          >
            <IconPlus size={10} stroke={2} />
          </button>
        </div>
      </div>
    </div>
    {showPicker && isShow && (
      <ShowtimePicker a={a} onClose={() => setShowPicker(false)} />
    )}
    </>
  );
}

function RestaurantRow({ r, color, selected, onSelect }: {
  r: Restaurant; color: string; selected: boolean; onSelect: () => void;
}) {
  const badge = SERVICE_BADGE[r.service] ?? "bg-bg-hover text-ink-muted";
  return (
    <div
      onClick={onSelect}
      style={{ borderLeft: `2px solid ${color}` }}
      className={clsx(
        "card row-item cursor-pointer transition-colors hover:bg-bg-hover",
        selected && "ring-1 ring-accent",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className={clsx("text-[12px] leading-snug truncate", selected ? "font-medium" : "font-normal")}>
            {r.name}
          </div>
          <div className="text-[10px] text-ink-secondary mt-1 flex items-center gap-1">
            <span className={clsx("chip", badge)}>{r.service === "full" ? "Table" : r.service}</span>
            <span className="truncate text-ink-muted">{r.cuisine}</span>
          </div>
        </div>
        <div className="text-[10px] text-ink-muted shrink-0 flex items-center gap-0.5 mt-0.5">
          <IconClock size={9} stroke={1.5} />
          {r.avg_meal_minutes}m
        </div>
      </div>
    </div>
  );
}

export function LandSidebar({ onAttractionClick, onRestaurantClick, selectedId, open, onToggle, mobileOpen }: SidebarProps) {
  const { lands, attractions, restaurants } = usePlanner();
  const [query, setQuery] = useState("");
  const [showKind, setShowKind] = useState<"all" | "ride" | "show" | "experience" | "restaurant">("ride");

  const isRestaurantTab = showKind === "restaurant";

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return attractions.filter(a =>
      (showKind === "all" || a.kind === showKind) &&
      (q === "" || a.name.toLowerCase().includes(q) || a.land.toLowerCase().includes(q))
    );
  }, [query, showKind, attractions]);

  const filteredRestaurants = useMemo(() => {
    const q = query.toLowerCase();
    return restaurants.filter(r =>
      q === "" || r.name.toLowerCase().includes(q) || r.cuisine.toLowerCase().includes(q) || r.land.toLowerCase().includes(q)
    );
  }, [query, restaurants]);

  const byLand = useMemo(() => {
    const g: Record<string, Attraction[]> = {};
    filtered.forEach(a => {
      g[a.land] = g[a.land] || [];
      g[a.land].push(a);
    });
    return g;
  }, [filtered]);

  const restaurantsByLand = useMemo(() => {
    const g: Record<string, Restaurant[]> = {};
    filteredRestaurants.forEach(r => {
      g[r.land] = g[r.land] || [];
      g[r.land].push(r);
    });
    return g;
  }, [filteredRestaurants]);

  return (
    <aside className={clsx(
      "shrink-0 border-r border-bg-hover bg-bg-panel flex flex-col transition-all duration-200",
      mobileOpen
        ? "fixed inset-0 z-40 w-full"
        : open ? "w-80" : "w-9",
    )}>
      {!mobileOpen && !open ? (
        /* Collapsed strip — icon right-aligned, near the timeline edge */
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-end pr-2 py-2.5 text-ink-muted hover:text-ink-primary hover:bg-bg-hover transition-colors shrink-0"
          title="Expand sidebar"
        >
          <IconLayoutSidebarLeftExpand size={15} stroke={1.5} />
        </button>
      ) : (
        <>
          {!lands && <div className="p-4 text-ink-secondary text-xs">Loading…</div>}

          {lands && (
            <>
              {/* Header row: title left, collapse button right (near timeline edge) */}
              <div className="flex items-center justify-between pl-3 pr-1 py-2 border-b border-bg-hover shrink-0">
                <h2 className="text-sm font-medium">Attractions</h2>
                <button
                  onClick={onToggle}
                  className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted hover:text-ink-primary hover:bg-bg-hover transition-colors"
                  title="Collapse sidebar"
                >
                  <IconLayoutSidebarLeftCollapse size={15} stroke={1.5} />
                </button>
              </div>

              <div className="px-3 py-2.5 border-b border-bg-hover space-y-2">
                <div className="relative">
                  <IconSearch size={13} stroke={1.5}
                    className="absolute left-2 top-1/2 -translate-y-1/2 text-ink-muted" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search attractions"
                    className="w-full bg-bg-card border border-bg-hover rounded-md pl-7 pr-2 py-1.5 text-[12px] placeholder:text-ink-muted"
                    style={{ borderWidth: "0.5px" }}
                  />
                </div>
                <div className="flex gap-1 text-[11px] flex-wrap">
                  {([
                    { key: "ride",       label: "Rides",  icon: IconRollercoaster },
                    { key: "show",       label: "Shows",  icon: IconTheater },
                    { key: "experience", label: "Exp",    icon: IconDiamond },
                    { key: "restaurant", label: "Dining", icon: IconToolsKitchen2 },
                    { key: "all",        label: "All",    icon: IconCategory },
                  ] as const).map(({ key, label, icon: Tab }) => (
                    <button
                      key={key}
                      onClick={() => setShowKind(key)}
                      className={clsx(
                        "px-2 py-0.5 rounded transition-colors flex items-center gap-1",
                        showKind === key
                          ? "bg-accent text-bg-base font-medium"
                          : "bg-bg-card text-ink-secondary hover:bg-bg-hover",
                      )}
                    >
                      <Tab size={10} stroke={1.5} />
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-3 py-2" style={{ paddingTop: "var(--space-4)" }}>
                {isRestaurantTab ? (
                  <>
                    {Object.entries(restaurantsByLand).map(([landId, items]) => {
                      const land = lands[landId as LandId];
                      if (!land) return null;
                      const LandIcon = LAND_ICONS[landId as LandId];
                      return (
                        <section key={landId} style={{ marginBottom: "var(--space-5)" }}>
                          <div className="section-label flex items-center gap-1 mb-2">
                            {LandIcon && <LandIcon size={13} stroke={1.5} style={{ color: land.color }} />}
                            <span className="truncate">{land.name}</span>
                          </div>
                          <div>
                            {items.map(r => (
                              <RestaurantRow
                                key={r.id}
                                r={r}
                                color={land.color}
                                selected={selectedId === r.id}
                                onSelect={() => onRestaurantClick(r)}
                              />
                            ))}
                          </div>
                        </section>
                      );
                    })}
                    {filteredRestaurants.length === 0 && (
                      <div className="text-ink-muted text-xs text-center mt-12">No restaurants match.</div>
                    )}
                  </>
                ) : (
                  <>
                    {Object.entries(byLand).map(([landId, items]) => {
                      const land = lands[landId as LandId];
                      if (!land) return null;
                      const LandIcon = LAND_ICONS[landId as LandId];
                      return (
                        <section key={landId} style={{ marginBottom: "var(--space-5)" }}>
                          <div className="section-label flex items-center gap-1 mb-2">
                            {LandIcon && <LandIcon size={13} stroke={1.5} style={{ color: land.color }} />}
                            <span className="truncate">{land.name}</span>
                          </div>
                          <div>
                            {items.map(a => (
                              <AttractionRow
                                key={a.id}
                                a={a}
                                color={land.color}
                                selected={selectedId === a.id}
                                onSelect={() => onAttractionClick(a)}
                              />
                            ))}
                          </div>
                        </section>
                      );
                    })}
                    {filtered.length === 0 && (
                      <div className="text-ink-muted text-xs text-center mt-12">No attractions match.</div>
                    )}
                  </>
                )}
              </div>
            </>
          )}
        </>
      )}
    </aside>
  );
}
