import { IconX, IconExternalLink, IconClock, IconToolsKitchen2 } from "@tabler/icons-react";
import clsx from "clsx";
import { usePlanner } from "../store/plannerStore";
import type { Restaurant } from "../types";

const SERVICE_LABELS: Record<string, { label: string; cls: string }> = {
  full:  { label: "Table Service",   cls: "bg-indigo-500/20 text-indigo-300" },
  quick: { label: "Quick Service",   cls: "bg-emerald-500/20 text-emerald-300" },
  bar:   { label: "Bar",             cls: "bg-violet-500/20 text-violet-300" },
  snack: { label: "Snack",           cls: "bg-amber-500/20 text-amber-300" },
  cart:  { label: "Cart",            cls: "bg-slate-500/20 text-slate-300" },
};

export function RestaurantPanel({ restaurant: r, onClose }: { restaurant: Restaurant; onClose: () => void }) {
  const { addBreak, earlyEntry } = usePlanner();
  const svc = SERVICE_LABELS[r.service] ?? { label: r.service, cls: "bg-bg-hover text-ink-secondary" };

  function addFoodBreak() {
    addBreak("break_food", r.avg_meal_minutes);
    onClose();
  }

  return (
    <div className="panel p-4">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className={clsx("chip text-[10px] font-medium", svc.cls)}>{svc.label}</span>
            {r.reservations && (
              <span className="chip bg-blue-500/15 text-blue-300 text-[10px]">Reservations</span>
            )}
            <span className="text-[10px] text-ink-muted capitalize">{r.cuisine}</span>
          </div>
          <h3 className="text-base font-medium leading-tight mt-1">{r.name}</h3>
          {r.description && (
            <p className="text-[11px] text-ink-secondary mt-0.5 leading-relaxed">{r.description}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-ink-secondary hover:text-ink-primary hover:bg-bg-hover transition-colors"
        >
          <IconX size={14} stroke={1.5} />
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 text-center mb-3 text-[11px]">
        <div className="card px-2 py-1.5">
          <div className="text-ink-secondary text-[9px]">Avg time</div>
          <div className="font-medium">{r.avg_meal_minutes} min</div>
        </div>
        <div className="card px-2 py-1.5">
          <div className="text-ink-secondary text-[9px]">Service</div>
          <div className="font-medium capitalize">{r.service}</div>
        </div>
        <div className="card px-2 py-1.5">
          <div className="text-ink-secondary text-[9px]">Popular</div>
          <div className="font-medium truncate" title={r.popular_dish}>{r.popular_dish || "—"}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {/* Menu highlights */}
        {r.menu_highlights.length > 0 && (
          <div>
            <div className="section-label mb-1.5">Menu highlights</div>
            <ul className="space-y-1">
              {r.menu_highlights.map((item, i) => {
                const [title, ...rest] = item.split(" — ");
                return (
                  <li key={i} className="text-[11px]">
                    <span className="font-medium text-ink-primary">{title}</span>
                    {rest.length > 0 && (
                      <span className="text-ink-muted"> — {rest.join(" — ")}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Wait notes + actions */}
        <div className="space-y-2">
          {r.wait_notes && (
            <div>
              <div className="section-label mb-1.5">
                <IconClock size={10} stroke={1.5} className="inline mr-1" />
                Wait & dining notes
              </div>
              <p className="text-[11px] text-ink-secondary leading-relaxed">{r.wait_notes}</p>
            </div>
          )}

          <div className="flex flex-col gap-1.5 mt-2">
            <button
              onClick={addFoodBreak}
              className="btn-primary text-[11px] flex items-center justify-center gap-1"
            >
              <IconToolsKitchen2 size={12} stroke={1.5} />
              Add {r.avg_meal_minutes}-min food break
            </button>
            {r.url && (
              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost text-[11px] flex items-center justify-center gap-1"
              >
                <IconExternalLink size={11} stroke={1.5} />
                View on Universal's site
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
