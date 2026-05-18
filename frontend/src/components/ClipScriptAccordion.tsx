import { useCallback, useMemo, useState } from "react";

import { trimClip } from "../api";
import { useMasterPlayer } from "../contexts/MasterPlayerContext";
import type { Clip } from "../types";

interface ClipScriptAccordionProps {
  clip: Clip;
  sourceUrl: string | null;
  onTrimmed: () => void;
}

type EditMode = "seek" | "set_start" | "set_end";

export function ClipScriptAccordion({
  clip,
  sourceUrl,
  onTrimmed,
}: ClipScriptAccordionProps): JSX.Element {
  const { play } = useMasterPlayer();
  const [open, setOpen] = useState<boolean>(false);
  const [mode, setMode] = useState<EditMode>("seek");
  const [newStart, setNewStart] = useState<number | null>(null);
  const [newEnd, setNewEnd] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveStart = newStart ?? clip.start_time;
  const effectiveEnd = newEnd ?? clip.end_time;
  const isChanged = newStart !== null || newEnd !== null;
  const canApply =
    !submitting && isChanged && effectiveEnd > effectiveStart && sourceUrl !== null;

  const handleWordClick = useCallback(
    (wordStart: number, wordEnd: number): void => {
      if (mode === "set_start") {
        setNewStart(wordStart);
        if (newEnd !== null && wordStart >= newEnd) setNewEnd(null);
        setMode("seek");
      } else if (mode === "set_end") {
        setNewEnd(wordEnd);
        if (newStart !== null && wordEnd <= newStart) setNewStart(null);
        setMode("seek");
      } else if (sourceUrl) {
        play(sourceUrl, wordStart);
      }
    },
    [mode, newStart, newEnd, play, sourceUrl],
  );

  const handleApply = useCallback(async (): Promise<void> => {
    if (!canApply) return;
    setSubmitting(true);
    setError(null);
    try {
      await trimClip(clip.id, effectiveStart, effectiveEnd);
      setNewStart(null);
      setNewEnd(null);
      onTrimmed();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trim failed");
    } finally {
      setSubmitting(false);
    }
  }, [canApply, clip.id, effectiveStart, effectiveEnd, onTrimmed]);

  const wordRows = useMemo(() => clip.words, [clip.words]);

  return (
    <div className="mt-3 pt-2 border-t border-slate-800">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between text-xs uppercase tracking-wider text-slate-400 hover:text-slate-200"
        aria-expanded={open}
      >
        <span>View Clip Script</span>
        <span className="font-mono">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          <div className="flex flex-wrap items-center gap-1 text-[10px]">
            <button
              type="button"
              onClick={() => setMode("seek")}
              className={`px-2 py-0.5 rounded border ${
                mode === "seek"
                  ? "bg-slate-700 border-slate-600 text-white"
                  : "bg-slate-950 border-slate-800 text-slate-400"
              }`}
            >
              Click to seek
            </button>
            <button
              type="button"
              onClick={() => setMode("set_start")}
              className={`px-2 py-0.5 rounded border ${
                mode === "set_start"
                  ? "bg-emerald-600 border-emerald-500 text-white"
                  : "bg-slate-950 border-slate-800 text-slate-400"
              }`}
            >
              Set new start
            </button>
            <button
              type="button"
              onClick={() => setMode("set_end")}
              className={`px-2 py-0.5 rounded border ${
                mode === "set_end"
                  ? "bg-red-600 border-red-500 text-white"
                  : "bg-slate-950 border-slate-800 text-slate-400"
              }`}
            >
              Set new end
            </button>
          </div>

          <div className="text-[10px] text-slate-500 space-x-2">
            <span>
              Range: <span className="font-mono text-slate-300">{effectiveStart.toFixed(2)}s</span>{" "}
              → <span className="font-mono text-slate-300">{effectiveEnd.toFixed(2)}s</span>
            </span>
            {isChanged && <span className="text-amber-400">(modified)</span>}
          </div>

          {wordRows.length === 0 ? (
            <p className="text-xs text-slate-600 italic">
              No transcript words available for this clip yet.
            </p>
          ) : (
            <div className="max-h-48 overflow-y-auto rounded bg-slate-900 p-2 flex flex-wrap gap-1">
              {wordRows.map((w, idx) => {
                const isStart = newStart !== null && w.start === newStart;
                const isEnd = newEnd !== null && w.end === newEnd;
                const inNewRange =
                  newStart !== null && newEnd !== null && w.start >= newStart && w.end <= newEnd;
                const baseClass = "px-1 py-0.5 rounded text-xs font-mono transition-colors";
                let className = `${baseClass} bg-slate-800 hover:bg-slate-700 text-slate-200`;
                if (isStart) {
                  className = `${baseClass} bg-emerald-600 text-white`;
                } else if (isEnd) {
                  className = `${baseClass} bg-red-600 text-white`;
                } else if (inNewRange) {
                  className = `${baseClass} bg-slate-700 text-slate-100`;
                }
                return (
                  <button
                    key={`${w.start}-${idx}`}
                    type="button"
                    title={`${w.start.toFixed(2)}s — ${w.end.toFixed(2)}s`}
                    onClick={() => handleWordClick(w.start, w.end)}
                    className={className}
                  >
                    {w.word}
                  </button>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={!canApply}
              onClick={handleApply}
              className="text-xs font-semibold px-3 py-1.5 rounded bg-accent text-slate-900 disabled:opacity-40 hover:opacity-90"
            >
              {submitting ? "Applying…" : "Apply Trim"}
            </button>
            {isChanged && (
              <button
                type="button"
                onClick={() => {
                  setNewStart(null);
                  setNewEnd(null);
                }}
                className="text-xs px-2 py-1 rounded text-slate-400 hover:text-slate-200"
              >
                Reset
              </button>
            )}
          </div>

          {error && <p className="text-xs text-red-400">{error}</p>}
          {!sourceUrl && (
            <p className="text-[10px] text-slate-600 italic">
              Source video unavailable — seek and trim are disabled.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
