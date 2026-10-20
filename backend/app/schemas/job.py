from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.schemas.edit_plan import EditPlan
from app.schemas.instruction_response import InstructionOutcome, InstructionStatus, ProcessInstructionRequest

class JobStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    AWAITING_APPROVAL = "awaiting_approval"
    QUEUED = "queued"
    PROCESSING = "processing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"

class MediaMetadata(BaseModel):
    duration: float = Field(0.0, description="Duration in seconds")
    width: int = Field(0, description="Video width in pixels")
    height: int = Field(0, description="Video height in pixels")
    aspect_ratio: str = Field("unknown", description="e.g. 16:9, 9:16, 1:1")
    fps: float = Field(0.0, description="Frames per second")
    video_codec: str = Field("unknown", description="Video codec name")
    audio_codec: Optional[str] = Field(None, description="Audio codec name")
    has_audio: bool = Field(False, description="Whether audio stream exists")
    size_bytes: int = Field(0, description="File size in bytes")
    format_name: str = Field("unknown", description="Container format name")

class AnalyzePromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000, description="Natural language editing instruction")

class ProcessJobRequest(BaseModel):
    approved_plan: EditPlan = Field(..., description="Confirmed or modified edit plan to execute")
    callback_url: Optional[str] = Field(None, description="Optional HMAC-signed callback URL upon job completion")

class CreateUrlJobRequest(BaseModel):
    url: str = Field(..., description="Public HTTP/HTTPS media URL to safely ingest")
    prompt: Optional[str] = Field(None, description="Optional editing instruction prompt")
    callback_url: Optional[str] = Field(None, description="Optional callback URL")

class SilenceSegment(BaseModel):
    start: float
    end: float
    duration: float
    is_deliberate: bool = False
    classification: str = "dead_air"  # 'intentional_pause', 'uncertain', 'dead_air'
    confidence: float = 1.0

class SourceIntegrityInfo(BaseModel):
    original_hash: str
    final_hash: str
    hash_algorithm: str = "SHA-256"
    verified_identical: bool = True
    status: str = "verified_immutable"
    non_destructive: bool = True
    original_size_bytes: Optional[int] = None
    verification_message: str = "Original uploaded source was verified unchanged before and after editing operations."

class EditReceipt(BaseModel):
    job_id: str
    created_at: str
    completed_at: str
    input_metadata: MediaMetadata
    output_metadata: Optional[MediaMetadata] = None
    user_prompt: str
    applied_operations: List[Dict[str, Any]]
    processing_time_seconds: float
    warnings: List[str]
    app_version: str = "1.0.0"
    source_integrity: Optional[SourceIntegrityInfo] = None
    timeline: Optional[Dict[str, Any]] = None
    timeline_hash: Optional[str] = None
    instruction_audit: Optional[List[Dict[str, Any]]] = None

class SaveHistoryRequest(BaseModel):
    history: List[Dict[str, Any]]
    current_plan: Optional[EditPlan] = None

class UndoRedoResponse(BaseModel):
    status: str
    message: Optional[str] = None
    job_id: str
    current_index: int
    history_length: int
    can_undo: bool
    can_redo: bool
    current_plan: Optional[Dict[str, Any]] = None
    timeline: Optional[Dict[str, Any]] = None
    timeline_hash: Optional[str] = None
    description: Optional[str] = None

class HistoryStackResponse(BaseModel):
    job_id: str
    current_index: int
    history_length: int
    can_undo: bool
    can_redo: bool
    current_state: Optional[Dict[str, Any]] = None
    states: List[Dict[str, Any]]

class IntegrityVerificationResponse(BaseModel):
    job_id: str
    original_hash: str
    current_hash: str
    hash_algorithm: str = "SHA-256"
    verified: bool
    status: str
    message: str

class AddTimelineEffectRequest(BaseModel):
    type: str = Field(..., description="Effect type: caption, mute, beep, visual_effect, color_adjust")
    source_start: float = Field(..., ge=0.0, description="Anchor start timestamp in source media")
    source_end: float = Field(..., ge=0.0, description="Anchor end timestamp in source media")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Effect parameters like text, style, freq, etc.")
    label: Optional[str] = None

class TransformTimelineRequest(BaseModel):
    action: str = Field(..., description="Action: cut, speed, reorder, trim_start, trim_end, time_slice")
    cut_start: Optional[float] = None
    cut_end: Optional[float] = None
    speed: Optional[float] = None
    source_start: Optional[float] = None
    source_end: Optional[float] = None
    order: Optional[List[int]] = None
    seconds: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class TimelineMapRequest(BaseModel):
    source_time: Optional[float] = None
    timeline_time: Optional[float] = None
    source_range: Optional[Tuple[float, float]] = None
    timeline_range: Optional[Tuple[float, float]] = None

class TimelineMapResponse(BaseModel):
    source_time: Optional[float] = None
    timeline_time: Optional[float] = None
    mapped_timeline_times: List[float] = []
    mapped_source_info: Optional[Dict[str, Any]] = None
    mapped_source_intervals: Optional[List[Dict[str, Any]]] = None
    mapped_timeline_intervals: Optional[List[Dict[str, Any]]] = None

class JobResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    status: str
    standard_status: Optional[str] = None
    original_filename: str
    created_at: datetime
    updated_at: datetime
    prompt: Optional[str] = None
    input_metadata: Optional[MediaMetadata] = None
    output_metadata: Optional[MediaMetadata] = None
    edit_plan: Optional[EditPlan] = None
    detected_silence: Optional[List[SilenceSegment]] = None
    progress: int = Field(0, ge=0, le=100)
    error_message: Optional[str] = None
    errors: Optional[List[str]] = None
    output_available: bool = False
    processing_time_seconds: Optional[float] = None
    user_id: Optional[str] = None
    is_demo: bool = False
    original_file_hash: Optional[str] = None
    original_file_size: Optional[int] = None
    source_integrity_verified: bool = True
    source_integrity_status: str = "verified_immutable"
    edit_history: Optional[List[Dict[str, Any]]] = None
    timeline: Optional[Dict[str, Any]] = None
    instruction_history: Optional[List[Dict[str, Any]]] = None
    callback_url: Optional[str] = None
    download_url: Optional[str] = None
    manifest_url: Optional[str] = None
    receipt_url: Optional[str] = None
    preview_url: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class UndoRedoResponse(BaseModel):
    status: str
    message: Optional[str] = None
    job_id: str
    current_index: int
    history_length: int
    can_undo: bool
    can_redo: bool
    current_plan: Optional[Dict[str, Any]] = None
    timeline: Optional[Dict[str, Any]] = None
    timeline_hash: Optional[str] = None
    description: Optional[str] = None

class HistoryStackResponse(BaseModel):
    job_id: str
    current_index: int
    history_length: int
    can_undo: bool
    can_redo: bool
    current_state: Optional[Dict[str, Any]] = None
    states: List[Dict[str, Any]] = []
