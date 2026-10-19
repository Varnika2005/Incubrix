import re
import subprocess
from pathlib import Path
from typing import List, Tuple
from app.services.ffmpeg_finder import FFmpegFinder
from app.services.media_inspector import inspect_media
from app.schemas.job import SilenceSegment

class SilenceDetector:
    """
    Detects silent pauses in video audio stream using FFmpeg silencedetect audio filter.
    """

    @classmethod
    def detect_silence(
        cls,
        video_path: str,
        threshold_db: float = -30.0,
        min_duration: float = 0.5
    ) -> List[SilenceSegment]:
        path = Path(video_path)
        if not path.is_file():
            return []

        # Check if file has audio
        try:
            meta = inspect_media(video_path)
            if not meta.has_audio:
                return []
        except Exception:
            return []

        ffmpeg_bin = FFmpegFinder.get_ffmpeg_path()
        # Ensure threshold has dB and is negative
        th = f"{threshold_db}dB" if not str(threshold_db).endswith("dB") else str(threshold_db)

        cmd = [
            ffmpeg_bin,
            "-i", str(path),
            "-af", f"silencedetect=noise={th}:d={min_duration}",
            "-f", "null",
            "-"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            stderr = res.stderr
        except Exception:
            return []

        segments: List[SilenceSegment] = []
        cur_start: float = 0.0

        for line in stderr.splitlines():
            # Match silence_start: 3.123
            start_m = re.search(r"silence_start:\s*([\d.]+)", line)
            if start_m:
                cur_start = float(start_m.group(1))

            # Match silence_end: 6.456 | silence_duration: 3.333
            end_m = re.search(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)", line)
            if end_m:
                end_val = float(end_m.group(1))
                dur_val = float(end_m.group(2))
                segments.append(SilenceSegment(
                    start=round(cur_start, 3),
                    end=round(end_val, 3),
                    duration=round(dur_val, 3)
                ))

        return segments
