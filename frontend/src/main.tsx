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
    <>
      {/* Top nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center gap-1 px-4 py-2 bg-bg-base/90 backdrop-blur border-b border-zinc-800/60">
        <button
          onClick={() => switchTab("planner")}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            tab === "planner"
              ? "bg-accent/20 text-accent"
              : "text-ink-muted hover:text-ink-primary"
          }`}
        >
          Epic Planner
        </button>
        <button
          onClick={() => switchTab("ll-monitor")}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            tab === "ll-monitor"
              ? "bg-emerald-500/20 text-emerald-400"
              : "text-ink-muted hover:text-ink-primary"
          }`}
        >
          ⚡ LL Monitor
        </button>
      </nav>

      {/* Page content – offset for nav */}
      <div className="pt-10">
        {tab === "planner" ? <PlannerPage /> : <LLMonitorPage />}
      </div>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
