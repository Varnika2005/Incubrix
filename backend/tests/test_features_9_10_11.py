"""
Automated Test Suite for Features 9, 10, and 11:
Feature 9: Caption-Aware Timeline Editing
Feature 10: Ambiguity Resolution and Meaning-Based Search
Feature 11: Conflict Detection and Safe Edit Execution
"""

import copy
import pytest
from app.schemas.instruction_response import InstructionStatus
from app.schemas.job import MediaMetadata
from app.services.operation_processor import OperationProcessor
from app.services.timeline_model import Timeline, TimelineSegment, ContentAwareEffect
from app.services.transcript_search import TranscriptSearchEngine


# =============================================================================
# FEATURE 9: CAPTION-AWARE TIMELINE EDITING
# =============================================================================

def test_feature9_complete_caption_cut():
    """If all words associated with a caption are cut, remove that caption and notify the user."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    # Add caption with word-level timestamps in range 2.0s - 4.0s
    words = [
        {"word": "Hello", "start": 2.1, "end": 2.9},
        {"word": "world", "start": 3.1, "end": 3.9}
    ]
    tl.add_effect("caption", 2.0, 4.0, parameters={"text": "Hello world", "words": words}, label="Hello world")
    assert len(tl.effects) == 1

    # Cut entire interval [1.5s - 4.5s]
    outcome = OperationProcessor.process_instruction(
        instruction="cut from 1.5s to 4.5s in source",
        timeline=tl,
        time_reference="source"
    )
    assert outcome.status == InstructionStatus.APPLIED
    # Caption must be removed because all associated words were cut
    assert len(tl.effects) == 0
    # Notification recorded in timeline and reported in outcome warnings
    assert any("removed" in n.lower() and "Hello world" in n for n in tl.notifications)
    assert outcome.warnings is not None
    assert any("Hello world" in w for w in outcome.warnings)


def test_feature9_partial_caption_cut_with_surviving_words():
    """For partial cuts with word timestamps, retain only surviving words and update text & timing."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    words = [
        {"word": "Welcome", "start": 1.0, "end": 1.4},
        {"word": "to", "start": 1.5, "end": 1.9},
        {"word": "ClipPilot", "start": 2.1, "end": 2.8},
        {"word": "AI", "start": 2.9, "end": 3.5}
    ]
    tl.add_effect("caption", 1.0, 3.5, parameters={"text": "Welcome to ClipPilot AI", "words": words}, label="Welcome to ClipPilot AI")

    # Cut from 2.0s to 5.0s, excising 'ClipPilot' and 'AI', leaving 'Welcome' and 'to'
    outcome = OperationProcessor.process_instruction(
        instruction="cut from 2.0s to 5.0s in source",
        timeline=tl,
        time_reference="source"
    )
    assert outcome.status == InstructionStatus.APPLIED
    # Caption must survive with updated text and timing
    assert len(tl.effects) == 1
    retained_cap = tl.effects[0]
    assert retained_cap.parameters["text"] == "Welcome to"
    assert retained_cap.source_start == 1.0
    assert retained_cap.source_end == 1.9
    assert len(retained_cap.parameters["words"]) == 2
    assert any("Welcome to ClipPilot AI" in n and "Welcome to" in n for n in tl.notifications)


def test_feature9_partial_caption_cut_without_word_timing_requests_clarification():
    """If word-level timing is unavailable for a partial cut, request clarification rather than guessing."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    # Caption without words list
    tl.add_effect("caption", 1.0, 4.0, parameters={"text": "No word timestamps here"}, label="No word timestamps here")

    outcome = OperationProcessor.process_instruction(
        instruction="cut from 2.0s to 3.0s in source",
        timeline=tl,
        time_reference="source"
    )
    # Must NOT guess boundaries; must return NEEDS_CLARIFICATION
    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "CAPTION_WORD_TIMING_UNAVAILABLE"
    assert "word-level timestamps are unavailable" in outcome.message
    assert outcome.options is not None
    assert len(outcome.options) >= 2
    # Timeline must remain unmodified
    assert len(tl.segments) == 1
    assert tl.total_duration == 10.0


def test_feature9_caption_speed_readability_extension():
    """When speech is sped up, keep captions readable for approximately ~0.7s where possible."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    # Add caption with 1.0s duration on [2.0s - 3.0s]
    tl.add_effect("caption", 2.0, 3.0, parameters={"text": "Fast phrase"}, label="Fast phrase")

    # Speed up 2.0x on [0s - 10s]: raw duration becomes 0.5s (< 0.7s)
    outcome = OperationProcessor.process_instruction(
        instruction="speed up 2x",
        timeline=tl
    )
    assert outcome.status == InstructionStatus.APPLIED

    # Check transformed effects
    transformed = tl.transform_effects()
    assert len(transformed) == 1
    cap = transformed[0]
    # Check that duration was safely extended to 0.7s minimum readability
    assert cap.duration == 0.7
    assert cap.parameters.get("readability_extended") is True


def test_feature9_caption_speed_readability_conflict_reporting():
    """If 0.7s readability conflicts with clip boundaries, report conflict in warnings."""
    # Create timeline with a very short segment of 0.4s
    tl = Timeline(source_duration=0.4, source_id="src_short")
    tl.add_effect("caption", 0.0, 0.4, parameters={"text": "Short clip"}, label="Short clip")

    # Speed up 2.0x: duration becomes 0.2s, clip remaining is 0.2s (< 0.7s)
    tl.apply_speed_change(2.0)
    transformed = tl.transform_effects()
    assert len(transformed) == 1
    cap = transformed[0]
    assert cap.parameters.get("readability_conflict") is True
    assert len(tl.warnings) > 0
    assert any("readability conflict" in w.lower() for w in tl.warnings)


# =============================================================================
# FEATURE 10: AMBIGUITY RESOLUTION AND MEANING-BASED SEARCH
# =============================================================================

def test_feature10_vague_that_caption():
    """Handle vague instruction 'that caption'."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    # Case A: 0 captions -> REJECTED
    outcome_none = OperationProcessor.process_instruction(
        instruction="remove that caption",
        timeline=tl
    )
    assert outcome_none.status == InstructionStatus.REJECTED
    assert outcome_none.error_code == "NO_CAPTIONS_FOUND"

    # Case B: 1 caption -> NEEDS_CLARIFICATION with stated assumption & options
    tl.add_effect("caption", 1.0, 3.0, parameters={"text": "Intro title"}, label="Intro title")
    outcome_one = OperationProcessor.process_instruction(
        instruction="delete that caption",
        timeline=tl
    )
    assert outcome_one.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome_one.error_code == "AMBIGUOUS_CAPTION_CONFIRMATION"
    assert "Intro title" in outcome_one.message
    assert outcome_one.options is not None
    assert any("Delete caption 'Intro title'" in opt for opt in outcome_one.options)

    # Case C: Multiple captions -> NEEDS_CLARIFICATION listing all captions
    tl.add_effect("caption", 4.0, 6.0, parameters={"text": "Body caption"}, label="Body caption")
    outcome_multi = OperationProcessor.process_instruction(
        instruction="change that caption",
        timeline=tl
    )
    assert outcome_multi.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome_multi.error_code == "AMBIGUOUS_CAPTION_REFERENCE"
    assert outcome_multi.options is not None
    assert len(outcome_multi.options) >= 3


def test_feature10_vague_the_boring_part():
    """Handle vague instruction 'the boring part'."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    outcome = OperationProcessor.process_instruction(
        instruction="cut the boring part",
        timeline=tl
    )
    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_INSTRUCTION"
    assert "boring part" in outcome.message
    assert outcome.options is not None
    assert len(outcome.options) > 0


def test_feature10_vague_make_it_shorter():
    """Handle vague instruction 'make it shorter'."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    outcome = OperationProcessor.process_instruction(
        instruction="make it shorter",
        timeline=tl
    )
    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "AMBIGUOUS_INSTRUCTION"
    assert outcome.options is not None
    assert any("Trim the end" in opt for opt in outcome.options)
    assert any("Speed up" in opt for opt in outcome.options)


def test_feature10_vague_put_back_what_i_removed():
    """Never claim deleted content can be restored if edit history is unavailable; clarify if available."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    # Case A: No edit history -> REJECTED
    outcome_no_hist = OperationProcessor.process_instruction(
        instruction="put back what I removed",
        timeline=tl,
        edit_history=None
    )
    assert outcome_no_hist.status == InstructionStatus.REJECTED
    assert outcome_no_hist.error_code == "NO_RESTORATION_HISTORY"
    assert "Cannot restore deleted content" in outcome_no_hist.message

    # Case B: With edit history -> NEEDS_CLARIFICATION with confirmation
    dummy_history = [{"state_id": 1, "plan": {"timeline": tl.to_dict()}}]
    outcome_with_hist = OperationProcessor.process_instruction(
        instruction="put back what I removed",
        timeline=tl,
        edit_history=dummy_history
    )
    assert outcome_with_hist.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome_with_hist.error_code == "RESTORATION_CONFIRMATION"
    assert outcome_with_hist.options is not None


def test_feature10_semantic_search_pricing_matches_cost():
    """'pricing' should find speech about 'cost' without exact word match, requiring confirmation before cutting."""
    tl = Timeline(source_duration=15.0, source_id="src_1")
    transcript = [
        {"start": 0.0, "end": 4.0, "text": "Welcome to ClipPilot video editing demonstration."},
        {"start": 4.5, "end": 8.0, "text": "The monthly cost and subscription fee is ten dollars."},
        {"start": 8.5, "end": 12.0, "text": "Next we demonstrate cutting and audio synchronization."}
    ]

    outcome = OperationProcessor.process_instruction(
        instruction="cut the part about pricing",
        timeline=tl,
        transcript=transcript
    )
    # Never silently cut! Must return NEEDS_CLARIFICATION with candidate matches
    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "SEMANTIC_MATCH_CONFIRMATION"
    assert outcome.candidate_matches is not None
    assert len(outcome.candidate_matches) > 0

    best_match = outcome.candidate_matches[0]
    assert best_match["start"] == 4.5
    assert best_match["end"] == 8.0
    assert "cost" in best_match["text"].lower()
    assert best_match["confidence"] >= 0.80
    assert outcome.options is not None
    # Timeline must not be modified yet!
    assert tl.total_duration == 15.0


def test_feature10_semantic_search_no_match_rejected():
    """Nonexistent semantic match rejected with NO_SEMANTIC_MATCH."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    transcript = [
        {"start": 0.0, "end": 5.0, "text": "Welcome to ClipPilot AI software."},
        {"start": 5.0, "end": 10.0, "text": "This tutorial covers basic video editing."}
    ]
    outcome = OperationProcessor.process_instruction(
        instruction="cut the section discussing astrophysics and black holes",
        timeline=tl,
        transcript=transcript
    )
    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "NO_SEMANTIC_MATCH"


# =============================================================================
# FEATURE 11: CONFLICT DETECTION AND SAFE EDIT EXECUTION
# =============================================================================

def test_feature11_duplicate_cut_instruction_prevention():
    """Make repeated or duplicate cut instructions safe."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    # First cut: succeeds
    first_outcome = OperationProcessor.process_instruction(
        instruction="cut from 2s to 4s in source",
        timeline=tl,
        time_reference="source"
    )
    assert first_outcome.status == InstructionStatus.APPLIED
    assert tl.total_duration == 8.0

    # Repeat exact duplicate cut instruction: must be rejected safely
    second_outcome = OperationProcessor.process_instruction(
        instruction="cut from 2s to 4s in source",
        timeline=tl,
        time_reference="source"
    )
    assert second_outcome.status == InstructionStatus.REJECTED
    assert second_outcome.error_code == "DUPLICATE_OPERATION"
    assert "already been cut" in second_outcome.message
    # Timeline remains 8.0s
    assert tl.total_duration == 8.0


def test_feature11_duplicate_speed_instruction_prevention():
    """Prevent duplicate speed changes on already-sped-up ranges."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    # First speed change
    first_outcome = OperationProcessor.process_instruction(
        instruction="speed up 2x",
        timeline=tl
    )
    assert first_outcome.status == InstructionStatus.APPLIED
    assert tl.total_duration == 5.0

    # Second identical speed change
    second_outcome = OperationProcessor.process_instruction(
        instruction="speed up 2x",
        timeline=tl
    )
    assert second_outcome.status == InstructionStatus.REJECTED
    assert second_outcome.error_code == "DUPLICATE_OPERATION"
    assert "already set to 2.0x" in second_outcome.message


def test_feature11_whole_video_cut_rejection():
    """Reject cuts that would remove the entire video, explaining reason and offering alternatives."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    outcome = OperationProcessor.process_instruction(
        instruction="cut from 0s to 10s in source",
        timeline=tl,
        time_reference="source"
    )
    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.error_code == "WHOLE_VIDEO_CUT_REJECTED"
    assert "Whole-video cut rejected" in outcome.message
    assert outcome.options is not None
    assert any("Trim the start or end" in opt for opt in outcome.options)
    # Timeline intact
    assert tl.total_duration == 10.0


def test_feature11_invalid_time_ranges_rejected():
    """Reject negative timestamps, start >= end, and out of bounds."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    # Negative start
    out_neg = OperationProcessor.process_instruction(
        instruction="cut from -2s to 4s",
        timeline=tl
    )
    assert out_neg.status == InstructionStatus.REJECTED
    assert out_neg.error_code == "INVALID_TIME_RANGE"

    # Start >= End
    out_rev = OperationProcessor.process_instruction(
        instruction="cut from 6s to 3s",
        timeline=tl
    )
    assert out_rev.status == InstructionStatus.REJECTED
    assert out_rev.error_code == "INVALID_TIME_RANGE"


def test_feature11_overlapping_speed_changes_merge_and_conflict():
    """Merge identical speed overlaps; ask clarification for conflicting speed overlaps."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    # Apply 2.0x speed on [2s - 5s]
    op1 = OperationProcessor.process_instruction(
        instruction="speed up 2x from 2s to 5s in source",
        timeline=tl,
        time_reference="source"
    )
    assert op1.status == InstructionStatus.APPLIED

    # Overlapping identical speed: [4s - 7s] at 2.0x -> should merge without conflict
    op2 = OperationProcessor.process_instruction(
        instruction="speed up 2x from 4s to 7s in source",
        timeline=tl,
        time_reference="source"
    )
    assert op2.status == InstructionStatus.APPLIED

    # Overlapping CONFLICTING speed: [3s - 6s] at 0.5x -> MUST return NEEDS_CLARIFICATION
    op3 = OperationProcessor.process_instruction(
        instruction="speed up 0.5x from 3s to 6s in source",
        timeline=tl,
        time_reference="source"
    )
    assert op3.status == InstructionStatus.NEEDS_CLARIFICATION
    assert op3.error_code == "CONFLICTING_SPEED_OVERLAP"
    assert "Conflicting speed overlap detected" in op3.message
    assert op3.options is not None


def test_feature11_deliberate_pause_preservation():
    """Preserve deliberate pauses when removing silence."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    silences = [
        {"start": 2.0, "end": 3.0, "is_deliberate": False, "classification": "dead_air", "confidence": 0.95},
        {"start": 5.0, "end": 6.0, "is_deliberate": True, "classification": "deliberate_pause", "confidence": 0.98}
    ]

    outcome = OperationProcessor.process_instruction(
        instruction="remove silence",
        timeline=tl,
        silence_segments=silences
    )
    assert outcome.status == InstructionStatus.APPLIED
    assert "Preserved 1 deliberate speech pauses" in outcome.message
    assert "cut 1 dead air segments" in outcome.message
    # Dead air [2.0s - 3.0s] was cut (1.0s excised), deliberate pause [5.0s - 6.0s] remained
    assert tl.total_duration == 9.0


def test_feature11_uncertain_silence_requests_clarification():
    """Ask for confirmation when pause intent is uncertain."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    silences = [
        {"start": 3.0, "end": 4.5, "is_deliberate": False, "classification": "uncertain", "confidence": 0.50}
    ]

    outcome = OperationProcessor.process_instruction(
        instruction="remove silence",
        timeline=tl,
        silence_segments=silences
    )
    assert outcome.status == InstructionStatus.NEEDS_CLARIFICATION
    assert outcome.error_code == "UNCERTAIN_PAUSE_CLASSIFICATION"
    assert outcome.options is not None
    # Timeline untouched
    assert tl.total_duration == 10.0


def test_feature11_multi_part_instruction_success():
    """Multi-part instructions track each part independently and return parts status."""
    tl = Timeline(source_duration=10.0, source_id="src_1")

    outcome = OperationProcessor.process_instruction(
        instruction="cut 0s to 2s and speed up 2x from 2s to 4s",
        timeline=tl,
        time_reference="source"
    )
    assert outcome.status == InstructionStatus.APPLIED
    assert outcome.parts is not None
    assert outcome.parts[0]["status"] in ["APPLIED", "applied"]
    assert outcome.parts[1]["status"] in ["APPLIED", "applied"]


def test_feature11_multi_part_instruction_rollback_on_failure():
    """Multi-part instruction rolls back completely if a later part fails."""
    tl = Timeline(source_duration=10.0, source_id="src_1")
    initial_duration = tl.total_duration

    # First part is valid (cut 0s to 2s), second part is invalid (cut 0s to 10s = whole video cut)
    outcome = OperationProcessor.process_instruction(
        instruction="cut 0s to 2s and cut 0s to 10s",
        timeline=tl,
        time_reference="source"
    )
    assert outcome.status == InstructionStatus.REJECTED
    assert outcome.rollback_performed is True
    assert outcome.parts is not None
    assert len(outcome.parts) == 2
    assert outcome.parts[0]["status"] in ["APPLIED", "applied"]
    assert outcome.parts[1]["status"] in ["REJECTED", "rejected"]
    # Timeline must be rolled back completely to initial duration!
    assert tl.total_duration == initial_duration
    assert len(tl.segments) == 1
