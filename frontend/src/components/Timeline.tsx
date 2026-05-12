import { useDroppable, useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import { IconX } from "@tabler/icons-react";
import { usePlanner } from "../store/plannerStore";
import { minutesToTimeLabel } from "../lib/format";
import type { PlannedItem, LandId } from "../types";

export const PX_PER_MIN = 1.4;            // 1 hour = 84px
const PARK_OPEN = 9;
const PARK_OPEN_EARLY = 8;
const PARK_CLOSE = 22;
const MIN_BLOCK_HEIGHT = 28;
const HOUR_HEIGHT = 60 * PX_PER_MIN;

// Color thresholds for the wait pill on each block.
function waitColor(min: number): string {
  if (min <= 20) return "text-emerald-300";
  if (min <= 60) return "text-amber-300";
  return "text-red-300";
}

/** A droppable strip for a single hour. Both new-from-sidebar drops and
 *  drag-to-reposition land here and we snap to the top of the hour. */
function HourDropZone({ hour, openHour }: { hour: number; openHour: number }) {
  const { setNodeRef, isOver } = useDroppable({
    id: `timeline-hour-${hour}`,
    data: { kind: "timeline-hour", hour },
  });
  const top = (hour - openHour) * HOUR_HEIGHT;
  return (
    <div
      ref={setNodeRef}
      className={clsx(
        "absolute left-0 right-0 border-t border-bg-hover/60",
        isOver && "bg-accent/5",
      )}
      style={{ top, height: HOUR_HEIGHT }}
    >
      <div className="absolute left-2 -top-2 text-[10px] text-ink-muted bg-bg-base px-1">
        {minutesToTimeLabel(0, hour)}
      </div>
    </div>
  );
}

function ItineraryBar({ item, color }: { item: PlannedItem; color: string }) {
  const { worstCaseMode, removePlannedItem } = usePlanner();
  const displayWait = worstCaseMode && item.worst_case_wait != null
    ? item.worst_case_wait
    : item.wait_minutes;
  const rideMin = Math.max(0, item.duration_minute - item.wait_minutes);
  const totalMin = displayWait + rideMin;
  const heightPx = Math.max(MIN_BLOCK_HEIGHT, totalMin * PX_PER_MIN);

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `plan-${item.id}`,
    data: { plannedItem: item },
  });

  const style: React.CSSProperties = {
    top: item.start_minute * PX_PER_MIN,
    height: heightPx,
    backgroundColor: `${color}22`,
    borderLeft: `3px solid ${color}`,
    borderTopRightRadius: 4,
    borderBottomRightRadius: 4,
    borderTopLeftRadius: 0,
    borderBottomLeftRadius: 0,
    transform: transform ? `translate3d(0, ${transform.y}px, 0)` : undefined,
    opacity: isDragging ? 0.6 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={clsx(
        "absolute left-1 right-1 px-2 py-1 cursor-grab active:cursor-grabbing z-10 group",
        "hover:ring-1 hover:ring-accent transition-shadow",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-medium leading-tight truncate">{item.name}</div>
          <div className="text-[9px] text-ink-secondary mt-0.5 flex gap-1">
            <span>Wait</span>
            <span className={clsx("font-medium", waitColor(displayWait))}>{displayWait}m</span>
            <span>·</span>
            <span>Ride {rideMin}m</span>
            {worstCaseMode && item.worst_case_wait != null && (
              <span className="text-red-300">· worst case</span>
            )}
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); removePlannedItem(item.id); }}
          onPointerDown={(e) => e.stopPropagation()}
          className="opacity-0 group-hover:opacity-100 text-ink-secondary hover:text-red-400 transition-opacity"
          title="Remove"
        >
          <IconX size={12} stroke={1.5} />
        </button>
      </div>
    </div>
  );
}

export function Timeline() {
  const { earlyEntry, plannedItems, lands, worstCaseMode } = usePlanner();
  const openHour = earlyEntry ? PARK_OPEN_EARLY : PARK_OPEN;
  const totalMinutes = (PARK_CLOSE - openHour) * 60;
  const hours = Array.from({ length: PARK_CLOSE - openHour }, (_, i) => openHour + i);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-bg-hover">
        <h2 className="text-sm font-medium">Your day</h2>
        <div className="text-[10px] text-ink-secondary">
          Drag attractions from the left · drag bars to reposition
          {worstCaseMode && <span className="ml-2 text-red-300">· worst-case heights</span>}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto relative">
        <div className="relative" style={{ height: totalMinutes * PX_PER_MIN }}>
          {/* Per-hour droppables — these accept both sidebar drops and reposition drops. */}
          {hours.map(h => (
            <HourDropZone key={h} hour={h} openHour={openHour} />
          ))}

          {/* Plotted bars sit on top (higher z-index in the bar style). */}
          <div className="absolute left-14 right-2 top-0 bottom-0 pointer-events-none">
            <div className="relative w-full h-full pointer-events-auto">
              {plannedItems.map(p => (
                <ItineraryBar
                  key={p.id}
                  item={p}
                  color={lands?.[p.land as LandId]?.color || "#888"}
                />
              ))}
            </div>
          </div>

          {plannedItems.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-ink-muted text-xs text-center max-w-xs">
                Empty timeline.<br />
                <span className="text-ink-secondary">
                  Drag a ride from the left, or use AI optimizer on the right.
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export const TIMELINE_PX_PER_MIN = PX_PER_MIN;
