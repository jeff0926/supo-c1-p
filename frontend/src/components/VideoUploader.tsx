import { useCallback, useState } from "react";

import { uploadVideo } from "../api";

interface VideoUploaderProps {
  onUploaded: () => void;
}

export function VideoUploader({ onUploaded }: VideoUploaderProps): JSX.Element {
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File): Promise<void> => {
      setUploading(true);
      setError(null);
      try {
        await uploadVideo(file);
        onUploaded();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploaded],
  );

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-6">
      <h2 className="text-lg font-semibold mb-3">Upload long-form video</h2>
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
      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </div>
  );
}
