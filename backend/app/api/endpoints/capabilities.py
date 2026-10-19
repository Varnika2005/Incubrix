from fastapi import APIRouter
from app.core.config import settings
from app.schemas.capabilities import SystemCapabilities
from app.services.ffmpeg_finder import FFmpegFinder
from app.services.transcriber import Transcriber

router = APIRouter()

@router.get("/capabilities", response_model=SystemCapabilities)
def get_capabilities():
    ok, ffmpeg_ver, ffprobe_ver = FFmpegFinder.verify()
    whisper_ok, whisper_details = Transcriber.is_whisper_available()
    
    llm_enabled = bool(settings.GEMINI_API_KEY or settings.OPENAI_API_KEY)
    llm_provider = "Gemini" if settings.GEMINI_API_KEY else ("OpenAI" if settings.OPENAI_API_KEY else None)

    return SystemCapabilities(
        ffmpeg_installed=ok,
        ffmpeg_version=ffmpeg_ver,
        ffprobe_version=ffprobe_ver,
        whisper_available=whisper_ok,
        whisper_details=whisper_details,
        llm_enabled=llm_enabled,
        llm_provider=llm_provider,
        max_file_size_mb=round(settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024), 1),
        max_duration_seconds=settings.MAX_VIDEO_DURATION_SECONDS,
        supported_formats=sorted(list(settings.ALLOWED_EXTENSIONS)),
        supported_operations=[
            "Trim start segment",
            "Trim end segment",
            "Extract time slice (interval)",
            "Set target duration",
            "Convert aspect ratio (16:9, 9:16, 1:1) with fit/crop/pad",
            "Resolution scaling (720p, 1080p, 480p)",
            "Audio volume scaling & mute",
            "Brightness and contrast adjustment",
            "Silence detection & interactive removal",
            "Subtitle generation & burning"
        ]
    )
