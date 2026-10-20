"""
ClipPilot AI - Feature 4: Deterministic Timeline Automated Test Suite
=====================================================================
Validates that identical video inputs, edit instructions, and edit plans
always produce the exact same canonical timeline JSON and SHA-256 timeline_hash.

Verifications:
1. Three-way execution repeatability across identical edit plans and timelines.
2. Elimination of random UUIDs (clip_id, effect_id are deterministic).
3. Canonical float normalization, avoiding float precision noise or -0.0.
4. Independent effect order normalization.
5. Round-trip serialization invariance (Timeline -> dict -> Timeline).
6. API endpoint /receipt exposure of deterministic timeline_hash.
"""

import json
import hashlib
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.timeline_model import Timeline, TimelineSegment, ContentAwareEffect
from app.services.prompt_parser import PromptParser
from app.services.operation_processor import OperationProcessor
from app.schemas.job import MediaMetadata
from app.schemas.instruction_response import InstructionStatus
from app.database.models import JobModel, JobStatus


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_metadata():
    return MediaMetadata(
        duration=12.0,
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
# 1. THREE-WAY REPETITION TESTS (MANDATORY REQUIREMENT)
# =============================================================================

def test_three_way_timeline_transformations_repetition():
    """
    Requirement: Run the same edit plan three times and verify that all three
    canonical JSON outputs and hashes match exactly.
    """
    def run_pipeline() -> Timeline:
        tl = Timeline(source_duration=12.0, source_id="src_canon_test")
        # Step 1: Internal cut [3.0s - 5.0s]
        tl.apply_cut(3.0, 5.0)
        # Step 2: Speed change 2.0x on subrange [1.0s - 2.0s]
        tl.apply_speed_change(2.0, 1.0, 2.0)
        # Step 3: Add caption [0.5s - 2.5s] (spans across cut)
        tl.add_effect("caption", 0.5, 2.5, parameters={"text": "Title Intro"}, label="Title Intro")
        # Step 4: Add mute [6.0s - 8.0s]
        tl.add_effect("mute", 6.0, 8.0)
        # Step 5: Add visual effect [9.0s - 11.0s]
        tl.add_effect("visual_effect", 9.0, 11.0, parameters={"effect": "boxblur"})
        return tl

    # Run 1
    tl1 = run_pipeline()
    json1 = tl1.to_canonical_json()
    hash1 = tl1.timeline_hash

    # Run 2
    tl2 = run_pipeline()
    json2 = tl2.to_canonical_json()
    hash2 = tl2.timeline_hash

    # Run 3
    tl3 = run_pipeline()
    json3 = tl3.to_canonical_json()
    hash3 = tl3.timeline_hash

    # Verify SHA-256 format
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1.lower())

    # Exact byte-for-byte and hash match across all 3 runs
    assert json1 == json2, "Run 1 and Run 2 canonical JSON must match"
    assert json2 == json3, "Run 2 and Run 3 canonical JSON must match"
    assert hash1 == hash2, "Run 1 and Run 2 timeline_hash must match"
    assert hash2 == hash3, "Run 2 and Run 3 timeline_hash must match"


def test_three_way_prompt_parser_edit_plan_repetition(sample_metadata):
    """
    Requirement: Verify that parsing the same prompt 3 times produces
    identical canonical timeline JSON and identical timeline_hash on EditPlan.
    """
    prompt = "Cut out from 3s to 5s, speed up 2x, and add caption 'Scene One' from 1s to 3s"

    plan1 = PromptParser.parse(prompt, sample_metadata)
    plan2 = PromptParser.parse(prompt, sample_metadata)
    plan3 = PromptParser.parse(prompt, sample_metadata)

    assert plan1.timeline is not None
    assert plan2.timeline is not None
    assert plan3.timeline is not None

    hash1 = plan1.timeline_hash
    hash2 = plan2.timeline_hash
    hash3 = plan3.timeline_hash

    assert hash1 is not None and len(hash1) == 64
    assert hash1 == hash2 == hash3

    json1 = json.dumps(plan1.timeline, sort_keys=True, separators=(',', ':'))
    json2 = json.dumps(plan2.timeline, sort_keys=True, separators=(',', ':'))
    json3 = json.dumps(plan3.timeline, sort_keys=True, separators=(',', ':'))

    assert json1 == json2 == json3


def test_three_way_operation_processor_sequential_instructions(sample_metadata):
    """
    Requirement: Sequential instruction execution across 3 independent timelines
    must yield identical intermediate and final canonical JSON and timeline_hash.
    """
    instructions = [
        "Cut out from 2s to 4s",
        "Speed up 2x",
        "Mute audio from 5s to 7s",
        'Add caption "Chapter 1" from 0s to 2s',
        "Boost volume by 50%"
    ]

    def execute_all() -> Timeline:
        tl = Timeline(source_duration=sample_metadata.duration, source_id="src_test")
        for inst in instructions:
            outcome = OperationProcessor.process_instruction(
                instruction=inst,
                timeline=tl,
                metadata=sample_metadata
            )
            assert outcome.status == InstructionStatus.APPLIED
        return tl

    tl1 = execute_all()
    tl2 = execute_all()
    tl3 = execute_all()

    assert tl1.to_canonical_json() == tl2.to_canonical_json() == tl3.to_canonical_json()
    assert tl1.timeline_hash == tl2.timeline_hash == tl3.timeline_hash


# =============================================================================
# 2. NO RANDOM IDS & DETERMINISTIC NAMING TESTS
# =============================================================================

def test_deterministic_clip_and_effect_ids():
    """
    Verifies that clip IDs and effect IDs are 100% deterministic and do NOT use random UUIDs.
    """
    tl = Timeline(source_duration=10.0, source_id="src_test")
    # Initial clip must be clip_0
    assert tl.segments[0].clip_id == "clip_0"

    # Add 3 effects without explicit IDs
    e0 = tl.add_effect("caption", 0.0, 2.0)
    e1 = tl.add_effect("mute", 3.0, 4.0)
    e2 = tl.add_effect("beep", 5.0, 6.0)

    assert e0.effect_id == "eff_0"
    assert e1.effect_id == "eff_1"
    assert e2.effect_id == "eff_2"

    # Cut segment in the middle: splits clip_0 into clip_0_a and clip_0_b
    tl.apply_cut(3.0, 5.0)
    assert len(tl.segments) == 2
    assert tl.segments[0].clip_id == "clip_0_a"
    assert tl.segments[1].clip_id == "clip_0_b"


# =============================================================================
# 3. NORMALIZED ORDERING & CANONICAL SERIALIZATION TESTS
# =============================================================================

def test_canonical_ordering_independent_of_effect_insertion_sequence():
    """
    Adding the same effects in different insertion orders must produce
    identical canonical dictionaries and identical timeline_hash.
    """
    # Timeline A: add Mute first, then Caption
    tl_a = Timeline(source_duration=10.0, source_id="src_shared")
    tl_a.add_effect("mute", 5.0, 7.0, effect_id="eff_mute")
    tl_a.add_effect("caption", 1.0, 3.0, parameters={"text": "Intro"}, effect_id="eff_cap")

    # Timeline B: add Caption first, then Mute
    tl_b = Timeline(source_duration=10.0, source_id="src_shared")
    tl_b.add_effect("caption", 1.0, 3.0, parameters={"text": "Intro"}, effect_id="eff_cap")
    tl_b.add_effect("mute", 5.0, 7.0, effect_id="eff_mute")

    # Canonical representations must be strictly identical
    assert tl_a.to_canonical_json() == tl_b.to_canonical_json()
    assert tl_a.timeline_hash == tl_b.timeline_hash


def test_float_precision_and_negative_zero_normalization():
    """
    Verifies that float representations like 2.0000000000000004 or -0.0
    are normalized to clean 4-decimal floats (2.0 and 0.0).
    """
    norm_zero = Timeline._normalize_num(-0.0)
    assert norm_zero == 0.0
    assert str(norm_zero) == "0.0"

    norm_float = Timeline._normalize_num(2.0000000000000004)
    assert norm_float == 2.0


def test_round_trip_serialization_preserves_canonical_hash():
    """
    Reconstructing a Timeline from its dict representation (Timeline.from_dict)
    must produce the exact same canonical JSON and timeline_hash.
    """
    tl = Timeline(source_duration=10.0, source_id="src_roundtrip")
    tl.apply_cut(2.0, 4.0)
    tl.apply_speed_change(1.5, 4.0, 6.0)
    tl.add_effect("caption", 0.5, 3.0, parameters={"text": "Split Test"})
    tl.add_effect("mute", 7.0, 9.0)

    original_json = tl.to_canonical_json()
    original_hash = tl.timeline_hash

    # Round trip
    dict_repr = tl.to_dict()
    assert "timeline_hash" in dict_repr
    assert dict_repr["timeline_hash"] == original_hash

    restored_tl = Timeline.from_dict(dict_repr)
    assert restored_tl.to_canonical_json() == original_json
    assert restored_tl.timeline_hash == original_hash


# =============================================================================
# 4. REST API & EDIT RECEIPT DETERMINISM TESTS
# =============================================================================

def test_api_receipt_includes_deterministic_timeline_hash(client, db):
    """
    Verifies that GET /jobs/{id}/receipt returns the deterministic timeline_hash
    and matches between successive calls and job plan state.
    """
    # 1. Create Demo Job
    r_demo = client.post("/api/jobs/demo")
    assert r_demo.status_code == 200
    job_id = r_demo.json()["id"]

    # 2. Apply instruction
    r_inst = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Cut out from 3s to 5s"}
    )
    assert r_inst.status_code == 200
    out_inst = r_inst.json()
    assert out_inst["status"] == "APPLIED"
    assert "timeline_hash" in out_inst["timeline"]
    inst_hash = out_inst["timeline"]["timeline_hash"]
    assert len(inst_hash) == 64

    # Mark job as completed so edit receipt endpoint allows retrieval
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    job.status = JobStatus.COMPLETED.value
    db.commit()

    # 3. Verify EditReceipt contains the exact timeline_hash
    r_receipt = client.get(f"/api/jobs/{job_id}/receipt")
    assert r_receipt.status_code == 200
    receipt_data = r_receipt.json()
    assert "timeline_hash" in receipt_data
    assert receipt_data["timeline_hash"] == inst_hash
    assert receipt_data["timeline"]["timeline_hash"] == inst_hash
