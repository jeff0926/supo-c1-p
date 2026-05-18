import { ActiveClipProvider } from "./contexts/ActiveClipContext";
import { ClipSelectionProvider } from "./contexts/ClipSelectionContext";
import { MasterPlayerProvider } from "./contexts/MasterPlayerContext";
import { BatchRenderBar } from "./components/BatchRenderBar";
import { MasterPlayer } from "./components/MasterPlayer";
import { VideoUploader } from "./components/VideoUploader";
import { JobList } from "./components/JobList";
import { useJobs } from "./hooks/useJobs";

export default function App(): JSX.Element {
  const { jobs, loading, error, refresh } = useJobs();

  return (
    <MasterPlayerProvider>
      <ActiveClipProvider>
        <ClipSelectionProvider>
          <div className="max-w-6xl mx-auto px-4 py-8">
            <header className="mb-6">
              <h1 className="text-3xl font-bold tracking-tight">
                Omni<span className="text-accent">Clip</span>
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                Long-form video in, viral 9:16 hook clips out.
              </p>
            </header>

            <MasterPlayer />

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-6">
              <VideoUploader onUploaded={refresh} />
              <section>
                <BatchRenderBar onRendered={refresh} />
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold">Jobs</h2>
                  {loading && <span className="text-xs text-slate-500">Loading…</span>}
                </div>
                {error && <p className="text-sm text-red-400 mb-3">{error}</p>}
                <JobList jobs={jobs} onChanged={refresh} />
              </section>
            </div>
          </div>
        </ClipSelectionProvider>
      </ActiveClipProvider>
    </MasterPlayerProvider>
  );
}
