import { useMasterPlayer } from "../contexts/MasterPlayerContext";

export function MasterPlayer(): JSX.Element | null {
  const { currentSrc, registerVideo, clear } = useMasterPlayer();

  if (!currentSrc) return null;

  return (
    <div className="sticky top-2 z-20 mb-4 rounded-lg border border-slate-700 bg-slate-900 p-3">
      <div className="flex items-center justify-between mb-2 gap-2">
        <span className="text-xs uppercase tracking-wider text-slate-500">Master Player</span>
        <button
          type="button"
          onClick={clear}
          className="px-3 py-1 rounded text-xs font-semibold bg-red-600 text-white hover:bg-red-500"
        >
          Close Studio View
        </button>
      </div>
      <video
        ref={registerVideo}
        controls
        preload="metadata"
        className="w-full max-h-[40vh] rounded bg-black aspect-video"
        src={currentSrc}
      />
    </div>
  );
}
