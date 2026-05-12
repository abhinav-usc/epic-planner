import clsx from "clsx";
import { IconStar, IconX, IconSparkles } from "@tabler/icons-react";
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
    <aside className="w-72 shrink-0 border-l border-bg-hover bg-bg-panel flex flex-col">
      <div className="px-3 py-2 border-b border-bg-hover">
        <h2 className="text-sm font-medium">AI optimizer</h2>
        <p className="text-[10px] text-ink-secondary mt-0.5">Pick your priorities. We schedule them.</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3" style={{ paddingTop: "var(--space-3)" }}>
        {sorted.length === 0 && (
          <div className="text-ink-muted text-xs text-center mt-8 leading-relaxed">
            Mark attractions with <IconPlusInline /> or <IconStarInline /> from the left.
          </div>
        )}

        {sorted.map(p => {
          const a = attrMap.get(p.attraction_id);
          if (!a) return null;
          return (
            <div key={p.attraction_id} className="card row-item flex items-center gap-2">
              <button
                onClick={() => toggleMustDo(p.attraction_id)}
                className={clsx(
                  "shrink-0 w-6 h-6 rounded flex items-center justify-center",
                  p.must_do ? "bg-accent text-bg-base" : "bg-bg-hover text-ink-secondary",
                )}
                title="Must-do"
              >
                <IconStar size={11} stroke={2} />
              </button>
              <div className="min-w-0 flex-1">
                <div className="text-[11px] font-medium leading-tight truncate">{a.name}</div>
                <div className="text-[9px] text-ink-secondary mt-0.5">
                  {p.must_do ? "Must-do" : `Rank ${p.rank}`}
                </div>
              </div>
              <input
                type="number"
                min={1}
                value={p.rank}
                onChange={(e) => setRank(p.attraction_id, Number(e.target.value) || 1)}
                className="w-10 bg-bg-base rounded text-[10px] px-1 py-0.5 text-center"
                style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.06)" }}
                title="Rank"
              />
              <button
                onClick={() => togglePriority(p.attraction_id)}
                className="text-ink-secondary hover:text-red-400 transition-colors"
                title="Remove"
              >
                <IconX size={12} stroke={1.5} />
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
            "py-2 text-[11px] flex items-center justify-center gap-1",
          )}
        >
          <IconSparkles size={13} stroke={1.5} />
          {optimizing ? "Optimizing…" : "Optimize my day"}
        </button>

        {optimizeResult && (
          <div className="card p-3 text-[10px] space-y-1">
            <div className="flex justify-between">
              <span className="text-ink-secondary">Total wait</span>
              <span className="font-medium text-amber-300">
                {formatHM(optimizeResult.total_wait_minutes)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary">Active time</span>
              <span className="font-medium">{formatHM(optimizeResult.total_activity_minutes)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-ink-secondary">Status</span>
              <span className={optimizeResult.feasible ? "text-emerald-300" : "text-red-300"}>
                {optimizeResult.feasible ? "Feasible" : "Tight"}
              </span>
            </div>
            <button
              onClick={applyOptimizeResultToTimeline}
              className="btn-ghost w-full mt-2 text-[10px]"
            >
              Apply to timeline
            </button>
            {optimizeResult.warnings.length > 0 && (
              <details className="mt-2 text-ink-secondary">
                <summary className="cursor-pointer">{optimizeResult.warnings.length} warning(s)</summary>
                <ul className="mt-1 space-y-0.5 list-disc list-inside leading-relaxed">
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

function IconPlusInline() {
  return <span className="inline-flex items-center justify-center align-middle w-3 h-3 rounded bg-bg-hover text-accent">+</span>;
}
function IconStarInline() {
  return <IconStar size={11} stroke={2} className="inline align-middle text-accent" />;
}
