import type { Clip } from "../types";

interface ClipPreviewProps {
  clip: Clip;
}

export function ClipPreview({ clip }: ClipPreviewProps): JSX.Element {
  if (!clip.rendered || !clip.output_url) {
    return (
      <div className="aspect-[9/16] flex items-center justify-center bg-slate-900 rounded text-xs text-slate-500">
        Rendering…
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <video
        controls
        preload="metadata"
        className="w-full aspect-[9/16] rounded bg-black"
        src={clip.output_url}
      />
      <a
        href={clip.output_url}
        download
        className="block text-center text-xs font-semibold py-1.5 rounded bg-accent text-slate-900 hover:opacity-90"
      >
        Download MP4
      </a>
    </div>
  );
}
