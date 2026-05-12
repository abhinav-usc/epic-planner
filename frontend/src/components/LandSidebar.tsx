import { useMemo, useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import {
  IconSparkles, IconDeviceGamepad2, IconWand, IconGhost2, IconFlame,
  IconSearch, IconStar, IconPlus,
  type Icon,
} from "@tabler/icons-react";
import { usePlanner } from "../store/plannerStore";
import type { Attraction, LandId } from "../types";


interface SidebarProps {
  onAttractionClick: (a: Attraction) => void;
  selectedId: string | null;
}

const LAND_ICONS: Record<LandId, Icon> = {
  celestial_park: IconSparkles,
  super_nintendo_world: IconDeviceGamepad2,
  ministry_of_magic: IconWand,
  isle_of_berk: IconFlame,
  dark_universe: IconGhost2,
};

function waitPillClasses(min: number): string {
  if (min <= 0) return "bg-bg-hover text-ink-muted";
  if (min <= 20) return "bg-emerald-500/15 text-emerald-300";
  if (min <= 60) return "bg-amber-500/15 text-amber-300";
  return "bg-red-500/15 text-red-300";
}

function AttractionRow({ a, color, selected, onSelect }: {
  a: Attraction; color: string; selected: boolean; onSelect: () => void;
}) {
  const { priorities, togglePriority, toggleMustDo, daySummaries, worstCaseMode } = usePlanner();
  const pri = priorities.find(p => p.attraction_id === a.id);
  const summary = daySummaries[a.id];
  const pillWait = summary
    ? (worstCaseMode ? summary.worst_case_median : summary.median_wait)
    : 0;

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `attr-${a.id}`,
    data: { attraction: a },
  });

  const showPill = (a.kind === "ride" || a.kind === "experience") && summary && pillWait > 0;

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={(e) => { e.stopPropagation(); onSelect(); }}
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
          <div className={clsx("text-[11px] leading-tight truncate", selected ? "font-medium" : "font-normal")}>
            {a.name}
          </div>
          <div className="text-[9px] text-ink-secondary mt-0.5 flex items-center gap-1 capitalize">
            <span>{a.kind}</span>
            {a.tier >= 4 && <span className="text-accent normal-case">· E-ticket</span>}
            {a.has_single_rider && <span className="normal-case">· Single rider</span>}
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
  );
}

export function LandSidebar({ onAttractionClick, selectedId }: SidebarProps) {
  const { lands, attractions } = usePlanner();
  const [query, setQuery] = useState("");
  const [showKind, setShowKind] = useState<"all" | "ride" | "show" | "experience">("all");

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return attractions.filter(a =>
      (showKind === "all" || a.kind === showKind) &&
      (q === "" || a.name.toLowerCase().includes(q) || a.land.toLowerCase().includes(q))
    );
  }, [query, showKind, attractions]);

  const byLand = useMemo(() => {
    const g: Record<string, Attraction[]> = {};
    filtered.forEach(a => {
      g[a.land] = g[a.land] || [];
      g[a.land].push(a);
    });
    return g;
  }, [filtered]);

  if (!lands) return <div className="p-4 text-ink-secondary text-xs">Loading…</div>;

  return (
    <aside className="w-72 shrink-0 border-r border-bg-hover bg-bg-panel flex flex-col">
      <div className="px-3 py-2 border-b border-bg-hover space-y-2">
        <div className="relative">
          <IconSearch size={12} stroke={1.5}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-ink-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search attractions"
            className="w-full bg-bg-card border border-bg-hover rounded-md pl-7 pr-2 py-1 text-[11px] placeholder:text-ink-muted"
            style={{ borderWidth: "0.5px" }}
          />
        </div>
        <div className="flex gap-1 text-[10px]">
          {(["all", "ride", "show", "experience"] as const).map(k => (
            <button
              key={k}
              onClick={() => setShowKind(k)}
              className={clsx(
                "px-2 py-0.5 rounded transition-colors capitalize",
                showKind === k
                  ? "bg-accent text-bg-base font-medium"
                  : "bg-bg-card text-ink-secondary hover:bg-bg-hover",
              )}
            >
              {k}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2" style={{ paddingTop: "var(--space-3)" }}>
        {Object.entries(byLand).map(([landId, items]) => {
          const land = lands[landId as LandId];
          if (!land) return null;
          const Icon = LAND_ICONS[landId as LandId];
          return (
            <section key={landId} style={{ marginBottom: "var(--space-4)" }}>
              <div className="section-label flex items-center gap-1 mb-1.5">
                {Icon && <Icon size={12} stroke={1.5} style={{ color: land.color }} />}
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
      </div>
    </aside>
  );
}
