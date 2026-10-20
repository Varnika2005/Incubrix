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
from app.services.timeline_model import Timeline


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
    Converts user instructions into a strongly validated, typed EditPlan with
    content-aware timeline transformations.
    """

    SUPPORTED_CAPABILITIES = [
        "Trim opening (e.g., 'remove first 3 seconds')",
        "Trim ending (e.g., 'cut last 5s')",
        "Time slice (e.g., 'keep from 0:02 to 0:08')",
        "Internal cut (e.g., 'cut out from 2s to 4s')",
        "Speed changes (e.g., 'speed up 2x' or 'slow motion 0.5x')",
        "Clip reordering (e.g., 'swap clips' or 'reorder clips [1, 0]')",
        "Content-anchored captions (e.g., 'add caption \"Intro\" from 1s to 3s')",
        "Mute ranges (e.g., 'mute audio from 2s to 4s')",
        "Beep effects (e.g., 'beep audio from 3s to 5s' or 'censor 3s to 5s')",
        "Visual effects (e.g., 'apply blur from 2s to 4s')",
        "Aspect ratio (e.g., 'convert to 9:16 vertical' or '1:1 square')",
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

        # 3. Content-Aware Internal Cut
        cut_out_match = re.search(
            r"\b(?:cut\s+out|excise|delete\s+between|remove\s+between)\s+(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            lower_prompt
        )
        if cut_out_match:
            c1 = parse_time_str(cut_out_match.group(1))
            c2 = parse_time_str(cut_out_match.group(2))
            if c1 is not None and c2 is not None and c1 < c2:
                operations.append({
                    "type": OperationType.CUT.value,
                    "description": f"Cut out internal section from {c1}s to {c2}s",
                    "cut_start": c1,
                    "cut_end": c2,
                    "parameters": {"cut_start": c1, "cut_end": c2}
                })

        # 4. Time Slicing / Range Extraction
        range_match = re.search(
            r"\b(?:keep|extract|slice|cut\s+from|trim\s+from)\s+(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            lower_prompt
        )
        if range_match and not cut_out_match:
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

        # 5. Target Duration
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

        # 6. Playback Speed Change
        speed_match = re.search(r"\b(?:speed\s+up|speed|playback\s+speed|play\s+at)\s+(?:to\s+|by\s+)?([\d.]+)x?\b", lower_prompt)
        if not speed_match:
            speed_match = re.search(r"\b([\d.]+)x\s+(?:playback\s+)?speed\b", lower_prompt)
        slow_mo_match = re.search(r"\b(?:slow\s*motion|slowmo|slow-mo)\s*(?:at\s+|to\s+)?([\d.]*)x?\b", lower_prompt)

        if speed_match:
            try:
                spd_val = float(speed_match.group(1))
                if 0.1 <= spd_val <= 10.0:
                    operations.append({
                        "type": OperationType.SPEED.value,
                        "description": f"Adjust playback speed to {spd_val}x",
                        "speed": spd_val,
                        "parameters": {"speed": spd_val}
                    })
            except ValueError:
                pass
        elif slow_mo_match:
            val_str = slow_mo_match.group(1)
            spd_val = float(val_str) if val_str else 0.5
            operations.append({
                "type": OperationType.SPEED.value,
                "description": f"Apply slow motion effect ({spd_val}x speed)",
                "speed": spd_val,
                "parameters": {"speed": spd_val}
            })

        # 7. Clip Reordering
        reorder_match = re.search(r"\b(?:reorder\s+clips|reorder\s+segments)\s*(?:to\s+)?\[?([0-9,\s]+)\]?\b", lower_prompt)
        if reorder_match:
            try:
                order_list = [int(x.strip()) for x in reorder_match.group(1).split(",") if x.strip()]
                if order_list:
                    operations.append({
                        "type": OperationType.REORDER.value,
                        "description": f"Reorder segments to sequence {order_list}",
                        "order": order_list,
                        "parameters": {"order": order_list}
                    })
            except Exception:
                pass
        elif "swap clips" in lower_prompt or "swap segments" in lower_prompt:
            operations.append({
                "type": OperationType.REORDER.value,
                "description": "Swap first and second segments [1, 0]",
                "order": [1, 0],
                "parameters": {"order": [1, 0]}
            })

        # 8. Content-Aware Captions with Source Time Anchors
        caption_range_match = re.search(
            r"\b(?:add\s+)?caption\s+[\"']([^\"']+)[\"']\s+(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            clean_prompt,
            re.IGNORECASE
        )
        if caption_range_match:
            cap_text = caption_range_match.group(1)
            c_st = parse_time_str(caption_range_match.group(2))
            c_et = parse_time_str(caption_range_match.group(3))
            if c_st is not None and c_et is not None and c_st < c_et:
                operations.append({
                    "type": OperationType.CAPTION.value,
                    "description": f"Add caption \"{cap_text}\" anchored to source {c_st:.2f}s - {c_et:.2f}s",
                    "source_start": c_st,
                    "source_end": c_et,
                    "parameters": {"text": cap_text},
                    "label": f"Caption: \"{cap_text}\""
                })

        # 9. Content-Aware Mute Range
        mute_range_match = re.search(
            r"\bmute\s+(?:audio\s+)?(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            lower_prompt
        )
        if mute_range_match:
            m_st = parse_time_str(mute_range_match.group(1))
            m_et = parse_time_str(mute_range_match.group(2))
            if m_st is not None and m_et is not None and m_st < m_et:
                operations.append({
                    "type": OperationType.MUTE_RANGE.value,
                    "description": f"Mute audio between {m_st:.2f}s and {m_et:.2f}s",
                    "source_start": m_st,
                    "source_end": m_et,
                    "parameters": {},
                    "label": f"Mute Range ({m_st:.2f}s - {m_et:.2f}s)"
                })

        # 10. Content-Aware Beep / Censor Effect
        beep_range_match = re.search(
            r"\b(?:beep|bleep|censor)\s+(?:audio\s+)?(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            lower_prompt
        )
        if beep_range_match:
            b_st = parse_time_str(beep_range_match.group(1))
            b_et = parse_time_str(beep_range_match.group(2))
            if b_st is not None and b_et is not None and b_st < b_et:
                operations.append({
                    "type": OperationType.BEEP.value,
                    "description": f"Beep / censor audio between {b_st:.2f}s and {b_et:.2f}s",
                    "source_start": b_st,
                    "source_end": b_et,
                    "parameters": {"frequency": 1000},
                    "label": f"Beep / Censor ({b_st:.2f}s - {b_et:.2f}s)"
                })

        # 11. Content-Aware Visual Effect with Range
        vfx_range_match = re.search(
            r"\b(?:apply\s+)?(blur|invert|grayscale|brightness\s+boost|darken)\s+(?:video\s+)?(?:from\s+|between\s+)?([0-9:.]+)\s*(?:s|sec|seconds)?\s*(?:to|and|-)\s*([0-9:.]+)\s*(?:s|sec|seconds)?\b",
            lower_prompt
        )
        if vfx_range_match:
            v_effect = vfx_range_match.group(1).replace(" ", "_")
            v_st = parse_time_str(vfx_range_match.group(2))
            v_et = parse_time_str(vfx_range_match.group(3))
            if v_st is not None and v_et is not None and v_st < v_et:
                vfx_params = {"effect": v_effect}
                if "brightness" in v_effect:
                    vfx_params["brightness"] = 0.25
                elif "darken" in v_effect:
                    vfx_params["brightness"] = -0.25
                operations.append({
                    "type": OperationType.VISUAL_EFFECT.value,
                    "description": f"Apply {v_effect} effect between {v_st:.2f}s and {v_et:.2f}s",
                    "source_start": v_st,
                    "source_end": v_et,
                    "parameters": vfx_params,
                    "label": f"Visual: {v_effect.title()} ({v_st:.2f}s - {v_et:.2f}s)"
                })

        # 12. Aspect Ratio Conversion
        if any(w in lower_prompt for w in ["9:16", "vertical", "reel", "reels", "tiktok", "shorts"]):
            op = AspectRatioOp(
                description="Convert to 9:16 vertical format (optimized for Reels / TikTok / Shorts)",
                ratio="9:16",
                mode="crop"
            )
            operations.append(op.model_dump())
        elif any(w in lower_prompt for w in ["1:1", "square", "instagram post"]):
            op = AspectRatioOp(
                description="Convert to 1:1 square format (optimized for Instagram Feed)",
                ratio="1:1",
                mode="crop"
            )
            operations.append(op.model_dump())
        elif any(w in lower_prompt for w in ["16:9", "landscape", "widescreen", "youtube"]):
            op = AspectRatioOp(
                description="Standardize to 16:9 landscape format (optimized for YouTube)",
                ratio="16:9",
                mode="pad"
            )
            operations.append(op.model_dump())

        # 13. Resolution Standardization
        if "1080p" in lower_prompt or "full hd" in lower_prompt or "fhd" in lower_prompt:
            op = ResolutionOp(
                description="Standardize output resolution to 1080p FHD",
                standard="1080p"
            )
            operations.append(op.model_dump())
        elif "720p" in lower_prompt or "hd" in lower_prompt:
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

        # 14. Global Audio Volume Adjustment
        if not mute_range_match:
            if "mute" in lower_prompt or "silence audio" in lower_prompt or "remove audio" in lower_prompt:
                op = AudioVolumeOp(
                    description="Mute audio track completely",
                    volume_percent=0.0,
                    mute=True
                )
                operations.append(op.model_dump())
            else:
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

        # 15. Global Visual / Color Adjustments
        if not vfx_range_match:
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

        # 16. Silence Removal / Review
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

        # 17. Automated Subtitles / Captions (if not explicit range caption)
        if not caption_range_match:
            if any(w in lower_prompt for w in ["subtitle", "subtitles", "caption", "captions", "transcribe"]):
                burn = True
                op = SubtitlesOp(
                    description="Generate timestamped subtitles and burn into exported video",
                    burn=burn,
                    language="en",
                    style="bold_yellow_banner"
                )
                operations.append(op.model_dump())

        # 18. Format / Export
        op_export = ExportFormatOp(
            description="Export standard Web-Optimized MP4 (H.264 / AAC)",
            format="mp4",
            video_codec="libx264",
            audio_codec="aac"
        )
        operations.append(op_export.model_dump())

        # 19. Contradiction & Ambiguity Detection
        has_trim = any(op["type"] in [OperationType.TRIM_START, OperationType.TRIM_END] for op in operations)
        has_slice = any(op["type"] in [OperationType.TIME_SLICE, OperationType.TARGET_DURATION] for op in operations)
        if has_trim and has_slice:
            warnings.append("Both incremental trim and absolute time-slice were requested. Time-slice takes precedence.")

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

        # 20. Build Content-Aware Timeline Model
        source_dur = metadata.duration if metadata and metadata.duration > 0 else 10.0
        tl = Timeline(source_duration=source_dur, source_id="src_original")

        for op in operations:
            t = op.get("type")
            if t == OperationType.TRIM_START or t == OperationType.TRIM_START.value:
                tl.apply_trim_start(op.get("seconds", 0.0))
            elif t == OperationType.TRIM_END or t == OperationType.TRIM_END.value:
                tl.apply_trim_end(op.get("seconds", 0.0))
            elif t == OperationType.TIME_SLICE or t == OperationType.TIME_SLICE.value:
                tl.apply_time_slice(op.get("start_time", 0.0), op.get("end_time", source_dur))
            elif t == OperationType.CUT or t == OperationType.CUT.value:
                tl.apply_cut(op.get("cut_start", 0.0), op.get("cut_end", 0.0))
            elif t == OperationType.SPEED or t == OperationType.SPEED.value:
                tl.apply_speed_change(op.get("speed", 1.0), op.get("source_start"), op.get("source_end"))
            elif t == OperationType.REORDER or t == OperationType.REORDER.value:
                order = op.get("order", [])
                if order and set(order) == set(range(len(tl.segments))):
                    tl.reorder_segments(order)
            elif t == OperationType.CAPTION or t == OperationType.CAPTION.value:
                tl.add_effect("caption", op.get("source_start", 0.0), op.get("source_end", 0.0), parameters=op.get("parameters", {}), label=op.get("label"))
            elif t == OperationType.MUTE_RANGE or t == OperationType.MUTE_RANGE.value:
                tl.add_effect("mute", op.get("source_start", 0.0), op.get("source_end", 0.0), parameters=op.get("parameters", {}), label=op.get("label"))
            elif t == OperationType.BEEP or t == OperationType.BEEP.value:
                tl.add_effect("beep", op.get("source_start", 0.0), op.get("source_end", 0.0), parameters=op.get("parameters", {}), label=op.get("label"))
            elif t == OperationType.VISUAL_EFFECT or t == OperationType.VISUAL_EFFECT.value:
                tl.add_effect("visual_effect", op.get("source_start", 0.0), op.get("source_end", 0.0), parameters=op.get("parameters", {}), label=op.get("label"))
            elif t == OperationType.SILENCE_REMOVAL or t == OperationType.SILENCE_REMOVAL.value:
                for interval in op.get("confirmed_intervals", []):
                    tl.apply_cut(float(interval[0]), float(interval[1]))

        # 21. Unrecognized or Unsupported Prompt Check
        if len(operations) == 1 and operations[0]["type"] == OperationType.EXPORT_FORMAT:
            unsupported_phrases = ["reverse video", "3d effect", "generate new scene", "ai face swap", "greenscreen replacement"]
            found_unsupported = next((u for u in unsupported_phrases if u in lower_prompt), None)

            if found_unsupported:
                warnings.append(f"'{found_unsupported}' is currently unsupported. ClipPilot focuses on deterministic trimming, speed changes, content-aware captions, audio effects, and aspect ratio conversion.")
                suggested_repair = "Try: 'Trim the first 3 seconds, speed up 2x, and boost volume by 50%'."
            else:
                warnings.append("Could not confidently identify any editing commands from your prompt.")
                suggested_repair = "Try: 'Cut first 2 seconds, convert to 9:16 vertical, and add subtitles'."
                requires_confirmation = True
                confirmation_reason = "Prompt did not match any supported video editing action."

        # 22. Strict Three-Way Instruction Outcome Evaluation (Must-Have 3)
        from app.services.operation_processor import OperationProcessor
        import copy

        instruction_outcomes = []
        # Split compound clauses by comma or semicolons
        raw_clauses = [c.strip() for c in re.split(r"[,;]+", clean_prompt) if c.strip()]
        if not raw_clauses:
            raw_clauses = [clean_prompt]

        for clause in raw_clauses:
            outcome = OperationProcessor.process_instruction(
                instruction=clause,
                timeline=copy.deepcopy(tl),
                metadata=metadata
            )
            instruction_outcomes.append(outcome.model_dump())
            if outcome.status == "NEEDS_CLARIFICATION":
                requires_confirmation = True
                if not confirmation_reason:
                    confirmation_reason = outcome.message
                if outcome.clarification_prompt and not suggested_repair:
                    suggested_repair = outcome.clarification_prompt
            elif outcome.status == "REJECTED":
                if outcome.error_code in ["SECURITY_VIOLATION", "UNSUPPORTED_EFFECT", "INVALID_TIME_RANGE"]:
                    if outcome.message not in warnings:
                        warnings.append(outcome.message)

        est_duration = round(tl.total_duration, 2) if tl.total_duration > 0 else (metadata.duration if metadata else None)

        return EditPlan(
            prompt=clean_prompt,
            operations=operations,
            warnings=warnings,
            requires_confirmation=requires_confirmation,
            confirmation_reason=confirmation_reason,
            suggested_repair=suggested_repair,
            estimated_duration=est_duration,
            timeline=tl.to_dict(),
            timeline_hash=tl.timeline_hash,
            instruction_outcomes=instruction_outcomes
        )
