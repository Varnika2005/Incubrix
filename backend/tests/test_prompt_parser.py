import pytest
from app.services.prompt_parser import PromptParser
from app.schemas.edit_plan import OperationType
from app.schemas.job import MediaMetadata

@pytest.fixture
def sample_metadata():
    return MediaMetadata(
        duration=15.0,
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

def test_trim_start_variations(sample_metadata):
    prompts = [
        "Remove the first 5 seconds",
        "Cut first 5s",
        "Trim opening 5 seconds",
        "Discard first 5 sec"
    ]
    for p in prompts:
        plan = PromptParser.parse(p, sample_metadata)
        trim_ops = [op for op in plan.operations if op["type"] == OperationType.TRIM_START]
        assert len(trim_ops) == 1, f"Failed for prompt: {p}"
        assert trim_ops[0]["seconds"] == 5.0

def test_keep_first_vs_remove_first(sample_metadata):
    plan_remove = PromptParser.parse("Remove first 3 seconds", sample_metadata)
    assert any(op["type"] == OperationType.TRIM_START for op in plan_remove.operations)
    assert not any(op["type"] == OperationType.TIME_SLICE for op in plan_remove.operations)

    plan_keep = PromptParser.parse("Keep the first 3 seconds", sample_metadata)
    assert any(op["type"] == OperationType.TIME_SLICE for op in plan_keep.operations)
    slice_op = next(op for op in plan_keep.operations if op["type"] == OperationType.TIME_SLICE)
    assert slice_op["start_time"] == 0.0
    assert slice_op["end_time"] == 3.0

def test_trim_end(sample_metadata):
    plan = PromptParser.parse("Cut the last 4 seconds", sample_metadata)
    trim_ops = [op for op in plan.operations if op["type"] == OperationType.TRIM_END]
    assert len(trim_ops) == 1
    assert trim_ops[0]["seconds"] == 4.0

def test_time_slice_intervals(sample_metadata):
    prompts = [
        ("Keep from 0:02 to 0:08", 2.0, 8.0),
        ("Extract between 3 and 10 seconds", 3.0, 10.0),
        ("Slice from 00:01 to 00:05", 1.0, 5.0)
    ]
    for prompt, start, end in prompts:
        plan = PromptParser.parse(prompt, sample_metadata)
        slice_ops = [op for op in plan.operations if op["type"] == OperationType.TIME_SLICE]
        assert len(slice_ops) == 1
        assert slice_ops[0]["start_time"] == start
        assert slice_ops[0]["end_time"] == end

def test_aspect_ratios():
    p1 = PromptParser.parse("Convert to 9:16 vertical for TikTok")
    op1 = next(op for op in p1.operations if op["type"] == OperationType.ASPECT_RATIO)
    assert op1["ratio"] == "9:16"

    p2 = PromptParser.parse("Make it square 1:1 for Instagram")
    op2 = next(op for op in p2.operations if op["type"] == OperationType.ASPECT_RATIO)
    assert op2["ratio"] == "1:1"

    p3 = PromptParser.parse("Convert to 16:9 landscape widescreen")
    op3 = next(op for op in p3.operations if op["type"] == OperationType.ASPECT_RATIO)
    assert op3["ratio"] == "16:9"

def test_audio_adjustments():
    p1 = PromptParser.parse("Mute the video audio")
    op1 = next(op for op in p1.operations if op["type"] == OperationType.AUDIO_VOLUME)
    assert op1["mute"] is True or op1["volume_percent"] == 0.0

    p2 = PromptParser.parse("Boost volume by 50%")
    op2 = next(op for op in p2.operations if op["type"] == OperationType.AUDIO_VOLUME)
    assert op2["volume_percent"] == 50.0

    p3 = PromptParser.parse("Double the volume")
    op3 = next(op for op in p3.operations if op["type"] == OperationType.AUDIO_VOLUME)
    assert op3["volume_percent"] == 200.0

def test_silence_and_subtitles():
    plan = PromptParser.parse("Remove silent pauses and add subtitles")
    types = [op["type"] for op in plan.operations]
    assert OperationType.SILENCE_REMOVAL in types
    assert OperationType.SUBTITLES in types

def test_invalid_range_detection(sample_metadata):
    plan = PromptParser.parse("Keep from 0:10 to 0:02", sample_metadata)
    assert plan.requires_confirmation is True
    assert any("start timestamp" in w for w in plan.warnings)

def test_out_of_bounds_trim(sample_metadata):
    # Metadata duration is 15s, trim is 20s
    plan = PromptParser.parse("Trim first 20 seconds", sample_metadata)
    assert any("greater than total duration" in w for w in plan.warnings)

def test_prompt_injection_safety():
    malicious = "Trim first 2s; rm -rf /; DROP TABLE jobs;"
    plan = PromptParser.parse(malicious)
    assert any("Potentially unsafe" in w for w in plan.warnings)
    assert len(plan.operations) == 0

def test_unsupported_operation_repair():
    plan = PromptParser.parse("Do an AI face swap and reverse video")
    assert plan.suggested_repair is not None
    assert "Try:" in plan.suggested_repair
