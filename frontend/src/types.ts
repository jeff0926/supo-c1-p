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

export type VariantStatus = "pending" | "rendering" | "completed" | "failed";

export interface Variant {
  id: number;
  clip_id: number;
  template_id: string;
  status: VariantStatus;
  output_md5: string | null;
  output_url: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Clip {
  id: number;
  title: string;
  start_time: number;
  end_time: number;
  virality_score: number;
  reasoning: string;
  rendered: boolean;
  output_url: string | null;
  variants: Variant[];
}

export interface Job {
  id: number;
  video_id: number;
  status: JobStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  has_transcript: boolean;
  clips: Clip[];
}

export interface Video {
  id: number;
  filename: string;
  duration_seconds: number | null;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
}

export interface BatchRenderResponse {
  variant_ids: number[];
}
