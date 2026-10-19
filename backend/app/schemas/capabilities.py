from typing import List, Optional
from pydantic import BaseModel

class SystemCapabilities(BaseModel):
    ffmpeg_installed: bool
    ffmpeg_version: str
    ffprobe_version: str
    whisper_available: bool
    whisper_details: str
    llm_enabled: bool
    llm_provider: Optional[str] = None
    max_file_size_mb: float
    max_duration_seconds: float
    supported_formats: List[str]
    supported_operations: List[str]
