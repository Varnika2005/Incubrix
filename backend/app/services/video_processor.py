import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.core.config import settings
from app.schemas.edit_plan import EditPlan, OperationType
from app.schemas.job import MediaMetadata, EditReceipt
from app.services.ffmpeg_finder import FFmpegFinder
from app.services.media_inspector import inspect_media, MediaInspectionError
from app.services.transcriber import Transcriber
from app.services.timeline_model import Timeline, TimelineSegment, ContentAwareEffect, TransformedTimelineEffect


class VideoProcessingError(Exception):
    pass


def format_srt_time(seconds: float) -> str:
    """Formats seconds into SRT timestamp HH:MM:SS,mmm."""
    millis = int(round(max(0.0, seconds) * 1000))
    hours = millis // 3600000
    millis %= 3600000
    mins = millis // 60000
    millis %= 60000
    secs = millis // 1000
    millis %= 1000
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def build_atempo_filter(speed: float) -> str:
    """Builds a valid FFmpeg atempo filter chain for any positive speed multiplier."""
    if abs(speed - 1.0) < 1e-4:
        return ""
    filters: List[str] = []
    rem = speed
    while rem > 2.0:
        filters.append("atempo=2.0")
        rem /= 2.0
    while rem < 0.5:
        filters.append("atempo=0.5")
        rem /= 0.5
    filters.append(f"atempo={rem:.4f}")
    return ",".join(filters)


class VideoProcessor:
    """
    Executes validated EditPlan and Content-Aware Timeline operations using FFmpeg.
    Ensures:
    - Content-anchored captions, mute ranges, beep effects, and visual filters
      survive cuts, trims, speed changes, and reorderings deterministically.
    - Safe subprocess array invocation (no shell injection)
    - Output verification with FFprobe
    - Temporary file cleanup
    - Audio sync preservation across transformed multi-segment timelines.
    """

    @classmethod
    def process_video(
        cls,
        job_id: str,
        input_path: str,
        edit_plan: EditPlan,
        progress_callback: Optional[callable] = None
    ) -> Tuple[str, MediaMetadata, float, List[Dict[str, Any]]]:
        """
        Executes the operations in edit_plan on input_path.
        Returns: (output_video_path, output_metadata, processing_time_seconds, applied_operations)
        """
        start_time = time.time()
        in_file = Path(input_path)
        if not in_file.is_file():
            raise VideoProcessingError(f"Input file not found: {input_path}")

        # Initial inspection
        input_meta = inspect_media(str(in_file))

        # Set up job output directory
        job_dir = settings.OUTPUT_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        final_output_path = job_dir / f"clippilot_edited_{job_id[:8]}.mp4"
        temp_dir = settings.TEMP_DIR / job_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        applied_ops: List[Dict[str, Any]] = []
        ffmpeg_bin = FFmpegFinder.get_ffmpeg_path()

        try:
            # 1. Parse parameters & initialize Timeline
            target_aspect: Optional[str] = None
            aspect_mode: str = "crop"
            target_res: Optional[str] = None
            volume_percent: Optional[float] = None
            is_muted: bool = False
            global_brightness: float = 0.0
            global_contrast: float = 1.0
            burn_subtitles: bool = False
            custom_sub_text: Optional[str] = None

            # Check if an explicit timeline was passed in edit_plan
            fps = float(input_meta.fps) if input_meta and input_meta.fps and input_meta.fps > 0 else 30.0
            timeline: Optional[Timeline] = None
            if edit_plan.timeline:
                timeline = Timeline.from_dict(edit_plan.timeline)
                if not timeline.fps or timeline.fps <= 0:
                    timeline.fps = fps
            else:
                timeline = Timeline(source_duration=input_meta.duration, source_id="src_original", fps=fps)

            for op in edit_plan.operations:
                op_type = op.get("type")

                if op_type == OperationType.TRIM_START or op_type == "trim_start":
                    sec = float(op.get("seconds", 0.0))
                    timeline.apply_trim_start(sec)
                    applied_ops.append(op)

                elif op_type == OperationType.TRIM_END or op_type == "trim_end":
                    sec = float(op.get("seconds", 0.0))
                    timeline.apply_trim_end(sec)
                    applied_ops.append(op)

                elif op_type == OperationType.TIME_SLICE or op_type == "time_slice":
                    st = float(op.get("start_time", 0.0))
                    et = float(op.get("end_time", input_meta.duration))
                    timeline.apply_time_slice(st, et)
                    applied_ops.append(op)

                elif op_type == OperationType.CUT or op_type == "cut":
                    cs = float(op.get("cut_start", 0.0))
                    ce = float(op.get("cut_end", 0.0))
                    timeline.apply_cut(cs, ce)
                    applied_ops.append(op)

                elif op_type == OperationType.SPEED or op_type == "speed":
                    spd = float(op.get("speed", 1.0))
                    timeline.apply_speed_change(spd, op.get("source_start"), op.get("source_end"))
                    applied_ops.append(op)

                elif op_type == OperationType.REORDER or op_type == "reorder":
                    ord_list = op.get("order", [])
                    if ord_list and set(ord_list) == set(range(len(timeline.segments))):
                        timeline.reorder_segments(ord_list)
                    applied_ops.append(op)

                elif op_type == OperationType.CAPTION or op_type == "caption":
                    timeline.add_effect(
                        "caption",
                        float(op.get("source_start", 0.0)),
                        float(op.get("source_end", 0.0)),
                        parameters=op.get("parameters", {"text": op.get("text", "Caption")}),
                        label=op.get("label")
                    )
                    applied_ops.append(op)

                elif op_type == OperationType.MUTE_RANGE or op_type == "mute_range":
                    timeline.add_effect(
                        "mute",
                        float(op.get("source_start", 0.0)),
                        float(op.get("source_end", 0.0)),
                        parameters=op.get("parameters", {}),
                        label=op.get("label")
                    )
                    applied_ops.append(op)

                elif op_type == OperationType.BEEP or op_type == "beep":
                    timeline.add_effect(
                        "beep",
                        float(op.get("source_start", 0.0)),
                        float(op.get("source_end", 0.0)),
                        parameters=op.get("parameters", {"frequency": 1000}),
                        label=op.get("label")
                    )
                    applied_ops.append(op)

                elif op_type == OperationType.VISUAL_EFFECT or op_type == "visual_effect":
                    timeline.add_effect(
                        "visual_effect",
                        float(op.get("source_start", 0.0)),
                        float(op.get("source_end", 0.0)),
                        parameters=op.get("parameters", {}),
                        label=op.get("label")
                    )
                    applied_ops.append(op)

                elif op_type == OperationType.ASPECT_RATIO or op_type == "aspect_ratio":
                    target_aspect = op.get("ratio")
                    aspect_mode = op.get("mode", "crop")
                    applied_ops.append(op)

                elif op_type == OperationType.RESOLUTION or op_type == "resolution":
                    target_res = op.get("standard")
                    applied_ops.append(op)

                elif op_type == OperationType.AUDIO_VOLUME or op_type == "audio_volume":
                    volume_percent = float(op.get("volume_percent", 100.0))
                    is_muted = bool(op.get("mute", False)) or (volume_percent == 0.0)
                    applied_ops.append(op)

                elif op_type == OperationType.COLOR_ADJUST or op_type == "color_adjust":
                    global_brightness = float(op.get("brightness", 0.0))
                    global_contrast = float(op.get("contrast", 1.0))
                    applied_ops.append(op)

                elif op_type == OperationType.SILENCE_REMOVAL or op_type == "silence_removal":
                    intervals = op.get("confirmed_intervals", [])
                    if intervals:
                        for inter in intervals:
                            timeline.apply_cut(float(inter[0]), float(inter[1]))
                        applied_ops.append(op)

                elif op_type == OperationType.SUBTITLES or op_type == "subtitles":
                    burn_subtitles = bool(op.get("burn", True))
                    custom_sub_text = op.get("custom_text")
                    applied_ops.append(op)

            # Determine dimensions
            base_res = target_res or ("1080p" if target_aspect else None)
            w, h = input_meta.width or 1920, input_meta.height or 1080

            if target_aspect == "9:16":
                if base_res == "720p":
                    target_w, target_h = 720, 1280
                else:
                    target_w, target_h = 1080, 1920
            elif target_aspect == "1:1":
                if base_res == "720p":
                    target_w, target_h = 720, 720
                else:
                    target_w, target_h = 1080, 1080
            elif target_aspect == "16:9":
                if base_res == "720p":
                    target_w, target_h = 1280, 720
                else:
                    target_w, target_h = 1920, 1080
            else:
                if base_res == "720p" and (w > 1280 or h > 720):
                    scale_factor = 720.0 / h if h > 0 else 1.0
                    target_w = int(w * scale_factor) // 2 * 2
                    target_h = 720
                else:
                    target_w, target_h = None, None

            # 2. Render via Content-Aware Timeline Renderer
            cls._render_timeline_graph(
                ffmpeg_bin=ffmpeg_bin,
                input_file=in_file,
                output_file=final_output_path,
                timeline=timeline,
                input_meta=input_meta,
                target_w=target_w,
                target_h=target_h,
                aspect_mode=aspect_mode,
                volume_percent=volume_percent,
                is_muted=is_muted,
                global_brightness=global_brightness,
                global_contrast=global_contrast,
                burn_subtitles=burn_subtitles,
                custom_sub_text=custom_sub_text,
                temp_dir=temp_dir,
                progress_callback=progress_callback
            )

            # 3. Output verification
            if not final_output_path.exists() or final_output_path.stat().st_size == 0:
                raise VideoProcessingError("Processed output file was not generated or has zero bytes.")

            out_meta = inspect_media(str(final_output_path))
            if out_meta.duration <= 0 or out_meta.width <= 0 or out_meta.height <= 0:
                raise VideoProcessingError("Output video verification failed: corrupt or zero duration.")

            # Record timeline audit in applied operations
            applied_ops.append({
                "type": "content_aware_timeline",
                "description": f"Content-aware timeline rendered with {len(timeline.segments)} segments, duration: {out_meta.duration:.2f}s",
                "timeline_summary": timeline.to_dict()["summary"],
                "active_effects": len([e for e in timeline.transform_effects() if e.status != "dropped_content_removed"]),
                "dropped_effects": len([e for e in timeline.transform_effects() if e.status == "dropped_content_removed"])
            })

            if progress_callback:
                progress_callback(100)

            processing_time = round(time.time() - start_time, 2)
            return str(final_output_path), out_meta, processing_time, applied_ops

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _render_timeline_graph(
        cls,
        ffmpeg_bin: str,
        input_file: Path,
        output_file: Path,
        timeline: Timeline,
        input_meta: MediaMetadata,
        target_w: Optional[int],
        target_h: Optional[int],
        aspect_mode: str,
        volume_percent: Optional[float],
        is_muted: bool,
        global_brightness: float,
        global_contrast: float,
        burn_subtitles: bool,
        custom_sub_text: Optional[str],
        temp_dir: Path,
        progress_callback: Optional[callable] = None
    ):
        """Constructs and runs the FFmpeg filter graph for arbitrary content-aware timelines."""
        if not timeline.segments:
            raise VideoProcessingError("Timeline has no active segments to render.")

        if progress_callback:
            progress_callback(25)

        transformed_effects = timeline.transform_effects()
        active_effects = [e for e in transformed_effects if e.status != "dropped_content_removed"]

        fps = float(input_meta.fps) if input_meta and input_meta.fps and input_meta.fps > 0 else (timeline.fps if timeline.fps > 0 else 30.0)
        frame_dur = 1.0 / fps
        has_audio = input_meta.has_audio and not is_muted and (volume_percent is None or volume_percent > 0.0)
        n_segs = len(timeline.segments)

        # Feature 5: Audio/Video Synchronization
        # Compute cumulative frame duration for exact A/V alignment and duration matching
        cum_time = 0.0
        prev_cum_frames = 0
        seg_exact_durs: List[float] = []
        for seg in timeline.segments:
            cum_time += seg.timeline_duration
            cum_frames = round(cum_time * fps)
            seg_frames = max(1, cum_frames - prev_cum_frames)
            prev_cum_frames += seg_frames
            seg_exact_durs.append(round(seg_frames / fps, 6))

        total_exact_dur = round(prev_cum_frames / fps, 6)

        filter_parts: List[str] = []

        # 1. Multi-segment trimming and speed changes with frame-locked A/V duration
        for idx, (seg, seg_dur) in enumerate(zip(timeline.segments, seg_exact_durs)):
            spd = seg.speed if seg.speed > 0.01 else 1.0
            setpts_val = f"{1.0 / spd:.6f}*(PTS-STARTPTS)"
            # Video: trim range -> scale PTS -> frame rate normalize -> pad if deficit -> exact frame duration cap
            filter_parts.append(
                f"[0:v]trim=start={seg.source_start:.4f}:end={seg.source_end:.4f},setpts={setpts_val},"
                f"fps={fps},tpad=stop_mode=clone:stop_duration={frame_dur * 2:.4f},trim=duration={seg_dur:.4f}[v_seg_{idx}]"
            )

            if has_audio:
                tempo_str = build_atempo_filter(spd)
                tempo_clause = ("," + tempo_str) if tempo_str else ""
                # Audio: trim range -> reset PTS -> apply tempo -> pad deficit -> exact duration cap
                filter_parts.append(
                    f"[0:a]atrim=start={seg.source_start:.4f}:end={seg.source_end:.4f},asetpts=PTS-STARTPTS{tempo_clause},"
                    f"apad,atrim=0:{seg_dur:.4f}[a_seg_{idx}]"
                )

        # 2. Concatenation
        if has_audio:
            concat_inputs = "".join(f"[v_seg_{i}][a_seg_{i}]" for i in range(n_segs))
            filter_parts.append(f"{concat_inputs}concat=n={n_segs}:v=1:a=1[v_cat][a_cat]")
        else:
            concat_inputs = "".join(f"[v_seg_{i}]" for i in range(n_segs))
            filter_parts.append(f"{concat_inputs}concat=n={n_segs}:v=1:a=0[v_cat]")

        # 3. Post-concat video filters
        v_filters: List[str] = [f"fps={fps}", "setsar=1"]

        # Aspect ratio / scaling
        if target_w and target_h:
            if aspect_mode == "crop":
                v_filters.append(f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}")
            else:
                v_filters.append(f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black")
        elif target_w or target_h:
            v_filters.append(f"scale={target_w or -2}:{target_h or -2}")

        # Global color adjustment
        if global_brightness != 0.0 or global_contrast != 1.0:
            v_filters.append(f"eq=brightness={global_brightness:.2f}:contrast={global_contrast:.2f}")

        # Content-Aware Visual Effects
        vfx_effects = [e for e in active_effects if e.type in ["visual_effect", "color_adjust"]]
        for eff in vfx_effects:
            t_st = max(0.0, eff.timeline_start)
            t_et = max(t_st + 0.02, eff.timeline_end)
            effect_name = str(eff.parameters.get("effect", "")).lower()

            if "blur" in effect_name:
                v_filters.append(f"boxblur=10:enable='between(t,{t_st:.3f},{t_et:.3f})'")
            elif "invert" in effect_name or "negate" in effect_name:
                v_filters.append(f"negate=enable='between(t,{t_st:.3f},{t_et:.3f})'")
            elif "grayscale" in effect_name:
                v_filters.append(f"hue=s=0:enable='between(t,{t_st:.3f},{t_et:.3f})'")
            elif "brightness" in eff.parameters or "contrast" in eff.parameters or "bright" in effect_name or "dark" in effect_name:
                b = float(eff.parameters.get("brightness", 0.25 if "bright" in effect_name else (-0.25 if "dark" in effect_name else 0.0)))
                c = float(eff.parameters.get("contrast", 1.0))
                v_filters.append(f"eq=brightness={b:.2f}:contrast={c:.2f}:enable='between(t,{t_st:.3f},{t_et:.3f})'")
            elif "filter" in eff.parameters:
                v_filters.append(f"{eff.parameters['filter']}:enable='between(t,{t_st:.3f},{t_et:.3f})'")

        # Content-Aware Captions / Subtitles
        caption_effects = [e for e in active_effects if e.type in ["caption", "subtitles"]]
        srt_cues: List[Tuple[float, float, str]] = []

        for eff in caption_effects:
            cue_text = eff.parameters.get("text") or eff.parameters.get("custom_text") or eff.label or "Caption"
            srt_cues.append((eff.timeline_start, eff.timeline_end, cue_text))

        # Automated subtitles fallback if requested and no timeline captions
        if burn_subtitles and not caption_effects:
            raw_srt = temp_dir / "raw_subs.srt"
            Transcriber.generate_srt(str(input_file), str(raw_srt), custom_text=custom_sub_text)
            # Map raw SRT cues to timeline
            # If segments were trimmed or cut, cues need timeline offset mapping
            if raw_srt.exists():
                lines = raw_srt.read_text(encoding="utf-8").splitlines()
                cur_s = 0.0
                cur_e = 0.0
                cur_t = ""
                for line in lines:
                    if "-->" in line:
                        parts = line.split("-->")
                        def parse_srt_ts(ts):
                            ts = ts.strip().replace(",", ".")
                            hp, mp, sp = ts.split(":")
                            return float(hp)*3600 + float(mp)*60 + float(sp)
                        cur_s = parse_srt_ts(parts[0])
                        cur_e = parse_srt_ts(parts[1])
                    elif line.strip() and not line.strip().isdigit():
                        cur_t = line.strip()
                        # Map through timeline
                        eff_temp = ContentAwareEffect(
                            effect_id=f"auto_{len(srt_cues)}",
                            type="caption",
                            source_id="src_original",
                            source_start=cur_s,
                            source_end=cur_e,
                            parameters={"text": cur_t}
                        )
                        timeline.effects.append(eff_temp)
                        for mapped in timeline.transform_effects():
                            if mapped.parent_effect_id == eff_temp.effect_id and mapped.status != "dropped_content_removed":
                                srt_cues.append((mapped.timeline_start, mapped.timeline_end, cur_t))
                        timeline.effects.remove(eff_temp)

        if srt_cues:
            srt_cues.sort(key=lambda c: c[0])
            srt_path = temp_dir / "timeline_captions.srt"
            srt_content = []
            for i, (c_start, c_end, c_text) in enumerate(srt_cues, 1):
                srt_content.append(f"{i}\n{format_srt_time(c_start)} --> {format_srt_time(c_end)}\n{c_text}\n")
            srt_path.write_text("\n".join(srt_content), encoding="utf-8")

            escaped_srt = Transcriber.escape_path_for_ffmpeg(str(srt_path))
            v_filters.append(f"subtitles='{escaped_srt}':force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=30'")

        v_filters.append(f"trim=duration={total_exact_dur:.4f}")
        filter_parts.append(f"[v_cat]{','.join(v_filters)}[v_final]")

        # 4. Post-concat audio filters (mute ranges, beep effects, volume)
        audio_final_label = "[a_cat]"
        if has_audio:
            mute_effects = [e for e in active_effects if e.type == "mute"]
            beep_effects = [e for e in active_effects if e.type == "beep"]

            a_filters: List[str] = ["aresample=async=1000"]

            if volume_percent is not None and volume_percent != 100.0:
                vol_factor = max(0.0, volume_percent / 100.0)
                a_filters.append(f"volume={vol_factor:.2f}")

            # Silence audio during mute intervals and during beep intervals
            duck_intervals: List[Tuple[float, float]] = []
            for m in mute_effects:
                duck_intervals.append((max(0.0, m.timeline_start), max(0.0, m.timeline_end)))
            for b in beep_effects:
                duck_intervals.append((max(0.0, b.timeline_start), max(0.0, b.timeline_end)))

            if duck_intervals:
                duck_expr = "+".join(f"between(t,{st:.3f},{et:.3f})" for st, et in duck_intervals)
                a_filters.append(f"volume=enable='{duck_expr}':volume=0")

            filter_parts.append(f"[a_cat]{','.join(a_filters)}[a_ducked]")

            # Mix censorship beep tone if beep effects exist
            if beep_effects:
                total_dur = max(1.0, timeline.total_duration)
                beep_labels: List[str] = []
                for b_idx, b_eff in enumerate(beep_effects):
                    b_st = max(0.0, b_eff.timeline_start)
                    b_et = max(b_st + 0.05, b_eff.timeline_end)
                    freq = b_eff.parameters.get("frequency", 1000)
                    filter_parts.append(f"sine=frequency={freq}:duration={total_dur}[beep_raw_{b_idx}]")
                    filter_parts.append(f"[beep_raw_{b_idx}]volume=enable='between(t,{b_st:.3f},{b_et:.3f})':volume=0.4:eval=frame[beep_gate_{b_idx}]")
                    beep_labels.append(f"[beep_gate_{b_idx}]")

                mix_inputs = "[a_ducked]" + "".join(beep_labels)
                num_inputs = 1 + len(beep_effects)
                filter_parts.append(f"{mix_inputs}amix=inputs={num_inputs}:duration=first:dropout_transition=0[a_final]")
                audio_mixed_label = "[a_final]"
            else:
                audio_mixed_label = "[a_ducked]"

            # Final audio timing sync locked to exact timeline duration
            filter_parts.append(f"{audio_mixed_label}apad,atrim=0:{total_exact_dur:.4f}[a_synced]")
            audio_final_label = "[a_synced]"

        # 5. Build FFmpeg command
        cmd: List[str] = [ffmpeg_bin, "-y", "-i", str(input_file)]
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
        cmd.extend(["-map", "[v_final]"])

        if has_audio:
            cmd.extend([
                "-map", audio_final_label,
                "-c:a", settings.DEFAULT_AUDIO_CODEC,
                "-b:a", "192k",
                "-ar", "44100",
                "-ac", "2"
            ])
        else:
            cmd.append("-an")

        cmd.extend([
            "-c:v", settings.DEFAULT_VIDEO_CODEC,
            "-preset", settings.DEFAULT_PRESET,
            "-crf", str(settings.DEFAULT_CRF),
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-level:v", "4.0",
            "-brand", "mp42",
            "-movflags", "+faststart",
            str(output_file)
        ])

        if progress_callback:
            progress_callback(50)

        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            err_msg = res.stderr.strip()[-600:] if res.stderr else "FFmpeg execution failed"
            raise VideoProcessingError(f"Timeline transcoding failed: {err_msg}")

        if progress_callback:
            progress_callback(90)
