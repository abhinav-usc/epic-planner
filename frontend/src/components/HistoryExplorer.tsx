import { useEffect, useRef, useState, useMemo } from "react";
import { IconX, IconCalendar, IconChevronRight, IconArrowsSort, IconFilter } from "@tabler/icons-react";
import clsx from "clsx";
import { api } from "../api/client";
import { usePlanner } from "../store/plannerStore";
import type { HistoryDateSummary, HistoryDayDetail } from "../types";

// ── Colour helpers ─────────────────────────────────────────────────────────────

function waitToHue(wait: number | null): string {
  if (wait === null) return "var(--bg-hover)";
  if (wait === 0)    return "var(--bg-hover)";
  if (wait <= 15)    return "rgba(16,185,129,0.75)";
  if (wait <= 30)    return "rgba(52,211,153,0.75)";
  if (wait <= 50)    return "rgba(251,191,36,0.80)";
  if (wait <= 75)    return "rgba(249,115,22,0.85)";
  return             "rgba(239,68,68,0.90)";
}

function avgWaitColor(avg: number): string {
  if (avg <= 20) return "var(--status-ok)";
  if (avg <= 45) return "var(--status-warn)";
  return "var(--status-bad)";
}

function waitDotClass(avg: number): string {
  if (avg <= 25) return "bg-emerald-500";
  if (avg <= 45) return "bg-amber-400";
  return "bg-red-500";
}

const HOURS = Array.from({ length: 14 }, (_, i) => i + 8); // 8..21

// ── Holiday period classifier ──────────────────────────────────────────────────

type Period = "all" | "winter" | "spring" | "summer" | "fall" | "thanksgiving" | "long_weekend";

function isInPeriod(dateStr: string, period: Period): boolean {
  if (period === "all") return true;
  const d = new Date(dateStr + "T12:00:00");
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const dow = d.getDay(); // 0=Sun … 6=Sat
  switch (period) {
    case "winter":       return (m === 12 && day >= 19) || (m === 1 && day <= 6);
    case "spring":       return (m >= 3 && m <= 4) || (m === 5 && day <= 5);
    case "summer":       return m >= 6 && m <= 8;
    case "fall":         return (m === 10 && day <= 20) || (m === 11 && day <= 4);
    case "thanksgiving": return m === 11 && day >= 20 && day <= 30;
    case "long_weekend": {
      const isWeekendAdj = dow === 5 || dow === 1 || dow === 0 || dow === 6;
      return isWeekendAdj && (
        (m === 1  && day >= 14 && day <= 22) ||   // MLK
        (m === 2  && day >= 14 && day <= 22) ||   // Presidents'
        (m === 5  && day >= 23 && day <= 31) ||   // Memorial Day
        (m === 7  && day >= 3  && day <= 6)  ||   // July 4
        (m === 9  && day >= 1  && day <= 8)  ||   // Labor Day
        (m === 10 && day >= 9  && day <= 15)       // Columbus Day
      );
    }
  }
}

const PERIOD_LABELS: Record<Period, string> = {
  all:          "All dates",
  winter:       "Winter Break",
  spring:       "Spring Break",
  summer:       "Summer",
  fall:         "Fall Break",
  thanksgiving: "Thanksgiving",
  long_weekend: "Long Weekends",
};

type SortKey = "newest" | "oldest" | "avg_desc" | "avg_asc" | "peak_desc";
const SORT_LABELS: Record<SortKey, string> = {
  newest:    "Newest first",
  oldest:    "Oldest first",
  avg_desc:  "Highest avg wait",
  avg_asc:   "Lowest avg wait",
  peak_desc: "Highest peak wait",
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function HeatmapRow({ a }: { a: HistoryDayDetail["attractions"][0] }) {
  const [hovered, setHovered] = useState<{ hour: number; wait: number | null } | null>(null);
  return (
    <div className="flex items-center gap-1 group relative">
      <div
        className="w-44 shrink-0 text-[11px] truncate text-ink-secondary pr-2 text-right"
        title={a.name}
        style={{ color: a.color }}
      >
        {a.name
          .replace("Harry Potter and the Battle at the Ministry", "HP: Ministry")
          .replace("Monsters Unchained: The Frankenstein Experiment", "Monsters Unchained")
          .replace("Mario Kart: Bowser's Challenge", "Mario Kart")
          .replace("Indiana Jones Adventure", "Indiana Jones")
          .replace("Star Wars: Rise of the Resistance", "Rise of Resistance")
          .replace("Millennium Falcon: Smugglers Run", "Smugglers Run")}
      </div>
      <div className="flex gap-0.5 flex-1">
        {HOURS.map(h => {
          const cell = a.hours.find(x => x.hour === h);
          const wait = cell?.wait_minutes ?? null;
          return (
            <div
              key={h}
              className="flex-1 rounded-sm cursor-default transition-opacity hover:opacity-80"
              style={{ height: 20, backgroundColor: waitToHue(wait), border: "0.5px solid var(--border-subtle)" }}
              title={wait !== null ? `${h}:00 — ${wait} min` : `${h}:00 — no data`}
              onMouseEnter={() => setHovered({ hour: h, wait })}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}
      </div>
      <div className="w-10 shrink-0 text-right text-[10px]" style={{ color: avgWaitColor(a.peak_wait) }}>
        {a.peak_wait}m
      </div>
      {hovered && (
        <div
          className="absolute left-48 z-50 pointer-events-none px-2 py-1 rounded text-[11px] shadow-lg whitespace-nowrap"
          style={{ background: "var(--bg-panel)", border: "1px solid var(--border-subtle)" }}
        >
          {hovered.hour}:00 — {hovered.wait !== null ? `${hovered.wait} min` : "no data"}
        </div>
      )}
    </div>
  );
}

function DayHeatmap({ detail }: { detail: HistoryDayDetail }) {
  return (
    <div className="relative space-y-1">
      <div className="flex items-center gap-1 mb-2">
        <div className="w-44 shrink-0" />
        <div className="flex gap-0.5 flex-1">
          {HOURS.map(h => (
            <div key={h} className="flex-1 text-center text-[9px] text-ink-muted">
              {h >= 12 ? `${h === 12 ? 12 : h - 12}p` : `${h}a`}
            </div>
          ))}
        </div>
        <div className="w-10 shrink-0 text-right text-[9px] text-ink-muted">Peak</div>
      </div>
      {detail.attractions.map(a => <HeatmapRow key={a.slug} a={a} />)}
      <div className="flex items-center gap-2 pt-2 text-[10px] text-ink-muted">
        <span>Wait:</span>
        {[
          { label: "≤15m", color: "rgba(16,185,129,0.75)" },
          { label: "≤30m", color: "rgba(52,211,153,0.75)" },
          { label: "≤50m", color: "rgba(251,191,36,0.80)" },
          { label: "≤75m", color: "rgba(249,115,22,0.85)" },
          { label: "75m+", color: "rgba(239,68,68,0.90)" },
        ].map(({ label, color }) => (
          <span key={label} className="flex items-center gap-1">
            <span style={{ display: "inline-block", width: 10, height: 10, borderRadius: 2, background: color }} />
            {label}
          </span>
        ))}
        <span className="ml-2">Grey = no data</span>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

interface Props { onClose: () => void; }

export function HistoryExplorer({ onClose }: Props) {
  const { setDate, currentPark } = usePlanner();
  const [dates, setDates] = useState<HistoryDateSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<HistoryDayDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("newest");
  const [period, setPeriod] = useState<Period>("all");
  const [showSort, setShowSort] = useState(false);
  const [showFilter, setShowFilter] = useState(false);

  const parkLabel = currentPark === "epic_universe" ? "Epic Universe"
    : currentPark === "disneyland" ? "Disneyland"
    : currentPark === "magic_kingdom" ? "Magic Kingdom"
    : currentPark === "epcot" ? "EPCOT"
    : currentPark === "hollywood_studios" ? "Hollywood Studios"
    : "Animal Kingdom";

  useEffect(() => {
    setDates([]);
    setSelected(null);
    setDetail(null);
    api.historyDates(currentPark).then(setDates).catch(() => {});
  }, [currentPark]);

  useEffect(() => {
    if (!selected) return;
    setLoadingDetail(true);
    setDetail(null);
    api.historyDay(selected, currentPark)
      .then(d => { setDetail(d); setLoadingDetail(false); })
      .catch(() => setLoadingDetail(false));
  }, [selected, currentPark]);

  const processed = useMemo(() => {
    let list = dates.filter(d =>
      (!search || d.date.includes(search)) && isInPeriod(d.date, period)
    );
    switch (sortKey) {
      case "newest":    list = [...list].sort((a, b) => b.date.localeCompare(a.date)); break;
      case "oldest":    list = [...list].sort((a, b) => a.date.localeCompare(b.date)); break;
      case "avg_desc":  list = [...list].sort((a, b) => b.avg_wait - a.avg_wait); break;
      case "avg_asc":   list = [...list].sort((a, b) => a.avg_wait - b.avg_wait); break;
      case "peak_desc": list = [...list].sort((a, b) => b.peak_wait - a.peak_wait); break;
    }
    return list;
  }, [dates, search, sortKey, period]);

  // Group by month only when sorted by date
  const isDateSort = sortKey === "newest" || sortKey === "oldest";
  const groups: Record<string, HistoryDateSummary[]> = useMemo(() => {
    if (!isDateSort) return { "": processed };
    const g: Record<string, HistoryDateSummary[]> = {};
    for (const d of processed) {
      const key = d.date.slice(0, 7);
      g[key] = g[key] ?? [];
      g[key].push(d);
    }
    return g;
  }, [processed, isDateSort]);

  function monthLabel(ym: string): string {
    if (!ym) return "";
    const [y, m] = ym.split("-");
    return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }

  const fmt = (d: string) => new Date(d + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

  function planThisDay() {
    if (!selected) return;
    setDate(selected);
    onClose();
  }

  const noData = dates.length === 0;

  return (
    <div className="fixed inset-0 z-50 flex items-stretch" style={{ background: "rgba(0,0,0,0.55)" }}>
      <div
        className="flex flex-col w-full max-w-6xl mx-auto my-6 rounded-xl overflow-hidden shadow-2xl"
        style={{ background: "var(--bg-panel)", border: "1px solid var(--border-subtle)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-bg-hover shrink-0">
          <div className="flex items-center gap-2">
            <IconCalendar size={16} stroke={1.5} className="text-accent" />
            <h2 className="text-sm font-medium">Historical Wait Times</h2>
            <span className="text-[11px] text-ink-secondary">{parkLabel} · {dates.length} days recorded</span>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-bg-hover text-ink-secondary hover:text-ink-primary transition-colors">
            <IconX size={14} stroke={1.5} />
          </button>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Date list */}
          <div className="w-60 shrink-0 border-r border-bg-hover flex flex-col">
            {/* Search + sort/filter toolbar */}
            <div className="p-2 border-b border-bg-hover space-y-1.5">
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search date…"
                className="w-full text-[11px] px-2 py-1 rounded-md"
                style={{ background: "var(--bg-card)", border: "0.5px solid var(--border-subtle)" }}
              />
              <div className="flex gap-1">
                {/* Sort */}
                <div className="relative flex-1">
                  <button
                    onClick={() => { setShowSort(s => !s); setShowFilter(false); }}
                    className={clsx(
                      "w-full flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors",
                      sortKey !== "newest" ? "text-accent bg-accent/10" : "text-ink-muted bg-bg-hover hover:text-ink-secondary"
                    )}
                  >
                    <IconArrowsSort size={10} stroke={1.5} />
                    <span className="truncate">{SORT_LABELS[sortKey]}</span>
                  </button>
                  {showSort && (
                    <div
                      className="absolute top-full left-0 mt-1 z-10 rounded-lg shadow-xl overflow-hidden w-44"
                      style={{ background: "var(--bg-panel)", border: "1px solid var(--border-subtle)" }}
                    >
                      {(Object.keys(SORT_LABELS) as SortKey[]).map(k => (
                        <button
                          key={k}
                          onClick={() => { setSortKey(k); setShowSort(false); }}
                          className={clsx(
                            "w-full text-left px-3 py-1.5 text-[11px] transition-colors hover:bg-bg-hover",
                            sortKey === k ? "text-accent" : "text-ink-secondary"
                          )}
                        >
                          {SORT_LABELS[k]}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {/* Filter */}
                <div className="relative flex-1">
                  <button
                    onClick={() => { setShowFilter(s => !s); setShowSort(false); }}
                    className={clsx(
                      "w-full flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors",
                      period !== "all" ? "text-accent bg-accent/10" : "text-ink-muted bg-bg-hover hover:text-ink-secondary"
                    )}
                  >
                    <IconFilter size={10} stroke={1.5} />
                    <span className="truncate">{period === "all" ? "Filter" : PERIOD_LABELS[period]}</span>
                  </button>
                  {showFilter && (
                    <div
                      className="absolute top-full left-0 mt-1 z-10 rounded-lg shadow-xl overflow-hidden w-44"
                      style={{ background: "var(--bg-panel)", border: "1px solid var(--border-subtle)" }}
                    >
                      {(Object.keys(PERIOD_LABELS) as Period[]).map(p => (
                        <button
                          key={p}
                          onClick={() => { setPeriod(p); setShowFilter(false); }}
                          className={clsx(
                            "w-full text-left px-3 py-1.5 text-[11px] transition-colors hover:bg-bg-hover",
                            period === p ? "text-accent" : "text-ink-secondary"
                          )}
                        >
                          {PERIOD_LABELS[p]}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="text-[9px] text-ink-muted px-0.5">{processed.length} of {dates.length} dates</div>
            </div>

            {/* Date rows */}
            <div className="flex-1 overflow-y-auto py-1" onClick={() => { setShowSort(false); setShowFilter(false); }}>
              {noData ? (
                <div className="text-center text-ink-muted text-[11px] mt-8 px-4 leading-relaxed">
                  No historical data for {parkLabel} yet.
                </div>
              ) : (
                Object.entries(groups).map(([ym, days]) => (
                  <div key={ym}>
                    {isDateSort && ym && (
                      <div className="px-3 py-1.5 text-[10px] font-medium text-ink-muted uppercase tracking-wider sticky top-0"
                        style={{ background: "var(--bg-panel)" }}>
                        {monthLabel(ym)}
                      </div>
                    )}
                    {days.map(d => (
                      <button
                        key={d.date}
                        onClick={() => setSelected(d.date)}
                        className="w-full text-left px-3 py-1.5 flex items-center gap-1.5 transition-colors hover:bg-bg-hover"
                        style={{ background: selected === d.date ? "var(--bg-hover)" : undefined }}
                      >
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${waitDotClass(d.avg_wait)}`} />
                        <span className="text-[11px] flex-1 min-w-0 truncate">{fmt(d.date)}</span>
                        <span
                          className="text-[10px] font-medium shrink-0 tabular-nums"
                          style={{ color: avgWaitColor(d.avg_wait) }}
                        >
                          {d.avg_wait}m
                        </span>
                        {selected === d.date && <IconChevronRight size={10} className="text-ink-muted shrink-0" />}
                      </button>
                    ))}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Detail panel */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {!selected && (
              <div className="flex-1 flex items-center justify-center text-ink-muted text-sm">
                {noData ? `No historical data available for ${parkLabel}.` : "Select a date to see per-hour wait times"}
              </div>
            )}
            {selected && (
              <>
                <div className="px-5 py-3 border-b border-bg-hover shrink-0 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">{fmt(selected)}</h3>
                    {detail && (
                      <p className="text-[11px] text-ink-secondary mt-0.5">
                        {detail.attractions.length} rides ·
                        peak {Math.max(...detail.attractions.map(a => a.peak_wait))} min ·
                        avg {Math.round(detail.attractions.reduce((s, a) => s + a.avg_wait, 0) / detail.attractions.length)} min
                      </p>
                    )}
                  </div>
                  <button onClick={planThisDay} className="btn-primary text-[11px] px-3 py-1.5">
                    Plan this day →
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-5">
                  {loadingDetail && <div className="text-ink-secondary text-sm text-center mt-12">Loading…</div>}
                  {detail && !loadingDetail && <DayHeatmap detail={detail} />}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
