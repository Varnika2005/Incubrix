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
# 1. DOCUMENTED DEFAULT POLICY (ORIGINAL-SOURCE TIMESTAMPS)
# =============================================================================

def test_default_policy_uses_source_coordinates(sample_timeline, sample_metadata):
    """
    Documented default policy:
    Unspecified editing instructions operate in original-source coordinates.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Mute audio from 00:02 to 00:05",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.time_reference == "source"
    assert outcome.operation["type"] == "MUTE"
    assert outcome.operation["start"] == 2.0
    assert outcome.operation["end"] == 5.0
    assert outcome.converted_timestamps is not None
    assert outcome.converted_timestamps["input_reference"] == "source"
    assert outcome.converted_timestamps["source_range"] == [2.0, 5.0]

    # Verify effect is anchored to source coordinates [2.0, 5.0]
    assert len(sample_timeline.source_effects) == 1
    eff = sample_timeline.source_effects[0]
    assert eff.type == "mute"
    assert eff.source_start == 2.0
    assert eff.source_end == 5.0


def test_explicit_source_reference_keyword(sample_timeline, sample_metadata):
    """
    Explicit source reference keyword: "in source" or "original footage".
    Must be validated against source duration and anchored directly.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Apply sepia from 3s to 6s in source footage",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.time_reference == "source"
    assert outcome.converted_timestamps["input_reference"] == "source"
    assert outcome.converted_timestamps["source_range"] == [3.0, 6.0]
    assert any(e.type == "visual_effect" and e.source_start == 3.0 for e in sample_timeline.source_effects)


# =============================================================================
# 2. CURRENT-TIMELINE COORDINATES & CONVERSION
# =============================================================================

def test_explicit_timeline_coordinates_on_diverged_timeline(sample_timeline, sample_metadata):
    """
    When timeline has diverged (e.g., trimmed start by 2s):
    - Original source duration: 10s
    - Trimmed start 2s -> Active timeline duration: 8s (Source [2s, 10s])
    - User says: "Mute from 1s to 3s on timeline"
    Timeline interval [1.0s, 3.0s] must map to Source [3.0s, 5.0s].
    """
    # Diverge timeline: trim first 2 seconds in source
    sample_timeline.apply_trim_start(2.0)
    assert sample_timeline.is_diverged() is True
    assert sample_timeline.total_duration == 8.0

    outcome = OperationProcessor.process_instruction(
        instruction="Mute audio from 1s to 3s on timeline",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.time_reference == "timeline"
    assert outcome.converted_timestamps is not None
    assert outcome.converted_timestamps["input_reference"] == "timeline"
    assert outcome.converted_timestamps["timeline_range"] == [1.0, 3.0]

    src_intervals = outcome.converted_timestamps["source_intervals"]
    assert len(src_intervals) == 1
    assert src_intervals[0]["source_start"] == 3.0
    assert src_intervals[0]["source_end"] == 5.0

    # Verify effect is anchored to source [3.0, 5.0]
    eff = sample_timeline.source_effects[0]
    assert eff.source_start == 3.0
    assert eff.source_end == 5.0

    # Verify active timeline transformation projects to timeline [1.0, 3.0]
    active_effects = sample_timeline.transform_effects()
    assert len(active_effects) == 1
    assert active_effects[0].timeline_start == 1.0
    assert active_effects[0].timeline_end == 3.0
    assert active_effects[0].status == "active"


def test_timeline_coordinates_via_api_parameter(sample_timeline, sample_metadata):
    """
    API parameter time_reference="timeline" explicitly directs resolution to timeline coordinates.
    """
    sample_timeline.apply_trim_start(3.0)
    assert sample_timeline.total_duration == 7.0

    outcome = OperationProcessor.process_instruction(
        instruction="Add caption 'Highlight' from 1s to 4s",
        timeline=sample_timeline,
        metadata=sample_metadata,
        time_reference="timeline"
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.time_reference == "timeline"
    assert outcome.converted_timestamps["timeline_range"] == [1.0, 4.0]
    src_ints = outcome.converted_timestamps["source_intervals"]
    assert src_ints[0]["source_start"] == 4.0  # 3.0 + 1.0 = 4.0s
    assert src_ints[0]["source_end"] == 7.0    # 3.0 + 4.0 = 7.0s


# =============================================================================
# 3. CONVERSIONS ACROSS CUTS, SPEED CHANGES, AND REORDERING
# =============================================================================

def test_complex_timeline_coordinate_conversion_multi_segment(sample_metadata):
    """
    Complex workflow with cuts, trims, and speed change:
    1. 10s video
    2. Cut 2s to 4s in source -> segments [0, 2s] and [4s, 10s] (duration 8s)
    3. Speed up first segment 2x -> [0, 2s] duration is 1.0s, [4s, 10s] duration is 6.0s. Total = 7.0s.
    4. Apply caption from 0.5s to 2.5s on timeline:
       - 0.5s to 1.0s falls in segment 1 (2x speed) -> source 1.0s to 2.0s
       - 1.0s to 2.5s falls in segment 2 (1x speed) -> source 4.0s to 5.5s
    """
    tl = Timeline(source_duration=10.0, source_id="src_multi")
    tl.apply_cut(2.0, 4.0)
    tl.set_segment_speed(0, 2.0)
    assert round(tl.total_duration, 4) == 7.0

    outcome = OperationProcessor.process_instruction(
        instruction="Add caption 'Dual Section' from 0.5s to 2.5s in timeline",
        timeline=tl,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.time_reference == "timeline"
    conv = outcome.converted_timestamps
    assert conv["timeline_range"] == [0.5, 2.5]
    src_ints = conv["source_intervals"]
    assert len(src_ints) == 2

    # First interval in segment 1 (at 2x speed)
    assert round(src_ints[0]["source_start"], 2) == 1.0
    assert round(src_ints[0]["source_end"], 2) == 2.0

    # Second interval in segment 2 (at 1x speed)
    assert round(src_ints[1]["source_start"], 2) == 4.0
    assert round(src_ints[1]["source_end"], 2) == 5.5

    # Verify transformed timeline effects reflect the split accurately
    active = tl.transform_effects()
    assert len(active) == 2
    assert active[0].timeline_start == 0.5
    assert active[0].timeline_end == 1.0
    assert active[1].timeline_start == 1.0
    assert active[1].timeline_end == 2.5


def test_timeline_cut_in_timeline_coordinates(sample_metadata):
    """
    Applying an internal CUT using timeline coordinates:
    10s video, trim start 2s -> timeline is [2s, 10s] in source, duration 8s.
    User cuts from 1s to 3s on timeline:
    Must cut source from 3s to 5s.
    Timeline duration becomes 6s.
    """
    tl = Timeline(source_duration=10.0, source_id="src_cut")
    tl.apply_trim_start(2.0)
    assert tl.total_duration == 8.0

    outcome = OperationProcessor.process_instruction(
        instruction="Cut from 1s to 3s on timeline",
        timeline=tl,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.time_reference == "timeline"
    assert round(tl.total_duration, 4) == 6.0
    # Segments should now be source [2s, 3s] and [5s, 10s]
    assert len(tl.segments) == 2
    assert tl.segments[0].source_start == 2.0
    assert tl.segments[0].source_end == 3.0
    assert tl.segments[1].source_start == 5.0
    assert tl.segments[1].source_end == 10.0


# =============================================================================
# 4. CONTENT-AWARE ANCHORING INTEGRITY
# =============================================================================

def test_effects_remain_anchored_after_clip_reorder(sample_metadata):
    """
    Captions and audio effects anchored to source content must track their
    respective content when clips are reordered.
    """
    tl = Timeline(source_duration=10.0, source_id="src_reorder")
    tl.apply_cut(4.0, 6.0)  # Segments: [0, 4s] (clip 0) and [6s, 10s] (clip 1)
    assert len(tl.segments) == 2

    # Add caption to source [7s, 9s] (inside segment 1)
    tl.add_effect("caption", 7.0, 9.0, label="Clip 1 Caption")

    # Before reorder: segment 0 is at timeline 0s-4s; segment 1 is at 4s-8s.
    # Effect source [7s, 9s] is at timeline [5s, 7s].
    active_before = tl.transform_effects()
    assert len(active_before) == 1
    assert active_before[0].timeline_start == 5.0
    assert active_before[0].timeline_end == 7.0

    # Reorder clips: [1, 0] (Clip 1 now plays first!)
    outcome = OperationProcessor.process_instruction(
        instruction="Reorder clips to [1, 0]",
        timeline=tl,
        metadata=sample_metadata
    )
    assert outcome.status == InstructionStatus.APPLIED

    # After reorder: segment 1 is at timeline 0s-4s!
    # Effect source [7s, 9s] must now automatically move to timeline [1s, 3s]!
    active_after = tl.transform_effects()
    assert len(active_after) == 1
    assert active_after[0].timeline_start == 1.0
    assert active_after[0].timeline_end == 3.0


# =============================================================================
# 5. GENUINE AMBIGUITY & CONFLICT RESOLUTION
# =============================================================================

def test_conflicting_source_and_timeline_keywords(sample_timeline, sample_metadata):
    """
    Direct conflict: Instruction contains references to both source and timeline.
    Must return NEEDS_CLARIFICATION with CONFLICTING_TIME_REFERENCE.
    Timeline must be completely unmodified.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Mute audio from 2s to 4s in source on timeline",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "CONFLICTING_TIME_REFERENCE"
    assert "conflicting" in outcome.message.lower()
    assert sample_timeline.to_dict() == initial_dict


def test_conflicting_parameter_and_text(sample_timeline, sample_metadata):
    """
    Parameter conflict: time_reference="timeline" while prompt states "in source footage".
    Must return NEEDS_CLARIFICATION with CONFLICTING_TIME_REFERENCE.
    """
    initial_dict = sample_timeline.to_dict()

    outcome = OperationProcessor.process_instruction(
        instruction="Cut from 2s to 4s in source footage",
        timeline=sample_timeline,
        metadata=sample_metadata,
        time_reference="timeline"
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "CONFLICTING_TIME_REFERENCE"
    assert sample_timeline.to_dict() == initial_dict


def test_ambiguous_parameter_triggers_clarification(sample_timeline, sample_metadata):
    """
    Explicit ambiguous parameter time_reference="ambiguous" requires clarification.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Mute from 2s to 4s",
        timeline=sample_timeline,
        metadata=sample_metadata,
        time_reference="ambiguous"
    )

    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "CONFLICTING_TIME_REFERENCE"


# =============================================================================
# 6. BOUNDARY & OUT-OF-BOUNDS VALIDATION
# =============================================================================

def test_out_of_bounds_timeline_coordinates_rejected(sample_timeline, sample_metadata):
    """
    When explicit timeline coordinates exceed active timeline duration:
    Must return REJECTED with INVALID_TIME_RANGE and informative message.
    """
    # Shorten timeline to 4s
    sample_timeline.apply_trim_start(6.0)
    assert sample_timeline.total_duration == 4.0

    outcome = OperationProcessor.process_instruction(
        instruction="Mute audio from 2s to 6s on timeline",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_TIME_RANGE"
    assert "exceeds current timeline duration" in outcome.message


def test_out_of_bounds_source_coordinates_rejected(sample_timeline, sample_metadata):
    """
    When source coordinates exceed total source media duration:
    Must return REJECTED with INVALID_TIME_RANGE.
    """
    outcome = OperationProcessor.process_instruction(
        instruction="Mute audio from 2s to 15s in source",
        timeline=sample_timeline,
        metadata=sample_metadata
    )

    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "INVALID_TIME_RANGE"
    assert "exceeds total source duration" in outcome.message


# =============================================================================
# 7. COORDINATE MAPPING API ENDPOINT
# =============================================================================

def test_api_timeline_range_mapping_endpoint(client):
    """
    Tests POST /api/jobs/{job_id}/timeline/map with timeline_range and source_range.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Trim start 2 seconds via instruction
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Trim start 2 seconds"})

    # Map timeline range [1.0, 3.0] -> maps to source [4.0, 6.0] (since demo job starts trimmed at 3.0s)
    map_res = client.post(
        f"/api/jobs/{job_id}/timeline/map",
        json={"timeline_range": [1.0, 3.0]}
    )
    assert map_res.status_code == 200
    data = map_res.json()
    assert data["mapped_source_intervals"] is not None
    assert len(data["mapped_source_intervals"]) == 1
    assert data["mapped_source_intervals"][0]["start"] == 4.0
    assert data["mapped_source_intervals"][0]["end"] == 6.0

    # Map source range [4.0, 6.0] -> should map back to timeline [1.0, 3.0]
    map_res2 = client.post(
        f"/api/jobs/{job_id}/timeline/map",
        json={"source_range": [4.0, 6.0]}
    )
    assert map_res2.status_code == 200
    data2 = map_res2.json()
    assert data2["mapped_timeline_intervals"] is not None
    assert len(data2["mapped_timeline_intervals"]) == 1
    assert data2["mapped_timeline_intervals"][0]["start"] == 1.0
    assert data2["mapped_timeline_intervals"][0]["end"] == 3.0
