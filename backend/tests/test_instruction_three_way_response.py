import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.operation_processor import OperationProcessor
from app.services.timeline_model import Timeline
from app.schemas.instruction_response import InstructionStatus, InstructionOutcome
from app.schemas.job import MediaMetadata


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_timeline():
    return Timeline(source_duration=10.0, source_id="src_test")


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
        size_bytes=1000000,
        format_name="mp4"
    )


# =============================================================================
# 1. APPLIED TESTS (VALID INSTRUCTIONS COMMITTED)
# =============================================================================

def test_applied_valid_mute_instruction(sample_timeline, sample_metadata):
    """
    Valid mute instruction: "Mute the video from 00:02 to 00:05"
    Must return APPLIED with normalized operation and update the timeline.
    """
    initial_effects_count = len(sample_timeline.source_effects)
    outcome = OperationProcessor.process_instruction(
        instruction="Mute the video from 00:02 to 00:05",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation is not None
    assert outcome.operation["type"] == "MUTE"
    assert outcome.operation["start"] == 2.0
    assert outcome.operation["end"] == 5.0
    assert outcome.operationId.startswith("op_")
    assert "successfully" in outcome.message.lower()
    assert len(sample_timeline.source_effects) == initial_effects_count + 1
    assert sample_timeline.source_effects[0].type == "mute"


def test_applied_valid_beep_instruction(sample_timeline, sample_metadata):
    """
    Valid beep instruction: "Censor audio from 00:04 to 00:06"
    Must return APPLIED with 1000Hz tone parameters.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Censor audio from 00:04 to 00:06",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "BEEP"
    assert outcome.operation["start"] == 4.0
    assert outcome.operation["end"] == 6.0
    assert outcome.operation["frequency"] == 1000
    assert any(e.type == "beep" for e in sample_timeline.source_effects)


def test_applied_valid_cut_instruction(sample_timeline, sample_metadata):
    """
    Valid internal cut instruction: "Cut out from 3s to 5s"
    Must return APPLIED, segment the timeline, and reduce total duration.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Cut out from 3s to 5s",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "CUT"
    assert outcome.operation["start"] == 3.0
    assert outcome.operation["end"] == 5.0
    assert len(sample_timeline.segments) == 2
    assert sample_timeline.total_duration == 8.0  # 10.0 - 2.0 = 8.0s


def test_applied_valid_speed_instruction(sample_timeline, sample_metadata):
    """
    Valid speed change: "Speed up 2x"
    Must return APPLIED and scale timeline duration to 5.0s.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Speed up 2x",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "SPEED"
    assert outcome.operation["speed"] == 2.0
    assert sample_timeline.total_duration == 5.0


def test_applied_valid_caption_instruction(sample_timeline, sample_metadata):
    """
    Valid caption instruction: 'Add caption "Chapter One" from 1s to 3s'
    Must return APPLIED with quoted text extracted.
    """
    outcome = OperationProcessor.process_instruction(
        instruction='Add caption "Chapter One" from 1s to 3s',
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "CAPTION"
    assert outcome.operation["text"] == "Chapter One"
    assert outcome.operation["start"] == 1.0
    assert outcome.operation["end"] == 3.0
    assert any(e.type == "caption" for e in sample_timeline.source_effects)


def test_applied_valid_resolution_instruction(sample_timeline, sample_metadata):
    """
    Valid resolution instruction: "Change resolution to 720p"
    Must return APPLIED with normalized RESOLUTION operation.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Change resolution to 720p",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "RESOLUTION"
    assert outcome.operation["standard"] == "720p"
    assert outcome.operationId.startswith("op_")


def test_applied_valid_color_adjust_instruction(sample_timeline, sample_metadata):
    """
    Valid color adjust instruction: "Increase brightness by 20%"
    Must return APPLIED with brightness=0.2 and contrast=1.0.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Increase brightness by 20%",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "COLOR_ADJUST"
    assert outcome.operation["brightness"] == 0.2
    assert outcome.operation["contrast"] == 1.0


def test_applied_pre_normalized_operation(sample_timeline, sample_metadata):
    """
    Pre-normalized operation execution: {"type": "VOLUME", "volume": 1.5}
    Must return APPLIED and record volume effect on timeline.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Boost volume to 150%",
        operation={"type": "VOLUME", "volume": 1.5},
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.operation["type"] == "VOLUME"
    assert outcome.operation["volume"] == 1.5
    assert any(e.type == "volume" for e in sample_timeline.source_effects)


# =============================================================================
# 2. NEEDS_CLARIFICATION TESTS (MISSING OR AMBIGUOUS INFORMATION)
# =============================================================================

def test_needs_clarification_missing_timestamps_mute(sample_timeline, sample_metadata):
    """
    Ambiguous mute instruction without range: "Mute the video"
    Must return NEEDS_CLARIFICATION, ask specific question, and leave timeline untouched.
    """
    initial_effects = len(sample_timeline.source_effects)
    initial_duration = sample_timeline.total_duration

    outcome = OperationProcessor.process_instruction(
        instruction="Mute the video",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.clarification_prompt is not None
    assert "clarify" in outcome.message.lower() or "timestamps" in outcome.message.lower()
    # Verification: Timeline must be completely unmodified
    assert len(sample_timeline.source_effects) == initial_effects
    assert sample_timeline.total_duration == initial_duration


def test_needs_clarification_ambiguous_cut(sample_timeline, sample_metadata):
    """
    Ambiguous cut instruction: "Cut out the middle part"
    Must return NEEDS_CLARIFICATION and leave timeline untouched.
    """
    initial_segments = len(sample_timeline.segments)
    initial_duration = sample_timeline.total_duration

    outcome = OperationProcessor.process_instruction(
        instruction="Cut out the middle part",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_TIMESTAMPS"
    assert "which section" in outcome.message.lower() or "timestamps" in outcome.message.lower()
    assert len(sample_timeline.segments) == initial_segments
    assert sample_timeline.total_duration == initial_duration


def test_needs_clarification_ambiguous_speed(sample_timeline, sample_metadata):
    """
    Ambiguous speed instruction: "Make the video faster" without factor
    Must return NEEDS_CLARIFICATION and leave timeline untouched.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Make the video faster",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_SPEED"
    assert "factor" in outcome.message.lower() or "speed" in outcome.message.lower()
    assert sample_timeline.total_duration == 10.0


def test_needs_clarification_missing_caption_details(sample_timeline, sample_metadata):
    """
    Missing caption details: "Add a caption"
    Must return NEEDS_CLARIFICATION.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Add a caption",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert "text" in outcome.message.lower()
    assert len(sample_timeline.source_effects) == 0


def test_needs_clarification_ambiguous_resolution(sample_timeline, sample_metadata):
    """
    Ambiguous resolution: "Change resolution" without specifying 1080p, 720p, or 480p
    Must return NEEDS_CLARIFICATION with standard options and untouched timeline.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Change resolution",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_RESOLUTION"
    assert outcome.clarification_prompt is not None
    assert "1080p" in outcome.clarification_prompt
    assert sample_timeline.to_dict() == initial_dict


def test_needs_clarification_ambiguous_color_adjustment(sample_timeline, sample_metadata):
    """
    Ambiguous color adjustment: "Adjust brightness" without percentage or offset
    Must return NEEDS_CLARIFICATION and leave timeline untouched.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Adjust brightness",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_PARAMETERS"
    assert outcome.clarification_prompt is not None
    assert sample_timeline.to_dict() == initial_dict


def test_needs_clarification_ambiguous_volume(sample_timeline, sample_metadata):
    """
    Ambiguous volume instruction: "Make the audio louder" without percentage
    Must return NEEDS_CLARIFICATION and leave timeline untouched.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Make the audio louder",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_VOLUME"
    assert outcome.clarification_prompt is not None
    assert sample_timeline.to_dict() == initial_dict


def test_needs_clarification_preserves_timeline_invariance(sample_timeline, sample_metadata):
    """
    Guarantees that multiple sequential NEEDS_CLARIFICATION instructions never mutate timeline.
    """
    initial_snapshot = sample_timeline.to_dict()

    ambiguous_prompts = [
        "Mute the audio",
        "Cut out the middle part",
        "Make it faster",
        "Change resolution",
        "Adjust contrast",
        "Add a visual effect"
    ]

    for p in ambiguous_prompts:
        res = OperationProcessor.process_instruction(
            instruction=p,
            timeline=sample_timeline,
            metadata=sample_metadata
        )
        assert res.status == InstructionStatus.NEEDS_CLARIFICATION
        assert res.operation is None or res.operation.get("type") is None
        # Strict invariant: timeline must remain 100% equal to the initial snapshot
        assert sample_timeline.to_dict() == initial_snapshot


# =============================================================================
# 3. REJECTED TESTS (UNSUPPORTED, INVALID, UNSAFE, OR IMPOSSIBLE)
# =============================================================================

def test_rejected_unsupported_effect(sample_timeline, sample_metadata):
    """
    Unsupported feature: "Reverse the video and add a 3D hologram"
    Must return REJECTED with clear reason and not modify the timeline.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Reverse the video and add a 3D hologram",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNSUPPORTED_EFFECT"
    assert "not supported" in outcome.message.lower()
    assert len(sample_timeline.source_effects) == 0


def test_rejected_security_violation(sample_timeline, sample_metadata):
    """
    Security violation: "Cut video; rm -rf /"
    Must return REJECTED immediately.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Cut video; rm -rf /",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "SECURITY_VIOLATION"
    assert "security" in outcome.message.lower()


def test_rejected_invalid_time_range_start_after_end(sample_timeline, sample_metadata):
    """
    Invalid time range where start > end: "Mute from 00:08 to 00:03"
    Must return REJECTED and leave timeline untouched.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Mute from 00:08 to 00:03",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_TIME_RANGE"
    assert "greater than" in outcome.message.lower()
    assert len(sample_timeline.source_effects) == 0


def test_rejected_time_range_exceeds_duration(sample_timeline, sample_metadata):
    """
    Interval exceeding media duration: "Cut from 15s to 20s" on 10s video
    Must return REJECTED.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Cut from 15s to 20s",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_TIME_RANGE"
    assert "exceeds" in outcome.message.lower()
    assert len(sample_timeline.segments) == 1


def test_rejected_invalid_clip_reorder_single_segment(sample_timeline, sample_metadata):
    """
    Attempting to reorder clips when timeline only has 1 segment:
    Must return REJECTED.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Reorder clips to [1, 0]",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INSUFFICIENT_SEGMENTS"
    assert "only 1 segment" in outcome.message.lower()


def test_rejected_unrecognized_instruction(sample_timeline, sample_metadata):
    """
    Completely unrecognized gibberish instruction.
    Must return REJECTED.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="foobar12345 qwertyuiop asdfghjkl",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNRECOGNIZED_INSTRUCTION"


def test_rejected_midway_failure_performs_rollback(sample_timeline, sample_metadata):
    """
    Requirement 7: If an operation fails midway, roll back its partial changes.
    Verify rollback restores timeline to previous state with rollback_performed=True.
    """
    initial_state = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Mute from 2s to 5s",
        timeline=sample_timeline,
        metadata=sample_metadata,
        simulate_execution_failure=True
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.rollback_performed is True
    assert "rollback performed" in outcome.message.lower()
    # Verify timeline is 100% identical to initial snapshot
    assert len(sample_timeline.source_effects) == 0
    assert sample_timeline.total_duration == initial_state["timeline_duration"]


# -----------------------------------------------------------------------------
# Additional Invalid Operation Tests
# -----------------------------------------------------------------------------

def test_rejected_empty_and_whitespace_instruction(sample_timeline, sample_metadata):
    """
    Empty or whitespace-only instructions must be rejected with EMPTY_INSTRUCTION.
    """
    for empty_input in ["", "   ", "\t\n  "]:
        outcome = OperationProcessor.process_instruction(
            instruction=empty_input,
            timeline=sample_timeline,
            metadata=sample_metadata
        )
        assert outcome.status == InstructionStatus.REJECTED
        assert outcome.error_code == "EMPTY_INSTRUCTION"
        assert len(sample_timeline.source_effects) == 0


def test_rejected_negative_start_timestamp(sample_timeline, sample_metadata):
    """
    Negative timestamp instruction: "Mute audio from -2s to 4s"
    Must return REJECTED with INVALID_TIME_RANGE.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Mute audio from -2s to 4s",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_TIME_RANGE"
    assert "negative" in outcome.message.lower()
    assert len(sample_timeline.source_effects) == 0


def test_rejected_pre_normalized_out_of_bounds_speed(sample_timeline, sample_metadata):
    """
    Pre-normalized speed exceeding bounds (e.g. 100x or -2x).
    Must return REJECTED and leave timeline completely untouched.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Speed up by 100x",
        operation={"type": "SPEED", "speed": 100.0},
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_SPEED"
    assert sample_timeline.to_dict() == initial_dict


def test_rejected_pre_normalized_out_of_bounds_volume(sample_timeline, sample_metadata):
    """
    Pre-normalized volume negative or exceeding max (e.g. volume=-1.0 or volume=10.0).
    Must return REJECTED.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Set volume to -1",
        operation={"type": "VOLUME", "volume": -1.0},
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_VOLUME"
    assert sample_timeline.to_dict() == initial_dict


def test_rejected_pre_normalized_invalid_time_range(sample_timeline, sample_metadata):
    """
    Pre-normalized interval where start >= end.
    Must return REJECTED with INVALID_TIME_RANGE.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Mute invalid range",
        operation={"type": "MUTE", "start": 8.0, "end": 2.0},
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_TIME_RANGE"
    assert sample_timeline.to_dict() == initial_dict


def test_rejected_out_of_bounds_brightness(sample_timeline, sample_metadata):
    """
    Brightness offset exceeding [-1.0, 1.0].
    Must return REJECTED with INVALID_PARAMETER.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Increase brightness to 2.5",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_PARAMETER"
    assert sample_timeline.to_dict() == initial_dict


# -----------------------------------------------------------------------------
# Additional Unsupported Operation Tests
# -----------------------------------------------------------------------------

def test_rejected_unsupported_resolution_4k(sample_timeline, sample_metadata):
    """
    Unsupported resolution 4K: "Resize video to 4k"
    Must return REJECTED with UNSUPPORTED_RESOLUTION and list supported standards.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Resize video to 4k",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNSUPPORTED_RESOLUTION"
    assert "4k" in outcome.message.lower()
    assert "1080p" in outcome.message.lower()
    assert sample_timeline.to_dict() == initial_dict


def test_rejected_unsupported_resolution_8k(sample_timeline, sample_metadata):
    """
    Unsupported resolution 8K: "Export in 8K resolution"
    Must return REJECTED with UNSUPPORTED_RESOLUTION.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Export in 8K resolution",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNSUPPORTED_RESOLUTION"


def test_rejected_unsupported_stabilize_camera(sample_timeline, sample_metadata):
    """
    Unsupported feature: "Stabilize the shaky camera footage"
    Must return REJECTED with UNSUPPORTED_EFFECT.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Stabilize the shaky camera footage",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNSUPPORTED_EFFECT"
    assert "not supported" in outcome.message.lower()


def test_rejected_unsupported_remove_watermark(sample_timeline, sample_metadata):
    """
    Unsupported feature: "Remove watermark from top right corner"
    Must return REJECTED with UNSUPPORTED_EFFECT.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Remove watermark from top right corner",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNSUPPORTED_EFFECT"


def test_rejected_unsupported_ai_voiceover(sample_timeline, sample_metadata):
    """
    Unsupported feature: "Generate AI voiceover for this clip"
    Must return REJECTED with UNSUPPORTED_EFFECT.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Generate AI voiceover for this clip",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "UNSUPPORTED_EFFECT"


# -----------------------------------------------------------------------------
# Additional Failed Operation & Atomic Rollback Tests
# -----------------------------------------------------------------------------

def test_rejected_atomic_rollback_on_pre_normalized_failure(sample_timeline, sample_metadata):
    """
    Pre-normalized valid operation that fails during execution.
    Must trigger atomic rollback, return REJECTED, and leave timeline identical to pre-call snapshot.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Mute from 1s to 4s",
        operation={"type": "MUTE", "start": 1.0, "end": 4.0},
        timeline=sample_timeline,
        metadata=sample_metadata,
        simulate_execution_failure=True
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.rollback_performed is True
    assert outcome.error_code == "EXECUTION_FAILED"
    assert sample_timeline.to_dict() == initial_dict


def test_rejected_atomic_rollback_preserves_complex_timeline_state(sample_timeline, sample_metadata):
    """
    Set up a complex timeline with prior cuts and effects, then simulate a failure.
    Verify that rollback restores exactly the complex state with zero partial corruption.
    """
    # 1. Apply a valid cut to create 2 segments
    res_cut = OperationProcessor.process_instruction(
        instruction="Cut out from 4s to 6s",
        timeline=sample_timeline,
        metadata=sample_metadata
    )
    assert res_cut.status == InstructionStatus.APPLIED
    assert len(sample_timeline.segments) == 2
    assert sample_timeline.total_duration == 8.0

    # 2. Add an effect to the timeline
    sample_timeline.add_effect("caption", 1.0, 3.0, parameters={"text": "Intro"}, label="Intro")
    assert len(sample_timeline.source_effects) == 1

    # Snapshot of the complex state
    complex_snapshot = sample_timeline.to_dict()

    # 3. Attempt a second operation with simulated failure
    res_failed = OperationProcessor.process_instruction(
        instruction="Speed up 2x",
        timeline=sample_timeline,
        metadata=sample_metadata,
        simulate_execution_failure=True
    )

    assert res_failed.status == InstructionStatus.REJECTED
    assert res_failed.rollback_performed is True

    # 4. Invariant: Timeline must match complex snapshot 100%
    assert sample_timeline.to_dict() == complex_snapshot
    assert len(sample_timeline.segments) == 2
    assert sample_timeline.total_duration == 8.0
    assert len(sample_timeline.source_effects) == 1
    assert sample_timeline.source_effects[0].label == "Intro"


# =============================================================================
# 4. REST API ENDPOINT & AUDIT RECEIPT LIFECYCLE TESTS
# =============================================================================

def test_api_instruction_endpoint_lifecycle(client):
    """
    Verifies the full REST API lifecycle of POST /api/jobs/{id}/instruction:
    1. Submits valid mute instruction -> APPLIED
    2. Submits missing timestamp cut -> NEEDS_CLARIFICATION
    3. Submits invalid interval -> REJECTED
    4. Submits simulate failure -> REJECTED with rollback
    5. Checks EditReceipt includes instruction_audit with all 4 records.
    """
    # 1. Create Demo Job
    r_demo = client.post("/api/jobs/demo")
    assert r_demo.status_code == 200
    job_id = r_demo.json()["id"]

    # 2. Test APPLIED
    r_applied = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Mute the video from 00:04 to 00:06"}
    )
    assert r_applied.status_code == 200
    out_applied = r_applied.json()
    assert out_applied["status"] == "APPLIED"
    assert out_applied["operation"]["type"] == "MUTE"
    assert out_applied["operationId"] is not None

    # Verify timeline updated
    r_tl = client.get(f"/api/jobs/{job_id}/timeline")
    assert r_tl.status_code == 200
    assert any(e["type"] == "mute" for e in r_tl.json()["source_effects"])

    # 3. Test NEEDS_CLARIFICATION
    r_clarify = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Cut out the middle part"}
    )
    assert r_clarify.status_code == 200
    out_clarify = r_clarify.json()
    assert out_clarify["status"] == "NEEDS_CLARIFICATION"
    assert out_clarify["clarification_prompt"] is not None

    # 4. Test REJECTED
    r_rejected = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Mute from 00:09 to 00:02"}
    )
    assert r_rejected.status_code == 200
    out_rejected = r_rejected.json()
    assert out_rejected["status"] == "REJECTED"
    assert "greater than" in out_rejected["message"].lower()

    # 5. Test SIMULATED FAILURE & ROLLBACK
    r_rollback = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Mute from 00:01 to 00:03", "simulate_failure": True}
    )
    assert r_rollback.status_code == 200
    out_rollback = r_rollback.json()
    assert out_rollback["status"] == "REJECTED"
    assert out_rollback["rollback_performed"] is True

    # 6. Verify Job Response has instruction_history
    r_job = client.get(f"/api/jobs/{job_id}")
    assert r_job.status_code == 200
    job_data = r_job.json()
    assert job_data.get("instruction_history") is not None
    assert len(job_data["instruction_history"]) == 4

    statuses = [item["status"] for item in job_data["instruction_history"]]
    assert "APPLIED" in statuses
    assert "NEEDS_CLARIFICATION" in statuses
    assert "REJECTED" in statuses
