import os
from pathlib import Path
import pytest

from app.core.config import settings
from app.services.media_inspector import inspect_media
from app.services.prompt_parser import PromptParser
from app.services.video_processor import VideoProcessor
from app.services.silence_detector import SilenceDetector

@pytest.fixture
def sample_video_1():
    path = settings.SAMPLE_DIR / "sample_1_talking_head.mp4"
    assert path.exists(), "Sample 1 video must exist"
    return str(path)

@pytest.fixture
def sample_silent_video():
    path = settings.SAMPLE_DIR / "sample_3_silent_clip.mp4"
    assert path.exists(), "Sample 3 silent clip must exist"
    return str(path)

def test_media_inspector(sample_video_1):
    meta = inspect_media(sample_video_1)
    assert meta.duration == 10.0
    assert meta.width == 1920
    assert meta.height == 1080
    assert meta.aspect_ratio == "16:9"
    assert meta.has_audio is True

def test_silence_detection(sample_video_1):
    cuts = SilenceDetector.detect_silence(sample_video_1)
    assert len(cuts) >= 1
    # Silence was injected between 3s and 6s
    cut = cuts[0]
    assert 2.5 <= cut.start <= 3.5
    assert 5.5 <= cut.end <= 6.5
    assert 2.5 <= cut.duration <= 3.5

def test_trim_and_vertical_aspect(sample_video_1):
    meta = inspect_media(sample_video_1)
    plan = PromptParser.parse("Cut first 3 seconds and convert to 9:16 vertical", meta)
    
    job_id = "test-proc-vertical"
    out_path, out_meta, proc_time, ops = VideoProcessor.process_video(job_id, sample_video_1, plan)

    assert Path(out_path).exists()
    assert out_meta.duration == 7.0
    assert out_meta.width == 1080
    assert out_meta.height == 1920
    assert out_meta.aspect_ratio == "9:16"
    assert proc_time > 0.0

def test_square_aspect_and_resolution(sample_video_1):
    meta = inspect_media(sample_video_1)
    plan = PromptParser.parse("Make it 1:1 square at 720p", meta)
    
    job_id = "test-proc-square"
    out_path, out_meta, proc_time, ops = VideoProcessor.process_video(job_id, sample_video_1, plan)

    assert Path(out_path).exists()
    assert out_meta.width == 720
    assert out_meta.height == 720
    assert out_meta.aspect_ratio == "1:1"

def test_silent_video_processing(sample_silent_video):
    # Verify processing a video without audio stream does not fail
    meta = inspect_media(sample_silent_video)
    assert meta.has_audio is False
    plan = PromptParser.parse("Make it brighter and export at 720p", meta)
    
    job_id = "test-proc-silent"
    out_path, out_meta, proc_time, ops = VideoProcessor.process_video(job_id, sample_silent_video, plan)

    assert Path(out_path).exists()
    assert out_meta.has_audio is False
    assert out_meta.width == 720
    assert out_meta.height == 720

def test_subtitle_burning(sample_video_1):
    meta = inspect_media(sample_video_1)
    plan = PromptParser.parse("Add subtitles and export at 720p", meta)
    
    job_id = "test-proc-subs"
    out_path, out_meta, proc_time, ops = VideoProcessor.process_video(job_id, sample_video_1, plan)

    assert Path(out_path).exists()
    assert out_meta.duration == 10.0
