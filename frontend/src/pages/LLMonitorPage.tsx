import { useCallback, useEffect, useMemo, useRef, useState } from "react";

const PARKS = [
  { key: "disneyland",        name: "Disneyland",        icon: "🏯", short: "DL" },
  { key: "magic_kingdom",     name: "Magic Kingdom",     icon: "🏰", short: "MK" },
  { key: "epcot",             name: "EPCOT",             icon: "🌍", short: "EP" },
  { key: "hollywood_studios", name: "Hollywood Studios", icon: "🎬", short: "HS" },
  { key: "animal_kingdom",    name: "Animal Kingdom",    icon: "🌿", short: "AK" },
] as const;

type ParkKey = typeof PARKS[number]["key"];

interface RideStatus {
  name: string;
  status: string;
  entityType: string;
  llState: string | null;
  returnStart: string | null;
  returnEnd: string | null;
  waitMinutes: number | null;
}

interface Snapshot {
  rides: Record<string, RideStatus>;
  fetchedAt: string | null;
  error?: string;
}

// ── LocalStorage helpers ──────────────────────────────────────────────────────

function loadPinned(park: string): Set<string> {
  try {
    const raw = localStorage.getItem(`ll-pinned-${park}`);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch { return new Set(); }
}

function savePinned(park: string, pinned: Set<string>) {
  localStorage.setItem(`ll-pinned-${park}`, JSON.stringify([...pinned]));
}

function loadThresholds(park: string): Record<string, number | null> {
  try {
    const raw = localStorage.getItem(`ll-thresholds-${park}`);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveThresholds(park: string, t: Record<string, number | null>) {
  localStorage.setItem(`ll-thresholds-${park}`, JSON.stringify(t));
}

function loadReturnBefores(park: string): Record<string, string | null> {
  try {
    const raw = localStorage.getItem(`ll-return-befores-${park}`);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveReturnBefores(park: string, t: Record<string, string | null>) {
  localStorage.setItem(`ll-return-befores-${park}`, JSON.stringify(t));
}

function getDeviceId(): string {
  let id = localStorage.getItem("ll-device-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("ll-device-id", id);
  }
  return id;
}

// ── Web Push helpers ──────────────────────────────────────────────────────────

async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return null;
  try {
    return await navigator.serviceWorker.register("/sw.js");
  } catch { return null; }
}

async function subscribeToPush(reg: ServiceWorkerRegistration): Promise<PushSubscription | null> {
  try {
    const existing = await reg.pushManager.getSubscription();
    if (existing) return existing;

    const res = await fetch("/api/ll/vapid-public-key");
    if (!res.ok) return null;
    const { publicKey } = await res.json();

    return await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: publicKey,
    });
  } catch { return null; }
}

async function syncWatchConfig(
  park: string,
  pinned: Set<string>,
  thresholds: Record<string, number | null>,
  returnBefores: Record<string, string | null>,
  pushSub: PushSubscription | null,
): Promise<void> {
  if (!pushSub || pinned.size === 0) return;
  const watches = [...pinned].map((key) => ({
    key,
    threshold: thresholds[key] ?? null,
    return_before: returnBefores[key] ?? null,
  }));
  try {
    await fetch("/api/ll/push-subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        device_id: getDeviceId(),
        push_subscription: pushSub.toJSON(),
        park,
        watches,
      }),
    });
  } catch {/* best-effort */}
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt12(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch { return iso; }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function LLBadge({ state }: { state: string | null }) {
  if (state === "AVAILABLE")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shrink-0">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        LL Open
      </span>
    );
  if (state === "TEMPORARILY_FULL")
    return (
      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 shrink-0">
        LL Full
      </span>
    );
  if (state === "FINISHED")
    return (
      <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-zinc-700/60 text-zinc-400 border border-zinc-600/30 shrink-0">
        LL Done
      </span>
    );
  return null;
}

function RideRow({
  rideKey, ride, pinned, threshold, returnBefore, onPinToggle, onThresholdChange, onReturnBeforeChange,
}: {
  rideKey: string;
  ride: RideStatus;
  pinned: boolean;
  threshold: number | null;
  returnBefore: string | null;
  onPinToggle: () => void;
  onThresholdChange: (val: number | null) => void;
  onReturnBeforeChange: (val: string | null) => void;
}) {
  const llOpen = ride.llState === "AVAILABLE";
  const belowThreshold = pinned && threshold !== null && ride.waitMinutes !== null && ride.waitMinutes <= threshold;
  const isDown = ride.status === "DOWN" || ride.status === "REFURBISHMENT" || ride.status === "CLOSED";

  return (
    <div className={`rounded-2xl border overflow-hidden transition-all duration-300 ${
      pinned && llOpen
        ? "border-emerald-500/40 bg-emerald-950/20"
        : pinned && belowThreshold
        ? "border-sky-500/40 bg-sky-950/20"
        : pinned
        ? "border-amber-500/25 bg-zinc-900/80"
        : "border-zinc-800/50 bg-zinc-900/30"
    }`}>
      {/* Main row */}
      <div className="flex items-stretch">
        {/* Star button — full-height touch target */}
        <button
          onClick={onPinToggle}
          className={`w-12 flex items-center justify-center shrink-0 text-xl transition-all active:scale-90 ${
            pinned
              ? "text-amber-400 bg-amber-500/10"
              : "text-zinc-700 hover:text-zinc-400"
          }`}
          style={{ minHeight: 54 }}
          aria-label={pinned ? "Unpin ride" : "Pin to watch"}
        >
          {pinned ? "★" : "☆"}
        </button>

        {/* Name + status + return time — all left-aligned together */}
        <div className="flex-1 min-w-0 py-3 pl-0.5">
          <p className={`font-semibold text-sm leading-tight truncate pr-2 ${
            isDown ? "text-zinc-500" : "text-zinc-100"
          }`}>{ride.name}</p>
          <p className={`text-xs mt-0.5 ${
            ride.status === "OPERATING" ? "text-emerald-500" :
            ride.status === "DOWN" ? "text-red-400" :
            ride.status === "REFURBISHMENT" ? "text-amber-400" :
            "text-zinc-600"
          }`}>{ride.status.replace("_", " ")}</p>
          {llOpen && ride.returnStart && (
            <p className="text-xs text-emerald-400 font-medium mt-0.5">
              Return: {fmt12(ride.returnStart)}{ride.returnEnd ? ` – ${fmt12(ride.returnEnd)}` : ""}
            </p>
          )}
        </div>

        {/* Wait + LL badge */}
        <div className="flex flex-col items-end justify-center gap-1 pr-3 py-3 shrink-0">
          {ride.waitMinutes != null && (
            <span className={`font-bold tabular-nums ${
              belowThreshold ? "text-sky-400" :
              ride.waitMinutes >= 60 ? "text-red-400" :
              ride.waitMinutes >= 30 ? "text-amber-400" : "text-emerald-400"
            }`}>
              <span className="text-base">{ride.waitMinutes}</span>
              <span className="text-xs font-normal text-zinc-500">m{belowThreshold ? " ✓" : ""}</span>
            </span>
          )}
          <LLBadge state={ride.llState} />
        </div>
      </div>

      {/* Alerts — pinned rides only */}
      {pinned && (
        <div className="border-t border-zinc-800/50 px-4 py-3 flex flex-col gap-3">
          {/* Wait threshold slider */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-zinc-500">Notify if wait drops to</span>
              <span className={`text-xs font-semibold ${threshold !== null ? "text-sky-400" : "text-zinc-600"}`}>
                {threshold === null ? "off" : `${threshold} min`}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={0} max={120} step={5}
                value={threshold ?? 0}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  onThresholdChange(v === 0 ? null : v);
                }}
                className="flex-1 accent-sky-400 cursor-pointer"
              />
              {threshold !== null && (
                <button
                  onClick={() => onThresholdChange(null)}
                  className="w-7 h-7 flex items-center justify-center rounded-full bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-xs shrink-0"
                >✕</button>
              )}
            </div>
          </div>

          {/* LL return time picker */}
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-zinc-500 shrink-0">Notify if LL return by</span>
            <div className="flex items-center gap-2">
              <input
                type="time"
                value={returnBefore ?? ""}
                onChange={(e) => onReturnBeforeChange(e.target.value || null)}
                className="text-xs bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1 text-zinc-200 focus:outline-none focus:border-emerald-500 w-28"
              />
              {returnBefore !== null && (
                <button
                  onClick={() => onReturnBeforeChange(null)}
                  className="w-6 h-6 flex items-center justify-center rounded-full bg-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-xs shrink-0"
                >✕</button>
              )}
              {returnBefore === null && (
                <span className="text-xs text-zinc-600">off</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function LLMonitorPage() {
  const [parkKey, setParkKey] = useState<ParkKey>(() => {
    return (localStorage.getItem("ll-selected-park") as ParkKey) || "disneyland";
  });
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [connState, setConnState] = useState<"connecting" | "live" | "error">("connecting");
  const [notifPerm, setNotifPerm] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied"
  );
  const [pushSub, setPushSub] = useState<PushSubscription | null>(null);
  const [pushStatus, setPushStatus] = useState<"idle" | "subscribing" | "active" | "unsupported">("idle");
  const [pinned, setPinned] = useState<Set<string>>(() => loadPinned(parkKey));
  const [thresholds, setThresholds] = useState<Record<string, number | null>>(() => loadThresholds(parkKey));
  const [returnBefores, setReturnBefores] = useState<Record<string, string | null>>(() => loadReturnBefores(parkKey));

  const prevLL = useRef<Record<string, string | null>>({});
  const prevStatus = useRef<Record<string, string | null>>({});
  const prevWait = useRef<Record<string, number | null>>({});
  const isFirstUpdate = useRef(true);
  const pinnedRef = useRef(pinned);
  pinnedRef.current = pinned;
  const thresholdsRef = useRef(thresholds);
  thresholdsRef.current = thresholds;
  const returnBeforesRef = useRef(returnBefores);
  returnBeforesRef.current = returnBefores;
  const pushSubRef = useRef(pushSub);
  pushSubRef.current = pushSub;

  // ── Service Worker + Push subscription ──────────────────────────────────────

  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setPushStatus("unsupported");
      return;
    }
    registerServiceWorker().then((reg) => {
      if (!reg) { setPushStatus("unsupported"); return; }
      reg.pushManager.getSubscription().then((sub) => {
        if (sub) {
          setPushSub(sub);
          setPushStatus("active");
        }
      });
    });
  }, []);

  const enablePush = useCallback(async () => {
    setPushStatus("subscribing");
    const perm = await Notification.requestPermission();
    setNotifPerm(perm);
    if (perm !== "granted") { setPushStatus("idle"); return; }

    const reg = await registerServiceWorker();
    if (!reg) { setPushStatus("unsupported"); return; }

    const sub = await subscribeToPush(reg);
    if (!sub) { setPushStatus("idle"); return; }

    setPushSub(sub);
    setPushStatus("active");
  }, []);

  const syncWatches = useCallback((
    park: string, p: Set<string>, t: Record<string, number | null>,
    rb: Record<string, string | null>, sub: PushSubscription | null
  ) => {
    syncWatchConfig(park, p, t, rb, sub);
  }, []);

  useEffect(() => {
    syncWatches(parkKey, pinned, thresholds, returnBefores, pushSub);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parkKey, pinned, thresholds, returnBefores, pushSub]);

  // ── Park switching ────────────────────────────────────────────────────────────

  useEffect(() => {
    localStorage.setItem("ll-selected-park", parkKey);
    setSnapshot(null);
    setConnState("connecting");
    const p = loadPinned(parkKey);
    const t = loadThresholds(parkKey);
    const rb = loadReturnBefores(parkKey);
    setPinned(p);
    setThresholds(t);
    setReturnBefores(rb);
    prevLL.current = {};
    prevStatus.current = {};
    prevWait.current = {};
    isFirstUpdate.current = true;
  }, [parkKey]);

  // ── Pin / threshold helpers ──────────────────────────────────────────────────

  function togglePin(key: string) {
    setPinned((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      savePinned(parkKey, next);
      return next;
    });
  }

  function setThreshold(key: string, val: number | null) {
    setThresholds((prev) => {
      const next = { ...prev, [key]: val };
      saveThresholds(parkKey, next);
      return next;
    });
  }

  function setReturnBefore(key: string, val: string | null) {
    setReturnBefores((prev) => {
      const next = { ...prev, [key]: val };
      saveReturnBefores(parkKey, next);
      return next;
    });
  }

  // ── Service worker messages (auto-clear after notification fires) ─────────────

  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    const handler = (event: MessageEvent) => {
      if (event.data?.type !== "WATCH_REMOVED") return;
      const rideKey: string = event.data.rideKey;
      setThresholds((prev) => {
        if (prev[rideKey] === null || prev[rideKey] === undefined) return prev;
        const next = { ...prev, [rideKey]: null };
        saveThresholds(parkKey, next);
        return next;
      });
      setReturnBefores((prev) => {
        if (!prev[rideKey]) return prev;
        const next = { ...prev };
        delete next[rideKey];
        saveReturnBefores(parkKey, next);
        return next;
      });
    };
    navigator.serviceWorker.addEventListener("message", handler);
    return () => navigator.serviceWorker.removeEventListener("message", handler);
  }, [parkKey]);

  // Sync with server on mount so auto-cleared alerts reflect in UI even after app was closed
  useEffect(() => {
    const deviceId = getDeviceId();
    fetch(`/api/ll/watches/${deviceId}`)
      .then((r) => r.json())
      .then((data: { park: string | null; watches: Record<string, { threshold: number | null; return_before: string | null }> }) => {
        if (data.park !== parkKey) return;
        setThresholds((prev) => {
          let changed = false;
          const next = { ...prev };
          for (const [key, info] of Object.entries(data.watches)) {
            if (info.threshold === null && prev[key] != null) {
              next[key] = null;
              changed = true;
            }
          }
          if (changed) saveThresholds(parkKey, next);
          return changed ? next : prev;
        });
        setReturnBefores((prev) => {
          let changed = false;
          const next = { ...prev };
          for (const [key, info] of Object.entries(data.watches)) {
            if (info.return_before === null && prev[key]) {
              delete next[key];
              changed = true;
            }
          }
          if (changed) saveReturnBefores(parkKey, next);
          return changed ? next : prev;
        });
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parkKey]);

  // ── In-app notifications ─────────────────────────────────────────────────────

  function notifyInApp(title: string, body: string) {
    if (notifPerm !== "granted") return;
    new Notification(title, { body, icon: "/favicon.ico" });
  }

  // ── SSE connection ────────────────────────────────────────────────────────────

  useEffect(() => {
    let es: EventSource;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      setConnState("connecting");
      es = new EventSource(`/api/ll/${parkKey}/stream`);
      es.onopen = () => setConnState("live");

      es.onmessage = (e) => {
        try {
          const data: Snapshot = JSON.parse(e.data);
          setSnapshot(data);
          setConnState("live");

          if (isFirstUpdate.current) {
            isFirstUpdate.current = false;
            for (const [key, ride] of Object.entries(data.rides)) {
              prevLL.current[key] = ride.llState ?? null;
              prevStatus.current[key] = ride.status ?? null;
              prevWait.current[key] = ride.waitMinutes ?? null;
            }
            return;
          }

          const curPinned = pinnedRef.current;
          const curThresholds = thresholdsRef.current;

          for (const [key, ride] of Object.entries(data.rides)) {
            if (!curPinned.has(key)) {
              prevLL.current[key] = ride.llState ?? null;
              prevStatus.current[key] = ride.status ?? null;
              prevWait.current[key] = ride.waitMinutes ?? null;
              continue;
            }

            if (ride.llState === "AVAILABLE" && prevLL.current[key] !== "AVAILABLE") {
              const body = ride.returnStart ? `Return: ${fmt12(ride.returnStart)}` : "Book now!";
              notifyInApp(`⚡ ${ride.name} LL Open!`, body);
            }
            prevLL.current[key] = ride.llState ?? null;

            const prevSt = prevStatus.current[key];
            if (prevSt != null && prevSt !== ride.status) {
              if (ride.status === "OPERATING") notifyInApp(`✅ ${ride.name} is OPEN`, "Ride is back up!");
              else if (prevSt === "OPERATING") notifyInApp(`🚫 ${ride.name} closed`, `Status: ${ride.status}`);
            }
            prevStatus.current[key] = ride.status ?? null;

            const threshold = curThresholds[key];
            const prevW = prevWait.current[key];
            const curW = ride.waitMinutes;
            if (threshold !== null && curW !== null && prevW !== null && prevW > threshold && curW <= threshold) {
              notifyInApp(`⏱️ ${ride.name} wait is ${curW} min`, `Dropped below your ${threshold} min alert!`);
            }
            prevWait.current[key] = curW ?? null;
          }
        } catch {/* ignore parse errors */}
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
  }, [parkKey, notifPerm]);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/ll/${parkKey}/status?force=true`);
        const data: Snapshot = await res.json();
        setSnapshot(data);
      } catch {/* ignore */}
    }, 30_000);
    return () => clearInterval(interval);
  }, [parkKey]);

  const sortedRides = useMemo(() => {
    if (!snapshot) return [];
    return Object.entries(snapshot.rides).sort(([ka, a], [kb, b]) => {
      const pa = pinned.has(ka) ? 0 : 1;
      const pb = pinned.has(kb) ? 0 : 1;
      if (pa !== pb) return pa - pb;
      const sa = a.status === "OPERATING" ? 0 : 1;
      const sb = b.status === "OPERATING" ? 0 : 1;
      if (sa !== sb) return sa - sb;
      return (b.waitMinutes ?? -1) - (a.waitMinutes ?? -1);
    });
  }, [snapshot, pinned]);

  const fetchedAt = snapshot?.fetchedAt
    ? new Date(snapshot.fetchedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })
    : null;

  const selectedPark = PARKS.find((p) => p.key === parkKey)!;

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="h-full overflow-y-auto overflow-x-hidden">
      <div className="px-3 pt-3 pb-8 max-w-xl mx-auto flex flex-col gap-3">

        {/* Park tabs + live status */}
        <div className="flex items-center gap-2">
          <div
            className="flex gap-1.5 overflow-x-auto flex-1 min-w-0"
            style={{ touchAction: "pan-x", overflowY: "hidden" }}
          >
            {PARKS.map((p) => (
              <button
                key={p.key}
                onClick={() => setParkKey(p.key)}
                className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-all whitespace-nowrap active:scale-95 ${
                  parkKey === p.key
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                    : "text-zinc-500 border border-zinc-800/60 hover:text-zinc-300 hover:border-zinc-700"
                }`}
              >
                {p.icon} {p.short}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`w-2 h-2 rounded-full shrink-0 ${
              connState === "live" ? "bg-emerald-400 animate-pulse" :
              connState === "error" ? "bg-red-400" : "bg-amber-400 animate-pulse"
            }`} />
            <span className="text-[11px] text-zinc-500 capitalize">{connState}</span>
          </div>
        </div>

        {/* Push notification status */}
        {pushStatus === "active" ? (
          <div className="flex items-center gap-2.5 rounded-xl border border-emerald-500/25 bg-emerald-950/30 text-emerald-300 text-xs px-3.5 py-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <span>Background alerts on — star rides to watch them.</span>
          </div>
        ) : pushStatus === "unsupported" || typeof Notification === "undefined" ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 text-amber-300 text-xs px-3.5 py-2.5 leading-relaxed">
            <span className="font-semibold">iOS tip:</span> Share → <span className="font-semibold">"Add to Home Screen"</span> to enable push notifications.
          </div>
        ) : pushStatus === "subscribing" ? (
          <div className="flex items-center gap-2.5 rounded-xl border border-zinc-700 bg-zinc-800/60 text-zinc-400 text-xs px-3.5 py-2.5">
            <span className="w-4 h-4 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin shrink-0" />
            Enabling push notifications…
          </div>
        ) : (
          <button
            onClick={enablePush}
            className="w-full flex items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-950/20 text-amber-300 text-xs px-3.5 py-3 hover:bg-amber-950/30 transition-colors active:scale-[0.98]"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-base shrink-0">🔔</span>
              <span>Enable background push notifications</span>
            </div>
            <span className="font-bold shrink-0 text-amber-200">Allow →</span>
          </button>
        )}

        {/* Star hint */}
        {pinned.size === 0 && sortedRides.length > 0 && (
          <p className="text-center text-xs text-zinc-600 py-1">
            ☆ Tap a star to watch a ride
          </p>
        )}

        {/* Ride list */}
        <div className="flex flex-col gap-2">
          {!snapshot && (
            <div className="flex items-center justify-center py-16">
              <div className="flex flex-col items-center gap-3">
                <div className="w-6 h-6 rounded-full border-2 border-emerald-500 border-t-transparent animate-spin" />
                <p className="text-zinc-500 text-sm">Connecting to live data…</p>
              </div>
            </div>
          )}
          {snapshot?.error && (
            <p className="text-center text-red-400 text-sm py-4">Error: {snapshot.error}</p>
          )}
          {sortedRides.map(([key, ride]) => (
            <RideRow
              key={key}
              rideKey={key}
              ride={ride}
              pinned={pinned.has(key)}
              threshold={thresholds[key] ?? null}
              returnBefore={returnBefores[key] ?? null}
              onPinToggle={() => togglePin(key)}
              onThresholdChange={(v) => setThreshold(key, v)}
              onReturnBeforeChange={(v) => setReturnBefore(key, v)}
            />
          ))}
        </div>

        {fetchedAt && (
          <p className="text-center text-[11px] text-zinc-700 pt-1">
            Updated {fetchedAt} · themeparks.wiki
          </p>
        )}
      </div>
    </div>
  );
}
