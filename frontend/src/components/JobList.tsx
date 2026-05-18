import type { Job } from "../types";
import { ClipGrid } from "./ClipGrid";

interface JobListProps {
  jobs: Job[];
  onChanged: () => void;
}

const STATUS_LABEL: Record<Job["status"], string> = {
  pending: "Queued",
  extracting_audio: "Extracting audio",
  transcribing: "Transcribing",
  curating: "Finding viral hooks",
  reframing: "Tracking faces",
  captioning: "Building captions",
  rendering: "Rendering clips",
  completed: "Completed",
  failed: "Failed",
};

const STATUS_COLOR: Record<Job["status"], string> = {
  pending: "bg-slate-700 text-slate-200",
  extracting_audio: "bg-blue-600 text-white",
  transcribing: "bg-blue-600 text-white",
  curating: "bg-purple-600 text-white",
  reframing: "bg-purple-600 text-white",
  captioning: "bg-purple-600 text-white",
  rendering: "bg-amber-500 text-slate-900",
  completed: "bg-emerald-500 text-slate-900",
  failed: "bg-red-600 text-white",
};

export function JobList({ jobs, onChanged }: JobListProps): JSX.Element {
  if (jobs.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-center text-slate-500">
        No jobs yet — upload a video to start.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {jobs.map((job) => (
        <div key={job.id} className="rounded-lg border border-slate-800 bg-slate-900 p-5">
          <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
            <div>
              <h3 className="font-semibold">Job #{job.id}</h3>
              <p className="text-xs text-slate-500">
                Created {new Date(job.created_at).toLocaleString()}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {job.has_transcript && (
                <a
                  href={`/api/jobs/${job.id}/transcript`}
                  download
                  className="px-3 py-1 rounded-full text-xs font-semibold bg-slate-700 text-slate-100 hover:bg-slate-600"
                >
                  Download transcript
                </a>
              )}
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_COLOR[job.status]}`}
              >
                {STATUS_LABEL[job.status]}
              </span>
            </div>
          </div>
          {job.error_message && (
            <p className="text-sm text-red-400 mb-3">{job.error_message}</p>
          )}
          <ClipGrid clips={job.clips} sourceUrl={job.source_url} onTrimmed={onChanged} />
        </div>
      ))}
    </div>
  );
}
