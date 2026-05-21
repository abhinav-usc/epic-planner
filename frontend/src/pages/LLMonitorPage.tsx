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
      applicationServerKey: publicKey, // base64url string — browsers accept this directly
    });
  } catch { return null; }
}

async function syncWatchConfig(
  park: string,
  pinned: Set<string>,
  thresholds: Record<string, number | null>,
  pushSub: PushSubscription | null,
): Promise<void> {
  if (!pushSub || pinned.size === 0) return;
  const watches = [...pinned].map((key) => ({
    key,
    threshold: thresholds[key] ?? null,
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
      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shrink-0">
        <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
        LL Open
      </span>
    );
  if (state === "TEMPORARILY_FULL")
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 shrink-0">
        LL Full
      </span>
    );
  if (state === "FINISHED")
    return (
      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-zinc-700/60 text-zinc-400 border border-zinc-600/30 shrink-0">
        LL Done
      </span>
    );
  return null;
}

function RideRow({
  rideKey, ride, pinned, threshold, onPinToggle, onThresholdChange,
}: {
  rideKey: string;
  ride: RideStatus;
  pinned: boolean;
  threshold: number | null;
  onPinToggle: () => void;
  onThresholdChange: (val: number | null) => void;
}) {
  const llOpen = ride.llState === "AVAILABLE";
  const belowThreshold = pinned && threshold !== null && ride.waitMinutes !== null && ride.waitMinutes <= threshold;

  return (
    <div className={`rounded-lg border px-2.5 py-2 flex flex-col gap-1.5 transition-all duration-500 ${
      pinned && llOpen
        ? "border-emerald-500/50 bg-emerald-950/30"
        : pinned && belowThreshold
        ? "border-sky-500/50 bg-sky-950/20"
        : pinned
        ? "border-amber-500/30 bg-zinc-900/70"
        : "border-zinc-800/60 bg-zinc-900/20"
    }`}>
      {/* Top row */}
      <div className="flex items-center gap-2">
        <button
          onClick={onPinToggle}
          className={`shrink-0 text-base leading-none transition-colors ${
            pinned ? "text-amber-400" : "text-zinc-700 hover:text-zinc-400"
          }`}
          title={pinned ? "Unpin" : "Pin to watch"}
        >
          {pinned ? "★" : "☆"}
        </button>

        <div className="flex-1 min-w-0">
          <p className={`font-medium text-[13px] leading-tight truncate ${
            ride.status !== "OPERATING" && ride.status !== "UNKNOWN" ? "text-zinc-500" : "text-ink-primary"
          }`}>{ride.name}</p>
          <p className={`text-[10px] ${
            ride.status === "OPERATING" ? "text-emerald-400" :
            ride.status === "DOWN" ? "text-red-400" :
            ride.status === "REFURBISHMENT" ? "text-amber-400" :
            "text-zinc-600"
          }`}>{ride.status}</p>
        </div>

        {ride.waitMinutes != null && (
          <span className={`shrink-0 font-semibold text-[13px] tabular-nums ${
            belowThreshold ? "text-sky-400" :
            ride.waitMinutes >= 60 ? "text-red-400" :
            ride.waitMinutes >= 30 ? "text-amber-400" : "text-emerald-400"
          }`}>
            {ride.waitMinutes}m{belowThreshold ? " ✓" : ""}
          </span>
        )}

        <LLBadge state={ride.llState} />
      </div>

      {llOpen && ride.returnStart && (
        <p className="text-[10px] text-emerald-400 -mt-0.5">
          Return: {fmt12(ride.returnStart)}{ride.returnEnd ? ` – ${fmt12(ride.returnEnd)}` : ""}
        </p>
      )}

      {/* Threshold slider — pinned rides only */}
      {pinned && (
        <div className="border-t border-zinc-800/60 pt-1.5">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-zinc-600">Notify if wait ≤</span>
            <span className="text-[10px] font-medium text-ink-secondary">
              {threshold === null ? "off" : `${threshold} min`}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="range"
              min={0} max={120} step={5}
              value={threshold ?? 0}
              onChange={(e) => {
                const v = Number(e.target.value);
                onThresholdChange(v === 0 ? null : v);
              }}
              className="flex-1 h-1 accent-sky-400 cursor-pointer"
            />
            {threshold !== null && (
              <button
                onClick={() => onThresholdChange(null)}
                className="text-[10px] text-zinc-600 hover:text-zinc-300 px-1"
              >✕</button>
            )}
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

  // Refs for notification logic inside SSE handler (avoid stale closures)
  const prevLL = useRef<Record<string, string | null>>({});
  const prevStatus = useRef<Record<string, string | null>>({});
  const prevWait = useRef<Record<string, number | null>>({});
  const isFirstUpdate = useRef(true);
  const pinnedRef = useRef(pinned);
  pinnedRef.current = pinned;
  const thresholdsRef = useRef(thresholds);
  thresholdsRef.current = thresholds;
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

  // Sync watch config to backend whenever pinned/thresholds/park/pushSub changes
  const syncWatches = useCallback((
    park: string, p: Set<string>, t: Record<string, number | null>, sub: PushSubscription | null
  ) => {
    syncWatchConfig(park, p, t, sub);
  }, []);

  useEffect(() => {
    syncWatches(parkKey, pinned, thresholds, pushSub);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parkKey, pinned, thresholds, pushSub]);

  // ── Park switching ────────────────────────────────────────────────────────────

  useEffect(() => {
    localStorage.setItem("ll-selected-park", parkKey);
    setSnapshot(null);
    setConnState("connecting");
    const p = loadPinned(parkKey);
    const t = loadThresholds(parkKey);
    setPinned(p);
    setThresholds(t);
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

  // ── In-app notifications (when PWA is in foreground) ────────────────────────

  function notifyInApp(title: string, body: string) {
    if (notifPerm !== "granted" || pushStatus === "active") return; // backend handles it when push active
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

          // In-app notifications for pinned rides (backend handles push when app is closed)
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

  // Force-refresh every 30s regardless of SSE cache
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

  // Sort: pinned first → OPERATING before others → wait time desc
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

  const selectedPark = PARKS.find((p) => p.key === parkKey)!;
  const fetchedAt = snapshot?.fetchedAt
    ? new Date(snapshot.fetchedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })
    : null;

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="h-full overflow-y-auto overflow-x-hidden">
      <div className="px-3 pt-3 pb-6 max-w-xl mx-auto flex flex-col gap-2.5">

        {/* Header — compact, just park + status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Park selector inline pills */}
            <div
              className="flex gap-1 overflow-x-auto"
              style={{ touchAction: "pan-x", overflowY: "hidden" }}
            >
              {PARKS.map((p) => (
                <button
                  key={p.key}
                  onClick={() => setParkKey(p.key)}
                  className={`shrink-0 px-2 py-0.5 rounded text-[11px] font-medium transition-colors whitespace-nowrap ${
                    parkKey === p.key
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                      : "text-zinc-500 border border-transparent hover:text-zinc-300"
                  }`}
                >
                  {p.icon} {p.short}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1.5 shrink-0 ml-2">
            <span className={`w-1.5 h-1.5 rounded-full ${
              connState === "live" ? "bg-emerald-400 animate-pulse" :
              connState === "error" ? "bg-red-400" : "bg-amber-400 animate-pulse"
            }`} />
            <span className="text-[10px] text-ink-muted capitalize">{connState}</span>
          </div>
        </div>

        {/* Push notification banner */}
        {pushStatus === "active" ? (
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-[11px] px-3 py-1.5 flex items-center gap-1.5">
            <span>✓</span>
            <span>Background push on — star rides to get notified.</span>
          </div>
        ) : pushStatus === "unsupported" || typeof Notification === "undefined" ? (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 text-amber-300 text-[11px] px-3 py-1.5">
            📱 <strong>iOS:</strong> Share → <strong>"Add to Home Screen"</strong> to enable push
          </div>
        ) : pushStatus === "subscribing" ? (
          <div className="rounded-lg border border-zinc-700 bg-zinc-800/60 text-zinc-400 text-[11px] px-3 py-1.5 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full border-2 border-zinc-400 border-t-transparent animate-spin" />
            Enabling push…
          </div>
        ) : (
          <button
            onClick={enablePush}
            className="w-full rounded-lg border border-amber-500/40 bg-amber-500/10 text-amber-300 text-[11px] px-3 py-1.5 text-left flex items-center justify-between hover:bg-amber-500/15 transition-colors"
          >
            <span>🔔 Enable background push notifications</span>
            <span className="font-semibold shrink-0 ml-2">Allow →</span>
          </button>
        )}

        {/* Hint when nothing pinned */}
        {pinned.size === 0 && sortedRides.length > 0 && (
          <p className="text-center text-[11px] text-zinc-600">
            ☆ Star a ride to get push notifications
          </p>
        )}

        {/* Ride list */}
        <div className="flex flex-col gap-1.5">
          {!snapshot && (
            <p className="text-center text-zinc-500 text-sm py-8">Connecting to live data…</p>
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
              onPinToggle={() => togglePin(key)}
              onThresholdChange={(v) => setThreshold(key, v)}
            />
          ))}
        </div>

        <p className="text-center text-[10px] text-zinc-700">
          {fetchedAt ? `Updated ${fetchedAt}` : "Fetching…"} · themeparks.wiki
        </p>
      </div>
    </div>
  );
}
