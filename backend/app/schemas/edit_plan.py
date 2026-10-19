from enum import Enum
from typing import List, Optional, Literal, Tuple
from pydantic import BaseModel, Field

class OperationType(str, Enum):
    TRIM_START = "trim_start"
    TRIM_END = "trim_end"
    TIME_SLICE = "time_slice"
    TARGET_DURATION = "target_duration"
    ASPECT_RATIO = "aspect_ratio"
    RESOLUTION = "resolution"
    AUDIO_VOLUME = "audio_volume"
    COLOR_ADJUST = "color_adjust"
    SILENCE_REMOVAL = "silence_removal"
    SUBTITLES = "subtitles"
    EXPORT_FORMAT = "export_format"

class BaseOperation(BaseModel):
    type: OperationType
    description: str = Field(..., description="Human-readable explanation of this step")
    parameters: dict = Field(default_factory=dict, description="Raw parameters dictionary for flexibility")

class TrimStartOp(BaseOperation):
    type: Literal[OperationType.TRIM_START] = OperationType.TRIM_START
    seconds: float = Field(..., ge=0.0, description="Seconds to discard from video start")

class TrimEndOp(BaseOperation):
    type: Literal[OperationType.TRIM_END] = OperationType.TRIM_END
    seconds: float = Field(..., ge=0.0, description="Seconds to discard from video end")

class TimeSliceOp(BaseOperation):
    type: Literal[OperationType.TIME_SLICE] = OperationType.TIME_SLICE
    start_time: float = Field(..., ge=0.0, description="Start timestamp in seconds")
    end_time: float = Field(..., gt=0.0, description="End timestamp in seconds")

class TargetDurationOp(BaseOperation):
    type: Literal[OperationType.TARGET_DURATION] = OperationType.TARGET_DURATION
    target_seconds: float = Field(..., gt=0.0, description="Desired total output duration in seconds")

class AspectRatioOp(BaseOperation):
    type: Literal[OperationType.ASPECT_RATIO] = OperationType.ASPECT_RATIO
    ratio: Literal["16:9", "9:16", "1:1"] = Field(..., description="Target aspect ratio")
    mode: Literal["fit", "crop", "pad"] = Field(default="crop", description="Fitting strategy")

class ResolutionOp(BaseOperation):
    type: Literal[OperationType.RESOLUTION] = OperationType.RESOLUTION
    standard: Literal["720p", "1080p", "480p", "source"] = Field("1080p", description="Standard resolution")
    target_width: Optional[int] = None
    target_height: Optional[int] = None

class AudioVolumeOp(BaseOperation):
    type: Literal[OperationType.AUDIO_VOLUME] = OperationType.AUDIO_VOLUME
    volume_percent: float = Field(default=100.0, ge=0.0, le=400.0, description="Volume percentage (100 = unchanged)")
    mute: bool = False

class ColorAdjustOp(BaseOperation):
    type: Literal[OperationType.COLOR_ADJUST] = OperationType.COLOR_ADJUST
    brightness: float = Field(default=0.0, ge=-1.0, le=1.0, description="Brightness offset [-1.0 to 1.0]")
    contrast: float = Field(default=1.0, ge=0.0, le=3.0, description="Contrast multiplier [0.0 to 3.0]")

class SilenceRemovalOp(BaseOperation):
    type: Literal[OperationType.SILENCE_REMOVAL] = OperationType.SILENCE_REMOVAL
    threshold_db: float = Field(default=-30.0, le=0.0, description="Volume silence threshold in dB")
    min_duration: float = Field(default=0.5, gt=0.0, description="Minimum silence duration in seconds to trigger cut")
    confirmed_intervals: List[Tuple[float, float]] = Field(default_factory=list, description="Approved [start, end] cuts")

class SubtitlesOp(BaseOperation):
    type: Literal[OperationType.SUBTITLES] = OperationType.SUBTITLES
    burn: bool = True
    language: str = "en"
    style: str = "bold_yellow_banner"
    custom_text: Optional[str] = None

class ExportFormatOp(BaseOperation):
    type: Literal[OperationType.EXPORT_FORMAT] = OperationType.EXPORT_FORMAT
    format: str = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"

class EditPlan(BaseModel):
    prompt: str = Field(..., description="Original user prompt")
    operations: List[dict] = Field(default_factory=list, description="Ordered list of validated operations")
    warnings: List[str] = Field(default_factory=list, description="Potential issues, quality warnings, or notes")
    requires_confirmation: bool = False
    confirmation_reason: Optional[str] = None
    suggested_repair: Optional[str] = None
    estimated_duration: Optional[float] = None
    estimated_dimensions: Optional[Tuple[int, int]] = None
