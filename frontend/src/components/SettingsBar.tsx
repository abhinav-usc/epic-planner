import { useEffect, useState } from "react";
import clsx from "clsx";
import { IconBolt, IconKey, IconSun, IconMoon, IconCalendar, IconRadar2 } from "@tabler/icons-react";
import { usePlanner } from "../store/plannerStore";

function useTheme() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = (localStorage.getItem("theme") ?? "dark") as "dark" | "light";
    // Apply synchronously to avoid a flash if the inline script in index.html
    // already did this; calling classList.toggle again is idempotent.
    document.documentElement.classList.toggle("light", saved === "light");
    return saved;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggle = () => setTheme(t => t === "dark" ? "light" : "dark");
  return { theme, toggle };
}

interface Props {
  onShowHistory: () => void;
}

export function SettingsBar({ onShowHistory }: Props) {
  const {
    targetDate, earlyEntry, worstCaseMode, forecast, apiKey,
    setDate, setEarlyEntry, setWorstCaseMode, setApiKey,
    liveMode, liveData, liveLastFetchedAt, setLiveMode,
  } = usePlanner();
  const [showKey, setShowKey] = useState(false);
  const [draftKey, setDraftKey] = useState(apiKey);
  const { theme, toggle: toggleTheme } = useTheme();

  return (
    <header className="flex items-center justify-between gap-2 px-3 py-2 border-b border-bg-hover bg-bg-panel relative">
      <div className="flex items-center gap-2 shrink-0">
        <IconBolt size={16} stroke={1.5} className="text-accent" />
        <div>
          <h1 className="text-sm font-medium leading-none">
            <span className="hidden sm:inline">Orlando Trip Planner</span>
            <span className="sm:hidden">Trip Planner</span>
          </h1>
          <div className="text-[10px] text-ink-secondary mt-0.5 hidden sm:block">Plan your day. Beat the lines.</div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0 overflow-hidden">
        <label className="flex items-center gap-1 sm:gap-1.5 text-[11px] shrink-0">
          <span className="text-ink-secondary hidden sm:inline">Date</span>
          <input
            type="date"
            value={targetDate}
            min={(() => { const d = new Date(); d.setDate(d.getDate() - 14); return d.toISOString().slice(0,10); })()}
            max={(() => { const d = new Date(); d.setDate(d.getDate() + 14); return d.toISOString().slice(0,10); })()}
            onChange={(e) => setDate(e.target.value)}
            className="bg-bg-card border rounded-md px-1.5 sm:px-2 py-0.5 text-[11px] w-[120px] sm:w-auto"
            style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
          />
        </label>

        <label className="hidden sm:flex items-center gap-1.5 text-[11px]">
          <input
            type="checkbox"
            checked={earlyEntry}
            onChange={(e) => setEarlyEntry(e.target.checked)}
            className="accent-accent w-3 h-3"
          />
          <span className="text-ink-secondary">Early entry</span>
        </label>

        <label className="hidden sm:flex items-center gap-1.5 text-[11px]" title="Use 90th-percentile historical waits for timeline block heights">
          <input
            type="checkbox"
            checked={worstCaseMode}
            onChange={(e) => setWorstCaseMode(e.target.checked)}
            className="accent-red-400 w-3 h-3"
          />
          <span className="text-ink-secondary">Worst case</span>
        </label>

        {forecast && (
          <div className="chip bg-bg-card border hidden md:inline-flex" style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}>
            <span className="text-ink-secondary">Crowd</span>
            <span className="font-medium text-accent">{forecast.crowd_level}/10</span>
            {forecast.holiday_label && (
              <span className="text-ink-secondary hidden lg:inline">· {forecast.holiday_label}</span>
            )}
          </div>
        )}

        <button
          onClick={() => setLiveMode(!liveMode)}
          className={clsx(
            "flex items-center gap-1 px-1.5 sm:px-2 py-1 rounded-md text-[11px] transition-colors shrink-0",
            liveMode
              ? "bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25"
              : "bg-bg-card text-ink-secondary hover:bg-bg-hover",
          )}
          style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
          title={liveMode
            ? `Polling queue-times.com every 5 min · last update ${liveLastFetchedAt ? new Date(liveLastFetchedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "—"}`
            : "Toggle live mode: poll real wait times and calibrate predictions"
          }
        >
          <IconRadar2 size={12} stroke={1.5} className={clsx(liveMode && "animate-pulse")} />
          <span className="hidden sm:inline">
            {liveMode ? "Live" : "Go live"}
            {liveMode && liveData && liveData.calibration.minutes_of_history >= 30 && (
              <span className="ml-1 text-[10px] font-medium">
                {liveData.calibration.park_wide_factor > 1.0 ? "+" : ""}
                {Math.round((liveData.calibration.park_wide_factor - 1) * 100)}%
              </span>
            )}
          </span>
          {liveMode && liveData && liveData.calibration.minutes_of_history >= 30 && (
            <span className="sm:hidden text-[10px] font-medium">
              {liveData.calibration.park_wide_factor > 1.0 ? "+" : ""}
              {Math.round((liveData.calibration.park_wide_factor - 1) * 100)}%
            </span>
          )}
        </button>

        <button
          onClick={onShowHistory}
          className="flex items-center gap-1 px-1.5 sm:px-2 py-1 rounded-md text-[11px] bg-bg-card text-ink-secondary hover:bg-bg-hover transition-colors shrink-0"
          style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
          title="Browse historical wait times"
        >
          <IconCalendar size={12} stroke={1.5} />
          <span className="hidden sm:inline">History</span>
        </button>

        <button
          onClick={() => setShowKey((v) => !v)}
          className={clsx(
            "hidden sm:flex items-center gap-1 px-2 py-1 rounded-md text-[11px] transition-colors",
            apiKey
              ? "bg-bg-card text-ink-secondary hover:bg-bg-hover"
              : "bg-accent/15 text-accent hover:bg-accent/25",
          )}
          style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
          title="Anthropic API key for AI features"
        >
          <IconKey size={12} stroke={1.5} />
          <span>{apiKey ? "AI key set" : "Add AI key"}</span>
        </button>

        <button
          onClick={toggleTheme}
          className="w-7 h-7 rounded-md flex items-center justify-center text-ink-secondary hover:text-ink-primary hover:bg-bg-hover transition-colors shrink-0"
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark"
            ? <IconSun size={14} stroke={1.5} />
            : <IconMoon size={14} stroke={1.5} />}
        </button>

        {showKey && (
          <div className="absolute right-4 top-12 z-30 panel p-3 w-80 sm:w-96 shadow-xl">
            <div className="text-[11px] font-medium mb-1">Anthropic API key</div>
            <div className="text-[10px] text-ink-secondary mb-2">
              Stored only in your browser. Sent per-request as a header to your local backend.
            </div>
            <input
              type="password"
              value={draftKey}
              onChange={(e) => setDraftKey(e.target.value)}
              placeholder="sk-ant-..."
              className="w-full bg-bg-card rounded-md px-2 py-1 text-[11px] font-mono"
              style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
            />
            <div className="flex justify-end gap-2 mt-2">
              <button onClick={() => setShowKey(false)} className="btn-ghost">Cancel</button>
              <button
                onClick={() => { setApiKey(draftKey); setShowKey(false); }}
                className="btn-primary"
              >
                Save
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
