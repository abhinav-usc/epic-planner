import { useEffect, useRef, useState } from "react";
import { IconBookmark, IconBookmarkFilled, IconX, IconDownload, IconTrash } from "@tabler/icons-react";
import clsx from "clsx";
import { useSavedPlans } from "../hooks/useSavedPlans";
import { usePlanner } from "../store/plannerStore";
import type { SavedPlan } from "../types";

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function PlanRow({ plan, onLoad, onDelete }: { plan: SavedPlan; onLoad: () => void; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 hover:bg-bg-hover transition-colors group">
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-medium truncate">{plan.name}</div>
        <div className="text-[10px] text-ink-muted flex items-center gap-1.5 mt-0.5">
          <span>{plan.items.length} item{plan.items.length !== 1 ? "s" : ""}</span>
          <span>·</span>
          <span>{relTime(plan.savedAt)}</span>
          {plan.earlyEntry && <span>· Early entry</span>}
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={onLoad}
          className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] bg-accent/15 text-accent hover:bg-accent/25 transition-colors"
          title="Load this plan"
        >
          <IconDownload size={10} stroke={1.5} />
          Load
        </button>
        <button
          onClick={onDelete}
          className="w-5 h-5 rounded flex items-center justify-center text-ink-muted hover:text-status-bad hover:bg-status-bad/10 transition-colors opacity-0 group-hover:opacity-100"
          title="Delete this plan"
        >
          <IconTrash size={10} stroke={1.5} />
        </button>
      </div>
    </div>
  );
}

export function SavedPlansPopover() {
  const { plannedItems, targetDate } = usePlanner();
  const { plansForDate, savePlan, loadPlan, deletePlan } = useSavedPlans();
  const [open, setOpen] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [saved, setSaved] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  function handleSave() {
    savePlan(nameInput);
    setNameInput("");
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const fmtDate = new Date(targetDate + "T12:00:00").toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric",
  });

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className={clsx(
          "flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] transition-colors",
          open || plansForDate.length > 0
            ? "bg-accent/15 text-accent"
            : "bg-bg-card text-ink-secondary hover:bg-bg-hover",
        )}
        style={{ borderWidth: "0.5px", borderColor: open ? "var(--accent)" : "var(--border-subtle)" }}
        title="Save or load plans for this day"
      >
        {plansForDate.length > 0
          ? <IconBookmarkFilled size={12} stroke={1.5} />
          : <IconBookmark size={12} stroke={1.5} />}
        Plans
        {plansForDate.length > 0 && (
          <span className="text-[10px] font-medium">{plansForDate.length}</span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1.5 w-72 rounded-lg shadow-xl z-40 overflow-hidden"
          style={{ background: "var(--bg-panel)", border: "1px solid var(--border-subtle)" }}
        >
          {/* Save section */}
          <div className="p-3 border-b border-bg-hover">
            <div className="text-[10px] font-medium text-ink-secondary uppercase tracking-wider mb-2">
              Save current plan · {fmtDate}
            </div>
            {plannedItems.length === 0 ? (
              <p className="text-[11px] text-ink-muted">Add rides to the timeline first.</p>
            ) : (
              <div className="flex gap-1.5">
                <input
                  type="text"
                  value={nameInput}
                  onChange={e => setNameInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleSave()}
                  placeholder={`Plan name (${plannedItems.length} items)`}
                  className="flex-1 text-[11px] px-2 py-1 rounded-md bg-bg-card"
                  style={{ border: "0.5px solid var(--border-subtle)" }}
                  autoFocus
                />
                <button
                  onClick={handleSave}
                  className={clsx(
                    "px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors shrink-0",
                    saved ? "bg-status-ok/20 text-status-ok" : "btn-primary",
                  )}
                >
                  {saved ? "Saved!" : "Save"}
                </button>
              </div>
            )}
          </div>

          {/* Saved plans for this date */}
          <div>
            {plansForDate.length === 0 ? (
              <p className="text-[11px] text-ink-muted px-3 py-3">No saved plans for {fmtDate} yet.</p>
            ) : (
              <>
                <div className="px-3 pt-2 pb-1 text-[10px] font-medium text-ink-secondary uppercase tracking-wider">
                  Saved for {fmtDate}
                </div>
                <div className="max-h-52 overflow-y-auto">
                  {[...plansForDate].reverse().map(plan => (
                    <PlanRow
                      key={plan.id}
                      plan={plan}
                      onLoad={() => { loadPlan(plan.id); setOpen(false); }}
                      onDelete={() => deletePlan(plan.id)}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
