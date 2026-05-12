import { useState } from "react";
import { usePlanner } from "../store/plannerStore";
import { api } from "../api/client";

interface Msg { role: "user" | "assistant"; content: string }

export function AIChat() {
  const { apiKey, plannedItems, targetDate, forecast } = usePlanner();
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  if (!apiKey) return null;

  async function send() {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    setMsgs(m => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const ctx = { date: targetDate, crowd: forecast?.holiday_label || forecast?.crowd_level, itinerary: plannedItems };
      const r = await api.aiChat(text, ctx);
      setMsgs(m => [...m, { role: "assistant", content: r.reply }]);
    } catch (e: any) {
      setMsgs(m => [...m, { role: "assistant", content: `Error: ${e.message ?? e}` }]);
    } finally {
      setBusy(false);
    }
  }

  async function evaluatePlan() {
    setBusy(true);
    setMsgs(m => [...m, { role: "user", content: "Evaluate my current plan." }]);
    try {
      const r = await api.aiEvaluate(plannedItems, targetDate, forecast?.holiday_label);
      setMsgs(m => [...m, { role: "assistant", content: r.reply }]);
    } catch (e: any) {
      setMsgs(m => [...m, { role: "assistant", content: `Error: ${e.message ?? e}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-5 right-5 z-30 btn-primary rounded-full px-4 py-3 shadow-glow"
      >
        🤖 Ask Claude
      </button>

      {open && (
        <div className="fixed bottom-20 right-5 z-30 panel w-[360px] h-[480px] flex flex-col shadow-xl">
          <div className="px-3 py-2 border-b border-bg-hover flex items-center justify-between">
            <div className="font-display font-semibold text-sm">Trip Assistant</div>
            <button onClick={() => setOpen(false)} className="text-ink-secondary hover:text-ink-primary">✕</button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm">
            {msgs.length === 0 && (
              <div className="text-ink-secondary">
                Ask me anything about Epic Universe. I have your current plan as context.
                <div className="mt-3 space-y-1">
                  <button onClick={evaluatePlan} className="btn-ghost w-full text-xs text-left">
                    🔍 Critique my plan
                  </button>
                </div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div
                key={i}
                className={`whitespace-pre-wrap rounded-md px-3 py-2 ${
                  m.role === "user" ? "bg-bg-card ml-6" : "bg-bg-hover mr-6"
                }`}
              >
                {m.content}
              </div>
            ))}
            {busy && <div className="text-ink-muted text-xs">…</div>}
          </div>
          <form
            onSubmit={(e) => { e.preventDefault(); send(); }}
            className="p-2 border-t border-bg-hover flex gap-2"
          >
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about a ride, restaurant, or plan…"
              className="flex-1 bg-bg-card border border-bg-hover rounded-md px-2 py-1.5 text-sm"
            />
            <button disabled={busy} className="btn-primary text-xs">Send</button>
          </form>
        </div>
      )}
    </>
  );
}
