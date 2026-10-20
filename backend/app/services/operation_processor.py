import copy
import re
import uuid
from typing import Dict, Any, Optional, List, Tuple

from app.schemas.instruction_response import InstructionOutcome, InstructionStatus
from app.schemas.job import MediaMetadata
from app.services.timeline_model import Timeline
from app.services.transcript_search import TranscriptSearchEngine


def parse_time_str(val: str) -> Optional[float]:
    """
    Parses time strings like '00:05', '0:10', '1:23', '90s', '5.5 seconds', '10', '-2s'.
    Returns float seconds or None.
    """
    if not val:
        return None
    val = val.strip().lower()

    # Format MM:SS or HH:MM:SS
    if ":" in val:
        parts = val.split(":")
        try:
            if len(parts) == 2:
                sign = -1.0 if parts[0].startswith("-") else 1.0
                p0 = abs(float(parts[0]))
                p1 = float(parts[1])
                return sign * (p0 * 60 + p1)
            elif len(parts) == 3:
                sign = -1.0 if parts[0].startswith("-") else 1.0
                p0 = abs(float(parts[0]))
                p1 = float(parts[1])
                p2 = float(parts[2])
                return sign * (p0 * 3600 + p1 * 60 + p2)
        except ValueError:
            return None

    # Format like 5s, 5.5s, 5 sec, 5 seconds, 5, -2s, -5
    m = re.match(r"^(-?[\d.]+)\s*(?:s|sec|secs|seconds|second)?$", val)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None

    return None


class OperationProcessor:
    """
    Central Operation-Processing Layer enforcing:
    1. Feature 3: STRICT THREE-WAY RESPONSE SYSTEM (APPLIED, NEEDS_CLARIFICATION, REJECTED).
    2. Feature 7: CONSISTENT TIMESTAMP REFERENCE POLICY.
       - Clearly distinguishes original-source timestamps from current-timeline timestamps.
       - Documented default: current-timeline timestamps in active edit mode (when diverged).
       - Requires clarification (NEEDS_CLARIFICATION) when an instruction is genuinely ambiguous.
       - Anchors captions and audio effects to underlying source content.
       - Converts timestamps accurately across cuts, trims, speeds, and clip reordering.
    """

    UNSUPPORTED_KEYWORDS = [
        "reverse video",
        "reverse",
        "3d effect",
        "3d hologram",
        "3d",
        "generate new scene",
        "ai face swap",
        "face swap",
        "greenscreen replacement",
        "greenscreen",
        "text to video",
        "remove person",
        "hologram",
        "deepfake",
        "stabilize video",
        "stabilize",
        "stabilization",
        "motion tracking",
        "tracking",
        "remove background",
        "background removal",
        "remove watermark",
        "watermark removal",
        "ai voiceover",
        "voice clone",
        "pitch shift",
        "super resolution",
        "upscale"
    ]

    MALICIOUS_PATTERNS = [
        r"[;&|]\s*(?:rm|del|erase|format|bash|sh|cmd|powershell|curl|wget|python|drop|exec|eval)\b",
        r"--exec\b",
        r"format\s+[a-z]:",
        r"<script",
        r"DROP\s+TABLE",
        r"\brm\s+-rf\b",
        r"&&\s*rm\b",
        r"&&\s*del\b"
    ]

    @classmethod
    def _split_multi_part(cls, text: str) -> List[str]:
        """
        Splits multi-part instructions separated by semicolons, ', then', 'and then',
        or 'and' followed by an editing action verb.
        """
        if ";" in text:
            parts = [p.strip() for p in text.split(";") if p.strip()]
            if len(parts) > 1:
                return parts
        then_parts = re.split(r",?\s+(?:and\s+)?then\s+", text, flags=re.IGNORECASE)
        if len(then_parts) > 1:
            return [p.strip() for p in then_parts if p.strip()]
        action_split = re.split(
            r"\s+and\s+(?=(?:cut|trim|mute|speed|caption|subtitles?|beep|censor|volume|remove|slice|delete)\b)",
            text,
            flags=re.IGNORECASE
        )
        if len(action_split) > 1:
            return [p.strip() for p in action_split if p.strip()]
        return [text]

    @classmethod
    def _execute_multi_part_instruction(
        cls,
        instruction: str,
        parts: List[str],
        timeline: Timeline,
        metadata: Optional[MediaMetadata],
        simulate_execution_failure: bool,
        time_reference: Optional[str],
        edit_history: Optional[List[Dict[str, Any]]],
        transcript: Optional[List[Dict[str, Any]]],
        silence_segments: Optional[List[Dict[str, Any]]],
        op_id: str
    ) -> InstructionOutcome:
        """
        Executes a multi-part instruction transactionally.
        Tracks each part independently with status, operation, and reason.
        If any part fails (REJECTED or execution failure) or requires clarification,
        the timeline is rolled back to its initial state to prevent corruption.
        """
        temp_timeline = Timeline.from_dict(copy.deepcopy(timeline.to_dict()))
        part_records: List[Dict[str, Any]] = []

        for part_str in parts:
            part_outcome = cls.process_instruction(
                instruction=part_str,
                timeline=temp_timeline,
                metadata=metadata,
                simulate_execution_failure=simulate_execution_failure,
                time_reference=time_reference,
                edit_history=edit_history,
                transcript=transcript,
                silence_segments=silence_segments,
                allow_multi_part=False
            )
            rec = {
                "part": part_str,
                "status": part_outcome.status.value,
                "message": part_outcome.message,
                "operation": part_outcome.operation
            }
            if part_outcome.error_code:
                rec["error_code"] = part_outcome.error_code
            part_records.append(rec)

            if part_outcome.status == InstructionStatus.REJECTED:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=instruction,
                    operation=None,
                    message=f"Multi-part instruction failed on step '{part_str}': {part_outcome.message}. Transactional rollback performed.",
                    operationId=op_id,
                    error_code="MULTI_PART_EXECUTION_FAILED",
                    rollback_performed=True,
                    parts=part_records,
                    timeline=timeline.to_dict()
                )
            elif part_outcome.status == InstructionStatus.NEEDS_CLARIFICATION:
                return InstructionOutcome(
                    status=InstructionStatus.NEEDS_CLARIFICATION,
                    instruction=instruction,
                    operation=None,
                    message=f"Multi-part instruction requires clarification on step '{part_str}': {part_outcome.message}.",
                    clarification_prompt=part_outcome.clarification_prompt,
                    options=part_outcome.options,
                    candidate_matches=part_outcome.candidate_matches,
                    operationId=op_id,
                    error_code=part_outcome.error_code or "MULTI_PART_CLARIFICATION_NEEDED",
                    parts=part_records,
                    timeline=timeline.to_dict()
                )

        restored = Timeline.from_dict(temp_timeline.to_dict())
        timeline.source_duration = restored.source_duration
        timeline.source_id = restored.source_id
        timeline.segments = restored.segments
        timeline.effects = restored.effects
        timeline.notifications = restored.notifications
        timeline.warnings = restored.warnings
        timeline._recalculate_timeline()

        all_warnings = list(timeline.warnings)
        if timeline.notifications:
            all_warnings.extend(timeline.notifications)

        return InstructionOutcome(
            status=InstructionStatus.APPLIED,
            instruction=instruction,
            operation={"type": "MULTI_PART", "count": len(parts)},
            message=f"All {len(parts)} parts of multi-part instruction executed and committed successfully.",
            operationId=op_id,
            timeline=timeline.to_dict(),
            parts=part_records,
            warnings=all_warnings if all_warnings else None
        )

    @classmethod
    def process_instruction(
        cls,
        instruction: str,
        timeline: Optional[Timeline] = None,
        metadata: Optional[MediaMetadata] = None,
        pre_normalized_op: Optional[Dict[str, Any]] = None,
        operation: Optional[Dict[str, Any]] = None,
        simulate_execution_failure: bool = False,
        time_reference: Optional[str] = None,
        edit_history: Optional[List[Dict[str, Any]]] = None,
        transcript: Optional[List[Dict[str, Any]]] = None,
        silence_segments: Optional[List[Dict[str, Any]]] = None,
        allow_multi_part: bool = True
    ) -> InstructionOutcome:
        """
        Main entry point for processing an editing instruction against the timeline.
        Guarantee: Returns exactly one valid outcome (APPLIED, NEEDS_CLARIFICATION, or REJECTED).
        Guarantee: If outcome is not APPLIED, the timeline is guaranteed unmodified.
        Guarantee: Consistent timestamp reference policy is enforced across all operations.
        """
        clean_instruction = (instruction or "").strip()
        lower_instruction = clean_instruction.lower()
        op_id = f"op_{uuid.uuid4().hex[:12]}"

        # Empty instruction check
        if not clean_instruction:
            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=instruction or "",
                operation=None,
                message="Invalid instruction: Instruction string cannot be empty.",
                operationId=op_id,
                error_code="EMPTY_INSTRUCTION"
            )

        # Resolve duration baseline
        source_dur = 10.0
        if metadata and metadata.duration and metadata.duration > 0:
            source_dur = float(metadata.duration)
        elif timeline and timeline.source_duration and timeline.source_duration > 0:
            source_dur = float(timeline.source_duration)

        if not timeline:
            timeline = Timeline(source_duration=source_dur, source_id="src_original")

        # Snapshot timeline state before any operation for transactional rollback safety
        timeline_snapshot = copy.deepcopy(timeline.to_dict())

        # ---------------------------------------------------------------------
        # 1. SECURITY & INTEGRITY CHECK (REJECTED)
        # ---------------------------------------------------------------------
        for pat in cls.MALICIOUS_PATTERNS:
            if re.search(pat, clean_instruction, re.IGNORECASE):
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message="Security violation: Instruction contains forbidden shell or script command patterns.",
                    operationId=op_id,
                    error_code="SECURITY_VIOLATION"
                )

        # ---------------------------------------------------------------------
        # 2. UNSUPPORTED FEATURES CHECK (REJECTED)
        # ---------------------------------------------------------------------
        for kw in cls.UNSUPPORTED_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower_instruction):
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"Unsupported operation: '{kw}' is not supported by ClipPilot AI. Supported operations: trim, cut, slice, speed, captions, mute, beep, aspect ratio, resolution, audio volume, color adjust, and silence removal.",
                    operationId=op_id,
                    error_code="UNSUPPORTED_EFFECT"
                )

        # Multi-part instructions check (Feature 11)
        if allow_multi_part and not (operation or pre_normalized_op):
            parts = cls._split_multi_part(clean_instruction)
            if len(parts) > 1:
                return cls._execute_multi_part_instruction(
                    instruction=clean_instruction,
                    parts=parts,
                    timeline=timeline,
                    metadata=metadata,
                    simulate_execution_failure=simulate_execution_failure,
                    time_reference=time_reference,
                    edit_history=edit_history,
                    transcript=transcript,
                    silence_segments=silence_segments,
                    op_id=op_id
                )

        # ---------------------------------------------------------------------
        # 3. DIRECT NORMALIZED OPERATION (If provided by caller)
        # ---------------------------------------------------------------------
        effective_op = operation if operation is not None else pre_normalized_op
        if effective_op:
            return cls._execute_normalized_operation(
                instruction=clean_instruction,
                normalized_op=effective_op,
                timeline=timeline,
                timeline_snapshot=timeline_snapshot,
                source_dur=source_dur,
                op_id=op_id,
                simulate_execution_failure=simulate_execution_failure,
                explicit_time_reference=time_reference,
                silence_segments=silence_segments
            )

        # ---------------------------------------------------------------------
        # 4. TIMESTAMP POLICY: DETECT TIME REFERENCE & CONFLICTS
        # ---------------------------------------------------------------------
        ref_mode, is_conflict = cls._detect_time_reference(clean_instruction, explicit_ref=time_reference)
        if is_conflict:
            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Conflicting timestamp reference: Instruction contains references to both source coordinates and timeline coordinates. Please specify either source or timeline timestamps (e.g., 'mute 2s to 4s in source' or 'mute 2s to 4s on timeline').",
                operationId=op_id,
                clarification_prompt="Specify whether the timestamps refer to source footage or current timeline playback.",
                error_code="CONFLICTING_TIME_REFERENCE"
            )

        # ---------------------------------------------------------------------
        # 5. VAGUE INSTRUCTIONS & MEANING-BASED SEARCH (FEATURE 10)
        # ---------------------------------------------------------------------

        # A. "that caption" / "the caption"
        if re.search(r"\b(?:that|the)\s+caption\b", lower_instruction) or lower_instruction == "that caption":
            captions = [eff for eff in timeline.effects if eff.type == "caption"]
            if len(captions) == 0:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message="No captions found on the timeline to reference.",
                    operationId=op_id,
                    error_code="NO_CAPTIONS_FOUND"
                )
            elif len(captions) == 1:
                cap = captions[0]
                return InstructionOutcome(
                    status=InstructionStatus.NEEDS_CLARIFICATION,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"Identified single caption: '{cap.label}' [{cap.source_start:.2f}s - {cap.source_end:.2f}s]. Please confirm your intended action on this caption.",
                    clarification_prompt=f"Confirm action on caption '{cap.label}'.",
                    options=[
                        f"Delete caption '{cap.label}'",
                        f"Edit text of caption '{cap.label}'",
                        f"Adjust timing of caption '{cap.label}'",
                        "Cancel"
                    ],
                    operationId=op_id,
                    error_code="AMBIGUOUS_CAPTION_CONFIRMATION"
                )
            else:
                opts = [f"Caption at {c.source_start:.2f}s - {c.source_end:.2f}s: '{c.label}'" for c in captions] + ["Cancel"]
                return InstructionOutcome(
                    status=InstructionStatus.NEEDS_CLARIFICATION,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"Multiple captions found ({len(captions)}). Which caption are you referring to?",
                    clarification_prompt="Select the intended caption from the list.",
                    options=opts,
                    operationId=op_id,
                    error_code="AMBIGUOUS_CAPTION_REFERENCE"
                )

        # B. "the boring part"
        if "boring part" in lower_instruction or "boring section" in lower_instruction or lower_instruction == "the boring part":
            candidates = TranscriptSearchEngine.search_transcript("boring", transcript) if transcript else []
            cand_list = [
                {"start": c["start"], "end": c["end"], "text": c["text"], "confidence": c["confidence"], "matched_terms": c.get("matched_terms", [])}
                for c in candidates
            ]
            opts = [f"Cut {c['start']:.2f}s - {c['end']:.2f}s: '{c['text']}' ({int(c['confidence']*100)}% relevance)" for c in candidates]
            if not opts and silence_segments:
                for s in silence_segments[:3]:
                    opts.append(f"Cut silence pause {s.get('start', 0.0):.2f}s - {s.get('end', 0.0):.2f}s ({s.get('duration', 0.0):.2f}s)")
            if not opts:
                opts = [
                    "Cut longest silent pause",
                    "Cut filler speech section",
                    "Specify exact start and end timestamps"
                ]
            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Ambiguous reference: 'the boring part' depends on subjective viewer interest. Found potential candidates to review.",
                clarification_prompt="Confirm the exact time range or candidate section to cut.",
                candidate_matches=cand_list if cand_list else None,
                options=opts,
                operationId=op_id,
                error_code="AMBIGUOUS_INSTRUCTION"
            )

        # C. "make it shorter" / "shorten the video"
        if lower_instruction in ["make it shorter", "shorten it", "make shorter", "shorten the video", "make video shorter"] or re.search(r"\bmake\s+(?:the\s+video\s+)?shorter\b", lower_instruction):
            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Instruction 'make it shorter' is ambiguous. Please select how you would like to reduce video duration:",
                clarification_prompt="Choose a method to reduce duration.",
                options=[
                    "Trim the end (e.g. cut the last 5 seconds)",
                    "Speed up playback (e.g. 1.25x or 1.5x speed)",
                    "Remove silent pauses and dead air",
                    "Cut a specific time range"
                ],
                operationId=op_id,
                error_code="AMBIGUOUS_INSTRUCTION"
            )

        # D. "put back what I removed" / "restore what I cut"
        if any(p in lower_instruction for p in ["put back what i removed", "put back what was removed", "restore what i cut", "restore what was cut", "undo my cut", "bring back what was deleted", "restore deleted part"]):
            if edit_history and len(edit_history) > 0:
                return InstructionOutcome(
                    status=InstructionStatus.NEEDS_CLARIFICATION,
                    instruction=clean_instruction,
                    operation=None,
                    message="Found prior edit state with removed content in edit history. Would you like to restore the previous state to recover what was removed?",
                    clarification_prompt="Confirm whether to restore previous state.",
                    options=[
                        "Restore previous state (undo last cut)",
                        "Cancel"
                    ],
                    operationId=op_id,
                    error_code="RESTORATION_CONFIRMATION"
                )
            else:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message="Cannot restore deleted content: no previous cut history or original media is available to recover.",
                    operationId=op_id,
                    error_code="NO_RESTORATION_HISTORY",
                    options=[
                        "Specify an exact time range to add back",
                        "Start a new edit project"
                    ]
                )

        # E. Meaning-Based Transcript Search for Cuts (e.g., "cut part about pricing", "remove section discussing cost")
        m_topic = re.search(r"\b(?:cut|remove|delete)\s+(?:the\s+)?(?:part|section|discussion|speech|mention)?\s*(?:about|on|regarding|discussing)\s+([a-zA-Z0-9_\-\s]+)", lower_instruction)
        m_topic2 = re.search(r"\b(?:cut|remove|delete)\s+(?:the\s+)?(pricing|cost|intro|introduction|outro|conclusion|features|subscriptions?|demo)\b", lower_instruction)
        if (m_topic or m_topic2) and not cls._extract_time_range(lower_instruction) and not any(k in lower_instruction for k in ["first", "last", "beginning", "end", "silence", "pause"]):
            query_term = (m_topic.group(1) if m_topic else m_topic2.group(1)).strip()
            active_transcript = transcript
            if not active_transcript:
                active_transcript = TranscriptSearchEngine.get_sample_transcript(source_dur)

            candidates = TranscriptSearchEngine.search_transcript(query_term, active_transcript, threshold=0.50)
            if candidates:
                cand_matches = [
                    {"start": c["start"], "end": c["end"], "text": c["text"], "confidence": c["confidence"], "matched_terms": c.get("matched_terms", [])}
                    for c in candidates
                ]
                opts = [f"Cut {c['start']:.2f}s - {c['end']:.2f}s: '{c['text']}' (Confidence: {int(c['confidence']*100)}%)" for c in candidates] + ["Cancel"]
                return InstructionOutcome(
                    status=InstructionStatus.NEEDS_CLARIFICATION,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"Found candidate transcript passages matching '{query_term}'. Please select or confirm the intended section to cut:",
                    clarification_prompt=f"Confirm which passage to cut for '{query_term}'.",
                    candidate_matches=cand_matches,
                    options=opts,
                    operationId=op_id,
                    error_code="SEMANTIC_MATCH_CONFIRMATION"
                )
            else:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"No relevant transcript passages found matching '{query_term}' (confidence threshold not met).",
                    operationId=op_id,
                    error_code="NO_SEMANTIC_MATCH"
                )

        # ---------------------------------------------------------------------
        # 6. NATURAL LANGUAGE INTERPRETATION & AMBIGUITY CLASSIFICATION
        # ---------------------------------------------------------------------

        # A. MUTE / MUTE_RANGE
        if "mute" in lower_instruction or "silence audio" in lower_instruction:
            tr = cls._extract_time_range(lower_instruction)
            if tr:
                st, et = tr
                err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                    st, et, timeline, ref_mode, clean_instruction, op_id, "MUTE"
                )
                if err_outcome:
                    return err_outcome
                op = {
                    "type": "MUTE",
                    "start": st,
                    "end": et,
                    "time_reference": ref,
                    "source_intervals": src_intervals,
                    "converted_timestamps": conv
                }
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            # Check if user wants entire audio muted
            if any(k in lower_instruction for k in ["all", "entire", "whole", "completely", "entire video"]):
                op = {"type": "MUTE", "start": 0.0, "end": source_dur, "time_reference": "source"}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            # Ambiguous: user said "mute" without specifying whether entire or what interval
            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Please clarify: do you want to mute a specific range or the entire video? (e.g., 'mute from 00:02 to 00:05' or 'mute entire video').",
                operationId=op_id,
                clarification_prompt="Specify mute start and end timestamps or confirm entire video.",
                error_code="AMBIGUOUS_TIMESTAMPS"
            )

        # B. BEEP / CENSOR
        if any(k in lower_instruction for k in ["beep", "censor", "bleep"]):
            tr = cls._extract_time_range(lower_instruction)
            if tr:
                st, et = tr
                err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                    st, et, timeline, ref_mode, clean_instruction, op_id, "BEEP"
                )
                if err_outcome:
                    return err_outcome
                op = {
                    "type": "BEEP",
                    "start": st,
                    "end": et,
                    "frequency": 1000,
                    "time_reference": ref,
                    "source_intervals": src_intervals,
                    "converted_timestamps": conv
                }
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Missing timestamps: Please specify the start and end timestamps to beep (e.g., 'beep audio from 00:03 to 00:05').",
                operationId=op_id,
                clarification_prompt="Specify beep start and end timestamps.",
                error_code="MISSING_TIMESTAMPS"
            )

        # C. SPEED CHANGES
        if any(k in lower_instruction for k in ["speed", "slow motion", "fast forward", "faster", "slower", "tempo"]):
            spd: Optional[float] = None
            m_speed = re.search(r"(\d+(?:\.\d+)?)\s*(?:x|times|speed)", lower_instruction)
            if m_speed:
                try:
                    spd = float(m_speed.group(1))
                except ValueError:
                    pass
            elif "double" in lower_instruction or "2x" in lower_instruction:
                spd = 2.0
            elif "half" in lower_instruction or "slow motion" in lower_instruction or "slowmo" in lower_instruction:
                spd = 0.5

            if spd is not None:
                if spd <= 0.0 or spd > 16.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=clean_instruction,
                        operation={"type": "SPEED", "speed": spd},
                        message=f"Invalid speed factor ({spd}x): playback speed must be greater than 0 and at most 16.0x.",
                        operationId=op_id,
                        error_code="INVALID_SPEED_FACTOR"
                    )
                st, et = None, None
                tr = cls._extract_time_range(lower_instruction)
                if tr:
                    st, et = tr
                    err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                        st, et, timeline, ref_mode, clean_instruction, op_id, "SPEED"
                    )
                    if err_outcome:
                        return err_outcome
                    op = {
                        "type": "SPEED",
                        "speed": spd,
                        "start": st,
                        "end": et,
                        "time_reference": ref,
                        "source_intervals": src_intervals,
                        "converted_timestamps": conv
                    }
                else:
                    op = {"type": "SPEED", "speed": spd, "start": None, "end": None, "time_reference": ref_mode or "timeline"}

                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Ambiguous speed: What playback speed factor would you like to apply? (e.g., 'speed up 2x' or 'slow motion 0.5x').",
                operationId=op_id,
                clarification_prompt="Please specify a speed multiplier like 2.0x or 0.5x.",
                error_code="AMBIGUOUS_SPEED"
            )

        # D. CAPTIONS & SUBTITLES
        if "caption" in lower_instruction or "subtitles" in lower_instruction or "add text" in lower_instruction:
            m_text = re.search(r'["\']([^"\']+)["\']', clean_instruction)
            text = m_text.group(1) if m_text else None

            tr = cls._extract_time_range(lower_instruction)
            st, et = tr if tr else (None, None)

            if "subtitles" in lower_instruction and not tr and not text:
                op = {"type": "SUBTITLES", "burn": True}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            if text and st is not None and et is not None:
                err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                    st, et, timeline, ref_mode, clean_instruction, op_id, "CAPTION"
                )
                if err_outcome:
                    return err_outcome
                op = {
                    "type": "CAPTION",
                    "text": text,
                    "start": st,
                    "end": et,
                    "time_reference": ref,
                    "source_intervals": src_intervals,
                    "converted_timestamps": conv
                }
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message='Missing caption details: What text should the caption display and during which time range? (e.g., \'add caption "Intro" from 00:01 to 00:03\').',
                operationId=op_id,
                clarification_prompt='Please specify caption text in quotes and timestamps (e.g., \'add caption "Title" from 1s to 3s\').',
                error_code="MISSING_PARAMETERS"
            )

        # E. TIME SLICE / KEEP INTERVAL
        if any(k in lower_instruction for k in ["keep from", "slice from", "extract from", "only keep", "keep between"]):
            tr = cls._extract_time_range(lower_instruction)
            if tr:
                st, et = tr
                err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                    st, et, timeline, ref_mode, clean_instruction, op_id, "TIME_SLICE"
                )
                if err_outcome:
                    return err_outcome
                op = {
                    "type": "TIME_SLICE",
                    "start": st,
                    "end": et,
                    "time_reference": ref,
                    "source_intervals": src_intervals,
                    "converted_timestamps": conv
                }
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Missing slice interval: Please provide the start and end times to keep (e.g., 'keep from 00:02 to 00:08').",
                operationId=op_id,
                clarification_prompt="Provide start and end timestamps for the slice.",
                error_code="MISSING_TIMESTAMPS"
            )

        # F. TRIM START / FIRST SECONDS
        if re.search(r"\b(?:trim|cut|remove|delete)\s+(?:the\s+)?(?:first|opening|beginning|start)\b", lower_instruction):
            m_sec = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds|second)", lower_instruction)
            if m_sec:
                sec = float(m_sec.group(1))
                if sec <= 0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=clean_instruction,
                        operation={"type": "TRIM_START", "seconds": sec},
                        message=f"Invalid trim duration: trim length ({sec}s) must be positive.",
                        operationId=op_id,
                        error_code="INVALID_DURATION"
                    )

                tl_dur = round(float(timeline.total_duration), 4)
                src_dur_round = round(float(timeline.source_duration), 4)

                if ref_mode == "timeline":
                    if sec >= tl_dur:
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=clean_instruction,
                            operation={"type": "TRIM_START", "seconds": sec, "time_reference": "timeline"},
                            message=f"Invalid trim duration: trim start length ({sec}s) exceeds current timeline duration ({tl_dur}s).",
                            operationId=op_id,
                            error_code="DURATION_EXCEEDED"
                        )
                else:
                    if sec >= src_dur_round:
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=clean_instruction,
                            operation={"type": "TRIM_START", "seconds": sec, "time_reference": "source"},
                            message=f"Invalid trim duration: trim start length ({sec}s) exceeds total video duration ({src_dur_round}s).",
                            operationId=op_id,
                            error_code="DURATION_EXCEEDED"
                        )

                eff_ref = ref_mode or "source"
                op = {"type": "TRIM_START", "seconds": sec, "time_reference": eff_ref}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Missing duration: How many seconds should be trimmed from the start? (e.g., 'trim first 3 seconds').",
                operationId=op_id,
                clarification_prompt="Specify how many seconds to trim from the beginning.",
                error_code="MISSING_TIMESTAMPS"
            )

        # G. TRIM END / LAST SECONDS
        if re.search(r"\b(?:trim|cut|remove|delete)\s+(?:the\s+)?(?:last|end|ending|trailing)\b", lower_instruction):
            m_sec = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds|second)", lower_instruction)
            if m_sec:
                sec = float(m_sec.group(1))
                if sec <= 0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=clean_instruction,
                        operation={"type": "TRIM_END", "seconds": sec},
                        message=f"Invalid trim duration: trim length ({sec}s) must be positive.",
                        operationId=op_id,
                        error_code="INVALID_DURATION"
                    )

                tl_dur = round(float(timeline.total_duration), 4)
                src_dur_round = round(float(timeline.source_duration), 4)

                if ref_mode == "timeline":
                    if sec >= tl_dur:
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=clean_instruction,
                            operation={"type": "TRIM_END", "seconds": sec, "time_reference": "timeline"},
                            message=f"Invalid trim duration: trim end length ({sec}s) exceeds current timeline duration ({tl_dur}s).",
                            operationId=op_id,
                            error_code="DURATION_EXCEEDED"
                        )
                else:
                    if sec >= src_dur_round:
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=clean_instruction,
                            operation={"type": "TRIM_END", "seconds": sec, "time_reference": "source"},
                            message=f"Invalid trim duration: trim end length ({sec}s) exceeds total video duration ({src_dur_round}s).",
                            operationId=op_id,
                            error_code="DURATION_EXCEEDED"
                        )

                eff_ref = ref_mode or "source"
                op = {"type": "TRIM_END", "seconds": sec, "time_reference": eff_ref}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Missing duration: How many seconds should be trimmed from the end? (e.g., 'cut last 4 seconds').",
                operationId=op_id,
                clarification_prompt="Specify how many seconds to trim from the end.",
                error_code="MISSING_TIMESTAMPS"
            )

        # H. INTERNAL CUT (Cut from X to Y)
        if any(k in lower_instruction for k in ["cut", "trim", "remove", "delete"]) and not any(k in lower_instruction for k in ["first", "last", "beginning", "end", "silence", "pause"]):
            tr = cls._extract_time_range(lower_instruction)
            if tr:
                st, et = tr
                err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                    st, et, timeline, ref_mode, clean_instruction, op_id, "CUT"
                )
                if err_outcome:
                    return err_outcome
                op = {
                    "type": "CUT",
                    "start": st,
                    "end": et,
                    "time_reference": ref,
                    "source_intervals": src_intervals,
                    "converted_timestamps": conv
                }
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            target_desc = "the middle part" if "middle" in lower_instruction else "the specified section"
            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Ambiguous time reference: Which section should be cut? Please provide specific timestamps (e.g., 'cut from 00:03 to 00:06').",
                operationId=op_id,
                clarification_prompt=f"Ambiguous time reference: Which timestamps correspond to {target_desc}? Please specify start and end times.",
                error_code="AMBIGUOUS_TIMESTAMPS"
            )

        # I. CLIP REORDERING
        if any(k in lower_instruction for k in ["reorder", "swap clip", "swap clips", "change order"]):
            m_order = re.search(r"\[([\d\s,]+)\]", lower_instruction)
            if m_order:
                try:
                    order = [int(x.strip()) for x in m_order.group(1).split(",")]
                    num_segs = len(timeline.segments)
                    if num_segs <= 1:
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=clean_instruction,
                            operation={"type": "REORDER", "order": order},
                            message=f"Cannot reorder: timeline contains only {num_segs} segment. Cut or split the video first to produce multiple clips.",
                            operationId=op_id,
                            error_code="INSUFFICIENT_SEGMENTS"
                        )
                    if set(order) != set(range(num_segs)):
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=clean_instruction,
                            operation={"type": "REORDER", "order": order},
                            message=f"Invalid clip indices {order}: order must be a permutation of available indices {list(range(num_segs))}.",
                            operationId=op_id,
                            error_code="INVALID_CLIP_REFERENCE"
                        )
                    op = {"type": "REORDER", "order": order}
                    return cls._execute_normalized_operation(
                        clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                    )
                except ValueError:
                    pass

            if "swap" in lower_instruction and len(timeline.segments) == 2:
                op = {"type": "REORDER", "order": [1, 0]}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message=f"Missing clip order: Please specify the desired clip order (e.g., 'reorder clips to [1, 0]'). Available clips: {len(timeline.segments)}.",
                operationId=op_id,
                clarification_prompt="Specify new clip sequence like [1, 0].",
                error_code="MISSING_ORDER"
            )

        # J. ASPECT RATIO
        if any(k in lower_instruction for k in ["aspect ratio", "vertical", "tiktok", "reel", "shorts", "landscape", "square", "9:16", "16:9", "1:1"]):
            ratio = None
            if any(k in lower_instruction for k in ["9:16", "vertical", "tiktok", "reel", "shorts"]):
                ratio = "9:16"
            elif any(k in lower_instruction for k in ["16:9", "landscape", "horizontal", "youtube"]):
                ratio = "16:9"
            elif any(k in lower_instruction for k in ["1:1", "square", "instagram post"]):
                ratio = "1:1"

            m_unsupported_ratio = re.search(r"(\d+:\d+)", lower_instruction)
            if m_unsupported_ratio and m_unsupported_ratio.group(1) not in ["16:9", "9:16", "1:1"]:
                bad_ratio = m_unsupported_ratio.group(1)
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"Unsupported aspect ratio: '{bad_ratio}'. Supported ratios: 16:9 (Landscape), 9:16 (Vertical Reel), and 1:1 (Square).",
                    operationId=op_id,
                    error_code="UNSUPPORTED_ASPECT_RATIO"
                )

            if ratio:
                mode = "crop" if "crop" in lower_instruction else ("pad" if "pad" in lower_instruction else "crop")
                op = {"type": "ASPECT_RATIO", "ratio": ratio, "mode": mode}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Please specify target aspect ratio: 9:16 (Vertical Reel), 16:9 (Landscape), or 1:1 (Square).",
                operationId=op_id,
                clarification_prompt="Choose 9:16, 16:9, or 1:1.",
                error_code="MISSING_PARAMETERS"
            )

        # K. AUDIO VOLUME
        if "volume" in lower_instruction or "boost audio" in lower_instruction or "quieter" in lower_instruction or "louder" in lower_instruction:
            m_vol = re.search(r"(\d+)\s*%", lower_instruction)
            if m_vol:
                pct = float(m_vol.group(1))
                if pct < 0 or pct > 400:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=clean_instruction,
                        operation={"type": "AUDIO_VOLUME", "volume_percent": pct},
                        message=f"Invalid volume level: {pct}%. Permitted range is 0% to 400%.",
                        operationId=op_id,
                        error_code="INVALID_VOLUME"
                    )
                op = {"type": "AUDIO_VOLUME", "volume_percent": pct, "mute": (pct == 0)}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Ambiguous volume request: Please specify the desired volume percentage (e.g., 'boost volume by 50%' or 'set volume to 150%').",
                operationId=op_id,
                clarification_prompt="Specify volume percentage (e.g. 150%).",
                error_code="AMBIGUOUS_VOLUME"
            )

        # L. VISUAL EFFECTS (Blur, Sepia, Negate)
        if any(k in lower_instruction for k in ["blur", "boxblur", "sepia", "negate", "invert color", "visual effect"]):
            effect_name = "boxblur"
            if "sepia" in lower_instruction:
                effect_name = "sepia"
            elif "negate" in lower_instruction or "invert" in lower_instruction:
                effect_name = "negate"

            tr = cls._extract_time_range(lower_instruction)
            if tr:
                st, et = tr
                err_outcome, ref, src_intervals, conv = cls._resolve_time_range(
                    st, et, timeline, ref_mode, clean_instruction, op_id, "VISUAL_EFFECT"
                )
                if err_outcome:
                    return err_outcome
                op = {
                    "type": "VISUAL_EFFECT",
                    "effect": effect_name,
                    "start": st,
                    "end": et,
                    "time_reference": ref,
                    "source_intervals": src_intervals,
                    "converted_timestamps": conv
                }
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message=f"Please specify the time range for the {effect_name} effect (e.g., 'apply {effect_name} from 00:02 to 00:05').",
                operationId=op_id,
                clarification_prompt=f"Specify start and end timestamps for {effect_name}.",
                error_code="MISSING_TIMESTAMPS"
            )

        # M. RESOLUTION
        if any(k in lower_instruction for k in ["resolution", "1080p", "720p", "480p", "4k", "8k", "2160p", "1440p", "standardize to", "resize to 720", "resize to 1080"]):
            m_unsupported_res = re.search(r"\b(4k|8k|2160p|1440p|240p|360p)\b", lower_instruction)
            if m_unsupported_res:
                bad_res = m_unsupported_res.group(1)
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation=None,
                    message=f"Unsupported resolution: '{bad_res}'. Supported standard resolutions: 1080p (Full HD), 720p (HD), and 480p (SD).",
                    operationId=op_id,
                    error_code="UNSUPPORTED_RESOLUTION"
                )

            std_res = None
            if "1080" in lower_instruction or "fhd" in lower_instruction:
                std_res = "1080p"
            elif "720" in lower_instruction or "hd" in lower_instruction:
                std_res = "720p"
            elif "480" in lower_instruction or "sd" in lower_instruction:
                std_res = "480p"

            if std_res:
                op = {"type": "RESOLUTION", "standard": std_res}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Please specify target resolution: 1080p (Full HD), 720p (HD), or 480p (SD).",
                operationId=op_id,
                clarification_prompt="Specify 1080p, 720p, or 480p.",
                error_code="AMBIGUOUS_RESOLUTION"
            )

        # N. COLOR ADJUST (Brightness & Contrast)
        if any(k in lower_instruction for k in ["brightness", "contrast", "brighten", "darken"]):
            b_val: Optional[float] = None
            c_val: Optional[float] = None

            if any(k in lower_instruction for k in ["brightness", "brighten", "darken"]):
                m_b_pct = re.search(r"brightness\s+(?:by|to|=)?\s*([+-]?\d+)\s*%", lower_instruction)
                m_b_val = re.search(r"brightness\s+(?:by|to|=)\s*([+-]?\d*(?:\.\d+)?)\b", lower_instruction)
                if m_b_pct:
                    b_val = float(m_b_pct.group(1)) / 100.0
                elif m_b_val and m_b_val.group(1):
                    try:
                        b_val = float(m_b_val.group(1))
                    except ValueError:
                        b_val = None
                elif "increase brightness" in lower_instruction or "brighten" in lower_instruction:
                    m_gen_pct = re.search(r"([+-]?\d+)\s*%", lower_instruction)
                    b_val = float(m_gen_pct.group(1)) / 100.0 if m_gen_pct else 0.2
                elif "decrease brightness" in lower_instruction or "darken" in lower_instruction:
                    m_gen_pct = re.search(r"([+-]?\d+)\s*%", lower_instruction)
                    b_val = -(float(m_gen_pct.group(1)) / 100.0) if m_gen_pct else -0.2

            if "contrast" in lower_instruction:
                m_c_pct = re.search(r"contrast\s+(?:by|to|=)?\s*([+-]?\d+)\s*%", lower_instruction)
                m_c_mult = re.search(r"contrast\s+(?:by|to|=)?\s*(\d*(?:\.\d+)?)\s*(?:x|times)?\b", lower_instruction)
                if m_c_pct:
                    c_val = 1.0 + float(m_c_pct.group(1)) / 100.0
                elif m_c_mult and m_c_mult.group(1):
                    try:
                        c_val = float(m_c_mult.group(1))
                    except ValueError:
                        c_val = None
                elif "increase contrast" in lower_instruction or "boost contrast" in lower_instruction:
                    c_val = 1.3
                elif "decrease contrast" in lower_instruction:
                    c_val = 0.8

            if b_val is not None or c_val is not None:
                final_b = b_val if b_val is not None else 0.0
                final_c = c_val if c_val is not None else 1.0
                if final_b < -1.0 or final_b > 1.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=clean_instruction,
                        operation={"type": "COLOR_ADJUST", "brightness": final_b, "contrast": final_c},
                        message=f"Invalid brightness offset ({final_b}): must be between -1.0 and 1.0.",
                        operationId=op_id,
                        error_code="INVALID_PARAMETER"
                    )
                if final_c < 0.0 or final_c > 3.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=clean_instruction,
                        operation={"type": "COLOR_ADJUST", "brightness": final_b, "contrast": final_c},
                        message=f"Invalid contrast multiplier ({final_c}): must be between 0.0 and 3.0.",
                        operationId=op_id,
                        error_code="INVALID_PARAMETER"
                    )

                op = {"type": "COLOR_ADJUST", "brightness": round(final_b, 2), "contrast": round(final_c, 2)}
                return cls._execute_normalized_operation(
                    clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure
                )

            return InstructionOutcome(
                status=InstructionStatus.NEEDS_CLARIFICATION,
                instruction=clean_instruction,
                operation=None,
                message="Please specify the amount to adjust brightness or contrast (e.g., 'increase brightness by 20%' or 'set contrast to 1.5x').",
                operationId=op_id,
                clarification_prompt="Specify brightness percentage or contrast factor.",
                error_code="AMBIGUOUS_PARAMETERS"
            )

        # O. SILENCE REMOVAL
        if any(k in lower_instruction for k in ["silence", "silent pauses", "dead air", "remove pauses", "cut pauses"]):
            op = {"type": "SILENCE_REMOVAL", "threshold_db": -30.0, "min_duration": 0.5, "confirmed_intervals": []}
            return cls._execute_normalized_operation(
                clean_instruction, op, timeline, timeline_snapshot, source_dur, op_id, simulate_execution_failure, silence_segments=silence_segments
            )

        # ---------------------------------------------------------------------
        # 6. UNRECOGNIZED INSTRUCTION (REJECTED)
        # ---------------------------------------------------------------------
        return InstructionOutcome(
            status=InstructionStatus.REJECTED,
            instruction=clean_instruction,
            operation=None,
            message="Unrecognized instruction: Could not identify any supported video editing action from your prompt.",
            operationId=op_id,
            error_code="UNRECOGNIZED_INSTRUCTION"
        )

    # -------------------------------------------------------------------------
    # Helper: Detect Time Reference & Conflict
    # -------------------------------------------------------------------------
    @classmethod
    def _detect_time_reference(cls, text: str, explicit_ref: Optional[str] = None) -> Tuple[Optional[str], bool]:
        """
        Detects whether the instruction explicitly references 'timeline' or 'source' coordinates.
        Returns: (reference_mode, is_conflicting).
        reference_mode: 'timeline', 'source', or None (unspecified).
        """
        has_tl = False
        has_src = False

        if explicit_ref:
            ref_low = explicit_ref.strip().lower()
            if ref_low in ["timeline", "player", "playback"]:
                has_tl = True
            elif ref_low in ["source", "raw", "original"]:
                has_src = True
            elif ref_low in ["ambiguous", "unclear", "unknown"]:
                return None, True

        low = text.lower()
        if re.search(r"\b(timeline|in\s+timeline|on\s+timeline|playback|current\s+edit|current\s+video|player|preview)\b", low):
            has_tl = True
        if re.search(r"\b(source|in\s+source|original|raw\s+video|raw\s+footage|original\s+footage|original\s+video)\b", low):
            has_src = True

        if has_tl and has_src:
            return None, True
        if has_tl:
            return "timeline", False
        if has_src:
            return "source", False
        return None, False

    # -------------------------------------------------------------------------
    # Helper: Resolve Time Range according to Feature 7 Policy
    # -------------------------------------------------------------------------
    @classmethod
    def _resolve_time_range(
        cls,
        st: Optional[float],
        et: Optional[float],
        timeline: Timeline,
        ref_mode: Optional[str],
        clean_instruction: str,
        op_id: str,
        op_type: str
    ) -> Tuple[Optional[InstructionOutcome], str, List[Tuple[float, float, str]], Dict[str, Any]]:
        """
        Enforces Feature 7: Consistent Timestamp Reference Policy.
        - Clearly distinguishes original-source timestamps from current-timeline timestamps.
        - Documented default: current-timeline timestamps on diverged timeline.
        - Requires clarification (NEEDS_CLARIFICATION) when an instruction is genuinely ambiguous.
        - Converts timestamps correctly after cuts, trims, speed changes, and clip reordering.
        """
        if st is None or et is None:
            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=clean_instruction,
                operation={"type": op_type, "start": st, "end": et},
                message="Missing timestamps: start and end times must both be valid numbers.",
                operationId=op_id,
                error_code="INVALID_TIME_RANGE"
            ), "", [], {}

        if st < 0.0 or et < 0.0:
            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=clean_instruction,
                operation={"type": op_type, "start": st, "end": et},
                message=f"Invalid time range: timestamps cannot be negative (received start={st}s, end={et}s).",
                operationId=op_id,
                error_code="INVALID_TIME_RANGE"
            ), "", [], {}

        if st >= et:
            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=clean_instruction,
                operation={"type": op_type, "start": st, "end": et},
                message=f"Invalid time range: start timestamp ({st}s) cannot be greater than or equal to end timestamp ({et}s).",
                operationId=op_id,
                error_code="INVALID_TIME_RANGE"
            ), "", [], {}

        src_dur = round(float(timeline.source_duration), 4)
        tl_dur = round(float(timeline.total_duration), 4)

        # Whole-video cut rejection (Feature 11)
        if op_type in ["CUT", "TIME_SLICE"]:
            if ref_mode == "timeline" and st <= 1e-4 and et >= tl_dur - 1e-4:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation={"type": op_type, "start": st, "end": et, "time_reference": "timeline"},
                    message=f"Whole-video cut rejected: cutting from {st}s to {et}s would remove the entire video (timeline duration {tl_dur}s). ClipPilot AI requires at least one surviving video segment.",
                    operationId=op_id,
                    error_code="WHOLE_VIDEO_CUT_REJECTED",
                    options=[
                        "Trim the start or end instead of cutting the entire video",
                        "Mute the audio instead of cutting video",
                        "Adjust cut range to retain desired content"
                    ]
                ), "", [], {}
            elif ref_mode != "timeline" and st <= 1e-4 and et >= src_dur - 1e-4:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation={"type": op_type, "start": st, "end": et, "time_reference": "source"},
                    message=f"Whole-video cut rejected: cutting from {st}s to {et}s would remove the entire video (source duration {src_dur}s). ClipPilot AI requires at least one surviving video segment.",
                    operationId=op_id,
                    error_code="WHOLE_VIDEO_CUT_REJECTED",
                    options=[
                        "Trim the start or end instead of cutting the entire video",
                        "Mute the audio instead of cutting video",
                        "Adjust cut range to retain desired content"
                    ]
                ), "", [], {}

            # Feature 9: Check partial cut intersection with captions lacking word-level timing
            if ref_mode == "timeline":
                mapped_src = timeline.map_timeline_range_to_source(st, et)
                cs_intervals = [(s[0], s[1]) for s in mapped_src]
            else:
                cs_intervals = [(st, et)]

            for eff in timeline.effects:
                if eff.type == "caption":
                    for cs, ce in cs_intervals:
                        overlap_s = max(eff.source_start, cs)
                        overlap_e = min(eff.source_end, ce)
                        if overlap_e > overlap_s + 1e-4:
                            is_full_cut = (cs <= eff.source_start + 1e-4 and ce >= eff.source_end - 1e-4)
                            if not is_full_cut:
                                words = eff.parameters.get("words")
                                if not words or not isinstance(words, list) or len(words) == 0:
                                    return InstructionOutcome(
                                        status=InstructionStatus.NEEDS_CLARIFICATION,
                                        instruction=clean_instruction,
                                        operation={"type": op_type, "start": st, "end": et},
                                        message=f"Partial cut overlaps caption '{eff.label}' [{eff.source_start:.2f}s - {eff.source_end:.2f}s], but word-level timestamps are unavailable. Word-level timing is required to accurately trim caption text and timing.",
                                        clarification_prompt="Specify whether to keep the entire caption, remove it entirely, or adjust the cut range.",
                                        operationId=op_id,
                                        error_code="CAPTION_WORD_TIMING_UNAVAILABLE",
                                        options=[
                                            f"Keep entire caption '{eff.label}'",
                                            f"Remove entire caption '{eff.label}'",
                                            "Adjust cut range to avoid splitting caption"
                                        ]
                                    ), "", [], {}

        # Case 1: Explicit SOURCE reference
        if ref_mode == "source":
            if st >= src_dur:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation={"type": op_type, "start": st, "end": et, "time_reference": "source"},
                    message=f"Invalid source time range: start timestamp ({st}s) exceeds total source duration ({src_dur}s).",
                    operationId=op_id,
                    error_code="INVALID_TIME_RANGE"
                ), "", [], {}
            if et > src_dur:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation={"type": op_type, "start": st, "end": et, "time_reference": "source"},
                    message=f"Invalid source time range: end timestamp ({et}s) exceeds total source duration ({src_dur}s).",
                    operationId=op_id,
                    error_code="INVALID_TIME_RANGE"
                ), "", [], {}

            source_intervals = [(round(st, 4), round(et, 4), timeline.source_id)]
            tl_intervals = timeline.map_source_range_to_timeline(st, et)
            conv = {
                "input_reference": "source",
                "source_range": [round(st, 4), round(et, 4)],
                "timeline_intervals": [
                    {"timeline_start": round(t[0], 4), "timeline_end": round(t[1], 4), "clip_id": t[2]}
                    for t in tl_intervals
                ]
            }
            return None, "source", source_intervals, conv

        # Case 2: Explicit TIMELINE reference
        if ref_mode == "timeline":
            if st >= tl_dur:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation={"type": op_type, "start": st, "end": et, "time_reference": "timeline"},
                    message=f"Invalid timeline time range: start timestamp ({st}s) exceeds current timeline duration ({tl_dur}s).",
                    operationId=op_id,
                    error_code="INVALID_TIME_RANGE"
                ), "", [], {}
            if et > tl_dur:
                return InstructionOutcome(
                    status=InstructionStatus.REJECTED,
                    instruction=clean_instruction,
                    operation={"type": op_type, "start": st, "end": et, "time_reference": "timeline"},
                    message=f"Invalid timeline time range: end timestamp ({et}s) exceeds current timeline duration ({tl_dur}s).",
                    operationId=op_id,
                    error_code="INVALID_TIME_RANGE"
                ), "", [], {}

            source_intervals = timeline.map_timeline_range_to_source(st, et)
            conv = {
                "input_reference": "timeline",
                "timeline_range": [round(st, 4), round(et, 4)],
                "source_intervals": [
                    {"source_start": round(s[0], 4), "source_end": round(s[1], 4), "clip_id": s[2]}
                    for s in source_intervals
                ]
            }
            return None, "timeline", source_intervals, conv

        # Case 2: Explicit SOURCE reference OR Documented Default (Original-Source Timestamps)
        if st >= src_dur:
            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=clean_instruction,
                operation={"type": op_type, "start": st, "end": et, "time_reference": "source"},
                message=f"Invalid time range: start timestamp ({st}s) exceeds total media duration ({src_dur}s).",
                operationId=op_id,
                error_code="INVALID_TIME_RANGE"
            ), "", [], {}
        if et > src_dur:
            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=clean_instruction,
                operation={"type": op_type, "start": st, "end": et, "time_reference": "source"},
                message=f"Invalid time range: end timestamp ({et}s) exceeds total media duration ({src_dur}s).",
                operationId=op_id,
                error_code="INVALID_TIME_RANGE"
            ), "", [], {}

        source_intervals = [(round(st, 4), round(et, 4), timeline.source_id)]
        tl_intervals = timeline.map_source_range_to_timeline(st, et)
        conv = {
            "input_reference": "source",
            "source_range": [round(st, 4), round(et, 4)],
            "timeline_intervals": [
                {"timeline_start": round(t[0], 4), "timeline_end": round(t[1], 4), "clip_id": t[2]}
                for t in tl_intervals
            ]
        }
        return None, "source", source_intervals, conv

    # -------------------------------------------------------------------------
    # Helper: Extract and Validate Time Range Constraints
    # -------------------------------------------------------------------------
    @classmethod
    def _extract_time_range(cls, text: str) -> Optional[Tuple[float, float]]:
        """
        Extracts start and end timestamps (allowing negative numbers for rejection validation).
        Matches patterns like:
        - from 00:02 to 00:05
        - between 2s and 5s
        - from -2s to 4s
        - 3s to 5s
        """
        pat = r"(?:from\s+|between\s+)?(-?\d{1,2}:\d{2}(?:\.\d+)?|-?\d+(?:\.\d+)?\s*(?:s|sec|seconds)?)\s*(?:to|until|through|\band\b|-(?!\d))\s*(-?\d{1,2}:\d{2}(?:\.\d+)?|-?\d+(?:\.\d+)?\s*(?:s|sec|seconds)?)"
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            st = parse_time_str(m.group(1))
            et = parse_time_str(m.group(2))
            if st is not None and et is not None:
                return (st, et)
        return None

    @staticmethod
    def _validate_time_range(st: Optional[float], et: Optional[float], duration: float) -> Optional[str]:
        if st is None or et is None:
            return "Missing timestamps: start and end times must both be valid numbers."
        if st < 0.0 or et < 0.0:
            return f"Invalid time range: timestamps cannot be negative (received start={st}s, end={et}s)."
        if st >= et:
            return f"Invalid time range: start timestamp ({st}s) cannot be greater than or equal to end timestamp ({et}s)."
        if st >= duration:
            return f"Invalid time range: start timestamp ({st}s) exceeds total media duration ({duration}s)."
        if et > duration:
            return f"Invalid time range: end timestamp ({et}s) exceeds total media duration ({duration}s)."
        return None

    # -------------------------------------------------------------------------
    # Helper: Execute Normalized Operation with Rollback Transaction Safety
    # -------------------------------------------------------------------------
    @classmethod
    def _execute_normalized_operation(
        cls,
        instruction: str,
        normalized_op: Dict[str, Any],
        timeline: Timeline,
        timeline_snapshot: Dict[str, Any],
        source_dur: float,
        op_id: str,
        simulate_execution_failure: bool = False,
        explicit_time_reference: Optional[str] = None,
        silence_segments: Optional[List[Dict[str, Any]]] = None
    ) -> InstructionOutcome:
        """
        Executes normalized operation against timeline.
        Transactional guarantee: validates parameters before execution,
        and if anything fails, rolls back timeline state completely.
        Anchors content-aware effects to source media coordinates.
        """
        op_type = (normalized_op.get("type") or "").upper()

        try:
            if simulate_execution_failure:
                raise RuntimeError("Simulated internal rendering or timeline engine crash during operation execution.")

            # Resolve coordinates and enforce Feature 7 policy if start/end provided without source_intervals
            time_ref = normalized_op.get("time_reference") or explicit_time_reference
            if op_type in ["MUTE", "MUTE_RANGE", "BEEP", "CENSOR", "CUT", "TIME_SLICE", "CAPTION", "VISUAL_EFFECT", "SPEED"]:
                if "start" in normalized_op and "end" in normalized_op and normalized_op["start"] is not None and normalized_op["end"] is not None:
                    if "source_intervals" not in normalized_op:
                        st = float(normalized_op.get("start", 0.0))
                        et = float(normalized_op.get("end", 0.0))
                        err_outcome, resolved_ref, src_intervals, conv = cls._resolve_time_range(
                            st, et, timeline, time_ref, instruction, op_id, op_type
                        )
                        if err_outcome:
                            return err_outcome
                        normalized_op["time_reference"] = resolved_ref
                        normalized_op["source_intervals"] = src_intervals
                        normalized_op["converted_timestamps"] = conv

            # Parameter validation before modifying timeline
            if op_type == "SPEED":
                spd = float(normalized_op.get("speed", 1.0))
                if spd <= 0.0 or spd > 16.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Invalid speed factor ({spd}x): playback speed must be greater than 0 and at most 16.0x.",
                        operationId=op_id,
                        error_code="INVALID_SPEED"
                    )

            if op_type in ["AUDIO_VOLUME", "VOLUME"]:
                pct = float(normalized_op.get("volume_percent") if "volume_percent" in normalized_op else (normalized_op.get("volume", 1.0) * 100.0))
                if pct < 0.0 or pct > 400.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Invalid volume level: {pct}%. Permitted range is 0% to 400%.",
                        operationId=op_id,
                        error_code="INVALID_VOLUME"
                    )

            if op_type in ["TRIM_START", "TRIM_END"]:
                sec = float(normalized_op.get("seconds", 0.0))
                if sec <= 0.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Invalid trim duration: trim length ({sec}s) must be positive.",
                        operationId=op_id,
                        error_code="INVALID_DURATION"
                    )

            if op_type == "ASPECT_RATIO":
                ratio = normalized_op.get("ratio")
                if ratio not in ["16:9", "9:16", "1:1"]:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Unsupported aspect ratio: '{ratio}'. Supported ratios: 16:9, 9:16, 1:1.",
                        operationId=op_id,
                        error_code="UNSUPPORTED_ASPECT_RATIO"
                    )

            if op_type == "RESOLUTION":
                std = normalized_op.get("standard")
                if std not in ["720p", "1080p", "480p", "source"]:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Unsupported resolution: '{std}'. Supported resolutions: 1080p, 720p, and 480p.",
                        operationId=op_id,
                        error_code="UNSUPPORTED_RESOLUTION"
                    )

            if op_type == "COLOR_ADJUST":
                br = float(normalized_op.get("brightness", 0.0))
                ct = float(normalized_op.get("contrast", 1.0))
                if br < -1.0 or br > 1.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Invalid brightness offset ({br}): must be between -1.0 and 1.0.",
                        operationId=op_id,
                        error_code="INVALID_PARAMETER"
                    )
                if ct < 0.0 or ct > 3.0:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Invalid contrast multiplier ({ct}): must be between 0.0 and 3.0.",
                        operationId=op_id,
                        error_code="INVALID_PARAMETER"
                    )

            # -----------------------------------------------------------------
            # EXECUTION WITH CONTENT-AWARE ANCHORING
            # -----------------------------------------------------------------
            if op_type in ["MUTE", "MUTE_RANGE"]:
                src_intervals = normalized_op.get("source_intervals")
                if src_intervals:
                    for s_st, s_et, _ in src_intervals:
                        timeline.add_effect("mute", s_st, s_et, label=f"Mute [{s_st:.2f}s - {s_et:.2f}s]")
                else:
                    st = float(normalized_op.get("start", 0.0))
                    et = float(normalized_op.get("end", source_dur))
                    timeline.add_effect("mute", st, et, label=f"Mute [{st:.2f}s - {et:.2f}s]")

            elif op_type in ["BEEP", "CENSOR"]:
                freq = int(normalized_op.get("frequency", 1000))
                src_intervals = normalized_op.get("source_intervals")
                if src_intervals:
                    for s_st, s_et, _ in src_intervals:
                        timeline.add_effect("beep", s_st, s_et, parameters={"frequency": freq}, label=f"Beep {freq}Hz [{s_st:.2f}s - {s_et:.2f}s]")
                else:
                    st = float(normalized_op.get("start", 0.0))
                    et = float(normalized_op.get("end", source_dur))
                    timeline.add_effect("beep", st, et, parameters={"frequency": freq}, label=f"Beep {freq}Hz [{st:.2f}s - {et:.2f}s]")

            elif op_type == "CUT":
                st = float(normalized_op.get("start", 0.0))
                et = float(normalized_op.get("end", 0.0))
                eff_ref = normalized_op.get("time_reference", "timeline")

                # Check for duplicate cut instruction
                is_duplicate = any(
                    abs(c.get("start", 0.0) - st) < 1e-4 and
                    abs(c.get("end", 0.0) - et) < 1e-4 and
                    c.get("reference") == eff_ref
                    for c in timeline.applied_cuts
                )
                if is_duplicate:
                    return InstructionOutcome(
                        status=InstructionStatus.REJECTED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=f"Duplicate operation: cut range [{st:.2f}s - {et:.2f}s] in {eff_ref} has already been cut.",
                        operationId=op_id,
                        error_code="DUPLICATE_OPERATION"
                    )

                if eff_ref == "source":
                    timeline.apply_cut(st, et)
                else:
                    if st >= timeline.total_duration - 1e-4:
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=instruction,
                            operation=normalized_op,
                            message=f"Invalid cut: timeline range [{st:.2f}s - {et:.2f}s] is beyond current timeline duration ({timeline.total_duration:.2f}s).",
                            operationId=op_id,
                            error_code="INVALID_TIME_RANGE"
                        )
                    timeline.apply_timeline_cut(st, et)

                timeline.applied_cuts.append({"start": st, "end": et, "reference": eff_ref})

            elif op_type == "SPEED":
                spd = float(normalized_op.get("speed", 1.0))
                st = normalized_op.get("start")
                et = normalized_op.get("end")
                if st is not None and et is not None:
                    st_f = float(st)
                    et_f = float(et)
                    src_intervals = normalized_op.get("source_intervals")
                    check_ranges = [(s[0], s[1]) for s in src_intervals] if src_intervals else [(st_f, et_f)]

                    overlapping_segs = []
                    for seg in timeline.segments:
                        for cr_s, cr_e in check_ranges:
                            if max(seg.source_start, cr_s) < min(seg.source_end, cr_e):
                                overlapping_segs.append(seg)
                                break

                    if overlapping_segs:
                        # 1. Duplicate speed check: all overlapping segments already have spd
                        if all(abs(seg.speed - spd) < 1e-4 for seg in overlapping_segs):
                            return InstructionOutcome(
                                status=InstructionStatus.REJECTED,
                                instruction=instruction,
                                operation=normalized_op,
                                message=f"Duplicate operation: playback speed is already {spd}x for this range.",
                                operationId=op_id,
                                error_code="DUPLICATE_OPERATION"
                            )
                        # 2. Conflicting speed overlap check: segment has speed != 1.0 and speed != spd
                        conflicting = [seg.speed for seg in overlapping_segs if abs(seg.speed - spd) > 1e-4 and abs(seg.speed - 1.0) > 1e-4]
                        if conflicting:
                            conf_spd = conflicting[0]
                            return InstructionOutcome(
                                status=InstructionStatus.NEEDS_CLARIFICATION,
                                instruction=instruction,
                                operation=normalized_op,
                                message=f"Conflicting speed overlap detected: requested {spd}x on [{st_f:.2f}s - {et_f:.2f}s] overlaps with existing {conf_spd}x. Please clarify how to resolve the overlap.",
                                clarification_prompt="Choose how to resolve conflicting speed overlap.",
                                operationId=op_id,
                                error_code="CONFLICTING_SPEED_OVERLAP",
                                options=[
                                    f"Apply {spd}x across the entire range",
                                    f"Keep existing {conf_spd}x and apply {spd}x only to non-overlapping part",
                                    f"Replace existing with {spd}x",
                                    "Cancel"
                                ]
                            )

                    # Merge identical speeds or apply speed
                    if src_intervals:
                        for s_st, s_et, _ in src_intervals:
                            timeline.apply_speed_change(spd, s_st, s_et)
                    else:
                        timeline.apply_speed_change(spd, st_f, et_f)
                else:
                    if all(abs(seg.speed - spd) < 1e-4 for seg in timeline.segments):
                        return InstructionOutcome(
                            status=InstructionStatus.REJECTED,
                            instruction=instruction,
                            operation=normalized_op,
                            message=f"Duplicate operation: entire video is already set to {spd}x speed.",
                            operationId=op_id,
                            error_code="DUPLICATE_OPERATION"
                        )
                    timeline.apply_speed_change(spd)

            elif op_type == "REORDER":
                order = normalized_op.get("order", [])
                timeline.reorder_segments(order)

            elif op_type in ["CAPTION", "SUBTITLES"]:
                if normalized_op.get("burn") and not normalized_op.get("text"):
                    # Global subtitle burn
                    pass
                else:
                    text = normalized_op.get("text", "Caption")
                    src_intervals = normalized_op.get("source_intervals")
                    if src_intervals:
                        for s_st, s_et, _ in src_intervals:
                            timeline.add_effect("caption", s_st, s_et, parameters={"text": text}, label=text)
                    else:
                        st = float(normalized_op.get("start", 0.0))
                        et = float(normalized_op.get("end", source_dur))
                        timeline.add_effect("caption", st, et, parameters={"text": text}, label=text)

            elif op_type == "TIME_SLICE":
                st = float(normalized_op.get("start", 0.0))
                et = float(normalized_op.get("end", source_dur))
                eff_ref = normalized_op.get("time_reference", "timeline")
                if eff_ref == "source":
                    timeline.apply_time_slice(st, et)
                else:
                    # Apply cut from end to timeline duration first
                    if et < timeline.total_duration - 1e-5:
                        timeline.apply_timeline_cut(et, timeline.total_duration)
                    # Apply cut from 0 to start
                    if st > 1e-5:
                        timeline.apply_timeline_cut(0.0, st)

            elif op_type == "TRIM_START":
                sec = float(normalized_op.get("seconds", 0.0))
                eff_ref = normalized_op.get("time_reference", "timeline")
                if eff_ref == "source":
                    timeline.apply_trim_start(sec)
                else:
                    timeline.apply_timeline_cut(0.0, sec)

            elif op_type == "TRIM_END":
                sec = float(normalized_op.get("seconds", 0.0))
                eff_ref = normalized_op.get("time_reference", "timeline")
                if eff_ref == "source":
                    timeline.apply_trim_end(sec)
                else:
                    cut_start = max(0.0, timeline.total_duration - sec)
                    timeline.apply_timeline_cut(cut_start, timeline.total_duration)

            elif op_type == "VISUAL_EFFECT":
                eff = normalized_op.get("effect", "boxblur")
                src_intervals = normalized_op.get("source_intervals")
                if src_intervals:
                    for s_st, s_et, _ in src_intervals:
                        timeline.add_effect("visual_effect", s_st, s_et, parameters={"effect": eff}, label=eff)
                else:
                    st = float(normalized_op.get("start", 0.0))
                    et = float(normalized_op.get("end", source_dur))
                    timeline.add_effect("visual_effect", st, et, parameters={"effect": eff}, label=eff)

            elif op_type in ["AUDIO_VOLUME", "VOLUME"]:
                pct = float(normalized_op.get("volume_percent") if "volume_percent" in normalized_op else (normalized_op.get("volume", 1.0) * 100.0))
                timeline.add_effect("volume", 0.0, source_dur, parameters={"volume": pct / 100.0}, label=f"Volume {pct}%")

            elif op_type == "SILENCE_REMOVAL":
                if silence_segments:
                    uncertain_segs = [
                        s for s in silence_segments
                        if s.get("classification") == "uncertain" or (0.3 <= float(s.get("confidence", 1.0)) <= 0.7)
                    ]
                    if uncertain_segs:
                        return InstructionOutcome(
                            status=InstructionStatus.NEEDS_CLARIFICATION,
                            instruction=instruction,
                            operation=normalized_op,
                            message="Detected silence contains pauses that may be intentional/deliberate speech pauses. Please confirm which pauses to remove.",
                            clarification_prompt="Confirm whether to preserve deliberate pauses or remove all silence.",
                            operationId=op_id,
                            error_code="UNCERTAIN_PAUSE_CLASSIFICATION",
                            options=[
                                "Remove only clear dead air (preserve deliberate pauses)",
                                "Remove all silence including potential pauses",
                                "Cancel"
                            ]
                        )
                    dead_air = [
                        s for s in silence_segments
                        if not s.get("is_deliberate", False) and s.get("classification") != "deliberate_pause"
                    ]
                    deliberate = [
                        s for s in silence_segments
                        if s.get("is_deliberate", False) or s.get("classification") == "deliberate_pause"
                    ]
                    for s in sorted(dead_air, key=lambda x: x.get("start", 0.0), reverse=True):
                        s_st = float(s.get("start", 0.0))
                        s_et = float(s.get("end", 0.0))
                        if s_et > s_st:
                            timeline.apply_cut(s_st, s_et)
                    msg = f"Silence removal applied: cut {len(dead_air)} dead air segments. Preserved {len(deliberate)} deliberate speech pauses."
                    all_warnings = list(timeline.warnings)
                    if timeline.notifications:
                        all_warnings.extend(timeline.notifications)
                    return InstructionOutcome(
                        status=InstructionStatus.APPLIED,
                        instruction=instruction,
                        operation=normalized_op,
                        message=msg,
                        operationId=op_id,
                        timeline=timeline.to_dict(),
                        time_reference="source",
                        warnings=all_warnings if all_warnings else None
                    )

            elif op_type in ["ASPECT_RATIO", "RESOLUTION", "COLOR_ADJUST"]:
                # Container / metadata level operations committed directly
                pass

            else:
                raise ValueError(f"Unknown normalized operation type: {op_type}")

            # Verify timeline invariant integrity after mutation
            if timeline.total_duration <= 0 or len(timeline.segments) == 0:
                raise ValueError("Timeline integrity violation: duration reduced to 0 or all segments deleted.")

            # Format informative message
            msg = f"{op_type} operation validated, executed, and committed successfully."
            ref = normalized_op.get("time_reference")
            conv = normalized_op.get("converted_timestamps")
            if conv and ref == "timeline" and timeline.is_diverged():
                tl_rng = conv.get("timeline_range")
                src_ints = conv.get("source_intervals")
                if tl_rng and src_ints:
                    src_desc = ", ".join([f"{s['source_start']:.2f}s-{s['source_end']:.2f}s" for s in src_ints])
                    msg = f"{op_type} operation applied successfully at timeline {tl_rng[0]:.2f}s-{tl_rng[1]:.2f}s (mapped to source {src_desc})."
            elif conv and ref == "source" and timeline.is_diverged():
                src_rng = conv.get("source_range")
                tl_ints = conv.get("timeline_intervals")
                if src_rng and tl_ints:
                    tl_desc = ", ".join([f"{t['timeline_start']:.2f}s-{t['timeline_end']:.2f}s" for t in tl_ints])
                    msg = f"{op_type} operation applied successfully at source {src_rng[0]:.2f}s-{src_rng[1]:.2f}s (active on timeline {tl_desc})."

            all_warnings = list(timeline.warnings)
            if timeline.notifications:
                all_warnings.extend(timeline.notifications)

            return InstructionOutcome(
                status=InstructionStatus.APPLIED,
                instruction=instruction,
                operation=normalized_op,
                message=msg,
                operationId=op_id,
                timeline=timeline.to_dict(),
                time_reference=ref,
                converted_timestamps=conv,
                warnings=all_warnings if all_warnings else None
            )

        except Exception as ex:
            # TRANSACTION ROLLBACK: Restore previous state completely
            restored = Timeline.from_dict(timeline_snapshot)
            timeline.source_duration = restored.source_duration
            timeline.source_id = restored.source_id
            timeline.segments = restored.segments
            timeline.effects = restored.effects
            timeline.notifications = restored.notifications
            timeline.warnings = restored.warnings
            timeline._recalculate_timeline()

            return InstructionOutcome(
                status=InstructionStatus.REJECTED,
                instruction=instruction,
                operation=normalized_op,
                message=f"Operation failed midway during execution: {str(ex)}. Rollback performed: timeline restored to previous state.",
                operationId=op_id,
                error_code="EXECUTION_FAILED",
                rollback_performed=True,
                timeline=timeline.to_dict(),
                time_reference=normalized_op.get("time_reference"),
                converted_timestamps=normalized_op.get("converted_timestamps")
            )
