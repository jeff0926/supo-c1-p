export type JobStatus =
  | "pending"
  | "extracting_audio"
  | "transcribing"
  | "curating"
  | "reframing"
  | "captioning"
  | "rendering"
  | "completed"
  | "failed";

export interface Clip {
  id: number;
  title: string;
  start_time: number;
  end_time: number;
  virality_score: number;
  reasoning: string;
  rendered: boolean;
  output_url: string | null;
}

export interface Job {
  id: number;
  video_id: number;
  status: JobStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  clips: Clip[];
}

export interface Video {
  id: number;
  filename: string;
  duration_seconds: number | null;
  created_at: string;
}
