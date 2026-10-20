import json
import math
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from app.services.ffmpeg_finder import FFmpegFinder
from app.schemas.job import MediaMetadata

class MediaInspectionError(Exception):
    pass

def calculate_aspect_ratio_str(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "unknown"
    
    # Calculate float ratio
    ratio = width / height
    if abs(ratio - (16.0 / 9.0)) < 0.05:
        return "16:9"
    elif abs(ratio - (9.0 / 16.0)) < 0.05:
        return "9:16"
    elif abs(ratio - 1.0) < 0.05:
        return "1:1"
    elif abs(ratio - (4.0 / 3.0)) < 0.05:
        return "4:3"
    elif abs(ratio - (21.0 / 9.0)) < 0.05:
        return "21:9"
    
    # Otherwise GCD
    common = math.gcd(width, height)
    if common > 0:
        return f"{width // common}:{height // common}"
    return f"{width}:{height}"

def parse_frame_rate(fps_str: str) -> float:
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/", 1)
            denominator = float(den)
            return round(float(num) / denominator, 2) if denominator != 0 else 0.0
        return round(float(fps_str), 2)
    except Exception:
        return 0.0

def inspect_media(file_path: str) -> MediaMetadata:
    """
    Inspects media file via FFprobe subprocess array and returns structured MediaMetadata.
    Raises MediaInspectionError on unreadable, corrupt, or missing files.
    """
    path = Path(file_path)
    if not path.is_file():
        raise MediaInspectionError(f"File not found: {file_path}")

    ffprobe_bin = FFmpegFinder.get_ffprobe_path()
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration,size,format_name",
        "-show_entries", "stream=index,codec_type,codec_name,width,height,r_frame_rate,channels",
        "-of", "json",
        str(path)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            err = result.stderr.strip() or "FFprobe exited with non-zero status"
            raise MediaInspectionError(f"Failed to inspect media: {err}")
        
        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise MediaInspectionError("Media inspection timed out")
    except json.JSONDecodeError as e:
        raise MediaInspectionError(f"Failed to parse FFprobe JSON: {str(e)}")
    except Exception as e:
        raise MediaInspectionError(f"Media inspection error: {str(e)}")

    format_info = data.get("format", {})
    streams = data.get("streams", [])

    duration_str = format_info.get("duration")
    try:
        duration = float(duration_str) if duration_str else 0.0
    except ValueError:
        duration = 0.0

    size_bytes = 0
    try:
        size_bytes = int(format_info.get("size", path.stat().st_size))
    except Exception:
        size_bytes = path.stat().st_size if path.exists() else 0

    format_name = format_info.get("format_name", "unknown")

    # Find video and audio streams
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    width = 0
    height = 0
    fps = 0.0
    video_codec = "none"

    if video_stream:
        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        fps = parse_frame_rate(video_stream.get("r_frame_rate", "0"))
        video_codec = video_stream.get("codec_name", "unknown")

    has_audio = audio_stream is not None
    audio_codec = audio_stream.get("codec_name") if audio_stream else None

    aspect_ratio = calculate_aspect_ratio_str(width, height)

    return MediaMetadata(
        duration=round(duration, 3),
        width=width,
        height=height,
        aspect_ratio=aspect_ratio,
        fps=fps,
        video_codec=video_codec,
        audio_codec=audio_codec,
        has_audio=has_audio,
        size_bytes=size_bytes,
        format_name=format_name
    )


def inspect_av_sync(file_path: str) -> Dict[str, Any]:
    """
    Detailed FFprobe inspection measuring:
    - video stream duration and start_time
    - audio stream duration and start_time
    - format duration
    - frame rate and frame count
    - audio-to-video skew in seconds and video frames
    - boolean flag confirming alignment within one frame
    """
    path = Path(file_path)
    if not path.is_file():
        raise MediaInspectionError(f"File not found: {file_path}")

    ffprobe_bin = FFmpegFinder.get_ffprobe_path()
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-show_entries", "stream=index,codec_type,duration,start_time,nb_frames,r_frame_rate",
        "-of", "json",
        str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise MediaInspectionError(f"FFprobe failed: {result.stderr}")
    data = json.loads(result.stdout)
    format_dur = float(data.get("format", {}).get("duration", 0.0))
    streams = data.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    v_dur = float(v_stream.get("duration", format_dur)) if v_stream else 0.0
    v_start = float(v_stream.get("start_time", 0.0)) if v_stream else 0.0
    v_frames = int(v_stream.get("nb_frames") or 0) if v_stream else 0
    fps = parse_frame_rate(v_stream.get("r_frame_rate", "30/1")) if v_stream else 30.0
    if fps <= 0:
        fps = 30.0
    frame_dur = 1.0 / fps

    a_dur = float(a_stream.get("duration", format_dur)) if a_stream else None
    a_start = float(a_stream.get("start_time", 0.0)) if a_stream else None

    # Calculate skew
    av_skew = abs(v_dur - a_dur) if a_dur is not None else 0.0
    skew_frames = av_skew / frame_dur if a_dur is not None else 0.0

    return {
        "file_path": str(path),
        "format_duration": format_dur,
        "video_duration": v_dur,
        "video_start_time": v_start,
        "video_frames": v_frames,
        "fps": fps,
        "frame_duration": frame_dur,
        "has_audio": a_stream is not None,
        "audio_duration": a_dur,
        "audio_start_time": a_start,
        "av_skew_seconds": round(av_skew, 6),
        "av_skew_frames": round(skew_frames, 4),
        "is_aligned_within_one_frame": skew_frames <= 1.0
    }
