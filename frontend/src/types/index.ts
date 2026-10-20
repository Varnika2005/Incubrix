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

export interface TimelineSegment {
  clip_id: string;
  source_id: string;
  source_start: number;
  source_end: number;
  speed: number;
  timeline_start: number;
  timeline_end: number;
  timeline_duration: number;
}

export interface ContentAwareEffect {
  effect_id: string;
  type: string;
  source_id: string;
  source_start: number;
  source_end: number;
  source_duration: number;
  parameters?: Record<string, any>;
  label?: string | null;
}

export interface TransformedTimelineEffect {
  effect_id: string;
  parent_effect_id?: string;
  type: string;
  source_id: string;
  source_start: number;
  source_end: number;
  segment_id: string;
  timeline_start: number;
  timeline_end: number;
  duration: number;
  speed: number;
  status: 'active' | 'clipped' | 'split' | 'dropped_content_removed' | string;
  parameters?: Record<string, any>;
  label?: string | null;
}

export interface TimelineData {
  source_id: string;
  source_duration: number;
  timeline_duration: number;
  segment_count: number;
  segments: TimelineSegment[];
  source_effects: ContentAwareEffect[];
  transformed_effects: TransformedTimelineEffect[];
  dropped_effects: TransformedTimelineEffect[];
  timeline_hash?: string;
  summary: {
    active_effects_count: number;
    dropped_effects_count: number;
    is_reordered: boolean;
    has_speed_change: boolean;
    has_cuts: boolean;
  };
}

export type InstructionStatus = 'APPLIED' | 'NEEDS_CLARIFICATION' | 'REJECTED';

export interface InstructionOutcome {
  status: InstructionStatus;
  instruction: string;
  operation?: Record<string, any> | null;
  message: string;
  operationId: string;
  operation_id?: string | null;
  timeline?: TimelineData | null;
  clarification_prompt?: string | null;
  error_code?: string | null;
  rollback_performed?: boolean;
  time_reference?: string | null;
  converted_timestamps?: Record<string, any> | null;
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
  timeline?: TimelineData | null;
  timeline_hash?: string | null;
  instruction_outcomes?: InstructionOutcome[] | null;
}

export interface SilenceSegment {
  start: number;
  end: number;
  duration: number;
}

export interface SourceIntegrityInfo {
  original_hash: string;
  final_hash: string;
  hash_algorithm: string;
  verified_identical: boolean;
  status: string;
  non_destructive: boolean;
  original_size_bytes?: number | null;
  verification_message: string;
}

export interface IntegrityVerificationResponse {
  job_id: string;
  original_hash: string;
  current_hash: string;
  hash_algorithm: string;
  verified: boolean;
  is_valid?: boolean;
  status: string;
  message: string;
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
  original_file_hash?: string | null;
  original_file_size?: number | null;
  source_integrity_verified?: boolean;
  source_integrity_status?: string;
  edit_history?: EditPlan[] | null;
  timeline?: TimelineData | null;
  instruction_history?: InstructionOutcome[] | null;
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
  source_integrity?: SourceIntegrityInfo | null;
  timeline?: TimelineData | null;
  timeline_hash?: string | null;
  instruction_audit?: InstructionOutcome[] | null;
}

export interface UndoRedoResponse {
  status: string;
  message?: string | null;
  job_id: string;
  current_index: number;
  history_length: number;
  can_undo: boolean;
  can_redo: boolean;
  current_plan?: EditPlan | null;
  timeline?: TimelineData | null;
  timeline_hash?: string | null;
  description?: string | null;
}

export interface HistoryStackResponse {
  job_id: string;
  current_index: number;
  history_length: number;
  can_undo: boolean;
  can_redo: boolean;
  current_state?: Record<string, any> | null;
  states: Record<string, any>[];
}

export interface TimelineMapRequest {
  source_time?: number | null;
  timeline_time?: number | null;
  source_range?: [number, number] | null;
  timeline_range?: [number, number] | null;
}

export interface TimelineMapResponse {
  source_time?: number | null;
  timeline_time?: number | null;
  mapped_timeline_times?: number[];
  mapped_source_info?: { clip_id: string; source_time: number } | null;
  mapped_source_intervals?: Array<{ start: number; end: number; clip_id: string }> | null;
  mapped_timeline_intervals?: Array<{ start: number; end: number; clip_id: string }> | null;
}

