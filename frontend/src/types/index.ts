export type JobStatus =
  | 'uploaded'
  | 'analyzing'
  | 'awaiting_approval'
  | 'queued'
  | 'processing'
  | 'verifying'
  | 'completed'
  | 'failed';

export interface MediaMetadata {
  duration: number;
  width: number;
  height: number;
  aspect_ratio: string;
  fps: number;
  video_codec: string;
  audio_codec?: string | null;
  has_audio: boolean;
  size_bytes: number;
  format_name: string;
}

export interface EditOperation {
  type: string;
  description: string;
  seconds?: number;
  start_time?: number;
  end_time?: number;
  target_seconds?: number;
  ratio?: '16:9' | '9:16' | '1:1';
  mode?: 'fit' | 'crop' | 'pad';
  standard?: '720p' | '1080p' | '480p';
  volume_percent?: number;
  mute?: boolean;
  brightness?: number;
  contrast?: number;
  confirmed_intervals?: [number, number][];
  burn?: boolean;
  custom_text?: string;
  format?: string;
  parameters?: Record<string, any>;
}

export interface EditPlan {
  prompt: string;
  operations: EditOperation[];
  warnings: string[];
  requires_confirmation: boolean;
  confirmation_reason?: string | null;
  suggested_repair?: string | null;
  estimated_duration?: number | null;
  estimated_dimensions?: [number, number] | null;
}

export interface SilenceSegment {
  start: number;
  end: number;
  duration: number;
}

export interface JobResponse {
  id: string;
  status: JobStatus;
  original_filename: string;
  created_at: string;
  updated_at: string;
  prompt?: string | null;
  input_metadata?: MediaMetadata | null;
  output_metadata?: MediaMetadata | null;
  edit_plan?: EditPlan | null;
  detected_silence?: SilenceSegment[] | null;
  progress: number;
  error_message?: string | null;
  output_available: boolean;
  processing_time_seconds?: number | null;
  user_id?: string | null;
  is_demo?: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SystemCapabilities {
  ffmpeg_installed: boolean;
  ffmpeg_version: string;
  ffprobe_version: string;
  whisper_available: boolean;
  whisper_details: string;
  llm_enabled: boolean;
  llm_provider?: string | null;
  max_file_size_mb: number;
  max_duration_seconds: number;
  supported_formats: string[];
  supported_operations: string[];
}

export interface EditReceipt {
  job_id: string;
  created_at: string;
  completed_at: string;
  input_metadata: MediaMetadata;
  output_metadata?: MediaMetadata | null;
  user_prompt: string;
  applied_operations: Record<string, any>[];
  processing_time_seconds: number;
  warnings: string[];
  app_version: string;
}
