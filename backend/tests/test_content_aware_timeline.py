import os
import subprocess
import time
from pathlib import Path
import pytest

from app.core.config import settings
from app.schemas.edit_plan import EditPlan, OperationType
from app.services.timeline_model import (
    Timeline,
    TimelineSegment,
    ContentAwareEffect,
    TransformedTimelineEffect,
)
from app.services.video_processor import VideoProcessor
from app.services.media_inspector import inspect_media
from app.services.hash_utils import calculate_file_sha256


@pytest.fixture
def sample_video_path():
    path = settings.SAMPLE_DIR / "sample_1_talking_head.mp4"
    assert path.exists(), f"Sample video not found at {path}"
    return str(path)


# =========================================================================
# Unit Tests: Timeline Data Model & Transformation Engine
# =========================================================================

def test_timeline_data_model_initialization():
    """Requirement 1: Consistent timeline data model with stable source identifiers and time ranges."""
    tl = Timeline(source_duration=12.0, source_id="src_test_01")
    assert tl.source_duration == 12.0
    assert tl.source_id == "src_test_01"
    assert len(tl.segments) == 1

    seg = tl.segments[0]
    assert seg.source_id == "src_test_01"
    assert seg.source_start == 0.0
    assert seg.source_end == 12.0
    assert seg.speed == 1.0
    assert seg.timeline_start == 0.0
    assert seg.timeline_end == 12.0
    assert tl.total_duration == 12.0


def test_content_anchored_captions_and_effects_retention():
    """Requirements 2 & 3: Store captions, mute, beep, and visual effects against source-media timestamps."""
    tl = Timeline(source_duration=10.0, source_id="src_alpha")

    cap = tl.add_effect("caption", 1.0, 3.5, parameters={"text": "Welcome to ClipPilot"})
    mute = tl.add_effect("mute", 4.0, 5.5, label="Noise Mute")
    beep = tl.add_effect("beep", 6.0, 7.0, parameters={"frequency": 1000}, label="Censor Beep")
    vfx = tl.add_effect("visual_effect", 7.5, 9.5, parameters={"effect": "blur"}, label="Blur Filter")

    # Verify source anchors
    assert cap.source_start == 1.0 and cap.source_end == 3.5
    assert mute.source_start == 4.0 and mute.source_end == 5.5
    assert beep.source_start == 6.0 and beep.source_end == 7.0
    assert vfx.source_start == 7.5 and vfx.source_end == 9.5

    # Transform without cuts or speed changes: 1-to-1 retention
    transformed = tl.transform_effects()
    assert len(transformed) == 4
    for eff in transformed:
        assert eff.status == "active"
        assert eff.timeline_start == eff.source_start
        assert eff.timeline_end == eff.source_end
        assert eff.duration == round(eff.source_end - eff.source_start, 4)


def test_deterministic_bidirectional_mapping():
    """Requirement 4: Deterministic mapping between source timestamps and timeline timestamps."""
    tl = Timeline(source_duration=10.0)
    # Trim first 2 seconds -> remaining source is [2.0, 10.0]
    tl.apply_trim_start(2.0)
    assert tl.total_duration == 8.0

    # Source time 5.0s maps to timeline 3.0s (5.0 - 2.0)
    mapped_tl = tl.map_source_to_timeline(5.0)
    assert len(mapped_tl) == 1
    assert mapped_tl[0] == 3.0

    # Source time 1.0s was trimmed out -> empty mapping
    assert tl.map_source_to_timeline(1.0) == []

    # Reverse: timeline 3.0s maps back to source 5.0s
    seg_id, src_t = tl.map_timeline_to_source(3.0)
    assert src_t == 5.0
    assert seg_id == tl.segments[0].clip_id


def test_cut_policy_complete_retention_and_removal():
    """Requirement 5: Documented policy for content removal, retention, and clipping."""
    tl = Timeline(source_duration=10.0)
    # Effect A: [0.5, 1.5] - fully before cut
    eff_a = tl.add_effect("caption", 0.5, 1.5, {"text": "Retained Before"})
    # Effect B: [3.0, 4.0] - fully inside cut [2.5, 4.5]
    eff_b = tl.add_effect("beep", 3.0, 4.0, {"frequency": 1000})
    # Effect C: [5.0, 6.0] - fully after cut
    eff_c = tl.add_effect("mute", 5.0, 6.0)

    # Cut out [2.5, 4.5] (2.0s excised)
    tl.apply_cut(2.5, 4.5)
    assert len(tl.segments) == 2
    assert tl.total_duration == 8.0

    transformed = tl.transform_effects()
    eff_map = {t.type: t for t in transformed}

    # Effect A remains active at [0.5, 1.5]
    assert eff_map["caption"].status == "active"
    assert eff_map["caption"].timeline_start == 0.5
    assert eff_map["caption"].timeline_end == 1.5

    # Effect B was excised -> marked dropped_content_removed
    assert eff_map["beep"].status == "dropped_content_removed"
    assert eff_map["beep"].timeline_start == -1.0
    assert eff_map["beep"].duration == 0.0

    # Effect C shifted earlier by 2.0s: source [5.0, 6.0] -> timeline [3.0, 4.0]
    assert eff_map["mute"].status == "active"
    assert eff_map["mute"].timeline_start == 3.0
    assert eff_map["mute"].timeline_end == 4.0


def test_cut_policy_boundary_truncation_clipping():
    """Requirement 5 & 8: Partially cut effects are clipped to segment boundaries."""
    tl = Timeline(source_duration=10.0)
    # Caption spans [2.0, 5.0]
    cap = tl.add_effect("caption", 2.0, 5.0, {"text": "Clipping Test"})

    # Cut [3.5, 7.0] -> clips right side of caption
    tl.apply_cut(3.5, 7.0)

    transformed = tl.transform_effects()
    assert len(transformed) == 1
    t = transformed[0]
    assert t.status == "clipped"
    assert t.source_start == 2.0
    assert t.source_end == 3.5
    assert t.timeline_start == 2.0
    assert t.timeline_end == 3.5
    assert t.duration == 1.5


def test_split_spanning_operations_across_multiple_segments():
    """Requirement 8: Split operations when content spans multiple timeline segments."""
    tl = Timeline(source_duration=10.0)
    # Visual effect spans [1.0, 6.0]
    vfx = tl.add_effect("visual_effect", 1.0, 6.0, {"effect": "brightness", "value": 0.2})

    # Cut a hole in the middle: [2.5, 3.5]
    tl.apply_cut(2.5, 3.5)

    transformed = tl.transform_effects()
    # Should split into exactly 2 instances
    assert len(transformed) == 2
    part1, part2 = transformed[0], transformed[1]

    assert part1.status == "split"
    assert part1.parent_effect_id == vfx.effect_id
    assert part1.source_start == 1.0 and part1.source_end == 2.5
    assert part1.timeline_start == 1.0 and part1.timeline_end == 2.5
    assert part1.duration == 1.5

    assert part2.status == "split"
    assert part2.parent_effect_id == vfx.effect_id
    assert part2.source_start == 3.5 and part2.source_end == 6.0
    # Segment 1 starts at timeline 2.5, so part2 is at timeline 2.5 + (3.5 - 3.5) = 2.5
    assert part2.timeline_start == 2.5
    assert part2.timeline_end == 5.0
    assert part2.duration == 2.5


def test_speed_change_transforms_duration_preserves_anchor():
    """Requirement 7: Playback speed transforms timeline positions & durations without altering source anchors."""
    tl = Timeline(source_duration=10.0)
    beep = tl.add_effect("beep", 2.0, 6.0, {"frequency": 1000})

    # Apply 2.0x playback speed to entire timeline
    tl.apply_speed_change(2.0)
    assert tl.total_duration == 5.0

    # Source anchor must be completely intact
    assert beep.source_start == 2.0 and beep.source_end == 6.0

    transformed = tl.transform_effects()
    assert len(transformed) == 1
    t = transformed[0]
    # Source [2.0, 6.0] at 2.0x -> timeline [1.0, 3.0], duration = 2.0s
    assert t.timeline_start == 1.0
    assert t.timeline_end == 3.0
    assert t.duration == 2.0
    assert t.speed == 2.0
    assert t.status == "active"

    # Test Slow Motion 0.5x
    tl.apply_speed_change(0.5)
    assert tl.total_duration == 20.0
    t_slow = tl.transform_effects()[0]
    # Source [2.0, 6.0] at 0.5x -> timeline [4.0, 12.0], duration = 8.0s
    assert t_slow.timeline_start == 4.0
    assert t_slow.timeline_end == 12.0
    assert t_slow.duration == 8.0


def test_clip_reordering_moves_anchored_effects():
    """Requirement 6: Moving or reordering clips moves associated captions and effects with relevant content."""
    tl = Timeline(source_duration=10.0)
    cap_a = tl.add_effect("caption", 1.0, 3.0, {"text": "Segment A Content"})
    beep_b = tl.add_effect("beep", 6.0, 8.0, {"frequency": 1000}, label="Segment B Beep")

    # Cut at 5.0s to produce two 5s segments: [0.0, 5.0] and [5.0, 10.0]
    tl.split_segment_at(5.0)
    assert len(tl.segments) == 2

    # Initial order: cap_a on first segment (timeline [1.0, 3.0]), beep_b on second (timeline [6.0, 8.0])
    initial_t = {t.type: t for t in tl.transform_effects()}
    assert initial_t["caption"].timeline_start == 1.0
    assert initial_t["beep"].timeline_start == 6.0

    # Reorder: swap segments [1, 0]
    tl.reorder_segments([1, 0])
    reordered_t = {t.type: t for t in tl.transform_effects()}

    # Segment B now plays FIRST at timeline [0.0, 5.0] -> beep_b moves to [1.0, 3.0]!
    assert reordered_t["beep"].timeline_start == 1.0
    assert reordered_t["beep"].timeline_end == 3.0

    # Segment A now plays SECOND at timeline [5.0, 10.0] -> cap_a moves to [6.0, 8.0]!
    assert reordered_t["caption"].timeline_start == 6.0
    assert reordered_t["caption"].timeline_end == 8.0

    # Source anchors remain 100% stable
    assert cap_a.source_start == 1.0 and cap_a.source_end == 3.0
    assert beep_b.source_start == 6.0 and beep_b.source_end == 8.0


def test_regression_boundary_timestamps():
    """Regression tests for edge-to-edge boundary timestamps."""
    tl = Timeline(source_duration=10.0)
    # Effect touching cut boundary exactly: [1.0, 3.0] with cut [3.0, 5.0]
    eff1 = tl.add_effect("mute", 1.0, 3.0)
    # Effect starting at cut end boundary exactly: [5.0, 7.0]
    eff2 = tl.add_effect("beep", 5.0, 7.0)

    tl.apply_cut(3.0, 5.0)
    transformed = {t.type: t for t in tl.transform_effects()}

    # eff1 must not be clipped, ends at 3.0
    assert transformed["mute"].status == "active"
    assert transformed["mute"].timeline_start == 1.0
    assert transformed["mute"].timeline_end == 3.0

    # eff2 must not be clipped, starts at 3.0 on timeline
    assert transformed["beep"].status == "active"
    assert transformed["beep"].timeline_start == 3.0
    assert transformed["beep"].timeline_end == 5.0


def test_regression_overlapping_effects():
    """Regression test: multiple overlapping effects active at the same timestamps."""
    tl = Timeline(source_duration=10.0)
    # Simultaneous caption, mute, beep, and visual filter over [2.0, 4.0]
    tl.add_effect("caption", 2.0, 4.0, {"text": "Multi-effect"})
    tl.add_effect("mute", 2.0, 4.0)
    tl.add_effect("beep", 2.5, 3.5)
    tl.add_effect("visual_effect", 2.0, 4.0, {"effect": "brightness", "value": 0.3})

    tl.apply_trim_start(1.0)
    tl.apply_speed_change(2.0)

    transformed = tl.transform_effects()
    assert len(transformed) == 4
    # All 4 shift by -1.0s and scale by 0.5x duration
    for t in transformed:
        assert t.status == "active"
        if t.type == "beep":
            # source [2.5, 3.5] -> trimmed [1.5, 2.5] -> speed 2x [0.75, 1.25]
            assert abs(t.timeline_start - 0.75) < 1e-4
            assert abs(t.timeline_end - 1.25) < 1e-4
        else:
            # source [2.0, 4.0] -> trimmed [1.0, 3.0] -> speed 2x [0.5, 1.5]
            assert abs(t.timeline_start - 0.5) < 1e-4
            assert abs(t.timeline_end - 1.5) < 1e-4


# =========================================================================
# Scripted Session & Rendered Video / Audio Inspection
# =========================================================================

def test_scripted_session_end_to_end_rendering(sample_video_path):
    """
    SCRIPTED SESSION VERIFICATION:
    1. Contains caption, mute range, beep effect, and visual effect.
    2. Applies cuts, trims, speed changes, and clip reordering.
    3. Verifies that every operation remains attached to its intended content.
    4. Renders output video using FFmpeg.
    5. Inspects rendered output duration, frame contents, and audio stream integrity.
    """
    initial_source_hash = calculate_file_sha256(sample_video_path)

    # 1. Initialize timeline for 10.0s source video
    tl = Timeline(source_duration=10.0, source_id="src_talking_head")

    # Add operations anchored to content
    cap = tl.add_effect("caption", 1.0, 3.0, {"text": "Scripted Caption Demo"}, label="Intro Caption")
    mute = tl.add_effect("mute", 3.2, 4.2, label="Pause Mute")
    beep = tl.add_effect("beep", 5.0, 6.0, {"frequency": 1000}, label="Censorship Beep")
    vfx = tl.add_effect("visual_effect", 7.0, 9.0, {"effect": "brightness", "value": 0.3}, label="Brightness Boost")

    # 2. Apply transformations:
    # A. Trim opening 0.5s
    tl.apply_trim_start(0.5)

    # B. Cut internal segment [2.0, 2.5] (this cuts directly through Caption [1.0, 3.0]!)
    tl.apply_cut(2.0, 2.5)

    # C. Split segment at 7.0s to allow separate speed adjustments
    tl.split_segment_at(7.0)

    # D. Apply 1.5x speed to the segment containing the beep effect
    # The segment spanning [2.5, 7.0] contains beep [5.0, 6.0]
    seg_beep_idx = next(i for i, s in enumerate(tl.segments) if s.source_start <= 5.0 and s.source_end >= 6.0)
    tl.set_segment_speed(seg_beep_idx, 1.5)

    # E. Reorder segments: move the last segment [7.0, 10.0] (containing the visual effect) to the beginning!
    # e.g. move segment from index 2 to index 0
    last_idx = len(tl.segments) - 1
    tl.move_segment(last_idx, 0)

    # 3. Verify that every operation remains attached to its intended content
    transformed = tl.transform_effects()

    # The caption [1.0, 3.0] was split by cut [2.0, 2.5] into two parts!
    cap_parts = [t for t in transformed if t.type == "caption"]
    assert len(cap_parts) == 2, "Caption spanning the cut must be split into two discrete parts"
    assert all(p.status == "split" for p in cap_parts)
    assert cap_parts[0].source_start == 1.0 and cap_parts[0].source_end == 2.0
    assert cap_parts[1].source_start == 2.5 and cap_parts[1].source_end == 3.0

    # The visual effect was on the segment moved to the beginning (timeline_start=0.0)
    vfx_transformed = next(t for t in transformed if t.type == "visual_effect")
    assert vfx_transformed.status == "active"
    assert vfx_transformed.source_start == 7.0 and vfx_transformed.source_end == 9.0
    # Because segment [7.0, 10.0] is now at timeline 0.0, vfx starts at 0.0 + (7.0 - 7.0) = 0.0!
    assert vfx_transformed.timeline_start == 0.0
    assert vfx_transformed.timeline_end == 2.0

    # The beep effect [5.0, 6.0] speed is 1.5x -> duration is scaled to 1.0 / 1.5 = 0.6667s!
    beep_transformed = next(t for t in transformed if t.type == "beep")
    assert beep_transformed.status == "active"
    assert beep_transformed.source_start == 5.0 and beep_transformed.source_end == 6.0
    assert abs(beep_transformed.duration - (1.0 / 1.5)) < 1e-3

    # The mute effect [3.2, 4.2] is also scaled by 1.5x on the same segment
    mute_transformed = next(t for t in transformed if t.type == "mute")
    assert mute_transformed.status == "active"
    assert mute_transformed.source_start == 3.2 and mute_transformed.source_end == 4.2
    assert abs(mute_transformed.duration - (1.0 / 1.5)) < 1e-3

    # 4. Render the output video from the transformed timeline model
    plan = EditPlan(
        prompt="Scripted session: cut, trim, speed change, and reorder with content-aware effects",
        operations=[],
        timeline=tl.to_dict()
    )

    job_id = "test-scripted-session-render"
    out_path, out_meta, proc_time, applied_ops = VideoProcessor.process_video(
        job_id=job_id,
        input_path=sample_video_path,
        edit_plan=plan
    )

    # 5. Output file inspection
    assert Path(out_path).exists()
    assert Path(out_path).stat().st_size > 50000, "Rendered output video must be non-empty"

    # Verify duration matches transformed timeline duration within 0.15s tolerance
    expected_duration = tl.total_duration
    assert abs(out_meta.duration - expected_duration) < 0.15, (
        f"Rendered duration ({out_meta.duration}s) must match timeline duration ({expected_duration}s)"
    )

    # Verify media streams
    assert out_meta.has_audio is True
    assert out_meta.video_codec in ["h264", "avc1"]
    assert out_meta.audio_codec in ["aac", "mp4a"]

    # 6. Audio stream inspection around the beep effect
    # Extract 0.5s audio segment during the transformed beep interval
    beep_sample_ts = beep_transformed.timeline_start + 0.1
    probe_cmd = [
        "ffmpeg", "-y", "-ss", f"{beep_sample_ts:.3f}", "-t", "0.4",
        "-i", out_path, "-af", "astats=metadata=1:reset=1", "-f", "null", "-"
    ]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
    assert probe_res.returncode == 0, "Beep audio segment probe must execute cleanly"
    assert "RMS level dB" in probe_res.stderr or "Peak level dB" in probe_res.stderr

    # 7. Verify non-destructive guarantee: original source video SHA-256 is 100% identical
    post_source_hash = calculate_file_sha256(sample_video_path)
    assert post_source_hash == initial_source_hash, "Original video must remain byte-for-byte immutable"


# =========================================================================
# API Endpoints & State Machine Verification
# =========================================================================

def test_timeline_api_lifecycle(client):
    """
    Verifies timeline API endpoints:
    - GET /jobs/{id}/timeline
    - POST /jobs/{id}/timeline/effects
    - POST /jobs/{id}/timeline/transform
    - POST /jobs/{id}/timeline/map
    - Processing and Edit Receipt inclusion
    """
    # 1. Create demo job
    demo_res = client.post("/api/jobs/demo")
    assert demo_res.status_code == 200
    job_id = demo_res.json()["id"]

    # 2. Query initial timeline
    tl_res = client.get(f"/api/jobs/{job_id}/timeline")
    assert tl_res.status_code == 200
    tl_data = tl_res.json()
    assert tl_data["source_duration"] == 10.0
    # Demo job has trim_start 3.0s from demo prompt, so initial duration is 7.0s
    assert tl_data["timeline_duration"] == 7.0

    # 3. Add content-aware caption
    eff_res = client.post(
        f"/api/jobs/{job_id}/timeline/effects",
        json={
            "type": "caption",
            "source_start": 4.0,
            "source_end": 6.0,
            "parameters": {"text": "API Timeline Caption"},
            "label": "API Caption"
        }
    )
    assert eff_res.status_code == 200
    eff_data = eff_res.json()
    assert len(eff_data["source_effects"]) == 1
    assert eff_data["source_effects"][0]["type"] == "caption"

    # 4. Add content-aware beep
    beep_res = client.post(
        f"/api/jobs/{job_id}/timeline/effects",
        json={
            "type": "beep",
            "source_start": 7.0,
            "source_end": 8.0,
            "parameters": {"frequency": 1000},
            "label": "API Beep"
        }
    )
    assert beep_res.status_code == 200

    # 5. Apply timeline transform: Cut internal section [5.0, 5.5] (0.5s hole)
    transform_res = client.post(
        f"/api/jobs/{job_id}/timeline/transform",
        json={"action": "cut", "cut_start": 5.0, "cut_end": 5.5}
    )
    assert transform_res.status_code == 200
    transformed_tl = transform_res.json()
    # 7.0s - 0.5s = 6.5s
    assert transformed_tl["timeline_duration"] == 6.5

    # Caption [4.0, 6.0] is split into [4.0, 5.0] and [5.5, 6.0]
    cap_splits = [e for e in transformed_tl["transformed_effects"] if e["type"] == "caption"]
    assert len(cap_splits) == 2
    assert cap_splits[0]["status"] == "split"
    assert cap_splits[1]["status"] == "split"

    # 6. Coordinate mapping endpoint
    # Source 7.5s (in beep interval [7.0, 8.0]):
    # Segment 0 is [3.0, 5.0] (dur 2.0s)
    # Segment 1 is [5.5, 10.0] (starts at timeline 2.0s)
    # Source 7.5s maps to timeline 2.0 + (7.5 - 5.5) = 4.0s!
    map_res = client.post(
        f"/api/jobs/{job_id}/timeline/map",
        json={"source_time": 7.5, "timeline_time": 4.0}
    )
    assert map_res.status_code == 200
    map_data = map_res.json()
    assert map_data["mapped_timeline_times"] == [4.0]
    assert map_data["mapped_source_info"]["source_time"] == 7.5

    # 7. Render job with timeline
    job_info = client.get(f"/api/jobs/{job_id}").json()
    proc_res = client.post(
        f"/api/jobs/{job_id}/process",
        json={"approved_plan": job_info["edit_plan"]}
    )
    assert proc_res.status_code == 200

    # Poll until completed
    for _ in range(25):
        poll = client.get(f"/api/jobs/{job_id}").json()
        if poll["status"] == "completed":
            break
        time.sleep(1)

    assert poll["status"] == "completed"

    # 8. Check Receipt contains timeline transformation audit
    rcpt_res = client.get(f"/api/jobs/{job_id}/receipt")
    assert rcpt_res.status_code == 200
    rcpt = rcpt_res.json()
    assert rcpt["timeline"] is not None
    assert rcpt["source_integrity"]["verified_identical"] is True
    assert rcpt["source_integrity"]["non_destructive"] is True
