import { useEffect, useState } from "react";

import { batchRender, listTemplates } from "../api";
import { useClipSelection } from "../contexts/ClipSelectionContext";
import type { Template } from "../types";

interface BatchRenderBarProps {
  onRendered: () => void;
}

export function BatchRenderBar({ onRendered }: BatchRenderBarProps): JSX.Element | null {
  const { selected, count, clear } = useClipSelection();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listTemplates()
      .then((tpls) => {
        if (!cancelled) setTemplates(tpls);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load templates");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (count === 0) return null;

  const toggleTemplate = (id: string): void => {
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const submit = async (): Promise<void> => {
    if (chosen.size === 0) {
      setError("Pick at least one template.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      const res = await batchRender(Array.from(selected), Array.from(chosen));
      setMessage(`Queued ${res.variant_ids.length} variants.`);
      clear();
      setChosen(new Set());
      onRendered();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Batch render failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="sticky top-2 z-10 mb-4 rounded-lg border border-accent bg-slate-900 p-3 shadow-lg">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-semibold">
          {count} clip{count === 1 ? "" : "s"} selected
        </span>
        <div className="flex flex-wrap gap-2 flex-1">
          {templates.map((t) => {
            const on = chosen.has(t.id);
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => toggleTemplate(t.id)}
                title={t.description}
                className={`text-xs px-2 py-1 rounded border ${
                  on
                    ? "bg-accent text-slate-900 border-accent"
                    : "bg-slate-950 text-slate-300 border-slate-700 hover:border-slate-500"
                }`}
              >
                {t.name}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          disabled={submitting}
          onClick={submit}
          className="text-xs font-semibold px-3 py-1.5 rounded bg-emerald-500 text-slate-900 disabled:opacity-50 hover:bg-emerald-400"
        >
          {submitting ? "Queuing…" : "Batch Render Template"}
        </button>
        <button
          type="button"
          onClick={() => {
            clear();
            setChosen(new Set());
          }}
          className="text-xs px-2 py-1 rounded text-slate-400 hover:text-slate-200"
        >
          Clear
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      {message && <p className="mt-2 text-xs text-emerald-400">{message}</p>}
    </div>
  );
}
