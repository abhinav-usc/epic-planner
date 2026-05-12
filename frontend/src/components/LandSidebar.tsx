import { useMemo, useState } from "react";
import { useDraggable } from "@dnd-kit/core";
import { usePlanner } from "../store/plannerStore";
import type { Attraction, LandId } from "../types";
import clsx from "clsx";

interface SidebarProps {
  onAttractionClick: (a: Attraction) => void;
  selectedId: string | null;
}

function AttractionRow({ a, color, selected, onSelect }: {
  a: Attraction; color: string; selected: boolean; onSelect: () => void;
}) {
  const { priorities, togglePriority, toggleMustDo } = usePlanner();
  const pri = priorities.find(p => p.attraction_id === a.id);

  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `attr-${a.id}`,
    data: { attraction: a },
  });

  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      onClick={(e) => { e.stopPropagation(); onSelect(); }}
      style={{ borderLeft: `3px solid ${color}` }}
      className={clsx(
        "card px-2.5 py-2 mb-1.5 cursor-grab active:cursor-grabbing transition-colors group",
        "hover:bg-bg-hover",
        selected && "ring-1 ring-accent",
        isDragging && "opacity-30",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium truncate">{a.name}</div>
          <div className="text-xs text-ink-secondary flex items-center gap-1.5">
            <span className="capitalize">{a.kind}</span>
            {a.tier >= 4 && <span className="text-accent">· E-ticket</span>}
            {a.has_single_rider && <span>· Single Rider</span>}
            {a.showtimes && <span>· {a.showtimes.length} showtimes</span>}
          </div>
        </div>
        <div className="flex gap-1 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); toggleMustDo(a.id); if (!pri) togglePriority(a.id); }}
            className={clsx(
              "text-xs px-1.5 py-0.5 rounded transition-opacity",
              pri?.must_do ? "bg-accent text-bg-base" : "bg-bg-hover text-ink-secondary opacity-0 group-hover:opacity-100",
            )}
            title="Must-do (rope drop priority)"
          >
            ★
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); togglePriority(a.id); }}
            className={clsx(
              "text-xs px-1.5 py-0.5 rounded transition-opacity",
              pri && !pri.must_do ? "bg-bg-hover text-ink-primary" : "bg-bg-hover text-ink-secondary opacity-0 group-hover:opacity-100",
            )}
            title="Add to priorities"
          >
            +
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

  if (!lands) return <div className="p-4 text-ink-secondary text-sm">Loading…</div>;

  return (
    <aside className="w-80 shrink-0 border-r border-bg-hover bg-bg-panel flex flex-col">
      <div className="p-3 border-b border-bg-hover space-y-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="🔍 Search attractions…"
          className="w-full bg-bg-card border border-bg-hover rounded-md px-3 py-1.5 text-sm placeholder:text-ink-muted"
        />
        <div className="flex gap-1 text-xs">
          {(["all", "ride", "show", "experience"] as const).map(k => (
            <button
              key={k}
              onClick={() => setShowKind(k)}
              className={clsx(
                "px-2 py-1 rounded capitalize",
                showKind === k ? "bg-accent text-bg-base font-semibold" : "bg-bg-card text-ink-secondary hover:bg-bg-hover",
              )}
            >
              {k}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {Object.entries(byLand).map(([landId, items]) => {
          const land = lands[landId as LandId];
          if (!land) return null;
          return (
            <section key={landId}>
              <div className="flex items-center gap-2 mb-1.5 text-sm font-semibold">
                <span style={{ color: land.color }} className="text-base">{land.icon}</span>
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
          <div className="text-ink-muted text-sm text-center mt-12">No attractions match.</div>
        )}
      </div>
    </aside>
  );
}
