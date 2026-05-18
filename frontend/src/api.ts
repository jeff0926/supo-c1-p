import type { BatchRenderResponse, Clip, Job, Template } from "./types";

const BASE = "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export type TargetLength = "auto" | "under_30" | "30_to_60";

export interface UploadOptions {
  useLlm: boolean;
  keywordFocus: string | null;
  targetLength: TargetLength;
}

export async function uploadVideo(file: File, opts: UploadOptions): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
  form.append("use_llm", String(opts.useLlm));
  if (opts.keywordFocus && opts.keywordFocus.trim().length > 0) {
    form.append("keyword_focus", opts.keywordFocus.trim());
  }
  form.append("target_length", opts.targetLength);
  const res = await fetch(`${BASE}/videos`, { method: "POST", body: form });
  return handle<Job>(res);
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${BASE}/jobs`);
  return handle<Job[]>(res);
}

export async function getJob(id: number): Promise<Job> {
  const res = await fetch(`${BASE}/jobs/${id}`);
  return handle<Job>(res);
}

export async function listTemplates(): Promise<Template[]> {
  const res = await fetch(`${BASE}/templates`);
  return handle<Template[]>(res);
}

export async function batchRender(
  clipIds: number[],
  templateIds: string[],
): Promise<BatchRenderResponse> {
  const res = await fetch(`${BASE}/clips/batch-render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clip_ids: clipIds, template_ids: templateIds }),
  });
  return handle<BatchRenderResponse>(res);
}

export async function trimClip(
  clipId: number,
  startTime: number,
  endTime: number,
): Promise<Clip> {
  const res = await fetch(`${BASE}/clips/${clipId}/trim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_time: startTime, end_time: endTime }),
  });
  return handle<Clip>(res);
}
