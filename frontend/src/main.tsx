import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import clsx from "clsx";
import { IconBolt, IconRadar2, IconSun, IconMoon, IconKey } from "@tabler/icons-react";
import { PlannerPage } from "./pages/PlannerPage";
import { LLMonitorPage } from "./pages/LLMonitorPage";
import { usePlanner } from "./store/plannerStore";
import "./index.css";

type Tab = "planner" | "ll-monitor";

function useTheme() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const saved = (localStorage.getItem("theme") ?? "dark") as "dark" | "light";
    document.documentElement.classList.toggle("light", saved === "light");
    return saved;
  });

  React.useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    localStorage.setItem("theme", theme);
  }, [theme]);

  return { theme, toggle: () => setTheme(t => t === "dark" ? "light" : "dark") };
}

function AppHeader({ tab, onTabChange }: { tab: Tab; onTabChange: (t: Tab) => void }) {
  const {
    targetDate, earlyEntry, worstCaseMode, forecast, apiKey,
    liveMode, liveData, liveLastFetchedAt, setLiveMode,
    setDate, setEarlyEntry, setWorstCaseMode, setApiKey,
  } = usePlanner();
  const { theme, toggle: toggleTheme } = useTheme();
  const [showKey, setShowKey] = useState(false);
  const [draftKey, setDraftKey] = useState(apiKey);

  const isPlanner = tab === "planner";

  return (
    <header className="shrink-0 bg-bg-panel border-b border-bg-hover z-50 relative">
      <div className="flex items-center gap-1.5 px-3 py-2">
        {/* App name — desktop only */}
        <div className="hidden sm:flex items-center gap-1.5 shrink-0 mr-2">
          <IconBolt size={14} stroke={1.5} className="text-accent" />
          <span className="text-[13px] font-semibold tracking-tight">Orlando Trip Planner</span>
        </div>

        {/* Tab buttons */}
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={() => onTabChange("planner")}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              isPlanner
                ? "bg-accent/20 text-accent"
                : "text-ink-muted hover:text-ink-secondary",
            )}
          >
            Pre-Plan
          </button>
          <button
            onClick={() => onTabChange("ll-monitor")}
            className={clsx(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
              !isPlanner
                ? "bg-emerald-500/20 text-emerald-400"
                : "text-ink-muted hover:text-ink-secondary",
            )}
          >
            ⚡ Live
          </button>
        </div>

        {/* Planner-specific controls — shown on planner tab */}
        {isPlanner && (
          <div className="flex items-center gap-1.5 min-w-0 overflow-hidden ml-1">
            <input
              type="date"
              value={targetDate}
              min={(() => { const d = new Date(); d.setDate(d.getDate() - 14); return d.toISOString().slice(0,10); })()}
              max={(() => { const d = new Date(); d.setDate(d.getDate() + 14); return d.toISOString().slice(0,10); })()}
              onChange={(e) => setDate(e.target.value)}
              className="bg-bg-card border rounded-md px-1.5 py-0.5 text-[11px] w-[110px] sm:w-auto shrink-0"
              style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
            />

            <label className="hidden sm:flex items-center gap-1 text-[11px] shrink-0 cursor-pointer">
              <input type="checkbox" checked={earlyEntry} onChange={(e) => setEarlyEntry(e.target.checked)} className="accent-accent w-3 h-3" />
              <span className="text-ink-secondary">Early</span>
            </label>

            <label className="hidden sm:flex items-center gap-1 text-[11px] shrink-0 cursor-pointer">
              <input type="checkbox" checked={worstCaseMode} onChange={(e) => setWorstCaseMode(e.target.checked)} className="accent-red-400 w-3 h-3" />
              <span className="text-ink-secondary">Worst case</span>
            </label>

            {forecast && (
              <div
                className="hidden md:inline-flex items-center gap-1 chip bg-bg-card border shrink-0"
                style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
              >
                <span className="text-ink-secondary">Crowd</span>
                <span className="font-medium text-accent">{forecast.crowd_level}/10</span>
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
                ? `Live · last ${liveLastFetchedAt ? new Date(liveLastFetchedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : "—"}`
                : "Poll real wait times every 5 min"
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
              onClick={() => setShowKey(v => !v)}
              className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-md text-[11px] transition-colors shrink-0 bg-bg-card text-ink-secondary hover:bg-bg-hover"
              style={{ borderWidth: "0.5px", borderColor: "var(--border-subtle)" }}
              title="Anthropic API key for AI chat"
            >
              <IconKey size={12} stroke={1.5} />
              <span>{apiKey ? "AI key" : "Add AI key"}</span>
            </button>
          </div>
        )}

        {/* Theme toggle — always visible, pushed right */}
        <button
          onClick={toggleTheme}
          className={clsx(
            "w-8 h-8 rounded-md flex items-center justify-center text-ink-secondary hover:text-ink-primary hover:bg-bg-hover transition-colors shrink-0",
            isPlanner ? "ml-auto" : "ml-auto",
          )}
        >
          {theme === "dark" ? <IconSun size={14} stroke={1.5} /> : <IconMoon size={14} stroke={1.5} />}
        </button>
      </div>

      {/* API key popover */}
      {showKey && (
        <div className="absolute right-4 top-12 z-30 panel p-3 w-80 sm:w-96 shadow-xl">
          <div className="text-[11px] font-medium mb-1">Anthropic API key</div>
          <div className="text-[10px] text-ink-secondary mb-2">
            Stored in your browser. Sent per-request to your local backend for AI chat.
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
            <button onClick={() => { setApiKey(draftKey); setShowKey(false); }} className="btn-primary">Save</button>
          </div>
        </div>
      )}
    </header>
  );
}

function App() {
  const [tab, setTab] = useState<Tab>(() => {
    return window.location.hash === "#ll" ? "ll-monitor" : "planner";
  });

  function switchTab(t: Tab) {
    setTab(t);
    window.location.hash = t === "ll-monitor" ? "ll" : "";
  }

  return (
    <div className="h-dvh flex flex-col overflow-hidden">
      <AppHeader tab={tab} onTabChange={switchTab} />
      <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {tab === "planner" ? <PlannerPage /> : <LLMonitorPage />}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
