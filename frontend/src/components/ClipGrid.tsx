import { useActiveClip } from "../contexts/ActiveClipContext";
import type { Clip } from "../types";
import { ClipPreview } from "./ClipPreview";

interface ClipGridProps {
  clips: Clip[];
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function ClipGrid({ clips }: ClipGridProps): JSX.Element {
  const { activeClipId } = useActiveClip();

  if (clips.length === 0) {
    return <p className="text-sm text-slate-500">No clips yet.</p>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {clips.map((clip) => {
        const isActive = activeClipId === clip.id;
        const borderClass = isActive
          ? "border-emerald-400 shadow-[0_0_0_2px_rgba(52,211,153,0.45)]"
          : "border-slate-800";
        return (
          <div
            key={clip.id}
            className={`rounded-md border bg-slate-950 p-3 flex flex-col transition-colors ${borderClass}`}
          >
            <div className="flex items-start justify-between mb-2">
              <h4 className="text-sm font-semibold leading-tight">{clip.title}</h4>
              <span className="ml-2 px-2 py-0.5 rounded bg-accent text-slate-900 text-xs font-bold">
                {clip.virality_score}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-2">
              {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
            </p>
            <p className="text-xs text-slate-500 mb-3 flex-1">{clip.reasoning}</p>
            <ClipPreview clip={clip} />
          </div>
        );
      })}
    </div>
  );
}
