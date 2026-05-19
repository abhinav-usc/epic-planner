import { useEffect, useRef, useState } from "react";
import { useDroppable, useDraggable } from "@dnd-kit/core";
import clsx from "clsx";
import { IconX, IconToolsKitchen2, IconShoppingBag, IconGripHorizontal, IconTrash, IconChartBar, IconLock, IconPencil, IconCheck } from "@tabler/icons-react";
import { SavedPlansPopover } from "./SavedPlansPopover";
import { usePlanner } from "../store/plannerStore";
import { minutesToTimeLabel } from "../lib/format";
import { walkMinutes } from "../lib/walkTimes";
import type { PlannedItem, LandId } from "../types";

export const PX_PER_MIN = 2.0;            // 1 hour = 120 px
const PARK_OPEN = 9;
const PARK_OPEN_EARLY = 8;
const PARK_CLOSE_HOURS: Record<string, number> = {
  epic_universe: 21,
  magic_kingdom: 22,
  epcot: 21,
  hollywood_studios: 21,
  animal_kingdom: 18,
  disneyland: 23,
};
const MIN_BLOCK_HEIGHT_COMPACT = 22;      // single-line layout for short blocks
const MIN_BLOCK_HEIGHT_NORMAL = 44;       // two-line layout
const MIN_ACTIVITY_HEIGHT = 40;           // reserved space for name + meta (normal mode)
const COMPACT_THRESHOLD_MIN = 16;         // blocks ≤ this use compact single-line layout
const HOUR_HEIGHT = 60 * PX_PER_MIN;

function waitColor(min: number): string {
  if (min <= 20) return "text-status-ok";
  if (min <= 60) return "text-status-warn";
  return "text-status-bad";
}

function fmtParkClock(minute: number, parkOpenHour: number): string {
  const total = parkOpenHour * 60 + minute;
  const h = Math.floor(total / 60);
  const m = total % 60;
  const hh = ((h + 11) % 12) + 1;
  const ampm = h >= 12 && h < 24 ? "p" : "a";
  return `${hh}:${m.toString().padStart(2, "0")}${ampm}`;
}

function ItineraryBar({ item, color }: { item: PlannedItem; color: string }) {
  const { worstCaseMode, removePlannedItem, removeLlReservation, setBreakDuration, toggleDone, llPlan, earlyEntry, waitOverrides, setWaitOverride } = usePlanner();
  const [editingWait, setEditingWait] = useState(false);
  const [editWaitVal, setEditWaitVal] = useState("");
  const parkOpenHour = earlyEntry ? 8 : 9;
  const llBooking = llPlan?.bookings.find(b => b.attraction_id === item.attraction_id);
  const isDone = !!item.done;
  const canMarkDone = item.kind === "ride" || item.kind === "show" || item.kind === "experience";
  const isShow = item.kind === "show";
  const isBreak = item.kind === "break_food" || item.kind === "break_shop";

  // Live duration override while the user is dragging the resize grip on a break.
  const [resizingDuration, setResizingDuration] = useState<number | null>(null);
  const resizeStartY = useRef(0);
  const resizeStartDuration = useRef(0);

  // Live wait override while dragging the wait-resize handle on ride blocks.
  const [resizingWait, setResizingWait] = useState<number | null>(null);
  const resizeWaitStartY = useRef(0);
  const resizeWaitStartVal = useRef(0);

  const isOverridden = !isBreak && item.attraction_id in (waitOverrides ?? {});
  const displayWait = resizingWait !== null
    ? resizingWait
    : (worstCaseMode && item.worst_case_wait != null
      ? item.worst_case_wait
      : item.wait_minutes);
  // Breaks use duration_minute as their visible length (wait is always 0);
  // override with live value while resizing.
  const rideMin = isBreak
    ? (resizingDuration ?? item.duration_minute)
    : item.ride_minutes;
  const totalMin = displayWait + rideMin;
  const isCompact = totalMin <= COMPACT_THRESHOLD_MIN;
  const minH = isCompact ? MIN_BLOCK_HEIGHT_COMPACT : MIN_BLOCK_HEIGHT_NORMAL;
  const heightPx = Math.max(minH, totalMin * PX_PER_MIN);

  const isLocked = !!item.locked;
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `plan-${item.id}`,
    data: { plannedItem: item },
    disabled: isLocked,
  });

  const style: React.CSSProperties = {
    top: item.start_minute * PX_PER_MIN,
    height: heightPx,
    opacity: isDragging ? 0.3 : 1,
  };

  // Compact blocks: no separate wait segment, one solid bar.
  // Normal blocks: split wait (dotted) + activity (solid) with min activity height.
  const naturalWaitHeight = isCompact ? 0 : Math.max(0, displayWait * PX_PER_MIN);
  const rideHeight = isCompact ? heightPx : Math.max(MIN_ACTIVITY_HEIGHT, heightPx - naturalWaitHeight);
  const waitHeight = Math.max(0, heightPx - rideHeight);

  function onResizeDown(e: React.PointerEvent) {
    e.stopPropagation();
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    resizeStartY.current = e.clientY;
    resizeStartDuration.current = item.duration_minute;
    setResizingDuration(item.duration_minute);

    const onMove = (ev: PointerEvent) => {
      const deltaMin = (ev.clientY - resizeStartY.current) / PX_PER_MIN;
      const next = Math.max(5, Math.round(resizeStartDuration.current + deltaMin));
      setResizingDuration(next);
    };
    const onUp = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      const finalDelta = (ev.clientY - resizeStartY.current) / PX_PER_MIN;
      const finalDuration = Math.max(5, Math.round(resizeStartDuration.current + finalDelta));
      setBreakDuration(item.id, finalDuration);
      setResizingDuration(null);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  function onWaitResizeDown(e: React.PointerEvent) {
    e.stopPropagation();
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    resizeWaitStartY.current = e.clientY;
    resizeWaitStartVal.current = displayWait;
    setResizingWait(displayWait);

    const onMove = (ev: PointerEvent) => {
      const deltaMin = (ev.clientY - resizeWaitStartY.current) / PX_PER_MIN;
      setResizingWait(Math.max(0, Math.round(resizeWaitStartVal.current + deltaMin)));
    };
    const onUp = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      const finalDelta = (ev.clientY - resizeWaitStartY.current) / PX_PER_MIN;
      const finalWait = Math.max(0, Math.round(resizeWaitStartVal.current + finalDelta));
      setWaitOverride(item.attraction_id, finalWait);
      setResizingWait(null);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={clsx(
        "absolute left-1 right-1 z-10 overflow-hidden rounded transition-opacity group",
        isLocked ? "cursor-default ring-1 ring-amber-400/60" : "cursor-grab active:cursor-grabbing",
        isDone && "opacity-40",
      )}
    >
      {/* Wait segment (dotted) */}
      {waitHeight > 0 && (
        <div
          className="overflow-hidden relative"
          style={{
            height: waitHeight,
            backgroundColor: isBreak ? "transparent" : `${color}14`,
            backgroundImage: isBreak
              ? undefined
              : `repeating-linear-gradient(135deg, ${color}33 0 4px, transparent 4px 9px)`,
            borderLeft: `3px solid ${color}80`,
            borderTopRightRadius: 4,
            borderTopLeftRadius: 0,
          }}
        >
          {!isBreak && (
            <div
              onPointerDown={onWaitResizeDown}
              className={clsx(
                "absolute bottom-0 left-0 right-0 h-3 flex items-center justify-center cursor-ns-resize z-20 transition-opacity",
                resizingWait !== null ? "opacity-100" : "opacity-0 group-hover:opacity-100",
              )}
              title="Drag to adjust wait time"
            >
              <IconGripHorizontal size={10} stroke={1.5} className="text-white/50" />
            </div>
          )}
        </div>
      )}
      {/* Activity segment (solid) */}
      <div
        className="hover:ring-1 hover:ring-accent transition-shadow overflow-hidden"
        style={{
          height: rideHeight,
          backgroundColor: isBreak ? "var(--bg-hover)" : `${color}33`,
          borderLeft: `3px solid ${color}`,
          borderBottomRightRadius: 4,
          borderBottomLeftRadius: 0,
          borderTopRightRadius: waitHeight > 0 ? 0 : 4,
          padding: isCompact ? "0 8px" : "6px 10px",
          display: "flex",
          alignItems: isCompact ? "center" : "flex-start",
        }}
      >
        {isCompact ? (
          /* ── Compact single-line layout ── */
          <div className="flex items-center gap-1.5 w-full min-w-0">
            {item.kind === "break_food" && <IconToolsKitchen2 size={11} stroke={1.5} className="shrink-0 text-ink-secondary" />}
            {item.kind === "break_shop" && <IconShoppingBag size={11} stroke={1.5} className="shrink-0 text-ink-secondary" />}
            <span className={clsx("text-[11px] font-medium leading-none truncate flex-1", isDone && "line-through")}>{item.name}</span>
            <span className="text-[10px] text-ink-secondary leading-none shrink-0 whitespace-nowrap">
              {!isBreak && displayWait > 0 && (
                editingWait ? (
                  <span className="mr-1 flex items-center gap-0.5" onClick={e => e.stopPropagation()} onPointerDown={e => e.stopPropagation()}>
                    <input
                      autoFocus
                      type="number"
                      min={0}
                      max={300}
                      value={editWaitVal}
                      onChange={e => setEditWaitVal(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === "Enter") { const v = parseInt(editWaitVal); if (!isNaN(v) && v >= 0) setWaitOverride(item.attraction_id, v); setEditingWait(false); }
                        if (e.key === "Escape") setEditingWait(false);
                      }}
                      className="w-10 text-[10px] rounded px-1 py-px text-center"
                      style={{ background: "var(--bg-panel)", border: "1px solid var(--accent)", color: "var(--text-primary)" }}
                    />
                    <button onPointerDown={e => e.stopPropagation()} onClick={e => { e.stopPropagation(); const v = parseInt(editWaitVal); if (!isNaN(v) && v >= 0) setWaitOverride(item.attraction_id, v); setEditingWait(false); }} className="text-status-ok"><IconCheck size={10} stroke={2} /></button>
                  </span>
                ) : (
                  <span
                    className={clsx("mr-1 cursor-pointer group/wait flex items-center gap-0.5", waitColor(displayWait))}
                    onClick={e => { e.stopPropagation(); setEditWaitVal(String(displayWait)); setEditingWait(true); }}
                    onPointerDown={e => e.stopPropagation()}
                    title="Click to override wait time"
                  >
                    {displayWait}m{isOverridden && <span className="text-accent text-[8px]">*</span>}
                    <IconPencil size={8} stroke={1.5} className="opacity-0 group-hover/wait:opacity-60 transition-opacity" />
                  </span>
                )
              )}
              {rideMin}m
            </span>
            {canMarkDone && (
              <button
                onClick={(e) => { e.stopPropagation(); toggleDone(item.id); }}
                onPointerDown={(e) => e.stopPropagation()}
                className={clsx(
                  "shrink-0 w-4 h-4 rounded-full border flex items-center justify-center transition-colors",
                  isDone
                    ? "bg-status-ok border-status-ok text-bg-base"
                    : "border-border-subtle text-ink-muted hover:border-status-ok hover:text-status-ok",
                )}
                title={isDone ? "Mark as not done" : "Mark as done"}
              >
                {isDone && <span className="text-[8px] leading-none">✓</span>}
              </button>
            )}
            {isLocked ? (
              <IconLock size={10} stroke={1.5} className="text-amber-400 shrink-0 ml-0.5" />
            ) : (
              <button
                onClick={(e) => { e.stopPropagation(); removePlannedItem(item.id); }}
                onPointerDown={(e) => e.stopPropagation()}
                className="opacity-0 group-hover:opacity-100 text-ink-secondary hover:text-red-400 transition-opacity shrink-0 ml-0.5"
                title="Remove"
              >
                <IconX size={11} stroke={1.5} />
              </button>
            )}
          </div>
        ) : (
          /* ── Normal two-line layout ── */
          <div className="flex items-start justify-between gap-2 w-full min-w-0">
            <div className="min-w-0 flex-1">
              <div className="text-[12px] font-medium leading-tight truncate flex items-center gap-1.5">
                {item.kind === "break_food" && <IconToolsKitchen2 size={12} stroke={1.5} className="shrink-0" />}
                {item.kind === "break_shop" && <IconShoppingBag size={12} stroke={1.5} className="shrink-0" />}
                <span className={clsx("truncate", isDone && "line-through")}>{item.name}</span>
              </div>
              <div className="text-[10px] text-ink-secondary mt-1 flex gap-1 flex-wrap leading-tight">
                {!isBreak && displayWait > 0 && (
                  editingWait ? (
                    <span className="flex items-center gap-0.5" onClick={e => e.stopPropagation()} onPointerDown={e => e.stopPropagation()}>
                      <span>Wait</span>
                      <input
                        autoFocus
                        type="number"
                        min={0}
                        max={300}
                        value={editWaitVal}
                        onChange={e => setEditWaitVal(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === "Enter") { const v = parseInt(editWaitVal); if (!isNaN(v) && v >= 0) setWaitOverride(item.attraction_id, v); setEditingWait(false); }
                          if (e.key === "Escape") setEditingWait(false);
                        }}
                        className="w-12 text-[10px] rounded px-1 py-px text-center mx-0.5"
                        style={{ background: "var(--bg-panel)", border: "1px solid var(--accent)", color: "var(--text-primary)" }}
                      />
                      <span>m</span>
                      <button onPointerDown={e => e.stopPropagation()} onClick={e => { e.stopPropagation(); const v = parseInt(editWaitVal); if (!isNaN(v) && v >= 0) setWaitOverride(item.attraction_id, v); setEditingWait(false); }} className="text-status-ok ml-0.5"><IconCheck size={10} stroke={2} /></button>
                      <span>·</span>
                    </span>
                  ) : (
                    <>
                      <span>Wait</span>
                      <span
                        className={clsx("font-medium cursor-pointer group/wait flex items-center gap-0.5", waitColor(displayWait))}
                        onClick={e => { e.stopPropagation(); setEditWaitVal(String(displayWait)); setEditingWait(true); }}
                        onPointerDown={e => e.stopPropagation()}
                        title="Click to override wait time"
                      >
                        {displayWait}m{isOverridden && <span className="text-accent text-[8px]">*</span>}
                        <IconPencil size={8} stroke={1.5} className="opacity-0 group-hover/wait:opacity-60 transition-opacity" />
                      </span>
                      <span>·</span>
                    </>
                  )
                )}
                <span>{isLocked ? "LLSP" : isShow ? "Show" : isBreak ? "Break" : "Ride"} {rideMin}m</span>
                {worstCaseMode && item.worst_case_wait != null && (
                  <span className="text-status-bad">· worst-case</span>
                )}
                {llBooking && llBooking.priority !== "skip" && (
                  <span className={clsx(
                    "ml-1 px-1.5 py-px rounded text-[9px] font-medium",
                    llBooking.priority === "urgent"
                      ? "bg-amber-500/20 text-amber-300"
                      : "bg-purple-500/15 text-purple-300",
                  )}
                  title={llBooking.reason || `Book LL at ${fmtParkClock(llBooking.book_at_minute, parkOpenHour)}, return ~${fmtParkClock(llBooking.predicted_return_minute, parkOpenHour)}`}
                  >
                    {llBooking.priority === "urgent" ? "⚡ Book first" : `⚡ Book ${fmtParkClock(llBooking.book_at_minute, parkOpenHour)}`}
                  </span>
                )}
                {llBooking && llBooking.priority === "skip" && (
                  <span className="ml-1 px-1.5 py-px rounded text-[9px] font-medium bg-zinc-500/15 text-ink-muted"
                    title={llBooking.reason}>
                    ⚡ Skip LL
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {canMarkDone && (
                <button
                  onClick={(e) => { e.stopPropagation(); toggleDone(item.id); }}
                  onPointerDown={(e) => e.stopPropagation()}
                  className={clsx(
                    "w-4 h-4 rounded-full border flex items-center justify-center transition-colors",
                    isDone
                      ? "bg-status-ok border-status-ok text-bg-base"
                      : "border-border-subtle text-ink-muted hover:border-status-ok hover:text-status-ok",
                  )}
                  title={isDone ? "Mark as not done" : "Mark as done"}
                >
                  {isDone && <span className="text-[9px] leading-none">✓</span>}
                </button>
              )}
              {isLocked ? (
                <IconLock size={12} stroke={1.5} className="text-amber-400 mt-0.5" />
              ) : (
                <button
                  onClick={(e) => { e.stopPropagation(); removePlannedItem(item.id); }}
                  onPointerDown={(e) => e.stopPropagation()}
                  className="opacity-0 group-hover:opacity-100 text-ink-secondary hover:text-red-400 transition-opacity"
                  title="Remove"
                >
                  <IconX size={13} stroke={1.5} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Resize grip — break blocks only */}
      {isBreak && (
        <div
          onPointerDown={onResizeDown}
          className="absolute left-0 right-0 bottom-0 h-2.5 flex items-center justify-center cursor-ns-resize hover:bg-bg-hover/60 transition-colors"
          title="Drag to resize"
        >
          <IconGripHorizontal size={12} stroke={1.5} className="text-ink-muted" />
        </div>
      )}
    </div>
  );
}

function WalkConnector({
  topMinute,
  gapMinutes,
  walkMin,
}: {
  topMinute: number;
  gapMinutes: number;
  walkMin: number;
}) {
  if (walkMin <= 0 || gapMinutes <= 0) return null;
  const heightPx = gapMinutes * PX_PER_MIN;
  if (heightPx < 6) return null;

  return (
    <div
      className="absolute pointer-events-none"
      style={{ left: 0, right: 0, top: topMinute * PX_PER_MIN, height: heightPx, zIndex: 5 }}
    >
      {/* Thin vertical line */}
      <div
        className="absolute top-1 bottom-1"
        style={{ left: 5, width: 1, background: "var(--border-subtle)" }}
      />
      {/* Walk label — only if there's room */}
      {heightPx >= 18 && (
        <div
          className="absolute flex items-center gap-1 text-[9px] text-ink-muted leading-none whitespace-nowrap"
          style={{
            left: 12,
            top: "50%",
            transform: "translateY(-50%)",
            background: "var(--bg-base)",
            padding: "2px 5px",
            borderRadius: 10,
            border: "1px solid var(--border-subtle)",
          }}
        >
          Walk {walkMin}m
        </div>
      )}
    </div>
  );
}

/** Visual block rendered inside a <DragOverlay> while the user is dragging.
 *  Width matches the timeline-content's bar column (left:56 right:8). */
export function BarPreview({
  item,
  color,
  width,
}: {
  item: { name: string; kind: PlannedItem["kind"]; wait_minutes: number; ride_minutes: number; worst_case_wait?: number };
  color: string;
  width: number;
}) {
  const isBreak = item.kind === "break_food" || item.kind === "break_shop";
  const isShow = item.kind === "show";
  const totalMin = item.wait_minutes + item.ride_minutes;
  const isCompact = totalMin <= COMPACT_THRESHOLD_MIN;
  const minH = isCompact ? MIN_BLOCK_HEIGHT_COMPACT : MIN_BLOCK_HEIGHT_NORMAL;
  const heightPx = Math.max(minH, totalMin * PX_PER_MIN);
  const naturalWait = isCompact ? 0 : Math.max(0, item.wait_minutes * PX_PER_MIN);
  const rideHeight = isCompact ? heightPx : Math.max(MIN_ACTIVITY_HEIGHT, heightPx - naturalWait);
  const waitHeight = Math.max(0, heightPx - rideHeight);
  return (
    <div
      style={{
        width,
        height: heightPx,
        pointerEvents: "none",
        boxShadow: "0 8px 24px rgba(0,0,0,0.35), 0 0 0 1px var(--border-subtle)",
        borderRadius: 5,
        overflow: "hidden",
      }}
    >
      {item.wait_minutes > 0 && (
        <div
          style={{
            height: waitHeight,
            backgroundColor: isBreak ? "transparent" : `${color}1f`,
            backgroundImage: isBreak
              ? undefined
              : `repeating-linear-gradient(135deg, ${color}40 0 4px, transparent 4px 9px)`,
            borderLeft: `3px solid ${color}80`,
          }}
        />
      )}
      <div
        className="px-2.5 py-1.5"
        style={{
          height: rideHeight,
          backgroundColor: isBreak ? "var(--bg-card)" : `${color}55`,
          borderLeft: `3px solid ${color}`,
        }}
      >
        <div className="text-[12px] font-medium leading-tight truncate flex items-center gap-1 text-ink-primary">
          {item.kind === "break_food" && <IconToolsKitchen2 size={12} stroke={1.5} />}
          {item.kind === "break_shop" && <IconShoppingBag size={12} stroke={1.5} />}
          {item.name}
        </div>
        <div className="text-[10px] text-ink-secondary mt-1 flex gap-1 flex-wrap">
          {!isBreak && item.wait_minutes > 0 && (
            <>
              <span>Wait {item.wait_minutes}m</span>
              <span>·</span>
            </>
          )}
          <span>{isShow ? "Show" : isBreak ? "Break" : "Ride"} {item.ride_minutes}m</span>
        </div>
      </div>
    </div>
  );
}

interface TimelineProps {
  onShowFeasibility: () => void;
}

export function Timeline({ onShowFeasibility }: TimelineProps) {
  const {
    earlyEntry, plannedItems, lands, worstCaseMode, addBreak, placementNote, setPlacementNote, clearTimeline, currentPark,
  } = usePlanner();
  const openHourVal = earlyEntry ? PARK_OPEN_EARLY : PARK_OPEN;

  // Compute walk connectors between consecutive items sorted by start time.
  const sortedItems = [...plannedItems].sort((a, b) => a.start_minute - b.start_minute);
  const walkConnectors: { topMinute: number; gapMinutes: number; walkMin: number }[] = [];
  for (let i = 1; i < sortedItems.length; i++) {
    const prev = sortedItems[i - 1];
    const curr = sortedItems[i];
    const prevEnd = prev.start_minute + prev.duration_minute;
    const gap = curr.start_minute - prevEnd;
    if (gap <= 0) continue;
    // Use stored walk (from optimizer) if set, else compute from land change.
    const wm = curr.walk_minutes_from_prev != null && curr.walk_minutes_from_prev > 0
      ? curr.walk_minutes_from_prev
      : walkMinutes(currentPark, prev.land as string, curr.land as string);
    if (wm > 0) {
      walkConnectors.push({ topMinute: prevEnd, gapMinutes: gap, walkMin: wm });
    }
  }
  const parkClose = PARK_CLOSE_HOURS[currentPark] ?? 21;
  const closeMinute = (parkClose - openHourVal) * 60;
  // Extend scrollable area 60 min past close so late rides aren't cut off.
  const totalMinutes = closeMinute + 60;
  const hours = Array.from({ length: parkClose - openHourVal + 1 }, (_, i) => openHourVal + i);

  // Make the scrolling content area droppable. Pointer position is read in
  // PlannerPage.onDragEnd via `data-timeline-content`.
  const { setNodeRef, isOver } = useDroppable({ id: "timeline", data: { kind: "timeline" } });

  // Auto-dismiss placement notes after 3s
  useEffect(() => {
    if (!placementNote) return;
    const t = setTimeout(() => setPlacementNote(null), 3000);
    return () => clearTimeout(t);
  }, [placementNote, setPlacementNote]);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex items-center justify-between px-3 py-2 border-b border-bg-hover shrink-0">
        <div className="flex items-center gap-2 min-w-0 mr-2">
          <h2 className="text-sm font-medium shrink-0">Your day</h2>
          <span className="text-[11px] text-ink-secondary hidden sm:block truncate">
            Drag attractions · reposition bars
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <SavedPlansPopover />
          <button
            onClick={() => addBreak("break_food", 45)}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] bg-bg-card text-ink-secondary hover:bg-bg-hover"
            style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
            title="Add a 45-min food break"
          >
            <IconToolsKitchen2 size={12} stroke={1.5} />
            <span className="hidden sm:inline">Food</span>
          </button>
          <button
            onClick={() => addBreak("break_shop", 20)}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] bg-bg-card text-ink-secondary hover:bg-bg-hover"
            style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
            title="Add a 20-min shopping break"
          >
            <IconShoppingBag size={12} stroke={1.5} />
            <span className="hidden sm:inline">Shop</span>
          </button>
          {plannedItems.length > 0 && (
            <>
              <button
                onClick={onShowFeasibility}
                className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] bg-bg-card text-ink-secondary hover:bg-bg-hover"
                style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
                title="Check if your plan would have worked historically"
              >
                <IconChartBar size={12} stroke={1.5} />
                <span className="hidden sm:inline">Feasibility</span>
              </button>
              <button
                onClick={() => { if (confirm("Clear all items from the timeline?")) clearTimeline(); }}
                className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-status-bad hover:bg-status-bad/10 transition-colors"
                style={{ borderWidth: "0.5px", borderColor: "var(--status-bad)" }}
                title="Remove all items from the timeline"
              >
                <IconTrash size={12} stroke={1.5} />
                <span className="hidden sm:inline">Clear</span>
              </button>
            </>
          )}
        </div>
      </div>

      {placementNote && (
        <div className="px-4 py-1 text-[11px] border-b border-bg-hover" style={{ background: "var(--status-warn-bg)", color: "var(--status-warn)" }}>
          {placementNote}
        </div>
      )}

      <div
        ref={setNodeRef}
        data-timeline-content
        data-park-open-hour={openHourVal}
        className={clsx("flex-1 overflow-y-auto relative", isOver && "bg-accent/5 ring-1 ring-inset ring-accent/30")}
      >
        <div className="relative" style={{ height: totalMinutes * PX_PER_MIN }}>
          {/* Hour grid (visual only — drop targets are pixel-precise via the parent droppable) */}
          {hours.map((h) => {
            const minute = (h - openHourVal) * 60;
            const isCloseHour = h === parkClose;
            return (
              <div
                key={h}
                className="absolute left-0 right-0 pointer-events-none"
                style={{
                  top: minute * PX_PER_MIN,
                  borderTop: isCloseHour ? "2px solid var(--status-bad)" : "1px solid var(--border-subtle)",
                }}
              >
                <div
                  className={clsx("text-[10px] -mt-2.5 ml-2 px-1 inline-block font-medium",
                    isCloseHour ? "text-status-bad" : "text-ink-muted")}
                  style={{ background: "var(--bg-base)" }}
                >
                  {minutesToTimeLabel(0, h)}{isCloseHour ? " — Park closes" : ""}
                </div>
              </div>
            );
          })}

          {/* Plotted bars */}
          <div
            data-timeline-bars
            className="absolute left-14 right-2 top-0 bottom-0 pointer-events-none"
          >
            <div className="relative w-full h-full pointer-events-auto">
              {/* Walk connectors (rendered behind bars) */}
              {walkConnectors.map((c, i) => (
                <WalkConnector key={i} {...c} />
              ))}
              {plannedItems.map(p => {
                const color = p.land === "break"
                  ? "#94A3B8"  // slate for breaks
                  : (lands?.[p.land as LandId]?.color || "#888");
                return <ItineraryBar key={p.id} item={p} color={color} />;
              })}
            </div>
          </div>

          {plannedItems.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-ink-muted text-sm text-center max-w-xs leading-relaxed">
                Empty timeline.<br />
                <span className="text-ink-secondary">
                  Drag a ride from the left, hit AI optimize, or add a break.
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
