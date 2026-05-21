import { useCallback, useState } from "react";
import { usePlanner } from "../store/plannerStore";
import type { SavedPlan } from "../types";

const KEY = "epic-planner-saved-plans";

function read(): SavedPlan[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
  catch { return []; }
}

function write(plans: SavedPlan[]) {
  localStorage.setItem(KEY, JSON.stringify(plans));
}

export function useSavedPlans() {
  const { plannedItems, targetDate, earlyEntry, currentPark, loadPlanItems } = usePlanner();
  const [plans, setPlans] = useState<SavedPlan[]>(read);

  const refresh = useCallback(() => setPlans(read()), []);

  const savePlan = useCallback((name: string) => {
    const plan: SavedPlan = {
      id: `plan-${Date.now()}`,
      date: targetDate,
      park: currentPark,
      name: name.trim() || `Plan ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
      savedAt: new Date().toISOString(),
      earlyEntry,
      items: plannedItems,
    };
    const updated = [...read(), plan];
    write(updated);
    setPlans(updated);
    return plan.id;
  }, [plannedItems, targetDate, earlyEntry, currentPark]);

  const loadPlan = useCallback((id: string) => {
    const plan = read().find(p => p.id === id);
    if (!plan) return;
    loadPlanItems(plan.items, plan.earlyEntry);
  }, [loadPlanItems]);

  const deletePlan = useCallback((id: string) => {
    const updated = read().filter(p => p.id !== id);
    write(updated);
    setPlans(updated);
  }, []);

  // Filter by both date AND current park — each park gets its own plan list.
  const plansForDate = plans.filter(p => p.date === targetDate && p.park === currentPark);

  return { plans, plansForDate, savePlan, loadPlan, deletePlan, refresh };
}
