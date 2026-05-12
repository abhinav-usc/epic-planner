import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { usePlanner } from "../store/plannerStore";
import type { Attraction, DayCurve } from "../types";

export function WaitTimeChart({ attraction }: { attraction: Attraction }) {
  const { targetDate, earlyEntry, lands, addPlannedItem } = usePlanner();
  const [curve, setCurve] = useState<DayCurve | null>(null);
  const [loading, setLoading] = useState(true);
  const color = lands?.[attraction.land]?.color || "#FBBF24";

  useEffect(() => {
    setLoading(true);
    api.dayCurve(attraction.id, targetDate, earlyEntry).then((d) => {
      setCurve(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [attraction.id, targetDate, earlyEntry]);

  const minWait = curve ? Math.min(...curve.hours.map(h => h.wait_minutes)) : 0;
  const maxWait = curve ? Math.max(...curve.hours.map(h => h.wait_minutes)) : 0;
  const bestHour = curve?.hours.find(h => h.wait_minutes === minWait);

  return (
    <div className="panel p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-wider text-ink-muted">{attraction.kind}</div>
          <h3 className="font-display font-bold text-lg leading-tight">{attraction.name}</h3>
          <p className="text-xs text-ink-secondary mt-0.5">{attraction.description}</p>
        </div>
      </div>

      {loading && <div className="text-ink-secondary text-sm py-8 text-center">Loading wait curve…</div>}

      {curve && !loading && (
        <>
          <div className="grid grid-cols-3 gap-2 text-center mb-3 text-xs">
            <div className="card px-2 py-1.5">
              <div className="text-ink-secondary">Best</div>
              <div className="font-semibold text-green-400">
                {bestHour && bestHour.hour}:00 · {minWait}m
              </div>
            </div>
            <div className="card px-2 py-1.5">
              <div className="text-ink-secondary">Peak</div>
              <div className="font-semibold text-red-400">{maxWait}m</div>
            </div>
            <div className="card px-2 py-1.5">
              <div className="text-ink-secondary">Ride</div>
              <div className="font-semibold">{attraction.duration_minutes}m</div>
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
                <CartesianGrid strokeDasharray="3 3" stroke="#22222F" />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: "#9999AE", fontSize: 11 }}
                  tickFormatter={(h: number) => `${((h + 11) % 12) + 1}${h >= 12 ? "p" : "a"}`}
                />
                <YAxis tick={{ fill: "#9999AE", fontSize: 11 }} width={32} />
                <Tooltip
                  contentStyle={{ background: "#13131D", border: "1px solid #22222F", borderRadius: 6 }}
                  labelFormatter={(h: number) => `${((h + 11) % 12) + 1}:00 ${h >= 12 ? "PM" : "AM"}`}
                  formatter={(v: number) => [`${v} min`, "Wait"]}
                />
                <Area type="monotone" dataKey="wait_minutes" stroke={color} fill="url(#grad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <button
              onClick={() => {
                if (!bestHour) return;
                const openHour = earlyEntry ? 8 : 9;
                const startMin = (bestHour.hour - openHour) * 60;
                addPlannedItem(attraction, startMin, bestHour.wait_minutes);
              }}
              className="btn-primary"
            >
              + Add at best time ({bestHour?.hour}:00)
            </button>
            <button
              onClick={() => {
                // add at first hour
                const openHour = earlyEntry ? 8 : 9;
                const first = curve.hours[0];
                addPlannedItem(attraction, 0, first.wait_minutes);
              }}
              className="btn-ghost"
            >
              + Add at rope drop
            </button>
          </div>
        </>
      )}
    </div>
  );
}
