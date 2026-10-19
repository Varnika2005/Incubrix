from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.edit_plan import EditPlan

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

class SilenceSegment(BaseModel):
    start: float
    end: float
    duration: float

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

class JobResponse(BaseModel):
    id: str
    status: JobStatus
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
    output_available: bool = False
    processing_time_seconds: Optional[float] = None
    user_id: Optional[str] = None
    is_demo: bool = False
