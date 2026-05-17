import { useCallback, useEffect, useRef, useState } from "react";

import { listJobs } from "../api";
import type { Job } from "../types";

const ACTIVE_STATES: ReadonlySet<Job["status"]> = new Set([
  "pending",
  "extracting_audio",
  "transcribing",
  "curating",
  "reframing",
  "captioning",
  "rendering",
]);

export function useJobs(): {
  jobs: Job[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
} {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const next = await listJobs();
      setJobs(next);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = async (): Promise<void> => {
      if (cancelled) return;
      await refresh();
      const anyActive = jobs.some((j) => ACTIVE_STATES.has(j.status));
      const delay = anyActive ? 2000 : 8000;
      timer.current = setTimeout(tick, delay);
    };
    tick();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  return { jobs, loading, error, refresh };
}
