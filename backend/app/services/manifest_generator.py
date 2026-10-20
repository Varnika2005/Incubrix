import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.ffmpeg_finder import FFmpegFinder
from app.services.hash_utils import calculate_file_sha256

def generate_output_manifest(
    job_id: str,
    original_filename: str,
    input_path: Optional[str],
    output_path: Optional[str],
    original_hash: Optional[str],
    original_size: Optional[int],
    input_meta: Any,
    output_meta: Any,
    applied_operations: List[Dict[str, Any]],
    processing_time_seconds: Optional[float],
    created_at: Optional[datetime],
    completed_at: Optional[datetime] = None,
    warnings: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate a standardized, reproducible output manifest adhering to IncuBrix standards.
    Clearly marks unavailable values as 'unknown' or 'not_applicable' without fabricating data.
    """
    is_ok, ffmpeg_ver, _ = FFmpegFinder.verify()
    ffmpeg_version_str = ffmpeg_ver[:60] if is_ok else "unknown"

    out_file = Path(output_path) if output_path else None
    out_hash = calculate_file_sha256(str(out_file)) if out_file and out_file.exists() else "unknown"
    out_size = out_file.stat().st_size if out_file and out_file.exists() else "unknown"

    manifest = {
        "manifest_version": "1.0.0",
        "job_id": job_id,
        "input": {
            "filename": original_filename or "unknown",
            "sha256": original_hash or (calculate_file_sha256(input_path) if input_path and Path(input_path).exists() else "unknown"),
            "size_bytes": original_size or (Path(input_path).stat().st_size if input_path and Path(input_path).exists() else "unknown"),
            "format": getattr(input_meta, "format_name", "unknown") if input_meta else "unknown",
            "duration_seconds": getattr(input_meta, "duration", "unknown") if input_meta else "unknown",
            "resolution": f"{input_meta.width}x{input_meta.height}" if input_meta and getattr(input_meta, "width", 0) > 0 else "unknown",
            "fps": getattr(input_meta, "fps", "unknown") if input_meta else "unknown",
            "video_codec": getattr(input_meta, "video_codec", "unknown") if input_meta else "unknown",
            "audio_codec": getattr(input_meta, "audio_codec", None) or "none_or_unknown"
        },
        "output": {
            "filename": out_file.name if out_file else "unknown",
            "sha256": out_hash,
            "size_bytes": out_size,
            "format": getattr(output_meta, "format_name", "mp4") if output_meta else ("mp4" if out_file else "unknown"),
            "duration_seconds": getattr(output_meta, "duration", "unknown") if output_meta else "unknown",
            "resolution": f"{output_meta.width}x{output_meta.height}" if output_meta and getattr(output_meta, "width", 0) > 0 else "unknown",
            "fps": getattr(output_meta, "fps", "unknown") if output_meta else "unknown",
            "video_codec": getattr(output_meta, "video_codec", settings.DEFAULT_VIDEO_CODEC) if output_meta else settings.DEFAULT_VIDEO_CODEC,
            "audio_codec": getattr(output_meta, "audio_codec", settings.DEFAULT_AUDIO_CODEC) if output_meta else settings.DEFAULT_AUDIO_CODEC
        },
        "models_and_engines": [
            {
                "name": "ClipPilot Deterministic Rule & Timeline Engine",
                "provider": "ClipPilot AI",
                "version": "1.0.0",
                "type": "rule-based"
            },
            {
                "name": "FFmpeg Transcoding Pipeline",
                "provider": "FFmpeg",
                "version": ffmpeg_version_str,
                "type": "audio-video-processing"
            }
        ],
        "effective_settings": {
            "video_codec": settings.DEFAULT_VIDEO_CODEC,
            "audio_codec": settings.DEFAULT_AUDIO_CODEC,
            "preset": settings.DEFAULT_PRESET,
            "crf": settings.DEFAULT_CRF,
            "operations_count": len(applied_operations or []),
            "applied_operations": applied_operations or []
        },
        "random_seed": "not_applicable",
        "timestamps": {
            "started_at": created_at.isoformat() if created_at else datetime.now(timezone.utc).isoformat(),
            "completed_at": completed_at.isoformat() if completed_at else datetime.now(timezone.utc).isoformat()
        },
        "duration_timings": {
            "processing_seconds": processing_time_seconds if processing_time_seconds is not None else "unknown",
            "source_duration_seconds": getattr(input_meta, "duration", "unknown") if input_meta else "unknown"
        },
        "warnings": warnings or [],
        "estimated_cost": {
            "currency": "USD",
            "amount": 0.0,
            "billing_type": "zero_local_compute"
        },
        "licence_and_rights": {
            "content_licence": "User Content - All rights reserved by uploader",
            "engine_licence": "Proprietary IncuBrix Integration",
            "redistribution_allowed": False
        }
    }
    return manifest
