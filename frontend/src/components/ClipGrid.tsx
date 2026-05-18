import { useClipSelection } from "../contexts/ClipSelectionContext";
import type { Clip, Variant } from "../types";
import { ClipPreview } from "./ClipPreview";

interface ClipGridProps {
  clips: Clip[];
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function VariantRow({ variant }: { variant: Variant }): JSX.Element {
  const statusLabel: Record<Variant["status"], string> = {
    pending: "Queued",
    rendering: "Rendering…",
    completed: "Ready",
    failed: "Failed",
  };
  const statusColor: Record<Variant["status"], string> = {
    pending: "text-slate-400",
    rendering: "text-amber-400",
    completed: "text-emerald-400",
    failed: "text-red-400",
  };
  return (
    <div className="flex items-center justify-between gap-2 text-xs">
      <span className="font-mono">{variant.template_id}</span>
      <div className="flex items-center gap-2">
        <span className={statusColor[variant.status]}>{statusLabel[variant.status]}</span>
        {variant.output_url && (
          <a
            href={variant.output_url}
            download
            className="px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600"
          >
            ↓
          </a>
        )}
      </div>
    </div>
  );
}

export function ClipGrid({ clips }: ClipGridProps): JSX.Element {
  const { isSelected, toggle } = useClipSelection();

  if (clips.length === 0) {
    return <p className="text-sm text-slate-500">No clips yet.</p>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {clips.map((clip) => {
        const selected = isSelected(clip.id);
        const baseBorder = selected ? "border-accent" : "border-slate-800";
        return (
          <div
            key={clip.id}
            tabIndex={0}
            className={`group rounded-md border bg-slate-950 p-3 flex flex-col transition-colors outline-none focus:border-emerald-400 focus:shadow-[0_0_0_2px_rgba(52,211,153,0.45)] focus-within:border-emerald-400 focus-within:shadow-[0_0_0_2px_rgba(52,211,153,0.45)] hover:border-emerald-400/60 ${baseBorder}`}
          >
            <div className="flex items-start gap-2 mb-2">
              <input
                type="checkbox"
                aria-label={`Select clip ${clip.title}`}
                checked={selected}
                onChange={() => toggle(clip.id)}
                disabled={!clip.rendered}
                className="mt-1 h-4 w-4 accent-yellow-400"
              />
              <h4 className="text-sm font-semibold leading-tight flex-1">{clip.title}</h4>
              <span className="px-2 py-0.5 rounded bg-accent text-slate-900 text-xs font-bold">
                {clip.virality_score}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-2">
              {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
            </p>
            <p className="text-xs text-slate-500 mb-3 flex-1">{clip.reasoning}</p>
            <ClipPreview clip={clip} />
            {clip.variants.length > 0 && (
              <div className="mt-3 space-y-1 pt-2 border-t border-slate-800">
                <p className="text-[10px] uppercase tracking-wider text-slate-500">Variants</p>
                {clip.variants.map((v) => (
                  <VariantRow key={v.id} variant={v} />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
