import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { PlannerPage } from "./pages/PlannerPage";
import { LLMonitorPage } from "./pages/LLMonitorPage";
import "./index.css";

type Tab = "planner" | "ll-monitor";

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
      {/* Top nav */}
      <nav className="shrink-0 flex items-center gap-1 px-3 py-1.5 bg-bg-base/90 backdrop-blur border-b border-zinc-800/60 z-50">
        <button
          onClick={() => switchTab("planner")}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
            tab === "planner"
              ? "bg-accent/20 text-accent"
              : "text-ink-muted hover:text-ink-primary"
          }`}
        >
          Epic Planner
        </button>
        <button
          onClick={() => switchTab("ll-monitor")}
          className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
            tab === "ll-monitor"
              ? "bg-emerald-500/20 text-emerald-400"
              : "text-ink-muted hover:text-ink-primary"
          }`}
        >
          ⚡ LL Monitor
        </button>
      </nav>

      {/* Page content */}
      <div className="flex-1 overflow-hidden flex flex-col">
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
