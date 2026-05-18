import { useCallback, useState } from "react";

import { uploadVideo } from "../api";
import type { TargetLength } from "../api";

interface VideoUploaderProps {
  onUploaded: () => void;
}

const TARGET_LENGTH_OPTIONS: ReadonlyArray<{ value: TargetLength; label: string }> = [
  { value: "auto", label: "Auto" },
  { value: "under_30", label: "Under 30s" },
  { value: "30_to_60", label: "30s – 60s" },
];

export function VideoUploader({ onUploaded }: VideoUploaderProps): JSX.Element {
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [useLlm, setUseLlm] = useState<boolean>(true);
  const [keywordFocus, setKeywordFocus] = useState<string>("");
  const [targetLength, setTargetLength] = useState<TargetLength>("auto");

  const handleFile = useCallback(
    async (file: File): Promise<void> => {
      setUploading(true);
      setError(null);
      try {
        await uploadVideo(file, {
          useLlm,
          keywordFocus: keywordFocus.trim() || null,
          targetLength,
        });
        onUploaded();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploaded, useLlm, keywordFocus, targetLength],
  );

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 space-y-4">
      <h2 className="text-lg font-semibold">Upload long-form video</h2>

      <div className="flex items-center justify-between rounded-md border border-slate-800 bg-slate-950 px-3 py-2">
        <div>
          <p className="text-sm font-semibold">AI Semantic Curation</p>
          <p className="text-xs text-slate-500">
            {useLlm
              ? "Claude picks viral hooks from the transcript."
              : "Deterministic pause-based segmentation (no LLM)."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={useLlm}
          onClick={() => setUseLlm((v) => !v)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            useLlm ? "bg-accent" : "bg-slate-700"
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-slate-950 transition-transform ${
              useLlm ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      </div>

      <div className="space-y-1">
        <label htmlFor="keyword-focus" className="text-xs font-semibold text-slate-300">
          Keyword Focus <span className="text-slate-500 font-normal">(optional)</span>
        </label>
        <input
          id="keyword-focus"
          type="text"
          value={keywordFocus}
          onChange={(e) => setKeywordFocus(e.target.value)}
          placeholder="e.g. agency, leadership, revenue"
          disabled={uploading}
          className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-accent focus:outline-none"
        />
        <p className="text-[10px] text-slate-500">
          Only clips mentioning this word are kept. Leave blank for no filter.
        </p>
      </div>

      <div className="space-y-1">
        <label htmlFor="target-length" className="text-xs font-semibold text-slate-300">
          Target Clip Length
        </label>
        <select
          id="target-length"
          value={targetLength}
          onChange={(e) => setTargetLength(e.target.value as TargetLength)}
          disabled={uploading}
          className="w-full rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-accent focus:outline-none"
        >
          {TARGET_LENGTH_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <p className="text-[10px] text-slate-500">
          Truncates over-long clips at word boundaries; drops clips below the minimum.
        </p>
      </div>

      <label
        className={`flex flex-col items-center justify-center border-2 border-dashed rounded-md p-10 cursor-pointer transition-colors ${
          uploading ? "border-slate-700 bg-slate-800/50" : "border-slate-700 hover:border-accent"
        }`}
      >
        <input
          type="file"
          accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
          className="hidden"
          disabled={uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <span className="text-sm text-slate-400">
          {uploading ? "Uploading…" : "Click to upload .mp4 / .mov / .mkv / .webm"}
        </span>
      </label>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
