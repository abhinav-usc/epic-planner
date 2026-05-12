import { useDroppable, useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import { usePlanner } from "../store/plannerStore";
import { minutesToTimeLabel } from "../lib/format";
import type { PlannedItem, LandId } from "../types";

const PX_PER_MIN = 1.4;          // 1 hour = 84 px
const PARK_OPEN_HOUR = 9;
const PARK_OPEN_HOUR_EARLY = 8;
const PARK_CLOSE_HOUR = 22;

function ItineraryBar({ item, color }: { item: PlannedItem; color: string }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `plan-${item.id}`,
    data: { plannedItem: item },
  });
  const { removePlannedItem } = usePlanner();

  const style: React.CSSProperties = {
    top: item.start_minute * PX_PER_MIN,
    height: Math.max(36, item.duration_minute * PX_PER_MIN),
    backgroundColor: `${color}22`,
    borderLeft: `4px solid ${color}`,
    transform: transform ? `translate3d(0, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.6 : 1,
  };
  const ride = Math.max(0, item.duration_minute - item.wait_minutes);

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className="absolute left-1 right-1 rounded-md px-2.5 py-1 cursor-grab active:cursor-grabbing
                 hover:ring-1 hover:ring-accent group transition-shadow z-10"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-xs font-semibold truncate leading-tight">{item.name}</div>
          <div className="text-[10px] text-ink-secondary mt-0.5">
            wait <span className="text-amber-300 font-medium">{item.wait_minutes}m</span> · ride {ride}m
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); removePlannedItem(item.id); }}
          onPointerDown={(e) => e.stopPropagation()}
          className="opacity-0 group-hover:opacity-100 text-xs text-ink-secondary hover:text-red-400"
          title="Remove"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

export function Timeline() {
  const { earlyEntry, plannedItems, lands } = usePlanner();
  const openHour = earlyEntry ? PARK_OPEN_HOUR_EARLY : PARK_OPEN_HOUR;
  const totalMinutes = (PARK_CLOSE_HOUR - openHour) * 60;
  const hours = Array.from({ length: PARK_CLOSE_HOUR - openHour }, (_, i) => openHour + i);

  const { setNodeRef, isOver } = useDroppable({ id: "timeline" });

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-bg-hover">
        <h2 className="font-display font-semibold text-base">Your Day</h2>
        <div className="text-xs text-ink-secondary">
          Drag attractions from the left → drop on the timeline. Drag bars to reposition.
        </div>
      </div>

      <div ref={setNodeRef} className={clsx(
        "flex-1 overflow-y-auto relative",
        isOver && "bg-bg-card/30",
      )}>
        <div className="relative" style={{ height: totalMinutes * PX_PER_MIN }}>
          {/* Hour grid */}
          {hours.map((h) => {
            const minute = (h - openHour) * 60;
            return (
              <div
                key={h}
                className="absolute left-0 right-0 border-t border-bg-hover"
                style={{ top: minute * PX_PER_MIN }}
              >
                <div className="flex">
                  <div className="w-14 text-xs text-ink-muted -mt-2 ml-2 bg-bg-base px-1">
                    {minutesToTimeLabel(0, h)}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Plotted bars */}
          <div className="absolute left-16 right-2 top-0 bottom-0">
            {plannedItems.map(p => (
              <ItineraryBar
                key={p.id}
                item={p}
                color={lands?.[p.land as LandId]?.color || "#888"}
              />
            ))}
          </div>

          {plannedItems.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-ink-muted text-sm text-center">
                Empty timeline.<br />
                <span className="text-ink-secondary">Drag a ride from the left, or hit “Optimize Day” on the right.</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export const TIMELINE_PX_PER_MIN = PX_PER_MIN;
