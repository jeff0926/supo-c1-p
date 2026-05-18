import { useEffect, useRef } from "react";

import { useActiveClip } from "../contexts/ActiveClipContext";
import type { Clip } from "../types";

interface ClipPreviewProps {
  clip: Clip;
}

export function ClipPreview({ clip }: ClipPreviewProps): JSX.Element {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const { activeClipId, setActiveClipId } = useActiveClip();

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (activeClipId !== clip.id && !video.paused) {
      video.pause();
    }
  }, [activeClipId, clip.id]);

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
        ref={videoRef}
        controls
        preload="metadata"
        className="w-full aspect-[9/16] rounded bg-black"
        src={clip.output_url}
        onPlay={() => setActiveClipId(clip.id)}
        onPause={() => {
          if (activeClipId === clip.id) setActiveClipId(null);
        }}
        onEnded={() => {
          if (activeClipId === clip.id) setActiveClipId(null);
        }}
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
