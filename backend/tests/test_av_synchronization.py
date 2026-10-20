"""
ClipPilot AI - Feature 5: Audio/Video Synchronization Automated Test Suite
===========================================================================
Validates that audio and video remain strictly synchronized within one video frame
after cuts, trims, speed changes, and clip reordering, and that the final output
duration matches the expected timeline duration within one video frame.

Verifications using FFprobe:
1. Audio/video timing alignment (skew <= 1.0 frame, typically <= 0.05 frames).
2. Final output duration within one frame of expected timeline duration.
3. Frame-rate and timestamp rounding consistency across discrete video frames.
4. Representative edits: cuts, trims, speed changes (fast/slow), reordering, and combined workflows.
"""

import json
import math
from pathlib import Path
import pytest

from app.core.config import settings
from app.services.media_inspector import inspect_media, inspect_av_sync
from app.services.video_processor import VideoProcessor
from app.services.timeline_model import Timeline
from app.schemas.edit_plan import EditPlan


@pytest.fixture
def sample_video():
    path = settings.SAMPLE_DIR / "sample_1_talking_head.mp4"
    assert path.exists(), "sample_1_talking_head.mp4 must exist for media testing"
    return str(path)


@pytest.fixture
def sample_silent_video():
    path = settings.SAMPLE_DIR / "sample_3_silent_clip.mp4"
    assert path.exists(), "sample_3_silent_clip.mp4 must exist for media testing"
    return str(path)


# =============================================================================
# 1. CUTS & TRIMS SYNCHRONIZATION TESTS
# =============================================================================

def test_av_sync_after_single_cut(sample_video):
    """
    Cut out an internal segment [3.0s - 5.0s].
    Verify audio and video remain aligned within one frame and duration matches expected.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_cut(3.0, 5.0)
    expected_dur = tl.total_duration
    assert expected_dur == 8.0

    plan = EditPlan(prompt="Cut out 3s to 5s", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-cut-single"
    out_path, out_meta, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["has_audio"] is True
    # 1. A/V timing alignment within one frame
    assert sync_info["is_aligned_within_one_frame"] is True, f"A/V skew: {sync_info['av_skew_frames']} frames"
    assert sync_info["av_skew_frames"] < 1.0
    # 2. Final duration within one frame of expected duration
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


def test_av_sync_after_multiple_sequential_cuts(sample_video):
    """
    Multiple cuts (4 cuts producing 5 segments).
    Verifies that inter-segment rounding does NOT cause cumulative drift.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_cut(1.0, 2.0)
    tl.apply_cut(3.0, 4.0)
    tl.apply_cut(5.5, 6.5)
    tl.apply_cut(7.5, 8.5)
    expected_dur = tl.total_duration  # 10 - 1 - 1 - 1 - 1 = 6.0s
    assert expected_dur == 6.0
    assert len(tl.segments) == 5

    plan = EditPlan(prompt="4 cuts across timeline", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-cuts-multi"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    assert sync_info["av_skew_frames"] < 0.5
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


def test_av_sync_after_trims_and_time_slice(sample_video):
    """
    Trim head and tail of video using trim_start and trim_end.
    Verify tight audio/video alignment.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_trim_start(1.5)
    tl.apply_trim_end(2.0)
    expected_dur = tl.total_duration  # 10 - 1.5 - 2.0 = 6.5s
    assert expected_dur == 6.5

    plan = EditPlan(prompt="Trim 1.5s start, 2s end", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-trims"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


# =============================================================================
# 2. SPEED CHANGES SYNCHRONIZATION TESTS
# =============================================================================

def test_av_sync_after_speed_up(sample_video):
    """
    Fast motion 2.0x speed.
    Tests atempo filter chaining and setpts scaling alignment.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_speed_change(2.0)
    expected_dur = tl.total_duration  # 10 / 2 = 5.0s
    assert expected_dur == 5.0

    plan = EditPlan(prompt="Speed up 2x", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-speed-fast"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    assert sync_info["av_skew_frames"] < 0.5
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


def test_av_sync_after_slow_motion(sample_video):
    """
    Slow motion 0.5x speed.
    Tests atempo 0.5 filter chaining and audio sample padding.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    # Use first 4 seconds at 0.5x to produce an 8.0s clip
    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_trim_end(6.0)  # leaves 4.0s
    tl.apply_speed_change(0.5)
    expected_dur = tl.total_duration  # 4.0 / 0.5 = 8.0s
    assert expected_dur == 8.0

    plan = EditPlan(prompt="Slow motion 0.5x", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-speed-slow"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


def test_av_sync_after_subrange_speed_change(sample_video):
    """
    Speed up middle portion (e.g. 1.5x between 3s and 6s) while keeping ends at 1.0x.
    Creates 3 segments: [0-3s @ 1x] + [3-6s @ 1.5x -> 2.0s] + [6-10s @ 1x] = 9.0s.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_speed_change(1.5, source_start=3.0, source_end=6.0)
    expected_dur = tl.total_duration  # 3.0 + 2.0 + 4.0 = 9.0s
    assert expected_dur == 9.0
    assert len(tl.segments) == 3

    plan = EditPlan(prompt="Speed up 1.5x from 3s to 6s", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-subrange-speed"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


# =============================================================================
# 3. CLIP REORDERING SYNCHRONIZATION TESTS
# =============================================================================

def test_av_sync_after_clip_reordering(sample_video):
    """
    Split video into 3 clips and reorder them [seg_2, seg_0, seg_1].
    Verifies that audio transitions accurately with video when clip order is rearranged.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_cut(3.0, 4.0)   # creates seg0 [0-3], seg1 [4-10]
    tl.apply_cut(7.0, 8.0)   # creates seg0 [0-3], seg1 [4-7], seg2 [8-10]
    assert len(tl.segments) == 3

    # Reorder segments to [2, 0, 1]
    tl.reorder_segments([2, 0, 1])
    expected_dur = tl.total_duration  # 2.0 + 3.0 + 3.0 = 8.0s
    assert expected_dur == 8.0

    plan = EditPlan(prompt="Cut and reorder clips", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-reorder"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    assert sync_info["av_skew_frames"] < 0.5
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


# =============================================================================
# 4. COMPLEX COMBINED WORKFLOW & FRACTIONAL TIMESTAMP TESTS
# =============================================================================

def test_av_sync_combined_workflow_with_fractional_cuts(sample_video):
    """
    Representative complex edit:
    - Multiple non-integer cuts (fractional timestamps)
    - Subrange speed change (1.25x)
    - Reordered segments
    - Mute and beep audio effects
    Verifies that cumulative frame quantization guarantees < 1 frame skew and duration match.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_cut(0.45, 1.35)
    tl.apply_cut(2.75, 3.85)
    tl.apply_cut(5.15, 6.25)
    tl.apply_cut(7.65, 8.45)
    tl.apply_speed_change(1.25, source_start=1.35, source_end=2.75)
    tl.add_effect("mute", 3.85, 4.5)
    tl.add_effect("beep", 6.5, 7.2)

    # Reorder remaining segments
    num_segs = len(tl.segments)
    reordered_idx = list(reversed(range(num_segs)))
    tl.reorder_segments(reordered_idx)

    expected_dur = tl.total_duration
    plan = EditPlan(prompt="Complex workflow with non-integer cuts", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-complex-workflow"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["is_aligned_within_one_frame"] is True
    # The A/V skew must be strictly less than one video frame
    assert sync_info["av_skew_frames"] <= 1.0
    # Final exported video and audio durations must be within one frame of expected duration
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


def test_timeline_frame_quantization_methods():
    """
    Tests Timeline.snap_to_frame and Timeline.align_to_frames for consistent
    frame-rate rounding.
    """
    fps = 30.0
    frame_dur = 1.0 / fps  # 0.033333...s
    tl = Timeline(source_duration=10.0, fps=fps)

    # 1. snap_to_frame tests
    assert tl.snap_to_frame(0.0) == 0.0
    # 0.034s is closest to frame 1 (0.0333s)
    assert abs(tl.snap_to_frame(0.034) - frame_dur) < 1e-4
    # 1.0s is exactly 30 frames
    assert tl.snap_to_frame(1.0) == 1.0

    # 2. align_to_frames tests
    tl.apply_cut(0.123, 1.879)
    tl.align_to_frames()
    for seg in tl.segments:
        # Every segment start and end should be an exact multiple of frame_dur
        start_frames = round(seg.source_start / frame_dur)
        end_frames = round(seg.source_end / frame_dur)
        assert abs(seg.source_start - round(start_frames * frame_dur, 4)) < 1e-3
        assert abs(seg.source_end - round(end_frames * frame_dur, 4)) < 1e-3


def test_silent_video_duration_preservation(sample_silent_video):
    """
    Verify that video-only clips (no audio stream) maintain frame duration accuracy
    without crashing or desyncing.
    """
    meta = inspect_media(sample_silent_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    tl.apply_cut(1.0, 3.0)
    expected_dur = tl.total_duration

    plan = EditPlan(prompt="Cut silent clip", operations=[], timeline=tl.to_dict())
    job_id = "test-sync-silent"
    out_path, out_meta, _, _ = VideoProcessor.process_video(job_id, sample_silent_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["has_audio"] is False
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
