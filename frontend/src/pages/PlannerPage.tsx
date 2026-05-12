import { useEffect, useState } from "react";
import { DndContext, DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SettingsBar } from "../components/SettingsBar";
import { LandSidebar } from "../components/LandSidebar";
import { Timeline } from "../components/Timeline";
import { OptimizePanel } from "../components/OptimizePanel";
import { WaitTimeChart } from "../components/WaitTimeChart";
import { AIChat } from "../components/AIChat";
import { usePlanner } from "../store/plannerStore";
import { api } from "../api/client";
import type { Attraction } from "../types";

export function PlannerPage() {
  const {
    loaded, catalogError, loadCatalog,
    addPlannedItem, movePlannedItem, plannedItems,
    targetDate, earlyEntry,
  } = usePlanner();
  const [selected, setSelected] = useState<Attraction | null>(null);
  const [refreshNote, setRefreshNote] = useState<string | null>(null);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);

  // Data freshness check on mount
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

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  async function onDragEnd(e: DragEndEvent) {
    const activeId = String(e.active.id);
    const over = e.over;
    if (!over) return;
    const overId = String(over.id);

    // Drop must land on one of the per-hour droppables.
    if (!overId.startsWith("timeline-hour-")) {
      // If we're repositioning, allow drop on the same hour the bar sits over
      // (e.over has bubbled from a child); otherwise cancel cleanly.
      return;
    }
    const targetHour = Number(overId.slice("timeline-hour-".length));
    const openHour = earlyEntry ? 8 : 9;
    const startMin = Math.max(0, (targetHour - openHour) * 60);

    // Case 1: dragging an attraction from the sidebar → add a new block
    if (activeId.startsWith("attr-")) {
      const a = e.active.data.current?.attraction as Attraction | undefined;
      if (!a) return;
      try {
        const curve = await api.dayCurve(a.id, targetDate, earlyEntry);
        const h = curve.hours.find(x => x.hour === targetHour) || curve.hours[0];
        addPlannedItem(a, startMin, h.wait_minutes, h.worst_case_wait ?? undefined);
      } catch {
        addPlannedItem(a, startMin, 30);
      }
      return;
    }

    // Case 2: repositioning an existing block → snap start to the target hour
    if (activeId.startsWith("plan-")) {
      const planId = activeId.slice("plan-".length);
      const existing = plannedItems.find(p => p.id === planId);
      if (!existing) return;
      movePlannedItem(planId, startMin);
      return;
    }
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

  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <div className="h-screen flex flex-col">
        <SettingsBar />
        {refreshNote && (
          <div className="px-4 py-1 text-[10px] bg-bg-card text-ink-secondary border-b border-bg-hover">
            ↻ {refreshNote}
          </div>
        )}
        <div className="flex-1 flex min-h-0">
          <LandSidebar onAttractionClick={setSelected} selectedId={selected?.id ?? null} />
          <main className="flex-1 flex flex-col min-w-0">
            <Timeline />
            {selected && (
              <div className="border-t border-bg-hover p-3 bg-bg-base/50">
                <WaitTimeChart attraction={selected} />
              </div>
            )}
          </main>
          <OptimizePanel />
        </div>
      </div>
      <AIChat />
    </DndContext>
  );
}
