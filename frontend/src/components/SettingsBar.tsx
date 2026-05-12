import { useState } from "react";
import clsx from "clsx";
import { IconBolt, IconKey } from "@tabler/icons-react";
import { usePlanner } from "../store/plannerStore";

export function SettingsBar() {
  const {
    targetDate, earlyEntry, worstCaseMode, forecast, apiKey,
    setDate, setEarlyEntry, setWorstCaseMode, setApiKey,
  } = usePlanner();
  const [showKey, setShowKey] = useState(false);
  const [draftKey, setDraftKey] = useState(apiKey);

  return (
    <header className="flex items-center justify-between gap-3 px-4 py-2 border-b border-bg-hover bg-bg-panel relative">
      <div className="flex items-center gap-2">
        <IconBolt size={16} stroke={1.5} className="text-accent" />
        <div>
          <h1 className="text-sm font-medium leading-none">Epic Universe planner</h1>
          <div className="text-[10px] text-ink-secondary mt-0.5">Plan your day. Beat the lines.</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-1.5 text-[11px]">
          <span className="text-ink-secondary">Date</span>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setDate(e.target.value)}
            className="bg-bg-card border rounded-md px-2 py-0.5 text-[11px]"
            style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.06)" }}
          />
        </label>

        <label className="flex items-center gap-1.5 text-[11px]">
          <input
            type="checkbox"
            checked={earlyEntry}
            onChange={(e) => setEarlyEntry(e.target.checked)}
            className="accent-accent w-3 h-3"
          />
          <span className="text-ink-secondary">Early entry</span>
        </label>

        <label className="flex items-center gap-1.5 text-[11px]" title="Use 90th-percentile historical waits for timeline block heights">
          <input
            type="checkbox"
            checked={worstCaseMode}
            onChange={(e) => setWorstCaseMode(e.target.checked)}
            className="accent-red-400 w-3 h-3"
          />
          <span className="text-ink-secondary">Worst case</span>
        </label>

        {forecast && (
          <div className="chip bg-bg-card border" style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.06)" }}>
            <span className="text-ink-secondary">Crowd</span>
            <span className="font-medium text-accent">{forecast.crowd_level}/10</span>
            {forecast.holiday_label && (
              <span className="text-ink-secondary">· {forecast.holiday_label}</span>
            )}
          </div>
        )}

        <button
          onClick={() => setShowKey((v) => !v)}
          className={clsx(
            "flex items-center gap-1 px-2 py-1 rounded-md text-[11px] transition-colors",
            apiKey
              ? "bg-bg-card text-ink-secondary hover:bg-bg-hover"
              : "bg-accent/15 text-accent hover:bg-accent/25",
          )}
          style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.06)" }}
          title="Anthropic API key for AI features"
        >
          <IconKey size={12} stroke={1.5} />
          <span>{apiKey ? "AI key set" : "Add AI key"}</span>
        </button>

        {showKey && (
          <div className="absolute right-4 top-12 z-30 panel p-3 w-96 shadow-xl">
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
              style={{ borderWidth: "0.5px", borderColor: "rgba(255,255,255,0.06)" }}
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
