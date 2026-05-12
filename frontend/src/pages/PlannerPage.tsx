import { useEffect, useState } from "react";
import { DndContext, DragEndEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SettingsBar } from "../components/SettingsBar";
import { LandSidebar } from "../components/LandSidebar";
import { Timeline, TIMELINE_PX_PER_MIN } from "../components/Timeline";
// TIMELINE_PX_PER_MIN imported above is used by the drag-to-move logic below.
import { OptimizePanel } from "../components/OptimizePanel";
import { WaitTimeChart } from "../components/WaitTimeChart";
import { AIChat } from "../components/AIChat";
import { usePlanner } from "../store/plannerStore";
import { api } from "../api/client";
import type { Attraction } from "../types";

export function PlannerPage() {
  const { loaded, catalogError, loadCatalog, addPlannedItem, movePlannedItem, targetDate, earlyEntry, plannedItems } = usePlanner();
  const [selected, setSelected] = useState<Attraction | null>(null);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  async function onDragEnd(e: DragEndEvent) {
    const id = String(e.active.id);
    const overId = e.over?.id;

    // Drag an attraction card → drop on timeline = add at predicted best hour
    if (id.startsWith("attr-") && overId === "timeline") {
      const a = e.active.data.current?.attraction as Attraction | undefined;
      if (!a) return;
      try {
        const curve = await api.dayCurve(a.id, targetDate, earlyEntry);
        const openHour = earlyEntry ? 8 : 9;
        // Pick the lowest-wait hour as the default landing slot.
        const best = curve.hours.reduce((acc, h) => h.wait_minutes < acc.wait_minutes ? h : acc, curve.hours[0]);
        addPlannedItem(a, (best.hour - openHour) * 60, best.wait_minutes);
      } catch {
        addPlannedItem(a, 0, 30);
      }
      return;
    }

    // Drag an existing bar to reposition
    if (id.startsWith("plan-")) {
      const planId = id.slice("plan-".length);
      const existing = plannedItems.find(p => p.id === planId);
      if (!existing) return;
      const deltaMin = Math.round((e.delta.y) / TIMELINE_PX_PER_MIN);
      movePlannedItem(planId, existing.start_minute + deltaMin);
      return;
    }
  }

  if (catalogError) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="panel p-6 max-w-md text-sm">
          <h2 className="font-display font-bold text-lg mb-2">Backend not reachable</h2>
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
