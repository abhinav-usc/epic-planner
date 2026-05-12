import clsx from "clsx";
import { usePlanner } from "../store/plannerStore";
import { formatHM } from "../lib/format";
import type { Attraction } from "../types";

export function OptimizePanel() {
  const {
    priorities, attractions, optimizing, optimizeResult,
    togglePriority, toggleMustDo, setRank,
    runOptimize, applyOptimizeResultToTimeline,
  } = usePlanner();

  const attrMap = new Map<string, Attraction>(attractions.map(a => [a.id, a]));
  const sorted = [...priorities].sort((a, b) =>
    (Number(!b.must_do) - Number(!a.must_do)) || (a.rank - b.rank)
  );

  return (
    <aside className="w-80 shrink-0 border-l border-bg-hover bg-bg-panel flex flex-col">
      <div className="px-4 py-3 border-b border-bg-hover">
        <h2 className="font-display font-semibold text-base">AI Optimizer</h2>
        <p className="text-xs text-ink-secondary">Pick your priorities. We schedule them.</p>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sorted.length === 0 && (
          <div className="text-ink-muted text-sm text-center mt-8">
            Mark attractions with <span className="text-accent">+</span> or <span className="text-accent">★</span> from the left.
          </div>
        )}

        {sorted.map(p => {
          const a = attrMap.get(p.attraction_id);
          if (!a) return null;
          return (
            <div key={p.attraction_id} className="card px-2.5 py-2 flex items-center gap-2">
              <button
                onClick={() => toggleMustDo(p.attraction_id)}
                className={clsx(
                  "shrink-0 text-sm w-7 h-7 rounded-md flex items-center justify-center",
                  p.must_do ? "bg-accent text-bg-base" : "bg-bg-hover text-ink-secondary",
                )}
                title="Must-do"
              >
                ★
              </button>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{a.name}</div>
                <div className="text-xs text-ink-secondary flex gap-2">
                  <span>{p.must_do ? "must-do" : `rank ${p.rank}`}</span>
                </div>
              </div>
              <input
                type="number"
                min={1}
                value={p.rank}
                onChange={(e) => setRank(p.attraction_id, Number(e.target.value) || 1)}
                className="w-12 bg-bg-base border border-bg-hover rounded text-sm px-1 py-0.5 text-center"
                title="Rank"
              />
              <button
                onClick={() => togglePriority(p.attraction_id)}
                className="text-ink-secondary hover:text-red-400 text-sm"
                title="Remove"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>

      <div className="p-3 border-t border-bg-hover space-y-2">
        <button
          onClick={runOptimize}
          disabled={priorities.length === 0 || optimizing}
          className={clsx(
            "w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed",
            "py-2 text-sm font-semibold",
          )}
        >
          {optimizing ? "Optimizing…" : "✨ Optimize My Day"}
        </button>

        {optimizeResult && (
          <div className="card p-3 text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-ink-secondary">Total wait</span>
              <span className="font-semibold text-amber-300">
                {formatHM(optimizeResult.total_wait_minutes)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary">Active time</span>
              <span className="font-semibold">{formatHM(optimizeResult.total_activity_minutes)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary">Status</span>
              <span className={optimizeResult.feasible ? "text-green-400" : "text-red-400"}>
                {optimizeResult.feasible ? "✓ Feasible" : "⚠ Tight"}
              </span>
            </div>
            <button
              onClick={applyOptimizeResultToTimeline}
              className="btn-ghost w-full mt-2 text-xs"
            >
              ← Apply to timeline
            </button>
            {optimizeResult.warnings.length > 0 && (
              <details className="mt-2 text-ink-secondary">
                <summary className="cursor-pointer">{optimizeResult.warnings.length} warning(s)</summary>
                <ul className="mt-1 space-y-0.5 list-disc list-inside">
                  {optimizeResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </details>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
