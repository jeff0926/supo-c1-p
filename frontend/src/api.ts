import type { Job } from "./types";

const BASE = "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadVideo(file: File): Promise<Job> {
  const form = new FormData();
  form.append("file", file);
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
