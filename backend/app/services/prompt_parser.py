import re
from typing import List, Optional, Tuple, Dict, Any
from app.schemas.edit_plan import (
    EditPlan,
    OperationType,
    TrimStartOp,
    TrimEndOp,
    TimeSliceOp,
    TargetDurationOp,
    AspectRatioOp,
    ResolutionOp,
    AudioVolumeOp,
    ColorAdjustOp,
    SilenceRemovalOp,
    SubtitlesOp,
    ExportFormatOp,
)
from app.schemas.job import MediaMetadata

def parse_time_str(val: str) -> Optional[float]:
    """
    Parses time strings like '00:05', '1:23', '90s', '5.5 seconds', '10'.
    Returns float seconds or None.
    """
    val = val.strip().lower()
    
    # Format MM:SS or HH:MM:SS
    if ":" in val:
        parts = val.split(":")
        try:
            if len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except ValueError:
            return None

    # Format like 5s, 5.5s, 5 sec, 5 seconds
    m = re.match(r"^([\d.]+)\s*(?:s|sec|secs|seconds|second)?$", val)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
            
    return None

class PromptParser:
    """
    Deterministic rule-based and regex-driven Natural Language Editing Parser.
    Converts user instructions into a strongly validated, typed EditPlan.
    """

    SUPPORTED_CAPABILITIES = [
        "Trim opening (e.g., 'remove first 3 seconds')",
        "Trim ending (e.g., 'cut last 5s')",
        "Time slice (e.g., 'keep from 0:02 to 0:08')",
        "Aspect ratio (e.g., 'convert to 9:16 vertical' or '1:1 square' or '16:9 landscape')",
        "Resolution (e.g., 'export at 1080p' or '720p')",
        "Audio volume (e.g., 'increase volume by 50%' or 'mute audio')",
        "Brightness / Contrast (e.g., 'increase brightness' or 'boost contrast')",
        "Silence removal (e.g., 'remove silent pauses')",
        "Subtitles / Captions (e.g., 'generate and burn subtitles')",
    ]

    @classmethod
    def parse(cls, prompt: str, metadata: Optional[MediaMetadata] = None) -> EditPlan:
        clean_prompt = prompt.strip()
        lower_prompt = clean_prompt.lower()
        
        operations: List[dict] = []
        warnings: List[str] = []
        requires_confirmation = False
        confirmation_reason: Optional[str] = None
        suggested_repair: Optional[str] = None
        
        # 0. Prompt Injection / Malicious pattern check
        malicious_patterns = [
            r"[;&|]\s*(?:rm|del|erase|format|bash|sh|cmd|powershell|curl|wget|python|drop|exec|eval)\b",
            r"--exec\b",
            r"format\s+[a-z]:",
            r"<script",
            r"DROP\s+TABLE",
            r"\brm\s+-rf\b",
            r"&&\s*rm\b",
            r"&&\s*del\b"
        ]
        for pat in malicious_patterns:
            if re.search(pat, clean_prompt, re.IGNORECASE):
                return EditPlan(
                    prompt=clean_prompt,
                    operations=[],
                    warnings=["Potentially unsafe prompt syntax detected and rejected."],
                    requires_confirmation=False,
                    suggested_repair="Please use natural language video editing commands such as 'Trim the first 3 seconds and convert to 9:16 vertical'."
                )

        # 1. Trimming Beginning
        # Match 'remove the first 5 seconds', 'cut first 3s', 'skip opening 4 seconds', 'discard first 2.5 sec'
        # Crucial distinction: 'keep the first 5 seconds' means slice 0 to 5!
        keep_first_match = re.search(r"\bkeep\s+(?:the\s+)?first\s+([\d.]+)\s*(?:s|sec|seconds)?\b", lower_prompt)
        if keep_first_match:
            keep_sec = float(keep_first_match.group(1))
            op = TimeSliceOp(
                description=f"Keep the first {keep_sec} seconds (extract 0.0s to {keep_sec}s)",
                start_time=0.0,
                end_time=keep_sec
            )
            operations.append(op.model_dump())
        else:
            trim_start_match = re.search(
                r"\b(?:remove|cut|trim|skip|discard|delete)\s+(?:the\s+)?(?:first|opening|beginning|initial)\s+([\d.]+)\s*(?:s|sec|seconds)?\b",
                lower_prompt
            )
            if trim_start_match:
                sec = float(trim_start_match.group(1))
                if sec <= 0:
                    warnings.append(f"Trim start must be greater than 0s (got {sec}s). Ignored.")
                else:
                    op = TrimStartOp(
                        description=f"Trim the first {sec} seconds from the video",
                        seconds=sec
                    )
                    operations.append(op.model_dump())

        # 2. Trimming Ending
        # 'cut last 5 seconds', 'remove ending 3s', 'trim the last 4 seconds'
        # Crucial distinction: 'keep the last 5 seconds'
        keep_last_match = re.search(r"\bkeep\s+(?:the\s+)?last\s+([\d.]+)\s*(?:s|sec|seconds)?\b", lower_prompt)
        if keep_last_match and metadata and metadata.duration > 0:
            k_sec = float(keep_last_match.group(1))
            st = max(0.0, metadata.duration - k_sec)
            op = TimeSliceOp(
                description=f"Keep the last {k_sec} seconds (extract {st}s to {metadata.duration}s)",
                start_time=st,
                end_time=metadata.duration
            )
            operations.append(op.model_dump())
        else:
            trim_end_match = re.search(
                r"\b(?:remove|cut|trim|discard|delete)\s+(?:the\s+)?(?:last|final|ending)\s+([\d.]+)\s*(?:s|sec|seconds)?\b",
                lower_prompt
            )
            if trim_end_match:
                sec = float(trim_end_match.group(1))
                if sec <= 0:
                    warnings.append(f"Trim end must be greater than 0s (got {sec}s). Ignored.")
                else:
                    op = TrimEndOp(
                        description=f"Trim the last {sec} seconds from the video",
                        seconds=sec
                    )
                    operations.append(op.model_dump())

        # 3. Time Slicing / Range Extraction
        # 'keep from 00:02 to 00:08', 'slice from 2 to 8 seconds', 'extract between 2 and 8 seconds'
        range_match = re.search(
            r"\b(?:keep|extract|slice|cut\s+from|trim\s+from)\s+(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            lower_prompt
        )
        if range_match:
            t1 = parse_time_str(range_match.group(1))
            t2 = parse_time_str(range_match.group(2))
            if t1 is not None and t2 is not None:
                if t1 < 0 or t2 < 0:
                    warnings.append("Timestamps cannot be negative.")
                elif t1 >= t2:
                    warnings.append(f"Invalid range: start timestamp ({t1}s) is greater than or equal to end timestamp ({t2}s).")
                    requires_confirmation = True
                    confirmation_reason = "Range start is after or equal to range end."
                else:
                    op = TimeSliceOp(
                        description=f"Extract video segment between {t1}s and {t2}s",
                        start_time=t1,
                        end_time=t2
                    )
                    operations.append(op.model_dump())

        # 4. Target Duration
        # 'make it 10 seconds long', 'shorten to 15s', 'limit duration to 30 seconds'
        duration_match = re.search(
            r"\b(?:make\s+it|shorten\s+to|limit\s+to|set\s+duration\s+to|output\s+length\s+of)\s+([\d.]+)\s*(?:s|sec|seconds)\b",
            lower_prompt
        )
        if duration_match and not any(op["type"] == OperationType.TIME_SLICE for op in operations):
            target_sec = float(duration_match.group(1))
            if metadata and metadata.duration > 0 and target_sec > metadata.duration:
                warnings.append(f"Requested duration ({target_sec}s) exceeds source video length ({metadata.duration}s). Will preserve full source video.")
            elif target_sec <= 0:
                warnings.append("Target duration must be positive.")
            else:
                op = TargetDurationOp(
                    description=f"Set video duration to {target_sec} seconds (extract opening segment)",
                    target_seconds=target_sec
                )
                operations.append(op.model_dump())

        # 5. Aspect Ratio Conversion
        # 'convert to 9:16 vertical', 'make it vertical', 'format for instagram reel / tiktok / shorts'
        # 'change to 16:9 landscape', 'make it square 1:1'
        if any(w in lower_prompt for w in ["9:16", "vertical", "reel", "reels", "tiktok", "shorts", "portrait", "story", "stories"]):
            mode = "pad" if "pad" in lower_prompt or "fit" in lower_prompt else "crop"
            op = AspectRatioOp(
                description=f"Convert to 9:16 Portrait (Reel/TikTok/Shorts format) with {mode} mode",
                ratio="9:16",
                mode=mode
            )
            operations.append(op.model_dump())
        elif any(w in lower_prompt for w in ["1:1", "square", "instagram post"]):
            mode = "pad" if "pad" in lower_prompt or "fit" in lower_prompt else "crop"
            op = AspectRatioOp(
                description=f"Convert to 1:1 Square (Instagram post format) with {mode} mode",
                ratio="1:1",
                mode=mode
            )
            operations.append(op.model_dump())
        elif any(w in lower_prompt for w in ["16:9", "landscape", "youtube landscape", "widescreen"]):
            mode = "pad" if "pad" in lower_prompt or "fit" in lower_prompt else "crop"
            op = AspectRatioOp(
                description=f"Convert to 16:9 Landscape (YouTube standard) with {mode} mode",
                ratio="16:9",
                mode=mode
            )
            operations.append(op.model_dump())

        # 6. Resolution Conversion
        # 'export at 1080p', '1080p', 'full hd', '720p', 'hd'
        if "1080p" in lower_prompt or "full hd" in lower_prompt or "fhd" in lower_prompt:
            op = ResolutionOp(
                description="Standardize output resolution to 1080p Full HD",
                standard="1080p"
            )
            operations.append(op.model_dump())
        elif "720p" in lower_prompt or "hd 720" in lower_prompt:
            op = ResolutionOp(
                description="Standardize output resolution to 720p HD",
                standard="720p"
            )
            operations.append(op.model_dump())
        elif "480p" in lower_prompt or "sd" in lower_prompt:
            op = ResolutionOp(
                description="Standardize output resolution to 480p SD",
                standard="480p"
            )
            operations.append(op.model_dump())

        # 7. Audio Volume Adjustment
        # 'mute', 'mute audio', 'remove audio'
        if "mute" in lower_prompt or "silence audio" in lower_prompt or "remove audio" in lower_prompt:
            op = AudioVolumeOp(
                description="Mute audio track completely",
                volume_percent=0.0,
                mute=True
            )
            operations.append(op.model_dump())
        else:
            # 'increase volume by 50%', 'double the volume', 'set volume to 150%', 'reduce volume to 50%'
            vol_match = re.search(r"\b(?:volume|audio)\s*(?:is|to|by|at|up\s*to)?\s*([\d.]+)\s*%", lower_prompt)
            if not vol_match:
                vol_match = re.search(r"\b(?:increase|decrease|boost|lower|raise|set)\s+(?:the\s+)?(?:volume|audio)\s*(?:to|by|at)?\s*([\d.]+)\s*%", lower_prompt)
            if vol_match:
                pct = float(vol_match.group(1))
                op = AudioVolumeOp(
                    description=f"Adjust audio volume to {pct}%",
                    volume_percent=pct,
                    mute=(pct == 0.0)
                )
                operations.append(op.model_dump())
            elif "double the volume" in lower_prompt or "boost audio" in lower_prompt or "make it louder" in lower_prompt:
                op = AudioVolumeOp(
                    description="Boost audio volume to 200%",
                    volume_percent=200.0,
                    mute=False
                )
                operations.append(op.model_dump())
            elif "half the volume" in lower_prompt or "lower audio" in lower_prompt or "reduce volume" in lower_prompt:
                op = AudioVolumeOp(
                    description="Reduce audio volume to 50%",
                    volume_percent=50.0,
                    mute=False
                )
                operations.append(op.model_dump())

        # 8. Visual / Color Adjustments
        # 'make it brighter', 'increase brightness', 'darken', 'increase contrast'
        brightness = 0.0
        contrast = 1.0
        has_color = False

        if "brighter" in lower_prompt or "increase brightness" in lower_prompt:
            brightness = 0.15
            has_color = True
        elif "darker" in lower_prompt or "decrease brightness" in lower_prompt:
            brightness = -0.15
            has_color = True
            
        if "increase contrast" in lower_prompt or "high contrast" in lower_prompt or "boost contrast" in lower_prompt:
            contrast = 1.3
            has_color = True
        elif "decrease contrast" in lower_prompt or "lower contrast" in lower_prompt:
            contrast = 0.8
            has_color = True

        if has_color:
            op = ColorAdjustOp(
                description=f"Adjust colors: Brightness={brightness:+.2f}, Contrast={contrast:.2f}x",
                brightness=brightness,
                contrast=contrast
            )
            operations.append(op.model_dump())

        # 9. Silence Removal / Review
        if any(w in lower_prompt for w in ["silence", "silent pauses", "dead air", "remove pauses", "cut pauses"]):
            op = SilenceRemovalOp(
                description="Detect and remove silent segments (< -30dB, >= 0.5s)",
                threshold_db=-30.0,
                min_duration=0.5,
                confirmed_intervals=[]
            )
            operations.append(op.model_dump())
            requires_confirmation = True
            confirmation_reason = "Silence cut review recommended before deletion."

        # 10. Subtitles & Captions
        if any(w in lower_prompt for w in ["subtitle", "subtitles", "caption", "captions", "transcribe"]):
            burn = True
            op = SubtitlesOp(
                description="Generate timestamped subtitles and burn into exported video",
                burn=burn,
                language="en",
                style="bold_yellow_banner"
            )
            operations.append(op.model_dump())

        # 11. Format / Export
        op_export = ExportFormatOp(
            description="Export standard Web-Optimized MP4 (H.264 / AAC)",
            format="mp4",
            video_codec="libx264",
            audio_codec="aac"
        )
        operations.append(op_export.model_dump())

        # 12. Contradiction & Ambiguity Detection
        # Check contradictory trim vs slice
        has_trim = any(op["type"] in [OperationType.TRIM_START, OperationType.TRIM_END] for op in operations)
        has_slice = any(op["type"] in [OperationType.TIME_SLICE, OperationType.TARGET_DURATION] for op in operations)
        if has_trim and has_slice:
            warnings.append("Both incremental trim and absolute time-slice were requested. Time-slice takes precedence.")

        # Check source duration bounds if metadata is provided
        if metadata and metadata.duration > 0:
            for op in operations:
                if op["type"] == OperationType.TRIM_START:
                    if op["seconds"] >= metadata.duration:
                        warnings.append(f"Trim start ({op['seconds']}s) is greater than total duration ({metadata.duration}s).")
                        requires_confirmation = True
                        confirmation_reason = "Trim start exceeds video length."
                elif op["type"] == OperationType.TRIM_END:
                    if op["seconds"] >= metadata.duration:
                        warnings.append(f"Trim end ({op['seconds']}s) is greater than total duration ({metadata.duration}s).")
                        requires_confirmation = True
                        confirmation_reason = "Trim end exceeds video length."
                elif op["type"] == OperationType.TIME_SLICE:
                    if op["end_time"] > metadata.duration:
                        warnings.append(f"Slice end ({op['end_time']}s) exceeds video duration ({metadata.duration}s). Capped to {metadata.duration}s.")
                        op["end_time"] = metadata.duration

        # 13. Unrecognized or Unsupported Prompt Check
        # If only the default ExportFormat operation was identified
        if len(operations) == 1 and operations[0]["type"] == OperationType.EXPORT_FORMAT:
            unsupported_phrases = ["slow motion", "reverse video", "3d effect", "generate new scene", "ai face swap", "greenscreen replacement"]
            found_unsupported = next((u for u in unsupported_phrases if u in lower_prompt), None)
            
            if found_unsupported:
                warnings.append(f"'{found_unsupported}' is currently unsupported. ClipPilot focuses on deterministic trimming, aspect ratio conversion, volume, silence removal, and subtitle burning.")
                suggested_repair = "Try: 'Trim the first 3 seconds, convert to 9:16 vertical, and boost volume by 50%'."
            else:
                warnings.append("Could not confidently identify any editing commands from your prompt.")
                suggested_repair = "Try: 'Cut first 2 seconds, convert to 9:16 vertical, and add subtitles'."
                requires_confirmation = True
                confirmation_reason = "Prompt did not match any supported video editing action."

        # Estimate duration if possible
        est_duration = metadata.duration if metadata else None
        if est_duration:
            for op in operations:
                if op["type"] == OperationType.TIME_SLICE:
                    est_duration = max(0.1, op["end_time"] - op["start_time"])
                elif op["type"] == OperationType.TARGET_DURATION:
                    est_duration = min(est_duration, op["target_seconds"])
                elif op["type"] == OperationType.TRIM_START:
                    est_duration = max(0.1, est_duration - op["seconds"])
                elif op["type"] == OperationType.TRIM_END:
                    est_duration = max(0.1, est_duration - op["seconds"])

        return EditPlan(
            prompt=clean_prompt,
            operations=operations,
            warnings=warnings,
            requires_confirmation=requires_confirmation,
            confirmation_reason=confirmation_reason,
            suggested_repair=suggested_repair,
            estimated_duration=round(est_duration, 2) if est_duration else None
        )
