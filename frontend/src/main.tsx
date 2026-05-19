import React, { useState } from "react";
import ReactDOM from "react-dom/client";
import { PlannerPage } from "./pages/PlannerPage";
import { LightningLanePage } from "./pages/LightningLanePage";
import "./index.css";

type Page = "planner" | "lightning-lanes";

function App() {
  const [page, setPage] = useState<Page>("planner");

  return (
    <div className="h-full relative">
      {page === "planner" ? (
        <>
          <PlannerPage />
          {/* Centered nav button floats in the header area */}
          <button
            onClick={() => setPage("lightning-lanes")}
            className="fixed top-[7px] left-1/2 -translate-x-1/2 z-50 flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-medium bg-bg-card text-ink-secondary hover:text-accent hover:bg-bg-hover transition-colors"
            style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.08)" }}
            title="Open Lightning Lane availability monitor"
          >
            ⚡ LL Monitor — Disneyland
          </button>
        </>
      ) : (
        <LightningLanePage onBack={() => setPage("planner")} />
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
