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

class VideoProcessingError(Exception):
    pass

class VideoProcessor:
    """
    Executes validated EditPlan operations using FFmpeg.
    Ensures:
    - Safe subprocess array invocation (no shell injection)
    - Output verification with FFprobe
    - Temporary file cleanup
    - Audio sync preservation
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
            # 1. Parse operations
            start_ss: Optional[float] = None
            end_to: Optional[float] = None
            duration_t: Optional[float] = None
            
            target_aspect: Optional[str] = None
            aspect_mode: str = "crop"
            
            target_res: Optional[str] = None
            
            volume_percent: Optional[float] = None
            is_muted: bool = False
            
            brightness: float = 0.0
            contrast: float = 1.0
            
            burn_subtitles: bool = False
            custom_sub_text: Optional[str] = None
            
            silence_cuts: List[Tuple[float, float]] = []

            for op in edit_plan.operations:
                op_type = op.get("type")
                
                if op_type == OperationType.TRIM_START:
                    start_ss = float(op.get("seconds", 0.0))
                    applied_ops.append(op)
                    
                elif op_type == OperationType.TRIM_END:
                    trim_end_sec = float(op.get("seconds", 0.0))
                    if input_meta.duration > trim_end_sec:
                        end_to = input_meta.duration - trim_end_sec
                    applied_ops.append(op)
                    
                elif op_type == OperationType.TIME_SLICE:
                    start_ss = float(op.get("start_time", 0.0))
                    end_to = float(op.get("end_time", input_meta.duration))
                    applied_ops.append(op)
                    
                elif op_type == OperationType.TARGET_DURATION:
                    duration_t = float(op.get("target_seconds", input_meta.duration))
                    applied_ops.append(op)
                    
                elif op_type == OperationType.ASPECT_RATIO:
                    target_aspect = op.get("ratio")
                    aspect_mode = op.get("mode", "crop")
                    applied_ops.append(op)
                    
                elif op_type == OperationType.RESOLUTION:
                    target_res = op.get("standard")
                    applied_ops.append(op)
                    
                elif op_type == OperationType.AUDIO_VOLUME:
                    volume_percent = float(op.get("volume_percent", 100.0))
                    is_muted = bool(op.get("mute", False))
                    applied_ops.append(op)
                    
                elif op_type == OperationType.COLOR_ADJUST:
                    brightness = float(op.get("brightness", 0.0))
                    contrast = float(op.get("contrast", 1.0))
                    applied_ops.append(op)
                    
                elif op_type == OperationType.SILENCE_REMOVAL:
                    intervals = op.get("confirmed_intervals", [])
                    if intervals:
                        silence_cuts = [(float(i[0]), float(i[1])) for i in intervals]
                        applied_ops.append(op)
                        
                elif op_type == OperationType.SUBTITLES:
                    burn_subtitles = bool(op.get("burn", True))
                    custom_sub_text = op.get("custom_text")
                    applied_ops.append(op)

            # Determine dimensions
            # Target resolution standard dimensions
            # 16:9 -> 1920x1080 (1080p), 1280x720 (720p)
            # 9:16 -> 1080x1920 (1080p), 720x1280 (720p)
            # 1:1  -> 1080x1080 (1080p), 720x720 (720p)
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
                # No aspect ratio change, check resolution change
                if base_res == "720p" and (w > 1280 or h > 720):
                    scale_factor = 720.0 / h if h > 0 else 1.0
                    target_w = int(w * scale_factor) // 2 * 2
                    target_h = 720
                else:
                    target_w, target_h = None, None

            # 2. Build Video Filter Chain
            video_filters: List[str] = []

            # Aspect Ratio / Scaling Filter
            if target_w and target_h:
                if aspect_mode == "crop":
                    video_filters.append(
                        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}"
                    )
                else:  # pad
                    video_filters.append(
                        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:black"
                    )

            # Color adjustment filter
            if brightness != 0.0 or contrast != 1.0:
                video_filters.append(f"eq=brightness={brightness}:contrast={contrast}")

            # Subtitle Burning Filter
            if burn_subtitles:
                srt_path = temp_dir / "subtitles.srt"
                Transcriber.generate_srt(str(in_file), str(srt_path), custom_text=custom_sub_text)
                escaped_srt = Transcriber.escape_path_for_ffmpeg(str(srt_path))
                # Burn subtitles with clean styling
                sub_filter = f"subtitles='{escaped_srt}':force_style='FontSize=16,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=30'"
                video_filters.append(sub_filter)

            # 3. Build Audio Filter Chain
            audio_filters: List[str] = []
            has_audio = input_meta.has_audio

            if has_audio and not is_muted:
                if volume_percent is not None and volume_percent != 100.0:
                    vol_factor = max(0.0, volume_percent / 100.0)
                    audio_filters.append(f"volume={vol_factor:.2f}")

            # 4. Construct Command
            cmd: List[str] = [ffmpeg_bin, "-y"]

            # Input seeking
            if start_ss is not None and start_ss > 0:
                cmd.extend(["-ss", str(start_ss)])
            if end_to is not None and end_to > 0:
                # If start_ss was specified after -i, -to is absolute; if before -i, relative
                # To be precise, put -ss and -to before -i for fast seek
                cmd.extend(["-to", str(end_to)])
            elif duration_t is not None and duration_t > 0:
                cmd.extend(["-t", str(duration_t)])

            cmd.extend(["-i", str(in_file)])

            # Apply Video Filters
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])

            # Audio handling
            if not has_audio or is_muted or (volume_percent == 0.0):
                cmd.append("-an")
            else:
                if audio_filters:
                    cmd.extend(["-af", ",".join(audio_filters)])
                cmd.extend(["-c:a", settings.DEFAULT_AUDIO_CODEC, "-b:a", "128k"])

            # Video encoding settings
            cmd.extend([
                "-c:v", settings.DEFAULT_VIDEO_CODEC,
                "-preset", settings.DEFAULT_PRESET,
                "-crf", str(settings.DEFAULT_CRF),
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(final_output_path)
            ])

            # 5. Execute processing
            if progress_callback:
                progress_callback(30)

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                err_msg = res.stderr.strip()[-500:] if res.stderr else "FFmpeg failed"
                raise VideoProcessingError(f"Video transcoding failed: {err_msg}")

            if progress_callback:
                progress_callback(85)

            # 6. Verify Output
            if not final_output_path.exists() or final_output_path.stat().st_size == 0:
                raise VideoProcessingError("Processed output file was not generated or has zero bytes.")

            out_meta = inspect_media(str(final_output_path))
            if out_meta.duration <= 0 or out_meta.width <= 0 or out_meta.height <= 0:
                raise VideoProcessingError("Output video verification failed: corrupt or zero duration.")

            if progress_callback:
                progress_callback(100)

            processing_time = round(time.time() - start_time, 2)
            return str(final_output_path), out_meta, processing_time, applied_ops

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
