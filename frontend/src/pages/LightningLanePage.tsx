import { useEffect, useRef, useState } from "react";
import {
  IconArrowLeft,
  IconBell,
  IconBellOff,
  IconClock,
  IconRefresh,
  IconTicket,
  IconAlertTriangle,
} from "@tabler/icons-react";
import clsx from "clsx";

interface AttractionStatus {
  name: string;
  status: string;
  standby_wait: number | null;
  ll_state: string | null;
  ll_return_start: string | null;
  ll_return_end: string | null;
  ll_type: string | null;
}

interface LLPayload {
  attractions: Record<string, AttractionStatus>;
  updated_at: string | null;
}

const ATTRACTION_ORDER = [
  "Indiana Jones Adventure",
  "Big Thunder Mountain Railroad",
  "Matterhorn Bobsleds",
];

const ATTRACTION_EMOJI: Record<string, string> = {
  "Indiana Jones Adventure": "🏺",
  "Big Thunder Mountain Railroad": "🚂",
  "Matterhorn Bobsleds": "⛰️",
};

function llLabel(state: string | null): string {
  if (!state) return "No LL";
  if (state === "AVAILABLE") return "Available";
  if (state === "TEMP_FULL") return "Temp. Full";
  if (state === "FINISHED") return "Sold Out";
  if (state === "CLOSED") return "Closed";
  return state;
}

function statusLabel(status: string): string {
  if (status === "OPERATING") return "Operating";
  if (status === "DOWN") return "Down";
  if (status === "CLOSED") return "Closed";
  if (status === "REFURBISHMENT") return "Refurb";
  return status;
}

function formatTime(raw: string | null): string | null {
  if (!raw) return null;
  // raw is "HH:MM:SS" or "HH:MM"
  const parts = raw.split(":");
  if (parts.length < 2) return raw;
  const h = parseInt(parts[0], 10);
  const m = parts[1];
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${m} ${ampm}`;
}

function useNotifications() {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "denied"
  );

  async function request() {
    if (typeof Notification === "undefined") return;
    const result = await Notification.requestPermission();
    setPermission(result);
  }

  function notify(title: string, body: string) {
    if (permission !== "granted") return;
    new Notification(title, { body, icon: "/favicon.ico", tag: title });
  }

  return { permission, request, notify };
}

interface Props {
  onBack: () => void;
}

export function LightningLanePage({ onBack }: Props) {
  const [payload, setPayload] = useState<LLPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const [nextRefreshSecs, setNextRefreshSecs] = useState(120);
  const prevStates = useRef<Record<string, string | null>>({});
  const { permission, request, notify } = useNotifications();

  // SSE connection
  useEffect(() => {
    let es: EventSource;
    let countdownInterval: ReturnType<typeof setInterval>;

    function connect() {
      es = new EventSource("/api/lightning-lanes/stream");

      es.onopen = () => setConnected(true);

      es.onmessage = (e) => {
        try {
          const data: LLPayload = JSON.parse(e.data);
          setPayload(data);
          setNextRefreshSecs(120);

          // Detect newly available attractions
          for (const [name, info] of Object.entries(data.attractions)) {
            const prev = prevStates.current[name];
            if (prev !== undefined && prev !== "AVAILABLE" && info.ll_state === "AVAILABLE") {
              notify("⚡ Lightning Lane Open!", `${name} is now available — book now!`);
            }
            prevStates.current[name] = info.ll_state;
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        setConnected(false);
        // EventSource auto-reconnects after a delay
      };
    }

    connect();

    // Countdown timer ticks every second
    countdownInterval = setInterval(() => {
      setNextRefreshSecs((s) => (s > 0 ? s - 1 : 120));
    }, 1000);

    return () => {
      es?.close();
      clearInterval(countdownInterval);
    };
  }, []);

  const hasAvailable = payload
    ? Object.values(payload.attractions).some((a) => a.ll_state === "AVAILABLE")
    : false;

  return (
    <div className="flex flex-col h-full bg-bg-base">
      {/* Header */}
      <header className="flex items-center justify-between gap-3 px-4 py-2 border-b border-bg-hover bg-bg-panel shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-ink-secondary hover:text-ink-primary text-[11px] transition-colors"
          >
            <IconArrowLeft size={14} stroke={1.5} />
            Back
          </button>
          <div className="w-px h-4 bg-bg-hover" />
          <div className="flex items-center gap-2">
            <IconTicket size={16} stroke={1.5} className="text-accent" />
            <div>
              <h1 className="text-sm font-medium leading-none">Lightning Lane Monitor</h1>
              <div className="text-[10px] text-ink-secondary mt-0.5">Disneyland Park · checks every 2 min</div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Connection indicator */}
          <div className="flex items-center gap-1.5 text-[11px]">
            <div
              className={clsx(
                "w-1.5 h-1.5 rounded-full",
                connected ? "bg-green-400 animate-pulse" : "bg-ink-muted"
              )}
            />
            <span className="text-ink-secondary">{connected ? "Live" : "Connecting…"}</span>
          </div>

          {/* Next refresh countdown */}
          <div className="flex items-center gap-1 text-[11px] text-ink-muted">
            <IconRefresh size={11} stroke={1.5} />
            <span>{nextRefreshSecs}s</span>
          </div>

          {/* Notification toggle */}
          <button
            onClick={request}
            className={clsx(
              "flex items-center gap-1 px-2 py-1 rounded-md text-[11px] transition-colors",
              permission === "granted"
                ? "bg-bg-card text-ink-secondary hover:bg-bg-hover"
                : "bg-accent/15 text-accent hover:bg-accent/25"
            )}
            style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.06)" }}
            title={
              permission === "granted"
                ? "Browser notifications enabled"
                : permission === "denied"
                ? "Notifications blocked — enable in browser settings"
                : "Enable browser notifications"
            }
            disabled={permission === "denied"}
          >
            {permission === "granted" ? (
              <IconBell size={12} stroke={1.5} />
            ) : (
              <IconBellOff size={12} stroke={1.5} />
            )}
            <span>
              {permission === "granted"
                ? "Notifs on"
                : permission === "denied"
                ? "Blocked"
                : "Enable notifs"}
            </span>
          </button>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 overflow-auto p-6">
        {/* Available banner */}
        {hasAvailable && (
          <div className="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm font-medium">
            <IconTicket size={16} stroke={1.5} />
            Lightning Lane is available — tap the Disney app now!
          </div>
        )}

        {/* Last updated */}
        {payload?.updated_at && (
          <div className="mb-4 flex items-center gap-1.5 text-[11px] text-ink-muted">
            <IconClock size={11} stroke={1.5} />
            Last updated: {new Date(payload.updated_at).toLocaleTimeString()}
          </div>
        )}

        {/* Notification permission nudge */}
        {permission === "default" && (
          <div className="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-lg bg-accent/10 border border-accent/20 text-[12px] text-ink-secondary">
            <IconBell size={14} stroke={1.5} className="text-accent shrink-0" />
            <span>
              Enable browser notifications to get pinged when a Lightning Lane opens — even if you
              switch tabs.
            </span>
            <button onClick={request} className="btn-primary ml-auto shrink-0 text-[11px]">
              Enable
            </button>
          </div>
        )}

        {/* Attraction cards */}
        {!payload ? (
          <div className="flex flex-col items-center justify-center py-24 text-ink-muted text-sm gap-2">
            <IconRefresh size={20} stroke={1.5} className="animate-spin" />
            Fetching live data…
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-4xl mx-auto">
            {ATTRACTION_ORDER.map((name) => {
              const info = payload.attractions[name];
              if (!info) return null;
              return (
                <AttractionCard key={name} displayName={name} info={info} />
              );
            })}
          </div>
        )}

        {/* Footer note */}
        <p className="mt-8 text-center text-[10px] text-ink-muted max-w-md mx-auto">
          Data from ThemeParks.wiki · Availability can change in seconds — always verify in the
          Disney app before heading to the ride.
        </p>
      </div>
    </div>
  );
}

function AttractionCard({
  displayName,
  info,
}: {
  displayName: string;
  info: AttractionStatus;
}) {
  const isAvailable = info.ll_state === "AVAILABLE";
  const isTempFull = info.ll_state === "TEMP_FULL";
  const isFinished = info.ll_state === "FINISHED";
  const isClosed = info.status === "CLOSED" || info.status === "DOWN" || info.status === "REFURBISHMENT";

  const returnRange =
    info.ll_return_start && info.ll_return_end
      ? `${formatTime(info.ll_return_start)} – ${formatTime(info.ll_return_end)}`
      : info.ll_return_start
      ? `from ${formatTime(info.ll_return_start)}`
      : null;

  return (
    <div
      className={clsx(
        "panel p-4 flex flex-col gap-3 transition-all duration-500",
        isAvailable && "ring-1 ring-green-500/40 shadow-[0_0_24px_rgba(34,197,94,0.12)]"
      )}
    >
      {/* Name row */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-base">{ATTRACTION_EMOJI[displayName] ?? "🎢"}</div>
          <div className="text-[13px] font-medium leading-tight mt-1">{displayName}</div>
        </div>

        {/* Ride status chip */}
        <div
          className={clsx(
            "chip shrink-0 mt-0.5",
            isClosed
              ? "bg-ink-muted/10 text-ink-muted"
              : info.status === "ERROR"
              ? "bg-red-500/10 text-red-400"
              : "bg-green-500/10 text-green-400"
          )}
        >
          {info.status === "ERROR" && <IconAlertTriangle size={10} />}
          {statusLabel(info.status)}
        </div>
      </div>

      {/* Standby wait */}
      <div className="flex items-center gap-2">
        <div className="section-label">STANDBY</div>
        <div className="ml-auto text-[13px] font-medium">
          {info.standby_wait != null ? (
            <span className="text-ink-primary">{info.standby_wait} min</span>
          ) : (
            <span className="text-ink-muted">—</span>
          )}
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-bg-hover" />

      {/* Lightning Lane state */}
      <div>
        <div className="section-label mb-1.5">LIGHTNING LANE</div>
        <div className="flex items-center justify-between gap-2">
          <div
            className={clsx(
              "text-sm font-semibold",
              isAvailable
                ? "text-green-400"
                : isTempFull
                ? "text-amber-400"
                : isFinished
                ? "text-red-400"
                : "text-ink-muted"
            )}
          >
            {llLabel(info.ll_state)}
          </div>
          {info.ll_type && (
            <div className="chip bg-bg-card text-ink-muted">{info.ll_type}</div>
          )}
        </div>

        {/* Return window */}
        {returnRange && (
          <div className="mt-1 flex items-center gap-1 text-[11px] text-ink-secondary">
            <IconClock size={11} stroke={1.5} />
            {returnRange}
          </div>
        )}
      </div>

      {/* Available CTA */}
      {isAvailable && (
        <div className="mt-1 px-3 py-2 rounded-md bg-green-500/10 border border-green-500/25 text-[11px] text-green-400 font-medium text-center animate-pulse">
          Book in the Disney app now!
        </div>
      )}
    </div>
  );
}
