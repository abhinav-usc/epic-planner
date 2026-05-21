import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { IconRollercoaster, IconCalendarEvent, IconSparkles as IconOptimize, IconCalendar } from "@tabler/icons-react";
import { LandSidebar } from "../components/LandSidebar";
import { Timeline, PX_PER_MIN, BarPreview } from "../components/Timeline";
import { OptimizePanel } from "../components/OptimizePanel";
import { WaitTimeChart } from "../components/WaitTimeChart";
import { AIChat } from "../components/AIChat";
import { HistoryExplorer } from "../components/HistoryExplorer";
import { RestaurantPanel } from "../components/RestaurantPanel";
import { FeasibilityReport } from "../components/FeasibilityReport";
import { usePlanner, SHOW_QUEUE_MINUTES } from "../store/plannerStore";
import { api } from "../api/client";
import type { Attraction, LandId, ParkId, PlannedItem, Restaurant } from "../types";

const PARKS: { id: ParkId; name: string; icon: string; short: string }[] = [
  { id: "epic_universe",       name: "Epic Universe",          icon: "🌌", short: "EU" },
  { id: "magic_kingdom",       name: "Magic Kingdom",          icon: "🏰", short: "MK" },
  { id: "epcot",               name: "EPCOT",                  icon: "🌍", short: "EP" },
  { id: "hollywood_studios",   name: "Hollywood Studios",      icon: "🎬", short: "HS" },
  { id: "animal_kingdom",      name: "Animal Kingdom",         icon: "🌿", short: "AK" },
  { id: "disneyland",          name: "Disneyland",             icon: "🏰", short: "DL" },
];

type ActiveDrag =
  | { kind: "attraction"; a: Attraction }
  | { kind: "plan"; item: PlannedItem }
  | null;

const AUTO_COLLAPSE_WIDTH = 1100; // px — collapse both sidebars below this
const MOBILE_WIDTH = 768; // px — below this, use mobile tab nav

export function PlannerPage() {
  const {
    loaded, catalogError, loadCatalog,
    placeAttraction, moveItem,
    lands, daySummaries, plannedItems,
    currentPark, switchPark,
    priorities, targetDate, earlyEntry, refreshLlPlan,
    liveMode, liveData, liveLastFetchedAt, setLiveMode, pollLive,
  } = usePlanner();
  const [selected, setSelected] = useState<Attraction | null>(null);
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [refreshNote, setRefreshNote] = useState<string | null>(null);
  const [activeDrag, setActiveDrag] = useState<ActiveDrag>(null);
  const dragStartScrollTop = useRef<number>(0);
  const lastPointerClientY = useRef<number>(0);
  const pointerMoveCleanup = useRef<(() => void) | null>(null);
  const [barColumnWidth, setBarColumnWidth] = useState<number>(280);

  // Sidebar collapse state
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [showFeasibility, setShowFeasibility] = useState(false);

  // Resizable sidebar widths (persisted)
  const [leftWidth, setLeftWidth] = useState(() =>
    Number(localStorage.getItem("sidebar-left-width") || 0) || 300
  );
  const [rightWidth, setRightWidth] = useState(() =>
    Number(localStorage.getItem("sidebar-right-width") || 0) || 272
  );
  const [isResizingLeft, setIsResizingLeft] = useState(false);
  const [isResizingRight, setIsResizingRight] = useState(false);
  const leftWidthRef = useRef(leftWidth);
  leftWidthRef.current = leftWidth;
  const rightWidthRef = useRef(rightWidth);
  rightWidthRef.current = rightWidth;

  const startLeftResize = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = leftWidthRef.current;
    setIsResizingLeft(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (ev: PointerEvent) =>
      setLeftWidth(Math.max(200, Math.min(520, startW + ev.clientX - startX)));
    const onUp = () => {
      setIsResizingLeft(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      localStorage.setItem("sidebar-left-width", String(leftWidthRef.current));
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }, []);

  const startRightResize = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = rightWidthRef.current;
    setIsResizingRight(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    const onMove = (ev: PointerEvent) =>
      setRightWidth(Math.max(200, Math.min(520, startW - (ev.clientX - startX))));
    const onUp = () => {
      setIsResizingRight(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      localStorage.setItem("sidebar-right-width", String(rightWidthRef.current));
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  }, []);

  // Mobile tab nav state
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_WIDTH);
  const [mobileTab, setMobileTab] = useState<"attractions" | "timeline" | "optimize">("timeline");

  // Auto-collapse on narrow windows
  useEffect(() => {
    const check = () => {
      const mobile = window.innerWidth < MOBILE_WIDTH;
      setIsMobile(mobile);
      if (window.innerWidth < AUTO_COLLAPSE_WIDTH) {
        setLeftOpen(false);
        setRightOpen(false);
      } else {
        setLeftOpen(true);
        setRightOpen(true);
      }
    };
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);

  // Debounced LL plan refresh whenever inputs change.
  useEffect(() => {
    const t = setTimeout(() => { refreshLlPlan(); }, 350);
    return () => clearTimeout(t);
  }, [plannedItems, priorities, targetDate, earlyEntry, currentPark, refreshLlPlan]);

  // Live mode: poll queue-times every 5 minutes while enabled.
  useEffect(() => {
    if (!liveMode) return;
    const interval = window.setInterval(() => { void pollLive(); }, 5 * 60_000);
    return () => clearInterval(interval);
  }, [liveMode, pollLive]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const f = await api.dataFreshness();
        if (!alive) return;
        if (f.refresh_running) {
          setRefreshNote("Updating wait-time data…");
        } else if (f.needs_refresh) {
          setRefreshNote(`Wait-time data is ${f.epic_age_days ?? "?"} days old. Refreshing…`);
          await api.dataRefresh();
        }
        setTimeout(() => alive && setRefreshNote(null), 5000);
      } catch {/* ignore */}
    })();
    return () => { alive = false; };
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } }),
  );

  function snapStart(rawStart: number, duration: number, excludeId: string | null): number {
    const GRID = 30;
    const GRID_THRESH = 8;
    const GAP_THRESH = 10;

    let best = rawStart;
    let bestDist = Infinity;

    const tryCandidate = (pos: number) => {
      const d = Math.abs(pos - rawStart);
      if (d < bestDist) { best = pos; bestDist = d; }
    };

    const gridNearest = Math.round(rawStart / GRID) * GRID;
    if (Math.abs(gridNearest - rawStart) <= GRID_THRESH) tryCandidate(gridNearest);

    for (const p of plannedItems) {
      if (p.id === excludeId) continue;
      const pEnd = p.start_minute + p.duration_minute;
      if (Math.abs(rawStart - pEnd) <= GAP_THRESH) tryCandidate(pEnd);
      const abutPos = p.start_minute - duration;
      if (Math.abs(rawStart - abutPos) <= GAP_THRESH) tryCandidate(abutPos);
    }

    return bestDist === Infinity ? rawStart : best;
  }

  function getTimelineContainer(): HTMLElement | null {
    return document.querySelector<HTMLElement>("[data-timeline-content]");
  }

  function viewportYToMinute(clientY: number): number | null {
    const container = getTimelineContainer();
    if (!container) return null;
    const rect = container.getBoundingClientRect();
    const localY = clientY - rect.top + container.scrollTop;
    if (localY < 0) return 0;
    return localY / PX_PER_MIN;
  }

  function onDragStart(e: DragStartEvent) {
    const data = e.active.data.current as
      | { attraction?: Attraction; plannedItem?: PlannedItem }
      | undefined;
    const container = getTimelineContainer();
    dragStartScrollTop.current = container?.scrollTop ?? 0;

    const ae = e.activatorEvent as PointerEvent;
    lastPointerClientY.current = ae?.clientY ?? 0;
    const onMove = (ev: PointerEvent) => { lastPointerClientY.current = ev.clientY; };
    window.addEventListener("pointermove", onMove);
    pointerMoveCleanup.current = () => window.removeEventListener("pointermove", onMove);

    const bars = document.querySelector<HTMLElement>("[data-timeline-bars]");
    if (bars) setBarColumnWidth(bars.getBoundingClientRect().width);
    if (data?.attraction) setActiveDrag({ kind: "attraction", a: data.attraction });
    else if (data?.plannedItem) setActiveDrag({ kind: "plan", item: data.plannedItem });
  }

  async function onDragEnd(e: DragEndEvent) {
    pointerMoveCleanup.current?.();
    pointerMoveCleanup.current = null;

    const data = e.active.data.current as
      | { attraction?: Attraction; plannedItem?: PlannedItem }
      | undefined;
    setActiveDrag(null);

    if (data?.plannedItem) {
      const item = data.plannedItem;
      const container = getTimelineContainer();
      const rect = container?.getBoundingClientRect();
      if (!container || !rect) return;

      const finalClientY = lastPointerClientY.current;
      const ae = e.activatorEvent as PointerEvent;
      const startClientY = ae?.clientY ?? finalClientY;

      const startScrollTop = dragStartScrollTop.current;
      const startContentY = startClientY - rect.top + startScrollTop;
      const grabOffsetPx = startContentY - item.start_minute * PX_PER_MIN;

      const finalContentY = finalClientY - rect.top + container.scrollTop;
      const rawStart = (finalContentY - grabOffsetPx) / PX_PER_MIN;
      const newStart = snapStart(rawStart, item.duration_minute, item.id);

      if (Math.abs(newStart - item.start_minute) < 0.5) return;
      moveItem(item.id, newStart);
      return;
    }

    const over = e.over;
    if (!over || String(over.id) !== "timeline") return;
    if (!data?.attraction) return;
    const a = data.attraction;

    const rawMinute = viewportYToMinute(lastPointerClientY.current);
    if (rawMinute == null) return;
    const minute = snapStart(rawMinute, 0, null);
    placeAttraction(a, minute);
  }

  function estimatedWaitFor(a: Attraction): number {
    if (a.kind === "show") return SHOW_QUEUE_MINUTES;
    return daySummaries[a.id]?.median_wait ?? 30;
  }

  if (catalogError) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="panel p-5 max-w-md text-sm">
          <h2 className="font-medium text-base mb-2">Backend not reachable</h2>
          <div className="text-ink-secondary mb-3">
            The FastAPI server didn't respond. Start it with:
          </div>
          <pre className="bg-bg-base rounded p-2 text-xs">cd backend && uvicorn main:app --reload</pre>
          <div className="mt-3 text-ink-muted text-xs">Error: {catalogError}</div>
        </div>
      </div>
    );
  }

  if (!loaded) {
    return (
      <div className="h-full flex items-center justify-center text-ink-secondary text-sm">
        Loading attractions…
      </div>
    );
  }

  let overlayBlock: React.ReactNode = null;
  if (activeDrag?.kind === "attraction") {
    const a = activeDrag.a;
    const color = lands?.[a.land as LandId]?.color || "#888";
    const wait = estimatedWaitFor(a);
    overlayBlock = (
      <BarPreview
        item={{
          name: a.name,
          kind: a.kind,
          wait_minutes: wait,
          ride_minutes: a.duration_minutes,
        }}
        color={color}
        width={barColumnWidth}
      />
    );
  } else if (activeDrag?.kind === "plan") {
    const p = activeDrag.item;
    const color = p.land === "break"
      ? "#94A3B8"
      : (lands?.[p.land as LandId]?.color || "#888");
    overlayBlock = (
      <BarPreview
        item={{
          name: p.name,
          kind: p.kind,
          wait_minutes: p.wait_minutes,
          ride_minutes: p.ride_minutes,
        }}
        color={color}
        width={barColumnWidth}
      />
    );
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
    >
      <div className="h-full flex flex-col overflow-hidden">
        {/* Park selector tabs + history button */}
        <div
          className="flex items-center border-b border-bg-hover bg-bg-panel shrink-0 overflow-x-auto px-1"
          style={{ touchAction: "pan-x", overflowY: "hidden" }}
        >
          {PARKS.map(p => (
            <button
              key={p.id}
              onClick={() => { if (p.id !== currentPark) switchPark(p.id); }}
              className={clsx(
                "flex items-center gap-1 px-2.5 py-2 text-[11px] font-medium whitespace-nowrap transition-colors shrink-0",
                "border-b-2 -mb-px",
                currentPark === p.id
                  ? "border-accent text-ink-primary"
                  : "border-transparent text-ink-muted hover:text-ink-secondary hover:border-bg-hover",
              )}
            >
              <span>{p.icon}</span>
              <span className="hidden sm:inline">{p.name}</span>
              <span className="sm:hidden">{p.short}</span>
            </button>
          ))}
          <button
            onClick={() => setShowHistory(true)}
            className="shrink-0 ml-auto flex items-center gap-1 px-2 py-2 text-ink-muted hover:text-ink-secondary hover:bg-bg-hover transition-colors rounded"
            title="Browse historical wait times"
          >
            <IconCalendar size={13} stroke={1.5} />
          </button>
        </div>

        {refreshNote && (
          <div className="px-4 py-1 text-[11px] bg-bg-card text-ink-secondary border-b border-bg-hover">
            ↻ {refreshNote}
          </div>
        )}
        <div className="flex-1 flex min-h-0 relative overflow-hidden">
          {/* Left sidebar */}
          {(!isMobile || mobileTab === "attractions") && (
            <LandSidebar
              open={leftOpen}
              mobileOpen={isMobile && mobileTab === "attractions"}
              width={leftWidth}
              isResizing={isResizingLeft}
              onToggle={() => {
                if (isMobile) setMobileTab("timeline");
                else setLeftOpen(o => !o);
              }}
              onAttractionClick={(a) => {
                setSelected(a); setSelectedRestaurant(null);
                if (isMobile) setMobileTab("timeline");
              }}
              onRestaurantClick={(r) => {
                setSelectedRestaurant(r); setSelected(null);
                if (isMobile) setMobileTab("timeline");
              }}
              selectedId={selected?.id ?? selectedRestaurant?.id ?? null}
            />
          )}

          {/* Left resize handle */}
          {!isMobile && leftOpen && (
            <div
              onPointerDown={startLeftResize}
              className={clsx(
                "shrink-0 w-1 cursor-col-resize select-none transition-colors duration-75",
                isResizingLeft ? "bg-accent/60" : "hover:bg-accent/40 bg-transparent",
              )}
              style={{ touchAction: "none" }}
            />
          )}

          <main className={clsx(
            "flex-1 flex flex-col min-w-0",
            isMobile && mobileTab !== "timeline" && "hidden",
          )}>
            <Timeline onShowFeasibility={() => setShowFeasibility(true)} />
            {selected && (
              <div className="border-t border-bg-hover p-3 bg-bg-base/50 shrink-0">
                <WaitTimeChart attraction={selected} onClose={() => setSelected(null)} />
              </div>
            )}
            {selectedRestaurant && (
              <div className="border-t border-bg-hover p-3 bg-bg-base/50 shrink-0">
                <RestaurantPanel restaurant={selectedRestaurant} onClose={() => setSelectedRestaurant(null)} />
              </div>
            )}
          </main>

          {/* Right resize handle */}
          {!isMobile && rightOpen && (
            <div
              onPointerDown={startRightResize}
              className={clsx(
                "shrink-0 w-1 cursor-col-resize select-none transition-colors duration-75",
                isResizingRight ? "bg-accent/60" : "hover:bg-accent/40 bg-transparent",
              )}
              style={{ touchAction: "none" }}
            />
          )}

          {/* Right sidebar */}
          {(!isMobile || mobileTab === "optimize") && (
            <OptimizePanel
              open={rightOpen}
              mobileOpen={isMobile && mobileTab === "optimize"}
              width={rightWidth}
              isResizing={isResizingRight}
              onToggle={() => {
                if (isMobile) setMobileTab("timeline");
                else setRightOpen(o => !o);
              }}
            />
          )}
        </div>

        {/* Mobile bottom tab nav */}
        {isMobile && (
          <nav className="shrink-0 flex border-t border-bg-hover bg-bg-panel safe-area-bottom">
            {([
              { tab: "attractions" as const, label: "Rides", Icon: IconRollercoaster },
              { tab: "timeline"    as const, label: "Day",   Icon: IconCalendarEvent },
              { tab: "optimize"   as const, label: "Plan",   Icon: IconOptimize },
            ]).map(({ tab, label, Icon }) => (
              <button
                key={tab}
                onClick={() => setMobileTab(tab)}
                className={clsx(
                  "flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[10px] font-medium transition-colors",
                  mobileTab === tab
                    ? "text-accent"
                    : "text-ink-muted hover:text-ink-secondary",
                )}
              >
                <Icon size={20} stroke={1.5} />
                {label}
              </button>
            ))}
          </nav>
        )}
      </div>
      <AIChat />
      {showHistory && <HistoryExplorer onClose={() => setShowHistory(false)} />}
      {showFeasibility && <FeasibilityReport onClose={() => setShowFeasibility(false)} />}
      <DragOverlay dropAnimation={null} zIndex={9999}>
        {overlayBlock}
      </DragOverlay>
    </DndContext>
  );
}
