import { useEffect, useRef, useState } from "react";

interface RideStatus {
  name: string;
  status: string;        // "OPERATING" | "DOWN" | "CLOSED" | "UNKNOWN"
  llState: string | null; // "AVAILABLE" | "TEMPORARILY_FULL" | "FINISHED" | null
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

const RIDE_KEYS = ["big thunder", "matterhorn", "indiana jones"] as const;

const RIDE_EMOJI: Record<string, string> = {
  "big thunder": "⛏️",
  "matterhorn": "🏔️",
  "indiana jones": "🪬",
};

function fmt12(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function LLBadge({ state }: { state: string | null }) {
  if (state === "AVAILABLE")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        Available
      </span>
    );
  if (state === "TEMPORARILY_FULL")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
        Sold Out
      </span>
    );
  if (state === "FINISHED")
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-zinc-700/60 text-zinc-400 border border-zinc-600/30">
        Done Today
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-zinc-700/60 text-zinc-400 border border-zinc-600/30">
      No LL
    </span>
  );
}

function RideCard({ rideKey, ride }: { rideKey: string; ride: RideStatus }) {
  const available = ride.llState === "AVAILABLE";
  return (
    <div
      className={`rounded-2xl border p-5 flex flex-col gap-3 transition-all duration-500 ${
        available
          ? "border-emerald-500/50 bg-emerald-950/30 shadow-[0_0_24px_rgba(16,185,129,0.12)]"
          : "border-zinc-700/50 bg-bg-card"
      }`}
    >
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

      <div className="grid grid-cols-2 gap-2 text-sm">
        {ride.waitMinutes != null && (
          <div className="flex flex-col">
            <span className="text-ink-muted text-xs">Standby wait</span>
            <span className="text-ink-primary font-medium">{ride.waitMinutes} min</span>
          </div>
        )}
        {available && ride.returnStart && (
          <div className="flex flex-col">
            <span className="text-ink-muted text-xs">Return window</span>
            <span className="text-emerald-400 font-medium">
              {fmt12(ride.returnStart)}
              {ride.returnEnd ? ` – ${fmt12(ride.returnEnd)}` : ""}
            </span>
          </div>
        )}
        {available && ride.price != null && (
          <div className="flex flex-col">
            <span className="text-ink-muted text-xs">Price</span>
            <span className="text-ink-primary font-medium">${ride.price}</span>
          </div>
        )}
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
  const prevStates = useRef<Record<string, string | null>>({});

  // Ask for notification permission
  async function requestNotifs() {
    const perm = await Notification.requestPermission();
    setNotifPerm(perm);
  }

  // Fire browser notification for newly available ride
  function notify(name: string, returnStart: string | null) {
    if (notifPerm !== "granted") return;
    const body = returnStart ? `Return window starts at ${fmt12(returnStart)}` : "Book now!";
    new Notification(`⚡ ${name} Lightning Lane Available!`, { body, icon: "/favicon.ico" });
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

          // Check for newly available rides
          for (const key of RIDE_KEYS) {
            const ride = data.rides[key];
            if (!ride) continue;
            const prev = prevStates.current[key];
            if (ride.llState === "AVAILABLE" && prev !== "AVAILABLE") {
              notify(ride.name, ride.returnStart);
            }
            prevStates.current[key] = ride.llState ?? null;
          }
        } catch {/* ignore parse errors */}
      };

      es.onerror = () => {
        setConnState("error");
        es.close();
        retryTimeout = setTimeout(connect, 5000);
      };
    }

    connect();
    return () => {
      es?.close();
      clearTimeout(retryTimeout);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notifPerm]);

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
          <p className="text-ink-muted text-sm mt-0.5">Disneyland · checks every 2 min</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              connState === "live" ? "bg-emerald-400 animate-pulse" :
              connState === "error" ? "bg-red-400" : "bg-amber-400 animate-pulse"
            }`}
          />
          <span className="text-xs text-ink-muted capitalize">{connState}</span>
        </div>
      </div>

      {/* Notification permission banner */}
      {notifPerm !== "granted" && (
        <button
          onClick={requestNotifs}
          className="w-full rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 text-sm px-4 py-3 text-left flex items-center justify-between hover:bg-amber-500/15 transition-colors"
        >
          <span>🔔 Enable browser notifications to get pinged when a ride opens</span>
          <span className="font-semibold shrink-0 ml-3">Allow →</span>
        </button>
      )}
      {notifPerm === "granted" && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-sm px-4 py-2 flex items-center gap-2">
          <span>✓</span> Notifications on — you'll be pinged when a lane opens
        </div>
      )}

      {/* Ride cards */}
      <div className="flex flex-col gap-3">
        {RIDE_KEYS.map((key) => (
          <RideCard key={key} rideKey={key} ride={rides[key] ?? {
            name: key.replace(/\b\w/g, (c) => c.toUpperCase()),
            status: "UNKNOWN",
            llState: null,
            returnStart: null,
            returnEnd: null,
            price: null,
            waitMinutes: null,
          }} />
        ))}
      </div>

      {/* Footer */}
      <p className="text-center text-xs text-ink-muted mt-2">
        {fetchedAt ? `Last updated ${fetchedAt}` : "Fetching data…"}
        {" · "}
        <span>Data via themeparks.wiki</span>
      </p>
    </div>
  );
}
