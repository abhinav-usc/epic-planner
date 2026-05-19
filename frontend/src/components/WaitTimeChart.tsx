import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { IconX } from "@tabler/icons-react";
import { api } from "../api/client";
import { usePlanner } from "../store/plannerStore";
import { useIsDark } from "../hooks/useIsDark";
import type { Attraction, DayCurve } from "../types";

export function WaitTimeChart({ attraction, onClose }: { attraction: Attraction; onClose?: () => void }) {
  const { targetDate, earlyEntry, lands, placeAttraction, currentPark } = usePlanner();
  const [curve, setCurve] = useState<DayCurve | null>(null);
  const [loading, setLoading] = useState(true);
  const isDark = useIsDark();
  const color = lands?.[attraction.land]?.color || "#FBBF24";

  useEffect(() => {
    setLoading(true);
    api.dayCurve(attraction.id, targetDate, earlyEntry, currentPark).then((d) => {
      setCurve(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [attraction.id, targetDate, earlyEntry]);

  // "Best time" should ignore rope-drop low waits (open hour + the hour after)
  // and the closing-hour drop-off (waits crater because guests leave). Those windows
  // are artificially low and not actionable recommendations.
  const allHours = curve?.hours ?? [];
  const openH = allHours[0]?.hour ?? 9;
  const lastH = allHours[allHours.length - 1]?.hour ?? 21;
  const eligibleHours = allHours.filter(h => h.hour >= openH + 2 && h.hour < lastH);
  const bestCandidates = eligibleHours.length > 0 ? eligibleHours : allHours;
  const minWait = bestCandidates.length ? Math.min(...bestCandidates.map(h => h.wait_minutes)) : 0;
  const bestHour = bestCandidates.find(h => h.wait_minutes === minWait);
  const maxWait = curve ? Math.max(...curve.hours.map(h => h.wait_minutes)) : 0;
  const maxWorstCase = curve ? Math.max(...curve.hours.map(h => h.worst_case_wait ?? 0)) : 0;
  const hasWorstCase = maxWorstCase > 0;
  const hasLL = !!attraction.ll_type;
  const isLLSP = attraction.ll_type === "single";
  const bestHourLL = bestHour?.ll_return_minutes ?? null;

  const chartColors = isDark
    ? { grid: "#1F1F1F", tick: "#8C8C8C", tooltipBg: "#111111", tooltipBorder: "#212121" }
    : { grid: "#E0E0E0", tick: "#777777", tooltipBg: "#FFFFFF", tooltipBorder: "#DEDEDE" };

  return (
    <div className="panel p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div className="section-label capitalize">{attraction.kind}</div>
            {curve?.source === "actual" && (
              <span className="chip chip-ok">Actual data</span>
            )}
          </div>
          <h3 className="text-base font-medium leading-tight mt-1">{attraction.name}</h3>
          <p className="text-[11px] text-ink-secondary mt-0.5 leading-relaxed">{attraction.description}</p>
          {/* Basic info chips */}
          <div className="flex flex-wrap gap-1 mt-1.5">
            {attraction.height_inches && (
              <span className="chip bg-bg-hover text-ink-secondary text-[10px]">
                {attraction.height_inches}″ min height
              </span>
            )}
            {attraction.has_single_rider && (
              <span className="chip bg-blue-500/15 text-blue-300 text-[10px]">Single rider</span>
            )}
            {attraction.has_express && (
              <span className="chip bg-amber-500/15 text-amber-300 text-[10px]">Express pass</span>
            )}
            {attraction.capacity_per_hour && (
              <span className="chip bg-bg-hover text-ink-muted text-[10px]">
                ~{attraction.capacity_per_hour.toLocaleString()}/hr
              </span>
            )}
            {attraction.tier >= 4 && (
              <span className="chip bg-accent/15 text-accent text-[10px] font-medium">E-ticket</span>
            )}
            {isLLSP && (
              <span className="chip bg-purple-500/15 text-purple-300 text-[10px] font-medium">⚡ LLSP · Immediate entry</span>
            )}
            {attraction.ll_type === "multi" && (
              <span className="chip bg-purple-500/15 text-purple-300 text-[10px]">⚡ LLMP</span>
            )}
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-ink-secondary hover:text-ink-primary hover:bg-bg-hover transition-colors"
            title="Close panel"
            aria-label="Close panel"
          >
            <IconX size={14} stroke={1.5} />
          </button>
        )}
      </div>

      {loading && <div className="text-ink-secondary text-sm py-8 text-center">Loading wait curve…</div>}

      {curve && !loading && (
        <>
          <div className={`grid gap-2 text-center mb-3 text-[11px] ${hasLL ? "grid-cols-5" : "grid-cols-4"}`}>
            <div className="card px-2 py-1">
              <div className="text-ink-secondary text-[9px]">Best</div>
              <div className="font-medium text-status-ok">
                {bestHour && bestHour.hour}:00 · {minWait}m
              </div>
            </div>
            <div className="card px-2 py-1">
              <div className="text-ink-secondary text-[9px]">Peak</div>
              <div className="font-medium text-status-warn">{maxWait}m</div>
            </div>
            <div className="card px-2 py-1" title="Historical 90th-percentile worst case">
              <div className="text-ink-secondary text-[9px]">Worst</div>
              <div className="font-medium text-status-bad">
                {hasWorstCase ? `${maxWorstCase}m` : "—"}
              </div>
            </div>
            {hasLL && (
              <div className="card px-2 py-1" title={isLLSP ? "Lightning Lane Single Pass — purchase per-ride, enter immediately" : "Lightning Lane Multi Pass — estimated return window at best time"}>
                <div className="text-purple-400 text-[9px]">⚡ LL Return</div>
                <div className="font-medium text-purple-300">
                  {isLLSP ? "Now" : bestHourLL != null ? `~${bestHourLL}m` : "—"}
                </div>
              </div>
            )}
            <div className="card px-2 py-1">
              <div className="text-ink-secondary text-[9px]">Ride</div>
              <div className="font-medium">{attraction.duration_minutes}m</div>
            </div>
          </div>

          <div className="h-40 -mx-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={curve.hours}>
                <defs>
                  <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={color} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: chartColors.tick, fontSize: 11 }}
                  tickFormatter={(h: number) => `${((h + 11) % 12) + 1}${h >= 12 ? "p" : "a"}`}
                />
                <YAxis tick={{ fill: chartColors.tick, fontSize: 11 }} width={32} />
                <Tooltip
                  contentStyle={{
                    background: chartColors.tooltipBg,
                    border: `1px solid ${chartColors.tooltipBorder}`,
                    borderRadius: 6,
                    color: isDark ? "#F0F0F0" : "#111111",
                  }}
                  labelFormatter={(h: number) => `${((h + 11) % 12) + 1}:00 ${h >= 12 ? "PM" : "AM"}`}
                  formatter={(v: number, name: string) => {
                    if (name === "wait_minutes") return [`${v} min`, "Standby"];
                    if (name === "ll_return_minutes") return [isLLSP ? "Immediate" : `~${v} min`, "⚡ LL Return"];
                    return [`${v} min`, "Worst case (p90)"];
                  }}
                />
                <Area type="monotone" dataKey="wait_minutes" stroke={color} fill="url(#grad)" strokeWidth={2} />
                {hasWorstCase && (
                  <Line
                    type="monotone"
                    dataKey="worst_case_wait"
                    stroke="#EF4444"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                )}
                {attraction.ll_type === "multi" && (
                  <Line
                    type="monotone"
                    dataKey="ll_return_minutes"
                    stroke="#A855F7"
                    strokeWidth={1.5}
                    strokeDasharray="3 3"
                    dot={false}
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
            <button
              onClick={() => {
                if (!bestHour) return;
                const openHour = earlyEntry ? 8 : 9;
                const startMin = (bestHour.hour - openHour) * 60;
                placeAttraction(attraction, startMin);
              }}
              className="btn-primary"
            >
              Add at best time ({bestHour?.hour}:00)
            </button>
            <button
              onClick={() => {
                placeAttraction(attraction, 0);
              }}
              className="btn-ghost"
            >
              Add at rope drop
            </button>
          </div>
        </>
      )}
    </div>
  );
}
