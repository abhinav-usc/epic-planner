import { useState } from "react";
import clsx from "clsx";
import { IconStar, IconX, IconSparkles, IconLayoutSidebarRightCollapse, IconLayoutSidebarRightExpand, IconPlus, IconShoppingBag, IconToolsKitchen2, IconBolt, IconLock } from "@tabler/icons-react";
import { usePlanner } from "../store/plannerStore";
import { formatHM } from "../lib/format";
import type { Attraction, LandId } from "../types";

const DURATIONS = [15, 30, 45, 60, 90];
const HOURS = Array.from({ length: 15 }, (_, i) => i + 8); // 8–22

function fmtHour(h: number) {
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = ((h + 11) % 12) + 1;
  return `${h12} ${ampm}`;
}

interface OptimizePanelProps {
  open: boolean;
  onToggle: () => void;
  mobileOpen?: boolean;
}

export function OptimizePanel({ open, onToggle, mobileOpen }: OptimizePanelProps) {
  const {
    priorities, attractions, optimizing, optimizeResult,
    ropeDropLand, arrivalHour, lands, currentPark,
    foodBreaks, shoppingBreaks, useLlMulti, llSingleIds, landHopping,
    plannedItems,
    togglePriority, toggleMustDo, setRank,
    setRopeDropLand, setArrivalHour,
    addFoodBreak, removeFoodBreak, updateFoodBreak,
    toggleShoppingBreak, setShoppingBreakDuration,
    setUseLlMulti, toggleLlSingle, setLandHopping,
    addLlReservation, removeLlReservation,
    runOptimize, applyOptimizeResultToTimeline,
    llPlan, llPlanLoading, earlyEntry,
  } = usePlanner();

  const [addingLlr, setAddingLlr] = useState(false);
  const [llrAttrId, setLlrAttrId] = useState("");
  const [llrTime, setLlrTime] = useState("10:00");

  const parkOpenHour = earlyEntry ? 8 : 9;
  const fmtClock = (minute: number): string => {
    const total = parkOpenHour * 60 + minute;
    const h = Math.floor(total / 60);
    const m = total % 60;
    const hh = ((h + 11) % 12) + 1;
    const ampm = h >= 12 && h < 24 ? "PM" : "AM";
    return `${hh}:${m.toString().padStart(2, "0")} ${ampm}`;
  };

  const isDisney = currentPark !== "epic_universe";

  // 15-minute time slots from park open to 11 PM.
  const timeSlots = (() => {
    const slots: { label: string; minFromOpen: number }[] = [];
    for (let absMin = parkOpenHour * 60; absMin <= 23 * 60; absMin += 15) {
      const h = Math.floor(absMin / 60);
      const m = absMin % 60;
      const hh = ((h + 11) % 12) + 1;
      const ampm = h >= 12 && h < 24 ? "PM" : "AM";
      slots.push({ label: `${hh}:${m.toString().padStart(2, "0")} ${ampm}`, minFromOpen: absMin - parkOpenHour * 60 });
    }
    return slots;
  })();

  const LANDS: { id: LandId; name: string }[] = lands
    ? Object.entries(lands).map(([id, l]) => ({ id: id as LandId, name: l.name }))
    : [];

  const attrMap = new Map<string, Attraction>(attractions.map(a => [a.id, a]));
  const sorted = [...priorities].sort((a, b) =>
    (Number(!b.must_do) - Number(!a.must_do)) || (a.rank - b.rank)
  );

  return (
    <aside className={clsx(
      "shrink-0 border-l border-bg-hover bg-bg-panel flex flex-col transition-all duration-200 min-h-0",
      mobileOpen
        ? "fixed inset-0 z-40 w-full"
        : open ? "w-72" : "w-9",
    )}>
      {!mobileOpen && !open ? (
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-start pl-2 py-2.5 text-ink-muted hover:text-ink-primary hover:bg-bg-hover transition-colors shrink-0"
          title="Expand optimizer"
        >
          <IconLayoutSidebarRightExpand size={15} stroke={1.5} />
        </button>
      ) : (
        <>
          {/* Header */}
          <div className="flex items-center gap-2 pl-1 pr-3 py-2 border-b border-bg-hover shrink-0">
            {!mobileOpen && (
              <button
                onClick={onToggle}
                className="w-7 h-7 flex items-center justify-center rounded-md text-ink-muted hover:text-ink-primary hover:bg-bg-hover transition-colors shrink-0"
                title="Collapse optimizer"
              >
                <IconLayoutSidebarRightCollapse size={15} stroke={1.5} />
              </button>
            )}
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-medium">AI Optimizer</h2>
              <p className="text-[10px] text-ink-secondary">Pick your priorities. We schedule them.</p>
            </div>
            {mobileOpen && (
              <button
                onClick={onToggle}
                className="w-8 h-8 flex items-center justify-center rounded-md text-ink-muted hover:text-ink-primary hover:bg-bg-hover transition-colors shrink-0"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto px-3 pt-3 space-y-4">
            {/* Priority list */}
            <div className="space-y-1">
              {sorted.length === 0 && (
                <div className="text-ink-muted text-xs text-center mt-4 leading-relaxed">
                  Add rides from the left sidebar to see them here.
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
                        {a.kind === "show" && p.chosen_showtime && ` · ${p.chosen_showtime}`}
                      </div>
                    </div>
                    <input
                      type="number"
                      min={1}
                      value={p.rank}
                      onChange={(e) => setRank(p.attraction_id, Number(e.target.value) || 1)}
                      className="w-10 bg-bg-base rounded text-[10px] px-1 py-0.5 text-center"
                      style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
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

            {/* Rope drop land */}
            <div>
              <label className="text-[10px] text-ink-secondary block mb-1">Rope drop land</label>
              <select
                value={ropeDropLand ?? ""}
                onChange={(e) => setRopeDropLand(e.target.value || null)}
                className="w-full bg-bg-card text-[11px] rounded-md px-2 py-1 text-ink-primary"
                style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
              >
                <option value="">Let optimizer decide</option>
                {LANDS.map(l => (
                  <option key={l.id} value={l.id}>{l.name}</option>
                ))}
              </select>
            </div>

            {/* Arrival time */}
            <div>
              <label className="text-[10px] text-ink-secondary block mb-1">Arrival time</label>
              <select
                value={arrivalHour ?? ""}
                onChange={(e) => setArrivalHour(e.target.value ? Number(e.target.value) : null)}
                className="w-full bg-bg-card text-[11px] rounded-md px-2 py-1 text-ink-primary"
                style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
              >
                <option value="">Park open (default)</option>
                {HOURS.slice(1).map(h => (
                  <option key={h} value={h}>{fmtHour(h)}</option>
                ))}
              </select>
            </div>

            {/* Food breaks */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1 text-[10px] text-ink-secondary">
                  <IconToolsKitchen2 size={11} stroke={1.5} />
                  <span className="uppercase tracking-wider font-medium">Meal breaks</span>
                </div>
                <button
                  onClick={addFoodBreak}
                  className="flex items-center gap-0.5 text-[10px] text-accent hover:text-accent/80"
                >
                  <IconPlus size={11} stroke={2} /> Add
                </button>
              </div>
              <div className="space-y-1">
                {foodBreaks.map((fb, i) => {
                  const startMin = fb.start_minute ?? Math.max(0, (fb.earliest_hour - parkOpenHour) * 60);
                  const endMin = fb.end_minute ?? (startMin + fb.duration_minutes);
                  const durMin = endMin - startMin;
                  return (
                    <div key={i} className="card p-2 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <select
                          value={startMin}
                          onChange={e => {
                            const sm = Number(e.target.value);
                            const em = Math.max(sm + 15, endMin);
                            updateFoodBreak(i, {
                              start_minute: sm, end_minute: em,
                              duration_minutes: em - sm,
                              earliest_hour: Math.floor((parkOpenHour * 60 + sm) / 60),
                              latest_hour: Math.floor((parkOpenHour * 60 + em) / 60),
                            });
                          }}
                          className="bg-bg-base text-[10px] rounded px-1 py-0.5 flex-1"
                          style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
                        >
                          {timeSlots.map(t => <option key={t.minFromOpen} value={t.minFromOpen}>{t.label}</option>)}
                        </select>
                        <span className="text-[9px] text-ink-muted shrink-0">–</span>
                        <select
                          value={endMin}
                          onChange={e => {
                            const em = Number(e.target.value);
                            updateFoodBreak(i, {
                              end_minute: em,
                              start_minute: startMin,
                              duration_minutes: em - startMin,
                              earliest_hour: Math.floor((parkOpenHour * 60 + startMin) / 60),
                              latest_hour: Math.floor((parkOpenHour * 60 + em) / 60),
                            });
                          }}
                          className="bg-bg-base text-[10px] rounded px-1 py-0.5 flex-1"
                          style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
                        >
                          {timeSlots.filter(t => t.minFromOpen > startMin).map(t => <option key={t.minFromOpen} value={t.minFromOpen}>{t.label}</option>)}
                        </select>
                        <button
                          onClick={() => removeFoodBreak(i)}
                          className="text-ink-secondary hover:text-red-400 shrink-0"
                        >
                          <IconX size={11} stroke={1.5} />
                        </button>
                      </div>
                      <div className="text-[9px] text-ink-muted px-0.5">{durMin}m break</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Shopping breaks */}
            <div>
              <div className="flex items-center gap-1 mb-1.5 text-[10px] text-ink-secondary">
                <IconShoppingBag size={11} stroke={1.5} />
                <span className="uppercase tracking-wider font-medium">Shopping breaks</span>
              </div>
              <div className="space-y-1">
                {LANDS.map(l => {
                  const active = shoppingBreaks.find(sb => sb.land === l.id);
                  return (
                    <div key={l.id} className="flex items-center gap-2">
                      <button
                        onClick={() => toggleShoppingBreak(l.id)}
                        className={clsx(
                          "flex-1 flex items-center gap-1.5 text-left px-2 py-1 rounded text-[10px] transition-colors",
                          active ? "bg-accent/10 text-accent" : "bg-bg-hover text-ink-muted hover:text-ink-secondary",
                        )}
                      >
                        <span className={clsx("w-3 h-3 rounded border flex items-center justify-center shrink-0",
                          active ? "border-accent bg-accent text-bg-base" : "border-border-subtle"
                        )}>
                          {active && <span className="text-[8px] leading-none">✓</span>}
                        </span>
                        <span className="truncate">{l.name}</span>
                      </button>
                      {active && (
                        <select
                          value={active.duration_minutes}
                          onChange={e => setShoppingBreakDuration(l.id, Number(e.target.value))}
                          className="bg-bg-base text-[10px] rounded px-1 py-0.5 w-14 shrink-0"
                          style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
                        >
                          {DURATIONS.map(d => <option key={d} value={d}>{d}m</option>)}
                        </select>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Land hopping toggle */}
            <div>
              <button
                onClick={() => setLandHopping(!landHopping)}
                className={clsx(
                  "w-full flex items-center gap-2 px-2 py-1.5 rounded text-[10px] transition-colors text-left",
                  landHopping ? "bg-accent/10 text-accent" : "bg-bg-hover text-ink-muted hover:text-ink-secondary",
                )}
              >
                <span className={clsx("w-3 h-3 rounded border flex items-center justify-center shrink-0",
                  landHopping ? "border-accent bg-accent text-bg-base" : "border-border-subtle"
                )}>
                  {landHopping && <span className="text-[8px] leading-none">✓</span>}
                </span>
                <span className="flex-1">Land hopping</span>
                <span className="text-[9px] opacity-60 shrink-0">{landHopping ? "global greedy" : "cluster lands"}</span>
              </button>
              {landHopping && (
                <p className="text-[9px] text-ink-muted mt-0.5 px-1 leading-relaxed">
                  Freely hops between lands — picks whichever ride has the lowest walk + wait next.
                </p>
              )}
            </div>

            {/* Lightning Lane — Disney parks only */}
            {isDisney && (
              <div>
                <div className="flex items-center gap-1 mb-1.5 text-[10px] text-ink-secondary">
                  <IconBolt size={11} stroke={1.5} />
                  <span className="uppercase tracking-wider font-medium">Lightning Lane</span>
                </div>
                <div className="space-y-1">
                  {/* LLMP toggle */}
                  <button
                    onClick={() => setUseLlMulti(!useLlMulti)}
                    className={clsx(
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded text-[10px] transition-colors text-left",
                      useLlMulti ? "bg-accent/10 text-accent" : "bg-bg-hover text-ink-muted hover:text-ink-secondary",
                    )}
                  >
                    <span className={clsx("w-3 h-3 rounded border flex items-center justify-center shrink-0",
                      useLlMulti ? "border-accent bg-accent text-bg-base" : "border-border-subtle"
                    )}>
                      {useLlMulti && <span className="text-[8px] leading-none">✓</span>}
                    </span>
                    <span>Multi Pass (LLMP)</span>
                    <span className="ml-auto text-[9px] opacity-60">most rides</span>
                  </button>

                  {/* LLSP per-ride — only for LLSP rides in the priority list */}
                  {sorted.some(p => attrMap.get(p.attraction_id)?.ll_type === "single") && (
                    <div className="mt-1 space-y-0.5">
                      <div className="text-[9px] text-ink-muted px-1 mb-0.5">Individual (LLSP) — select rides you're purchasing:</div>
                      {sorted.filter(p => attrMap.get(p.attraction_id)?.ll_type === "single").map(p => {
                        const a = attrMap.get(p.attraction_id)!;
                        const active = llSingleIds.includes(a.id);
                        return (
                          <button
                            key={a.id}
                            onClick={() => toggleLlSingle(a.id)}
                            className={clsx(
                              "w-full flex items-center gap-2 px-2 py-1 rounded text-[10px] transition-colors text-left",
                              active ? "bg-accent/10 text-accent" : "bg-bg-hover text-ink-muted hover:text-ink-secondary",
                            )}
                          >
                            <span className={clsx("w-3 h-3 rounded border flex items-center justify-center shrink-0",
                              active ? "border-accent bg-accent text-bg-base" : "border-border-subtle"
                            )}>
                              {active && <span className="text-[8px] leading-none">✓</span>}
                            </span>
                            <span className="truncate">{a.name}</span>
                            <span className="ml-auto text-[9px] opacity-50 shrink-0">LLSP</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {/* Pre-booked LLSP return windows */}
                  {(() => {
                    const llspAttractions = attractions.filter(a => a.ll_type === "single");
                    const lockedItems = plannedItems.filter(p => p.locked);
                    const parkOpen = earlyEntry ? 8 : 9;
                    const minuteToTime = (min: number) => {
                      const abs = parkOpen * 60 + min;
                      const h = Math.floor(abs / 60), m = abs % 60;
                      return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
                    };
                    if (llspAttractions.length === 0) return null;
                    return (
                      <div className="mt-2 space-y-1">
                        <div className="flex items-center gap-1 text-[9px] text-ink-muted px-1">
                          <IconLock size={9} stroke={1.5} />
                          <span>Pre-booked return windows:</span>
                        </div>
                        {lockedItems.map(item => (
                          <div key={item.id} className="flex items-center gap-1 px-2 py-1 rounded bg-amber-500/10 text-[10px] text-amber-400">
                            <IconLock size={9} stroke={1.5} className="shrink-0" />
                            <span className="truncate flex-1">{item.name}</span>
                            <span className="shrink-0 opacity-70">{minuteToTime(item.start_minute)}</span>
                            <button onClick={() => removeLlReservation(item.id)} className="ml-1 text-ink-muted hover:text-red-400 shrink-0">
                              <IconX size={10} stroke={2} />
                            </button>
                          </div>
                        ))}
                        {addingLlr ? (
                          <div className="flex flex-col gap-1 px-1 py-1.5 rounded bg-bg-hover text-[10px]">
                            <select
                              value={llrAttrId}
                              onChange={e => setLlrAttrId(e.target.value)}
                              className="w-full bg-bg-base border border-border-subtle rounded px-1.5 py-0.5 text-[10px] text-ink-primary"
                            >
                              <option value="">Select ride…</option>
                              {llspAttractions.map(a => (
                                <option key={a.id} value={a.id}>{a.name}</option>
                              ))}
                            </select>
                            <div className="flex gap-1 items-center">
                              <span className="text-ink-muted shrink-0">Window:</span>
                              <input
                                type="time"
                                value={llrTime}
                                onChange={e => setLlrTime(e.target.value)}
                                className="flex-1 bg-bg-base border border-border-subtle rounded px-1.5 py-0.5 text-[10px] text-ink-primary"
                              />
                            </div>
                            <div className="flex gap-1">
                              <button
                                onClick={() => {
                                  const a = llspAttractions.find(x => x.id === llrAttrId);
                                  if (!a || !llrTime) return;
                                  const [hh, mm] = llrTime.split(":").map(Number);
                                  const windowStartMinute = (hh * 60 + mm) - parkOpen * 60;
                                  if (windowStartMinute < 0) return;
                                  addLlReservation(a, windowStartMinute);
                                  setAddingLlr(false);
                                  setLlrAttrId("");
                                }}
                                disabled={!llrAttrId}
                                className="flex-1 btn-primary text-[10px] py-0.5 disabled:opacity-40"
                              >Add</button>
                              <button onClick={() => setAddingLlr(false)} className="px-2 text-ink-muted hover:text-ink-secondary text-[10px]">Cancel</button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setAddingLlr(true)}
                            className="w-full flex items-center gap-1 px-2 py-1 rounded bg-bg-hover text-[10px] text-ink-muted hover:text-ink-secondary transition-colors"
                          >
                            <IconPlus size={10} stroke={2} />
                            Add pre-booked return window
                          </button>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
            {optimizeResult && (
              <div className="card p-3 text-[10px] space-y-1">
                <div className="flex justify-between">
                  <span className="text-ink-secondary">Total wait</span>
                  <span className="font-medium text-status-warn">
                    {formatHM(optimizeResult.total_wait_minutes)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-secondary">Active time</span>
                  <span className="font-medium">{formatHM(optimizeResult.total_activity_minutes)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-secondary">Status</span>
                  <span className={optimizeResult.feasible ? "text-status-ok" : "text-status-bad"}>
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

            {/* Lightning Lane plan (compact, scrolls internally when long) */}
            {llPlan && llPlan.bookings.length > 0 && (
              <div className="card text-[10px]">
                <div className="px-2.5 pt-2 pb-1 flex items-center justify-between sticky top-0 bg-bg-card">
                  <div className="flex items-center gap-1 uppercase tracking-wider font-medium text-purple-300 text-[9px]">
                    <IconBolt size={10} stroke={1.5} /> LL Plan · {llPlan.bookings.length}
                  </div>
                  {llPlanLoading && <span className="text-ink-muted">…</span>}
                </div>
                <ul className="max-h-44 overflow-y-auto px-2 pb-2 space-y-1">
                  {llPlan.bookings.map((b, idx) => (
                    <li key={`${b.attraction_id}-${idx}`} className={clsx(
                      "rounded px-1.5 py-1 leading-tight",
                      b.priority === "urgent" && "bg-amber-500/10 border border-amber-500/30",
                      b.priority === "skip" && "bg-bg-hover opacity-50",
                      b.priority === "normal" && "bg-purple-500/5",
                    )}>
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-medium truncate">{b.attraction_name}</span>
                        {b.priority === "urgent" && (
                          <span className="shrink-0 text-[8px] font-medium uppercase text-amber-300">!</span>
                        )}
                      </div>
                      {b.priority !== "skip" ? (
                        <div className="text-ink-secondary text-[9px]" title={b.reason}>
                          Book {b.book_at_minute === 0 ? "park open" : fmtClock(b.book_at_minute)}
                          {" · "}return {fmtClock(b.predicted_return_minute)}
                          {b.savings_minutes > 0 && <span className="text-ink-muted"> · –{b.savings_minutes}m</span>}
                        </div>
                      ) : (
                        <div className="text-[9px] text-ink-muted" title={b.reason}>
                          Skip LL · {b.reason}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Optimize button — always pinned at bottom */}
          <div className="px-3 py-2.5 border-t border-bg-hover shrink-0">
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
          </div>
        </>
      )}
    </aside>
  );
}
