"""
ClipPilot AI - Feature 8: Full Integration Testing and Final Verification Suite
================================================================================
Comprehensive end-to-end integration tests verifying all 8 required criteria:
1. Original media immutability: SHA-256 is consistent before and after editing.
2. Content anchoring: Captions and audio effects remain anchored after cuts, trims, speed, and reordering.
3. Three-way instruction protocol: APPLIED, NEEDS_CLARIFICATION, REJECTED.
4. Determinism: Three identical runs produce identical canonical timeline JSON and timeline_hash.
5. Audio/Video synchronization: FFprobe verification of exported media (sync & duration within one frame).
6. Undo/Redo: Complete state restoration and redo stack clearing on new edit.
7. Timestamp reference policy: Documented source default, explicit timeline conversion, and conflict clarification.
8. End-to-end workflows: MP4 export/download, JSON receipt, and user job history.
"""

import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.hash_utils import calculate_file_sha256
from app.services.media_inspector import inspect_media, inspect_av_sync
from app.services.timeline_model import Timeline
from app.services.operation_processor import OperationProcessor
from app.services.video_processor import VideoProcessor
from app.schemas.job import MediaMetadata, InstructionStatus
from app.schemas.edit_plan import EditPlan


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_video():
    path = settings.SAMPLE_DIR / "sample_1_talking_head.mp4"
    assert path.exists(), f"Sample video not found at {path}"
    return str(path)


@pytest.fixture
def sample_metadata():
    return MediaMetadata(
        duration=10.0,
        width=1920,
        height=1080,
        aspect_ratio="16:9",
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        has_audio=True,
        size_bytes=2000000,
        format_name="mp4"
    )


# =============================================================================
# 1. ORIGINAL MEDIA IMMUTABILITY (SHA-256 BEFORE AND AFTER)
# =============================================================================

def test_v1_original_media_sha256_immutability(client):
    """
    Verification 1:
    Original media remains completely unchanged; SHA-256 is verified before
    and after extensive editing and rendering.
    """
    # 1. Create demo job and record disk SHA-256
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]

    upload_file = settings.UPLOAD_DIR / job_id / "original_sample_talking_head.mp4"
    assert upload_file.exists()
    sha_initial = calculate_file_sha256(upload_file)
    assert job["original_file_hash"] == sha_initial

    # 2. Perform editing operations on the job
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Mute audio from 2s to 4s"})
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Add caption 'Demo' from 1s to 3s"})

    # 3. Process/render the video
    proc_res = client.post(
        f"/api/jobs/{job_id}/process",
        json={"approved_plan": job["edit_plan"]}
    )
    assert proc_res.status_code == 200

    # Poll until completed
    for _ in range(30):
        poll_res = client.get(f"/api/jobs/{job_id}")
        assert poll_res.status_code == 200
        if poll_res.json()["status"] == "completed":
            break

    # 4. Verify original source media file was NOT modified by rendering
    sha_after_render = calculate_file_sha256(upload_file)
    assert sha_after_render == sha_initial, "Source file SHA-256 must remain identical"

    # 5. Check integrity check endpoint
    integrity_res = client.get(f"/api/jobs/{job_id}/verify-integrity")
    assert integrity_res.status_code == 200
    integrity = integrity_res.json()
    assert integrity["verified"] is True
    assert integrity["original_hash"] == sha_initial
    assert integrity["current_hash"] == sha_initial


# =============================================================================
# 2. CONTENT ANCHORING (EFFECTS TRACK MEDIA ACROSS TRANSFORMS)
# =============================================================================

def test_v2_anchored_effects_across_timeline_transformations():
    """
    Verification 2:
    Captions and audio effects remain correctly anchored to intended source
    content after cuts, trims, speed changes, and clip reordering.
    """
    tl = Timeline(source_duration=12.0, source_id="src_anchor_v2")

    # Anchor a caption at source content [6.0s - 9.0s]
    tl.add_effect("caption", 6.0, 9.0, label="Anchor Caption")
    # Anchor a censorship beep at source content [1.0s - 2.5s]
    tl.add_effect("beep", 1.0, 2.5, label="Bleep")

    # 1. Apply a cut earlier in the video: cut [3.0s - 5.0s] (duration removes 2.0s)
    tl.apply_cut(3.0, 5.0)
    # Timeline has 2 segments: [0-3s] and [5-12s]
    # Effect at [6.0s - 9.0s] is inside segment 1 (offset by 2.0s cut)
    effects_1 = tl.transform_effects()
    cap_eff = next(e for e in effects_1 if e.type == "caption")
    assert cap_eff.timeline_start == 4.0  # 3.0 + (6.0 - 5.0)
    assert cap_eff.timeline_end == 7.0    # 3.0 + (9.0 - 5.0)

    # 2. Apply 2.0x speed change on segment 1 [5.0s - 12.0s]
    tl.set_segment_speed(1, 2.0)
    # At 2x speed, segment duration is halved.
    # Source [6-9s] duration is 3.0s / 2 = 1.5s on timeline!
    effects_2 = tl.transform_effects()
    cap_eff2 = next(e for e in effects_2 if e.type == "caption")
    assert cap_eff2.timeline_start == 3.5  # 3.0 + (6.0 - 5.0) / 2
    assert cap_eff2.timeline_end == 5.0    # 3.5 + 1.5

    # 3. Reorder segments: clip 1 plays before clip 0
    tl.reorder_segments([1, 0])
    effects_3 = tl.transform_effects()
    cap_eff3 = next(e for e in effects_3 if e.type == "caption")
    # Now clip 1 starts at timeline 0.0s!
    # So caption starts at (6.0 - 5.0) / 2 = 0.5s!
    assert cap_eff3.timeline_start == 0.5
    assert cap_eff3.timeline_end == 2.0


# =============================================================================
# 3. THREE-WAY INSTRUCTION RESPONSE CONTRACT
# =============================================================================

def test_v3_instruction_three_way_response_contract(sample_metadata):
    """
    Verification 3:
    Every instruction strictly returns APPLIED, NEEDS_CLARIFICATION, or REJECTED.
    """
    tl = Timeline(source_duration=10.0, source_id="src_contract")

    # A. Valid Instruction -> APPLIED
    res_app = OperationProcessor.process_instruction(
        instruction="Mute audio from 2s to 4s",
        timeline=tl,
        metadata=sample_metadata
    )
    assert res_app.status == InstructionStatus.APPLIED
    assert res_app.operation["type"] == "MUTE"
    assert res_app.operationId is not None

    # B. Ambiguous Instruction -> NEEDS_CLARIFICATION
    res_clar = OperationProcessor.process_instruction(
        instruction="Cut out the noisy part",
        timeline=tl,
        metadata=sample_metadata
    )
    assert res_clar.status == InstructionStatus.NEEDS_CLARIFICATION
    assert res_clar.clarification_prompt is not None

    # C. Unsupported / Invalid Instruction -> REJECTED with atomic rollback
    tl_snapshot = tl.to_dict()
    res_rej = OperationProcessor.process_instruction(
        instruction="Mute from 8s to 2s",  # Invalid inverted range
        timeline=tl,
        metadata=sample_metadata
    )
    assert res_rej.status == InstructionStatus.REJECTED
    assert res_rej.error_code in ("INVALID_RANGE", "INVALID_TIME_RANGE")
    # Timeline is uncorrupted
    assert tl.to_dict() == tl_snapshot


# =============================================================================
# 4. THREE IDENTICAL RUNS PRODUCE IDENTICAL CANONICAL JSON & HASH
# =============================================================================

def test_v4_three_identical_runs_produce_identical_canonical_json_and_hash():
    """
    Verification 4:
    Three identical runs produce identical canonical timeline JSON and timeline hashes.
    """
    def generate_timeline() -> Timeline:
        t = Timeline(source_duration=15.0, source_id="src_determ")
        t.apply_cut(2.0, 4.0)
        t.apply_speed_change(1.5, source_start=5.0, source_end=8.0)
        t.add_effect("caption", 0.5, 2.0, parameters={"text": "Intro"}, label="Intro")
        t.add_effect("mute", 8.0, 10.0)
        return t

    run1 = generate_timeline()
    run2 = generate_timeline()
    run3 = generate_timeline()

    j1, h1 = run1.to_canonical_json(), run1.timeline_hash
    j2, h2 = run2.to_canonical_json(), run2.timeline_hash
    j3, h3 = run3.to_canonical_json(), run3.timeline_hash

    assert j1 == j2 == j3
    assert h1 == h2 == h3
    assert len(h1) == 64


# =============================================================================
# 5. AUDIO/VIDEO SYNC AND DURATION WITHIN ONE FRAME (FFPROBE)
# =============================================================================

def test_v5_exported_media_av_sync_and_duration_ffprobe(sample_video):
    """
    Verification 5:
    Exported audio/video sync and duration meet the one-frame tolerance.
    Verified on rendered MP4 file via FFprobe.
    """
    meta = inspect_media(sample_video)
    fps = meta.fps or 30.0
    frame_dur = 1.0 / fps

    tl = Timeline(source_duration=meta.duration, fps=fps)
    # Cut 2.0s to 4.0s
    tl.apply_cut(2.0, 4.0)
    # Speed 1.5x on 4.0s to 7.0s
    tl.apply_speed_change(1.5, source_start=4.0, source_end=7.0)
    expected_dur = tl.total_duration

    plan = EditPlan(prompt="Cut and speed sync test", operations=[], timeline=tl.to_dict())
    job_id = "test-feat8-sync"
    out_path, _, _, _ = VideoProcessor.process_video(job_id, sample_video, plan)

    sync_info = inspect_av_sync(out_path)
    assert sync_info["has_audio"] is True
    # A/V skew must be strictly <= 1.0 frame
    assert sync_info["is_aligned_within_one_frame"] is True
    assert sync_info["av_skew_frames"] < 1.0
    # Final video and audio durations within one frame of expected timeline duration
    assert abs(sync_info["video_duration"] - expected_dur) <= frame_dur
    assert abs(sync_info["audio_duration"] - expected_dur) <= frame_dur


# =============================================================================
# 6. UNDO/REDO COMPLETE WORKFLOW & REDO STACK CLEARING
# =============================================================================

def test_v6_complete_undo_redo_and_redo_clearing(client):
    """
    Verification 6:
    Undo/redo restores timeline states, and a new edit after undo clears redo history.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Initial state index 0
    hist0 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist0["current_index"] == 0

    # Edit 1: Speed up 2x
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Speed up by 2x"})
    # Edit 2: Mute audio
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Mute audio from 1s to 2s"})
    # Edit 3: Add caption
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Add caption 'Test' from 2s to 3s"})

    hist3 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist3["current_index"] == 3
    assert hist3["history_length"] == 4
    assert hist3["can_undo"] is True
    assert hist3["can_redo"] is False

    # Undo twice: from state 3 to state 2, then state 2 to state 1
    u1 = client.post(f"/api/jobs/{job_id}/undo").json()
    assert u1["current_index"] == 2
    assert u1["can_redo"] is True

    u2 = client.post(f"/api/jobs/{job_id}/undo").json()
    assert u2["current_index"] == 1
    assert u2["can_undo"] is True
    assert u2["can_redo"] is True

    # Now apply a NEW edit (Edit 4) after undo:
    # This MUST branch history and completely clear the redo stack!
    op_new = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Cut from 1s to 2s"}
    )
    assert op_new.status_code == 200

    hist_after = client.get(f"/api/jobs/{job_id}/history").json()
    # History length should now be 3 (state 0, state 1, new state 2)
    assert hist_after["current_index"] == 2
    assert hist_after["history_length"] == 3
    assert hist_after["can_undo"] is True
    assert hist_after["can_redo"] is False, "Redo stack must be cleared after branching edit"


# =============================================================================
# 7. TIMESTAMP REFERENCE POLICY
# =============================================================================

def test_v7_timestamp_reference_policy_and_clarification(client, sample_metadata):
    """
    Verification 7:
    Timestamp references follow the documented policy (source default,
    explicit timeline conversion, conflict clarification).
    """
    tl = Timeline(source_duration=10.0, source_id="src_policy")
    tl.apply_trim_start(3.0)  # Diverged: timeline 0.0s corresponds to source 3.0s

    # 1. Default policy references source coordinates
    out_default = OperationProcessor.process_instruction(
        instruction="Mute audio from 4s to 6s",
        timeline=tl,
        metadata=sample_metadata
    )
    assert out_default.status == InstructionStatus.APPLIED
    assert out_default.time_reference == "source"

    # 2. Explicit timeline keyword converts coordinates correctly
    out_timeline = OperationProcessor.process_instruction(
        instruction="Mute audio from 1s to 3s on timeline",
        timeline=tl,
        metadata=sample_metadata
    )
    assert out_timeline.status == InstructionStatus.APPLIED
    assert out_timeline.time_reference == "timeline"
    # Timeline [1s, 3s] maps to source [4s, 6s]
    assert out_timeline.converted_timestamps["source_intervals"][0]["source_start"] == 4.0
    assert out_timeline.converted_timestamps["source_intervals"][0]["source_end"] == 6.0

    # 3. Conflicting time references return NEEDS_CLARIFICATION
    out_conflict = OperationProcessor.process_instruction(
        instruction="Mute audio from 1s to 3s in source on timeline",
        timeline=tl,
        metadata=sample_metadata
    )
    assert out_conflict.status == InstructionStatus.NEEDS_CLARIFICATION
    assert out_conflict.error_code == "CONFLICTING_TIME_REFERENCE"


# =============================================================================
# 8. MP4 EXPORT/DOWNLOAD, JSON RECEIPT, AND HISTORY LIFECYCLE
# =============================================================================

def test_v8_mp4_export_receipt_and_history_lifecycle(client):
    """
    Verification 8:
    MP4 export/download, JSON receipt generation, and job history work end to end.
    """
    # 1. Create and complete demo job
    demo_res = client.post("/api/jobs/demo")
    assert demo_res.status_code == 200
    job = demo_res.json()
    job_id = job["id"]

    proc_res = client.post(f"/api/jobs/{job_id}/process", json={"approved_plan": job["edit_plan"]})
    assert proc_res.status_code == 200

    for _ in range(30):
        pj = client.get(f"/api/jobs/{job_id}").json()
        if pj["status"] == "completed":
            break

    # 2. Verify MP4 export download
    dl_res = client.get(f"/api/jobs/{job_id}/download")
    assert dl_res.status_code == 200
    assert "video/mp4" in dl_res.headers.get("content-type", "")
    assert "ClipPilot_Edited_Video.mp4" in dl_res.headers.get("content-disposition", "")
    assert len(dl_res.content) > 50000

    # 3. Verify JSON audit receipt download
    rcpt_res = client.get(f"/api/jobs/{job_id}/receipt")
    assert rcpt_res.status_code == 200
    rcpt = rcpt_res.json()
    assert rcpt["job_id"] == job_id
    assert rcpt["source_integrity"]["verified_identical"] is True
    assert "timeline_hash" in rcpt
    assert len(rcpt["timeline_hash"]) == 64
    assert len(rcpt["applied_operations"]) > 0

    # 4. Verify job history endpoint
    jobs_res = client.get(f"/api/jobs/{job_id}")
    assert jobs_res.status_code == 200
    assert jobs_res.json()["id"] == job_id
