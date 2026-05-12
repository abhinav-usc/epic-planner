import { useState } from "react";
import { usePlanner } from "../store/plannerStore";

export function SettingsBar() {
  const { targetDate, earlyEntry, forecast, apiKey, setDate, setEarlyEntry, setApiKey } = usePlanner();
  const [showKey, setShowKey] = useState(false);
  const [draftKey, setDraftKey] = useState(apiKey);

  return (
    <header className="flex items-center justify-between gap-4 px-5 py-3 border-b border-bg-hover bg-bg-panel">
      <div className="flex items-center gap-3">
        <div className="text-2xl">⚡</div>
        <div>
          <h1 className="font-display font-bold text-lg leading-none">Epic Universe Planner</h1>
          <div className="text-xs text-ink-secondary mt-0.5">Plan your day. Beat the lines.</div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-ink-secondary">Date</span>
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setDate(e.target.value)}
            className="bg-bg-card border border-bg-hover rounded-md px-2 py-1 text-sm"
          />
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={earlyEntry}
            onChange={(e) => setEarlyEntry(e.target.checked)}
            className="accent-accent"
          />
          <span className="text-ink-secondary">Early Entry</span>
        </label>

        {forecast && (
          <div className="chip bg-bg-card border border-bg-hover">
            <span className="text-ink-secondary">Crowd</span>
            <span className="font-semibold text-accent">{forecast.crowd_level}/10</span>
            {forecast.holiday_label && (
              <span className="text-ink-secondary">· {forecast.holiday_label}</span>
            )}
          </div>
        )}

        <button
          onClick={() => setShowKey((v) => !v)}
          className={`btn ${apiKey ? "btn-ghost" : "btn-primary"}`}
          title="Anthropic API key for AI features"
        >
          🔑 {apiKey ? "AI key set" : "Add AI key"}
        </button>

        {showKey && (
          <div className="absolute right-5 top-16 z-30 panel p-3 w-96 shadow-xl">
            <div className="text-sm font-medium mb-2">Anthropic API key</div>
            <div className="text-xs text-ink-secondary mb-2">
              Stored only in your browser (localStorage). Sent per-request as a header to your local backend.
            </div>
            <input
              type="password"
              value={draftKey}
              onChange={(e) => setDraftKey(e.target.value)}
              placeholder="sk-ant-..."
              className="w-full bg-bg-card border border-bg-hover rounded-md px-2 py-1.5 text-sm font-mono"
            />
            <div className="flex justify-end gap-2 mt-2">
              <button onClick={() => setShowKey(false)} className="btn btn-ghost">Cancel</button>
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
