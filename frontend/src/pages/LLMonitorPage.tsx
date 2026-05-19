import { useEffect, useRef, useState } from "react";

interface RideStatus {
  name: string;
  status: string;
  llState: string | null;
  returnStart: string | null;
  returnEnd: string | null;
  price: number | null;
  waitMinutes: number | null;
}

interface Snapshot {
  rides: Record<string, RideStatus>;
  fetchedAt: string | null;
  error?: string;
}

const RIDE_KEYS = ["big thunder", "matterhorn", "indiana jones", "star tours", "jungle cruise"] as const;
type RideKey = typeof RIDE_KEYS[number];

const RIDE_EMOJI: Record<RideKey, string> = {
  "big thunder": "⛏️",
  "matterhorn": "🏔️",
  "indiana jones": "🪬",
  "star tours": "🚀",
  "jungle cruise": "🛶",
};

const STORAGE_KEY = "ll-wait-thresholds";

function loadThresholds(): Record<string, number | null> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveThresholds(t: Record<string, number | null>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
}

function fmt12(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch { return iso; }
}

function LLBadge({ state }: { state: string | null }) {
  if (state === "AVAILABLE")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        LL Available
      </span>
    );
  if (state === "TEMPORARILY_FULL")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
        LL Sold Out
      </span>
    );
  if (state === "FINISHED")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-zinc-700/60 text-zinc-400 border border-zinc-600/30">
        LL Done
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-zinc-700/60 text-zinc-400 border border-zinc-600/30">
      No LL
    </span>
  );
}

function RideCard({
  rideKey, ride, threshold, onThresholdChange,
}: {
  rideKey: RideKey;
  ride: RideStatus;
  threshold: number | null;
  onThresholdChange: (val: number | null) => void;
}) {
  const available = ride.llState === "AVAILABLE";
  const belowThreshold = threshold !== null && ride.waitMinutes !== null && ride.waitMinutes <= threshold;

  return (
    <div className={`rounded-2xl border p-5 flex flex-col gap-3 transition-all duration-500 ${
      available
        ? "border-emerald-500/50 bg-emerald-950/30 shadow-[0_0_24px_rgba(16,185,129,0.12)]"
        : belowThreshold
        ? "border-sky-500/50 bg-sky-950/20 shadow-[0_0_20px_rgba(14,165,233,0.1)]"
        : "border-zinc-700/50 bg-bg-card"
    }`}>
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{RIDE_EMOJI[rideKey]}</span>
          <div>
            <p className="font-semibold text-ink-primary leading-tight">{ride.name}</p>
            <p className={`text-xs mt-0.5 ${ride.status === "OPERATING" ? "text-emerald-400" : "text-ink-muted"}`}>
              {ride.status}
            </p>
          </div>
        </div>
        <LLBadge state={ride.llState} />
      </div>

      {/* Wait + return time */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        {ride.waitMinutes != null && (
          <div className="flex flex-col">
            <span className="text-ink-muted text-xs">Standby wait</span>
            <span className={`font-medium ${belowThreshold ? "text-sky-400" : "text-ink-primary"}`}>
              {ride.waitMinutes} min {belowThreshold && "✓"}
            </span>
          </div>
        )}
        {available && ride.returnStart && (
          <div className="flex flex-col">
            <span className="text-ink-muted text-xs">Return window</span>
            <span className="text-emerald-400 font-medium">
              {fmt12(ride.returnStart)}{ride.returnEnd ? ` – ${fmt12(ride.returnEnd)}` : ""}
            </span>
          </div>
        )}
      </div>

      {/* Wait threshold slider */}
      <div className="pt-1 border-t border-zinc-700/40">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-ink-muted">Notify if wait ≤</span>
          <span className="text-xs font-medium text-ink-secondary">
            {threshold === null ? "off" : `${threshold} min`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="range"
            min={5} max={120} step={5}
            value={threshold ?? 0}
            onChange={(e) => {
              const v = Number(e.target.value);
              onThresholdChange(v === 0 ? null : v);
            }}
            className="flex-1 h-1.5 accent-sky-400 cursor-pointer"
          />
          {threshold !== null && (
            <button
              onClick={() => onThresholdChange(null)}
              className="text-xs text-ink-muted hover:text-ink-primary px-1"
            >
              ✕
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function LLMonitorPage() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connState, setConnState] = useState<"connecting" | "live" | "error">("connecting");
  const [notifPerm, setNotifPerm] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied"
  );
  const [thresholds, setThresholds] = useState<Record<string, number | null>>(loadThresholds());

  const prevLL = useRef<Record<string, string | null>>({});
  const prevStatus = useRef<Record<string, string | null>>({});
  const prevWait = useRef<Record<string, number | null>>({});
  const isFirstUpdate = useRef(true);
  const thresholdsRef = useRef(thresholds);
  thresholdsRef.current = thresholds;

  function setThreshold(key: string, val: number | null) {
    setThresholds((prev) => {
      const next = { ...prev, [key]: val };
      saveThresholds(next);
      return next;
    });
  }

  async function requestNotifs() {
    const perm = await Notification.requestPermission();
    setNotifPerm(perm);
  }

  function notify(title: string, body: string) {
    if (notifPerm !== "granted") return;
    new Notification(title, { body, icon: "/favicon.ico" });
  }

  useEffect(() => {
    let es: EventSource;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      setConnState("connecting");
      es = new EventSource("/api/ll/stream");
      es.onopen = () => setConnState("live");

      es.onmessage = (e) => {
        try {
          const data: Snapshot = JSON.parse(e.data);
          setSnapshot(data);
          setConnState("live");

          if (isFirstUpdate.current) {
            isFirstUpdate.current = false;
            for (const key of RIDE_KEYS) {
              const ride = data.rides[key];
              if (!ride) continue;
              prevLL.current[key] = ride.llState ?? null;
              prevStatus.current[key] = ride.status ?? null;
              prevWait.current[key] = ride.waitMinutes ?? null;
            }
            return;
          }

          for (const key of RIDE_KEYS) {
            const ride = data.rides[key];
            if (!ride) continue;

            // LL change
            if (ride.llState === "AVAILABLE" && prevLL.current[key] !== "AVAILABLE") {
              const body = ride.returnStart ? `Return: ${fmt12(ride.returnStart)}` : "Book now!";
              notify(`⚡ ${ride.name} LL Available!`, body);
            }
            prevLL.current[key] = ride.llState ?? null;

            // Ride open/close
            const prevSt = prevStatus.current[key];
            if (prevSt !== null && prevSt !== ride.status) {
              if (ride.status === "OPERATING") notify(`✅ ${ride.name} is OPEN`, "Ride is back up!");
              else if (prevSt === "OPERATING") notify(`🚫 ${ride.name} closed`, `Now: ${ride.status}`);
            }
            prevStatus.current[key] = ride.status ?? null;

            // Wait threshold crossed (above → below)
            const threshold = thresholdsRef.current[key];
            const prevW = prevWait.current[key];
            const curW = ride.waitMinutes;
            if (
              threshold !== null &&
              curW !== null && prevW !== null &&
              prevW > threshold && curW <= threshold
            ) {
              notify(`⏱️ ${ride.name} wait is ${curW} min`, `Dropped below your ${threshold} min alert!`);
            }
            prevWait.current[key] = curW ?? null;
          }
        } catch {/* ignore */}
      };

      es.onerror = () => {
        setConnState("error");
        es.close();
        retryTimeout = setTimeout(connect, 3000);
      };
    }

    connect();
    return () => { es?.close(); clearTimeout(retryTimeout); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notifPerm]);

  // Force-refresh every 30s regardless of SSE cache
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/api/ll/status?force=true");
        const data: Snapshot = await res.json();
        setSnapshot(data);
      } catch {/* ignore */}
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  const rides = snapshot?.rides ?? {};
  const fetchedAt = snapshot?.fetchedAt
    ? new Date(snapshot.fetchedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })
    : null;

  return (
    <div className="min-h-screen bg-bg-base px-4 py-8 max-w-xl mx-auto flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink-primary">⚡ LL Monitor</h1>
          <p className="text-ink-muted text-sm mt-0.5">Disneyland · checks every 30s</p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${
            connState === "live" ? "bg-emerald-400 animate-pulse" :
            connState === "error" ? "bg-red-400" : "bg-amber-400 animate-pulse"
          }`} />
          <span className="text-xs text-ink-muted capitalize">{connState}</span>
        </div>
      </div>

      {/* Notification banner */}
      {notifPerm === "granted" ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-sm px-4 py-2 flex items-center gap-2">
          <span>✓</span> Notifications on
        </div>
      ) : typeof Notification === "undefined" ? (
        <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 text-sm px-4 py-3">
          📱 <strong>iOS:</strong> Tap Share → <strong>"Add to Home Screen"</strong> → open from there to enable notifications
        </div>
      ) : (
        <button
          onClick={requestNotifs}
          className="w-full rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 text-sm px-4 py-3 text-left flex items-center justify-between hover:bg-amber-500/15 transition-colors"
        >
          <span>🔔 Enable notifications to get pinged when a ride opens</span>
          <span className="font-semibold shrink-0 ml-3">Allow →</span>
        </button>
      )}

      {/* Ride cards */}
      <div className="flex flex-col gap-3">
        {RIDE_KEYS.map((key) => (
          <RideCard
            key={key}
            rideKey={key}
            ride={rides[key] ?? {
              name: key.replace(/\b\w/g, (c) => c.toUpperCase()),
              status: "UNKNOWN",
              llState: null,
              returnStart: null,
              returnEnd: null,
              price: null,
              waitMinutes: null,
            }}
            threshold={thresholds[key] ?? null}
            onThresholdChange={(v) => setThreshold(key, v)}
          />
        ))}
      </div>

      <p className="text-center text-xs text-ink-muted mt-2">
        {fetchedAt ? `Last updated ${fetchedAt}` : "Fetching data…"} · Data via themeparks.wiki
      </p>
    </div>
  );
}
