import { useState } from "react";
import { IconX, IconChartBar, IconCheck, IconAlertTriangle } from "@tabler/icons-react";
import clsx from "clsx";
import { api } from "../api/client";
import { usePlanner } from "../store/plannerStore";
import type { FeasibilityResult, FeasibilityDateResult } from "../types";

function rateColor(rate: number) {
  if (rate >= 0.8) return "text-status-ok";
  if (rate >= 0.5) return "text-status-warn";
  return "text-status-bad";
}

function rateChip(rate: number) {
  if (rate >= 0.8) return "chip-ok";
  if (rate >= 0.5) return "chip-warn";
  return "chip-bad";
}

function fmtMin(min: number, parkOpen: number) {
  const total = parkOpen * 60 + min;
  const h = Math.floor(total / 60) % 24;
  const m = total % 60;
  const ampm = h >= 12 ? "PM" : "AM";
  return `${((h + 11) % 12) + 1}:${m.toString().padStart(2, "0")} ${ampm}`;
}

function fmtDate(d: string) {
  return new Date(d + "T12:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function DateRow({ r, parkOpen }: { r: FeasibilityDateResult; parkOpen: number }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 text-[11px] border-b border-bg-hover last:border-0">
      {r.passed
        ? <IconCheck size={11} className="text-status-ok shrink-0" />
        : <IconAlertTriangle size={11} className="text-status-bad shrink-0" />}
      <span className="flex-1">{fmtDate(r.date)}</span>
      <span className="text-ink-muted">done by {fmtMin(r.total_minutes, parkOpen)}</span>
      {r.overrun > 0 && (
        <span className="text-status-bad">+{r.overrun}m over</span>
      )}
    </div>
  );
}

interface Props {
  onClose: () => void;
}

export function FeasibilityReport({ onClose }: Props) {
  const { plannedItems, earlyEntry, arrivalHour } = usePlanner();
  const [result, setResult] = useState<FeasibilityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const parkOpen = earlyEntry ? 8 : 9;
  const arrivalMinute = arrivalHour ? Math.max(0, (arrivalHour - parkOpen) * 60) : 0;

  // Send all items so breaks and shows are included in the time simulation
  const allItems = [...plannedItems].sort((a, b) => a.start_minute - b.start_minute);

  async function run() {
    setLoading(true);
    setResult(null);
    try {
      const r = await api.feasibility({
        items: allItems.map(p => ({
          name: p.name,
          land: p.land,
          start_minute: p.start_minute,
          wait_minutes: p.wait_minutes,
          ride_minutes: p.ride_minutes,
          duration_minute: p.duration_minute,
          kind: p.kind,
        })),
        park_open_hour: parkOpen,
        arrival_minute: arrivalMinute,
      });
      setResult(r);
    } catch (e: any) {
      alert(`Feasibility check failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  const sortedResults = result
    ? [...result.all_results].sort((a, b) => b.date.localeCompare(a.date))
    : [];
  const displayed = result
    ? showAll ? sortedResults : sortedResults.slice(0, 30)
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.55)" }}>
      <div
        className="flex flex-col w-full max-w-2xl mx-4 rounded-xl overflow-hidden shadow-2xl"
        style={{ background: "var(--bg-panel)", border: "1px solid var(--border-subtle)", maxHeight: "85vh" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-bg-hover shrink-0">
          <div className="flex items-center gap-2">
            <IconChartBar size={16} stroke={1.5} className="text-accent" />
            <h2 className="text-sm font-medium">Plan Feasibility</h2>
            <span className="text-[11px] text-ink-secondary">
              Would your sequence have fit on each historical day?
            </span>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-bg-hover text-ink-secondary">
            <IconX size={14} stroke={1.5} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* What's being simulated */}
          <div>
            <div className="section-label mb-1.5">
              Sequence being simulated ({allItems.length} items in order)
            </div>
            <p className="text-[11px] text-ink-secondary mb-2">
              Each historical day is simulated in your planned order,
              starting at {arrivalHour ? fmtMin(arrivalMinute, parkOpen) : "park open"},
              using actual recorded waits. Food/show blocks anchor at their scheduled times
              (you wait if you arrive early). A day passes if the sequence finishes within
              your planned window + 30 min.
            </p>
            <div className="flex flex-wrap gap-1">
              {allItems.map((p, i) => (
                <span
                  key={p.id}
                  className={clsx(
                    "chip text-[10px]",
                    p.kind === "break_food" || p.kind === "break_shop"
                      ? "bg-bg-hover text-ink-muted"
                      : "bg-bg-card text-ink-secondary",
                  )}
                >
                  {i + 1}. {p.name}
                </span>
              ))}
            </div>
          </div>

          {!result && (
            <button
              onClick={run}
              disabled={loading || allItems.length === 0}
              className="btn-primary w-full"
            >
              {loading ? "Simulating across historical days…" : "Run simulation"}
            </button>
          )}

          {result && (
            <>
              {result.error ? (
                <p className="text-ink-muted text-sm text-center">{result.error}</p>
              ) : (
                <>
                  {/* Big pass rate + timing stats */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="card p-4 text-center col-span-1">
                      <div className={clsx("text-4xl font-bold", result.pass_rate !== null ? rateColor(result.pass_rate) : "text-ink-muted")}>
                        {result.pass_rate !== null ? `${Math.round(result.pass_rate * 100)}%` : "—"}
                      </div>
                      <div className="text-[10px] text-ink-secondary mt-1">
                        {result.days_passed} / {result.days_checked} days fit
                      </div>
                      {result.pass_rate !== null && (
                        <div className="mt-2">
                          <span className={clsx("chip", rateChip(result.pass_rate))}>
                            {result.pass_rate >= 0.8 ? "Solid plan" :
                             result.pass_rate >= 0.5 ? "Tight on busy days" :
                             "Often runs long"}
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="card p-3 col-span-2 grid grid-cols-2 gap-y-3 gap-x-4 text-[11px]">
                      <div>
                        <div className="text-ink-muted text-[9px] uppercase tracking-wider">Planned done by</div>
                        <div className="font-medium mt-0.5">{fmtMin(result.planned_end_minutes, parkOpen)}</div>
                      </div>
                      <div>
                        <div className="text-ink-muted text-[9px] uppercase tracking-wider">Avg actual done by</div>
                        <div className={clsx("font-medium mt-0.5",
                          result.avg_overrun_minutes > 30 ? "text-status-bad" :
                          result.avg_overrun_minutes > 0 ? "text-status-warn" : "text-status-ok"
                        )}>
                          {fmtMin(result.avg_actual_end_minutes, parkOpen)}
                        </div>
                      </div>
                      <div>
                        <div className="text-ink-muted text-[9px] uppercase tracking-wider">Avg overrun</div>
                        <div className={clsx("font-medium mt-0.5",
                          result.avg_overrun_minutes > 30 ? "text-status-bad" :
                          result.avg_overrun_minutes > 0 ? "text-status-warn" : "text-status-ok"
                        )}>
                          {result.avg_overrun_minutes > 0 ? `+${result.avg_overrun_minutes} min` : "On time"}
                        </div>
                      </div>
                      <div>
                        <div className="text-ink-muted text-[9px] uppercase tracking-wider">Tolerance</div>
                        <div className="font-medium mt-0.5 text-ink-secondary">±{result.slack_minutes} min buffer</div>
                      </div>
                    </div>
                  </div>

                  {/* Per-ride wait stats */}
                  {result.ride_stats.length > 0 && (
                    <div>
                      <div className="section-label mb-2">Ride waits — planned vs. actual avg</div>
                      <div className="card overflow-hidden">
                        {result.ride_stats.map((r, i) => {
                          const diff = r.avg_actual_wait - r.planned_wait;
                          return (
                            <div key={i} className="flex items-center gap-2 px-3 py-1.5 text-[11px] border-b border-bg-hover last:border-0">
                              <span className="flex-1 truncate font-medium">{r.name}</span>
                              <span className="text-ink-muted">planned {r.planned_wait}m</span>
                              <span className={clsx(
                                "font-medium",
                                diff > 15 ? "text-status-bad" : diff > 5 ? "text-status-warn" : "text-status-ok"
                              )}>
                                avg {r.avg_actual_wait}m
                              </span>
                              <span className={clsx(
                                "chip text-[10px]",
                                diff > 15 ? "chip-bad" : diff > 5 ? "chip-warn" : "chip-ok"
                              )}>
                                {diff > 0 ? `+${diff}m` : diff < 0 ? `${diff}m` : "~"}
                              </span>
                              {r.days_with_data === 0 && (
                                <span className="text-ink-muted text-[10px]">(no hist. data)</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Day-by-day */}
                  <div>
                    <div className="section-label mb-2">Day-by-day simulation results</div>
                    <div className="card overflow-hidden">
                      {displayed.map(r => (
                        <DateRow key={r.date} r={r} parkOpen={parkOpen} />
                      ))}
                      {!showAll && result.all_results.length > 30 && (
                        <button
                          onClick={() => setShowAll(true)}
                          className="w-full py-2 text-[11px] text-ink-secondary hover:bg-bg-hover transition-colors"
                        >
                          Show all {result.all_results.length} days…
                        </button>
                      )}
                    </div>
                  </div>

                  <button onClick={run} className="btn-ghost w-full text-[11px]">
                    Re-run simulation
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
