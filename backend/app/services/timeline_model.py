"""
ClipPilot AI - Content-Aware Timeline Transformation Model
=========================================================
Implements deterministic, content-anchored video editing timelines.

Captions, mute ranges, beep effects, and visual filters are anchored to
immutable source-media timestamps rather than volatile timeline positions.
When cuts, trims, speed changes, or clip reorderings occur, the timeline
engine deterministically maps source anchors into current timeline positions.

DOCUMENTED POLICY:
------------------
1. Complete Retention:
   If an effect's source interval [s_start, s_end] is fully enclosed within a retained
   segment, it transforms 1-to-1 to [tl_start, tl_end] with duration scaled by 1/speed.
2. Content Removal:
   If an effect's content was excised by a trim or cut, it is marked as 'dropped_content_removed'
   and omitted from the final rendering to avoid ghost effects.
3. Partial Cut / Boundary Truncation:
   If an effect partially overlaps a cut, it is clipped to the retained content boundary:
   [max(s_start, seg.source_start), min(s_end, seg.source_end)] with status 'clipped'.
4. Splitting Across Cuts:
   If an effect spans across a cut or across multiple segments, it is split into discrete
   timeline effect instances, each preserving its respective content affinity (status 'split').
5. Speed Transformation:
   Segment speed changes (e.g. 2.0x fast, 0.5x slow-mo) transform timeline duration:
   tl_dur = (s_end - s_start) / speed, without altering the underlying source anchor.
6. Clip Reordering:
   Moving or reordering segments automatically moves all anchored effects along with
   their corresponding video frames.
"""

import hashlib
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TimelineSegment:
    """Represents a piece of source media placed on the edited timeline."""
    clip_id: str
    source_id: str
    source_start: float
    source_end: float
    speed: float = 1.0
    timeline_start: float = 0.0
    timeline_end: float = 0.0

    @property
    def source_duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)

    @property
    def timeline_duration(self) -> float:
        if self.speed <= 0:
            return 0.0
        return self.source_duration / self.speed

    def to_dict(self) -> Dict[str, Any]:
        s_start = 0.0 if abs(self.source_start) < 1e-9 else round(float(self.source_start), 4)
        s_end = 0.0 if abs(self.source_end) < 1e-9 else round(float(self.source_end), 4)
        tl_start = 0.0 if abs(self.timeline_start) < 1e-9 else round(float(self.timeline_start), 4)
        tl_end = 0.0 if abs(self.timeline_end) < 1e-9 else round(float(self.timeline_end), 4)
        tl_dur = 0.0 if abs(self.timeline_duration) < 1e-9 else round(float(self.timeline_duration), 4)
        return {
            "clip_id": str(self.clip_id),
            "source_id": str(self.source_id),
            "source_start": s_start,
            "source_end": s_end,
            "speed": round(float(self.speed), 4),
            "timeline_start": tl_start,
            "timeline_end": tl_end,
            "timeline_duration": tl_dur,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineSegment":
        return cls(
            clip_id=str(data.get("clip_id") or "clip_0"),
            source_id=str(data.get("source_id", "src_original")),
            source_start=float(data.get("source_start", 0.0)),
            source_end=float(data.get("source_end", 0.0)),
            speed=float(data.get("speed", 1.0)),
            timeline_start=float(data.get("timeline_start", 0.0)),
            timeline_end=float(data.get("timeline_end", 0.0)),
        )


@dataclass
class ContentAwareEffect:
    """
    An edit operation anchored to source media timestamps.
    Supported types: 'caption', 'mute', 'beep', 'visual_effect', 'color_adjust'.
    """
    effect_id: str
    type: str
    source_id: str
    source_start: float
    source_end: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        params = {}
        for k in sorted((self.parameters or {}).keys()):
            v = self.parameters[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                params[k] = 0.0 if abs(v) < 1e-9 else round(float(v), 4)
            else:
                params[k] = v
        s_dur = max(0.0, self.source_end - self.source_start)
        s_start = 0.0 if abs(self.source_start) < 1e-9 else round(float(self.source_start), 4)
        s_end = 0.0 if abs(self.source_end) < 1e-9 else round(float(self.source_end), 4)
        s_dur_norm = 0.0 if abs(s_dur) < 1e-9 else round(float(s_dur), 4)
        return {
            "effect_id": str(self.effect_id),
            "type": str(self.type),
            "source_id": str(self.source_id),
            "source_start": s_start,
            "source_end": s_end,
            "source_duration": s_dur_norm,
            "parameters": params,
            "label": self.label or "",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentAwareEffect":
        return cls(
            effect_id=str(data.get("effect_id") or "eff_0"),
            type=str(data.get("type", "caption")),
            source_id=str(data.get("source_id", "src_original")),
            source_start=float(data.get("source_start", 0.0)),
            source_end=float(data.get("source_end", 0.0)),
            parameters=dict(data.get("parameters", {})),
            label=data.get("label"),
        )


@dataclass
class TransformedTimelineEffect:
    """The computed timeline position of a ContentAwareEffect after timeline transforms."""
    effect_id: str
    type: str
    source_id: str
    source_start: float
    source_end: float
    segment_id: str
    timeline_start: float
    timeline_end: float
    duration: float
    speed: float
    status: str  # 'active', 'clipped', 'split', 'dropped_content_removed'
    parameters: Dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None
    parent_effect_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        params = {}
        for k in sorted((self.parameters or {}).keys()):
            v = self.parameters[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                params[k] = 0.0 if abs(v) < 1e-9 else round(float(v), 4)
            else:
                params[k] = v
        s_start = 0.0 if abs(self.source_start) < 1e-9 else round(float(self.source_start), 4)
        s_end = 0.0 if abs(self.source_end) < 1e-9 else round(float(self.source_end), 4)
        tl_start = 0.0 if abs(self.timeline_start) < 1e-9 else round(float(self.timeline_start), 4)
        tl_end = 0.0 if abs(self.timeline_end) < 1e-9 else round(float(self.timeline_end), 4)
        dur = 0.0 if abs(self.duration) < 1e-9 else round(float(self.duration), 4)
        return {
            "effect_id": str(self.effect_id),
            "parent_effect_id": str(self.parent_effect_id or self.effect_id),
            "type": str(self.type),
            "source_id": str(self.source_id),
            "source_start": s_start,
            "source_end": s_end,
            "segment_id": str(self.segment_id),
            "timeline_start": tl_start,
            "timeline_end": tl_end,
            "duration": dur,
            "speed": round(float(self.speed), 4),
            "status": str(self.status),
            "parameters": params,
            "label": self.label or "",
        }


class Timeline:
    """
    Timeline transformation engine.
    Maintains a list of TimelineSegments and ContentAwareEffects.
    Provides deterministic bi-directional mapping and transformation.
    """

    def __init__(self, source_duration: float, source_id: str = "src_original", fps: float = 30.0):
        self.source_duration = max(0.0, float(source_duration))
        self.source_id = str(source_id).strip()
        self.fps = float(fps) if fps and float(fps) > 0 else 30.0
        # Start with a single deterministic full-length segment
        self.segments: List[TimelineSegment] = [
            TimelineSegment(
                clip_id="clip_0",
                source_id=self.source_id,
                source_start=0.0,
                source_end=self.source_duration,
                speed=1.0,
            )
        ]
        self.effects: List[ContentAwareEffect] = []
        self.applied_cuts: List[Dict[str, Any]] = []
        self.notifications: List[str] = []
        self.warnings: List[str] = []
        self._recalculate_timeline()

    @property
    def frame_duration(self) -> float:
        """Duration of a single video frame in seconds."""
        return 1.0 / self.fps if self.fps > 0 else 1.0 / 30.0

    def snap_to_frame(self, t: float) -> float:
        """Snaps a timestamp to the nearest video frame boundary based on timeline fps."""
        if not self.fps or self.fps <= 0:
            return round(float(t), 4)
        frame_dur = 1.0 / self.fps
        frame_idx = round(float(t) / frame_dur)
        return round(frame_idx * frame_dur, 4)

    def align_to_frames(self, fps: Optional[float] = None) -> "Timeline":
        """
        Aligns segment start and end timestamps to discrete video frame boundaries.
        Guarantees that each segment comprises an exact integer number of frames.
        """
        target_fps = float(fps) if fps and float(fps) > 0 else self.fps
        frame_dur = 1.0 / target_fps
        for seg in self.segments:
            seg.source_start = round(round(seg.source_start / frame_dur) * frame_dur, 4)
            seg.source_end = round(round(seg.source_end / frame_dur) * frame_dur, 4)
        self._recalculate_timeline()
        return self

    def _recalculate_timeline(self):
        """Recomputes timeline_start and timeline_end for all segments."""
        current_time = 0.0
        active_segments: List[TimelineSegment] = []
        for seg in self.segments:
            if seg.source_end > seg.source_start:
                seg.timeline_start = 0.0 if abs(current_time) < 1e-9 else round(current_time, 4)
                t_end = current_time + seg.timeline_duration
                seg.timeline_end = 0.0 if abs(t_end) < 1e-9 else round(t_end, 4)
                current_time = seg.timeline_end
                active_segments.append(seg)
        self.segments = active_segments

    @property
    def total_duration(self) -> float:
        if not self.segments:
            return 0.0
        return self.segments[-1].timeline_end

    @property
    def source_effects(self) -> List[ContentAwareEffect]:
        return self.effects

    @source_effects.setter
    def source_effects(self, val: List[ContentAwareEffect]):
        self.effects = val

    def add_effect(
        self,
        effect_type: str,
        source_start: float,
        source_end: float,
        parameters: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None,
        effect_id: Optional[str] = None
    ) -> ContentAwareEffect:
        """Anchors a new content-aware effect to the source media with deterministic ID."""
        s_start = max(0.0, min(self.source_duration, float(source_start)))
        s_end = max(s_start, min(self.source_duration, float(source_end)))

        if not effect_id:
            idx = len(self.effects)
            candidate = f"eff_{idx}"
            existing_ids = {e.effect_id for e in self.effects}
            while candidate in existing_ids:
                idx += 1
                candidate = f"eff_{idx}"
            effect_id = candidate

        eff = ContentAwareEffect(
            effect_id=str(effect_id),
            type=str(effect_type),
            source_id=self.source_id,
            source_start=s_start,
            source_end=s_end,
            parameters=dict(parameters or {}),
            label=label or f"{effect_type.replace('_', ' ').title()} ({s_start:.2f}s - {s_end:.2f}s)"
        )
        self.effects.append(eff)
        return eff

    def remove_effect(self, effect_id: str) -> bool:
        """Removes an anchored effect by effect_id."""
        initial_len = len(self.effects)
        self.effects = [e for e in self.effects if e.effect_id != effect_id]
        return len(self.effects) < initial_len

    def get_effect(self, effect_id: str) -> Optional[ContentAwareEffect]:
        """Returns the source effect matching effect_id."""
        return next((e for e in self.effects if e.effect_id == effect_id), None)

    def _sync_captions_after_cut(self, cut_start: float, cut_end: float):
        """
        Feature 9: Caption-Aware Timeline Editing.
        - Keeps captions synchronized with their spoken words.
        - If all words associated with a caption are removed, removes the caption and records notification.
        - For partial cuts: retains only surviving words, updating text and timing.
        """
        cs = max(0.0, min(self.source_duration, float(cut_start)))
        ce = max(cs, min(self.source_duration, float(cut_end)))
        if cs >= ce:
            return

        retained_effects: List[ContentAwareEffect] = []
        for eff in self.effects:
            if eff.type != "caption":
                retained_effects.append(eff)
                continue

            # Check overlap with cut
            overlap_s = max(eff.source_start, cs)
            overlap_e = min(eff.source_end, ce)
            if overlap_e <= overlap_s + 1e-5:
                # No overlap with cut
                retained_effects.append(eff)
                continue

            words = eff.parameters.get("words")
            if words and isinstance(words, list) and len(words) > 0:
                # Check surviving words within remaining segments
                surviving_words = []
                for w in words:
                    w_st = float(w.get("start", 0.0))
                    w_et = float(w.get("end", 0.0))
                    # Word survives if it falls within any retained segment
                    word_in_retained_segment = any(
                        seg.source_start <= w_st + 1e-4 and w_et <= seg.source_end + 1e-4
                        for seg in self.segments
                    )
                    if word_in_retained_segment:
                        surviving_words.append(w)

                if len(surviving_words) == 0:
                    # All words cut! Remove caption and notify user
                    msg = f"Caption '{eff.label}' removed: all associated spoken words were cut."
                    if msg not in self.notifications:
                        self.notifications.append(msg)
                elif len(surviving_words) < len(words):
                    # Partial cut: retain only surviving words, update text and timing
                    old_text = eff.parameters.get("text", eff.label)
                    new_text = " ".join(str(w.get("word", "")).strip() for w in surviving_words)
                    new_start = min(float(w.get("start", 0.0)) for w in surviving_words)
                    new_end = max(float(w.get("end", 0.0)) for w in surviving_words)
                    eff.source_start = round(new_start, 4)
                    eff.source_end = round(new_end, 4)
                    eff.parameters["text"] = new_text
                    eff.parameters["words"] = surviving_words
                    eff.label = new_text
                    msg = f"Caption '{old_text}' updated for surviving words: '{new_text}' [{eff.source_start:.2f}s - {eff.source_end:.2f}s]."
                    if msg not in self.notifications:
                        self.notifications.append(msg)
                    retained_effects.append(eff)
                else:
                    retained_effects.append(eff)
            else:
                # Caption without word-level timestamps:
                # If cut completely covers caption interval:
                if cs <= eff.source_start + 1e-4 and eff.source_end <= ce + 1e-4:
                    msg = f"Caption '{eff.label}' removed: entire caption interval was cut."
                    if msg not in self.notifications:
                        self.notifications.append(msg)
                else:
                    retained_effects.append(eff)

        self.effects = retained_effects

    def apply_trim_start(self, seconds: float):
        """Trims seconds from the beginning of the timeline in source time."""
        if seconds <= 0:
            return
        cut_point = min(self.source_duration, float(seconds))
        new_segments: List[TimelineSegment] = []
        for seg in self.segments:
            if seg.source_end <= cut_point + 1e-6:
                # Fully trimmed out
                continue
            elif seg.source_start < cut_point < seg.source_end:
                # Partially trimmed
                seg.source_start = cut_point
                new_segments.append(seg)
            else:
                new_segments.append(seg)
        self.segments = new_segments
        self._sync_captions_after_cut(0.0, cut_point)
        self._recalculate_timeline()

    def apply_trim_end(self, seconds: float):
        """Trims seconds from the end of the video in source time."""
        if seconds <= 0:
            return
        cut_point = max(0.0, self.source_duration - float(seconds))
        new_segments: List[TimelineSegment] = []
        for seg in self.segments:
            if seg.source_start >= cut_point - 1e-6:
                # Fully trimmed out
                continue
            elif seg.source_start < cut_point < seg.source_end:
                # Partially trimmed
                seg.source_end = cut_point
                new_segments.append(seg)
            else:
                new_segments.append(seg)
        self.segments = new_segments
        self._sync_captions_after_cut(cut_point, self.source_duration)
        self._recalculate_timeline()

    def apply_time_slice(self, start_time: float, end_time: float):
        """Restricts timeline strictly to [start_time, end_time] in source time."""
        st = max(0.0, min(self.source_duration, float(start_time)))
        et = max(st, min(self.source_duration, float(end_time)))
        new_segments: List[TimelineSegment] = []
        for seg in self.segments:
            overlap_st = max(seg.source_start, st)
            overlap_et = min(seg.source_end, et)
            if overlap_st < overlap_et:
                seg.source_start = overlap_st
                seg.source_end = overlap_et
                new_segments.append(seg)
        self.segments = new_segments
        if st > 0:
            self._sync_captions_after_cut(0.0, st)
        if et < self.source_duration:
            self._sync_captions_after_cut(et, self.source_duration)
        self._recalculate_timeline()

    def apply_cut(self, cut_start: float, cut_end: float):
        """Excises an internal source range [cut_start, cut_end], splitting segments."""
        cs = max(0.0, min(self.source_duration, float(cut_start)))
        ce = max(cs, min(self.source_duration, float(cut_end)))
        if cs >= ce:
            return

        new_segments: List[TimelineSegment] = []
        for seg in self.segments:
            if seg.source_end <= cs + 1e-6 or seg.source_start >= ce - 1e-6:
                # No overlap with cut
                new_segments.append(seg)
            elif seg.source_start >= cs - 1e-6 and seg.source_end <= ce + 1e-6:
                # Entire segment excised
                continue
            elif seg.source_start < cs and seg.source_end > ce:
                # Cut punches a hole in the middle: split into two segments
                seg1 = TimelineSegment(
                    clip_id=f"{seg.clip_id}_a",
                    source_id=seg.source_id,
                    source_start=seg.source_start,
                    source_end=cs,
                    speed=seg.speed
                )
                seg2 = TimelineSegment(
                    clip_id=f"{seg.clip_id}_b",
                    source_id=seg.source_id,
                    source_start=ce,
                    source_end=seg.source_end,
                    speed=seg.speed
                )
                new_segments.extend([seg1, seg2])
            elif seg.source_start < cs:
                # Cut clips right portion of segment
                seg.source_end = cs
                new_segments.append(seg)
            elif seg.source_end > ce:
                # Cut clips left portion of segment
                seg.source_start = ce
                new_segments.append(seg)

        self.segments = new_segments
        self._sync_captions_after_cut(cs, ce)
        self._recalculate_timeline()

    def apply_speed_change(
        self,
        speed: float,
        source_start: Optional[float] = None,
        source_end: Optional[float] = None
    ):
        """
        Adjusts playback speed (e.g. 2.0x, 0.5x).
        If source_start/source_end are provided, changes speed only for that sub-range,
        splitting segments as necessary. If omitted, applies to all segments.
        """
        if speed <= 0.05 or speed > 10.0:
            raise ValueError(f"Invalid speed multiplier: {speed}")

        if source_start is None or source_end is None:
            for seg in self.segments:
                seg.speed = speed
        else:
            s_start = max(0.0, min(self.source_duration, float(source_start)))
            s_end = max(s_start, min(self.source_duration, float(source_end)))
            new_segments: List[TimelineSegment] = []
            for seg in self.segments:
                overlap_s = max(seg.source_start, s_start)
                overlap_e = min(seg.source_end, s_end)
                if overlap_s >= overlap_e:
                    new_segments.append(seg)
                else:
                    # Segment needs split
                    if seg.source_start < overlap_s:
                        new_segments.append(TimelineSegment(
                            clip_id=f"{seg.clip_id}_pre",
                            source_id=seg.source_id,
                            source_start=seg.source_start,
                            source_end=overlap_s,
                            speed=seg.speed
                        ))
                    new_segments.append(TimelineSegment(
                        clip_id=f"{seg.clip_id}_spd",
                        source_id=seg.source_id,
                        source_start=overlap_s,
                        source_end=overlap_e,
                        speed=speed
                    ))
                    if seg.source_end > overlap_e:
                        new_segments.append(TimelineSegment(
                            clip_id=f"{seg.clip_id}_post",
                            source_id=seg.source_id,
                            source_start=overlap_e,
                            source_end=seg.source_end,
                            speed=seg.speed
                        ))
            self.segments = new_segments

        self._recalculate_timeline()

    def set_segment_speed(self, segment_index: int, speed: float):
        """Sets the speed multiplier of a specific segment by 0-indexed position."""
        if not (0 <= segment_index < len(self.segments)):
            raise IndexError(f"Segment index {segment_index} out of bounds")
        if speed <= 0.05 or speed > 10.0:
            raise ValueError(f"Invalid speed multiplier: {speed}")
        self.segments[segment_index].speed = speed
        self._recalculate_timeline()

    def reorder_segments(self, new_order: List[int]):
        """
        Reorders segments according to 0-indexed indices list.
        e.g. [1, 0] swaps first and second segment.
        """
        if set(new_order) != set(range(len(self.segments))):
            raise ValueError(f"Invalid reorder permutation: {new_order} for {len(self.segments)} segments")
        self.segments = [self.segments[i] for i in new_order]
        self._recalculate_timeline()

    def move_segment(self, from_index: int, to_index: int):
        """Moves a segment from from_index to to_index."""
        if not (0 <= from_index < len(self.segments)):
            raise IndexError(f"from_index {from_index} out of bounds")
        if not (0 <= to_index < len(self.segments)):
            raise IndexError(f"to_index {to_index} out of bounds")
        seg = self.segments.pop(from_index)
        self.segments.insert(to_index, seg)
        self._recalculate_timeline()

    def split_segment_at(self, source_time: float) -> bool:
        """Splits any segment containing source_time into two segments."""
        st = float(source_time)
        new_segments: List[TimelineSegment] = []
        split_performed = False
        for seg in self.segments:
            if seg.source_start < st < seg.source_end:
                seg1 = TimelineSegment(
                    clip_id=f"{seg.clip_id}_s1",
                    source_id=seg.source_id,
                    source_start=seg.source_start,
                    source_end=st,
                    speed=seg.speed
                )
                seg2 = TimelineSegment(
                    clip_id=f"{seg.clip_id}_s2",
                    source_id=seg.source_id,
                    source_start=st,
                    source_end=seg.source_end,
                    speed=seg.speed
                )
                new_segments.extend([seg1, seg2])
                split_performed = True
            else:
                new_segments.append(seg)
        if split_performed:
            self.segments = new_segments
            self._recalculate_timeline()
        return split_performed

    def map_source_to_timeline(self, source_time: float) -> List[float]:
        """Maps a source timestamp to all corresponding timeline timestamps (if retained)."""
        results: List[float] = []
        for seg in self.segments:
            if seg.source_start <= source_time <= seg.source_end:
                offset = (source_time - seg.source_start) / seg.speed
                results.append(round(seg.timeline_start + offset, 4))
        return results

    def map_timeline_to_source(self, timeline_time: float) -> Optional[Tuple[str, float]]:
        """
        Maps a timeline position to (clip_id, source_time).
        Returns None if out of bounds.
        """
        t = float(timeline_time)
        for seg in self.segments:
            if seg.timeline_start <= t <= seg.timeline_end:
                offset = (t - seg.timeline_start) * seg.speed
                src_t = seg.source_start + offset
                return (seg.clip_id, round(src_t, 4))
        return None

    def is_diverged(self) -> bool:
        """
        Returns True if the active timeline has diverged from raw source media
        (e.g., has trims, cuts, speed changes, or clip reordering).
        """
        if len(self.segments) != 1:
            return True
        seg = self.segments[0]
        if abs(seg.source_start - 0.0) > 1e-4:
            return True
        if abs(seg.source_end - self.source_duration) > 1e-4:
            return True
        if abs(seg.speed - 1.0) > 1e-4:
            return True
        if abs(self.total_duration - self.source_duration) > 1e-4:
            return True
        return False

    def map_timeline_range_to_source(self, timeline_start: float, timeline_end: float) -> List[Tuple[float, float, str]]:
        """
        Maps a timeline interval [timeline_start, timeline_end] into its constituent
        source media intervals: [(src_start, src_end, clip_id), ...].
        Accurately accounts for playback speeds, cuts, trims, and segment reordering.
        """
        t_start = max(0.0, float(timeline_start))
        t_end = max(t_start, float(timeline_end))
        source_intervals: List[Tuple[float, float, str]] = []

        for seg in self.segments:
            overlap_t_start = max(seg.timeline_start, t_start)
            overlap_t_end = min(seg.timeline_end, t_end)
            if (overlap_t_end - overlap_t_start) > 1e-5:
                s_start = seg.source_start + (overlap_t_start - seg.timeline_start) * seg.speed
                s_end = seg.source_start + (overlap_t_end - seg.timeline_start) * seg.speed
                source_intervals.append((round(s_start, 4), round(s_end, 4), seg.clip_id))

        return source_intervals

    def map_source_range_to_timeline(self, source_start: float, source_end: float) -> List[Tuple[float, float, str]]:
        """
        Maps a source media interval [source_start, source_end] into all its active
        timeline intervals: [(tl_start, tl_end, clip_id), ...].
        """
        s_start = max(0.0, float(source_start))
        s_end = max(s_start, float(source_end))
        timeline_intervals: List[Tuple[float, float, str]] = []

        for seg in self.segments:
            overlap_s_start = max(seg.source_start, s_start)
            overlap_s_end = min(seg.source_end, s_end)
            if (overlap_s_end - overlap_s_start) > 1e-5:
                t_start = seg.timeline_start + (overlap_s_start - seg.source_start) / seg.speed
                t_end = seg.timeline_start + (overlap_s_end - seg.source_start) / seg.speed
                timeline_intervals.append((round(t_start, 4), round(t_end, 4), seg.clip_id))

        return timeline_intervals

    def apply_timeline_cut(self, timeline_start: float, timeline_end: float):
        """
        Cuts out a section defined in current timeline coordinates [timeline_start, timeline_end].
        Converts timeline coordinates to source coordinates and applies cuts.
        """
        source_intervals = self.map_timeline_range_to_source(timeline_start, timeline_end)
        # Apply cuts in reverse order to preserve earlier coordinates
        for s_start, s_end, _ in sorted(source_intervals, key=lambda x: x[0], reverse=True):
            self.apply_cut(s_start, s_end)

    def transform_effects(self) -> List[TransformedTimelineEffect]:
        """
        Deterministic Content-Aware Mapping Algorithm:
        Maps each source-anchored effect onto current timeline coordinates.
        Handles complete retention, speed scaling, cuts, boundary truncation,
        and multi-segment splitting according to the documented policy.
        """
        transformed: List[TransformedTimelineEffect] = []

        for eff in self.effects:
            matching_segments: List[Tuple[TimelineSegment, float, float]] = []
            for seg in self.segments:
                overlap_s = max(seg.source_start, eff.source_start)
                overlap_e = min(seg.source_end, eff.source_end)
                if (overlap_e - overlap_s) > 1e-5:
                    matching_segments.append((seg, overlap_s, overlap_e))

            if not matching_segments:
                # Content was excised completely by cut or trim
                transformed.append(TransformedTimelineEffect(
                    effect_id=eff.effect_id,
                    parent_effect_id=eff.effect_id,
                    type=eff.type,
                    source_id=eff.source_id,
                    source_start=eff.source_start,
                    source_end=eff.source_end,
                    segment_id="none",
                    timeline_start=-1.0,
                    timeline_end=-1.0,
                    duration=0.0,
                    speed=1.0,
                    status="dropped_content_removed",
                    parameters=dict(eff.parameters),
                    label=eff.label
                ))
                continue

            is_split = len(matching_segments) > 1

            for idx, (seg, o_start, o_end) in enumerate(matching_segments):
                # Calculate timeline coordinates
                tl_start = seg.timeline_start + (o_start - seg.source_start) / seg.speed
                raw_dur = max(0.0, (o_end - o_start) / seg.speed)
                dur = raw_dur
                tl_end = tl_start + dur

                eff_params = dict(eff.parameters)

                # Feature 9: Readability check for sped-up speech (approx 0.7s minimum)
                if eff.type == "caption" and seg.speed > 1.0 and raw_dur < 0.7:
                    target_dur = 0.7
                    clip_remaining = seg.timeline_end - tl_start
                    if clip_remaining >= target_dur - 1e-4:
                        # Safely extend within valid clip boundaries
                        dur = target_dur
                        tl_end = tl_start + dur
                        eff_params["readability_extended"] = True
                        eff_params["min_readable_applied"] = 0.7
                    else:
                        # Report conflict: cannot extend without exceeding clip boundary
                        eff_params["readability_conflict"] = True
                        conflict_msg = (
                            f"Caption readability conflict: Sped-up caption '{eff.label}' duration ({raw_dur:.2f}s at {seg.speed}x) "
                            f"is below 0.7s readability threshold and cannot be extended within clip boundary of {seg.timeline_duration:.2f}s."
                        )
                        if conflict_msg not in self.warnings:
                            self.warnings.append(conflict_msg)

                # Determine status
                if is_split:
                    status = "split"
                elif o_start > eff.source_start + 1e-4 or o_end < eff.source_end - 1e-4:
                    status = "clipped"
                else:
                    status = "active"

                sub_label = eff.label
                if is_split:
                    sub_label = f"{eff.label} [Part {idx + 1}/{len(matching_segments)}]"

                transformed.append(TransformedTimelineEffect(
                    effect_id=f"{eff.effect_id}_part{idx}" if is_split else eff.effect_id,
                    parent_effect_id=eff.effect_id,
                    type=eff.type,
                    source_id=eff.source_id,
                    source_start=round(o_start, 4),
                    source_end=round(o_end, 4),
                    segment_id=seg.clip_id,
                    timeline_start=round(tl_start, 4),
                    timeline_end=round(tl_end, 4),
                    duration=round(dur, 4),
                    speed=round(seg.speed, 4),
                    status=status,
                    parameters=eff_params,
                    label=sub_label
                ))

        return transformed

    @staticmethod
    def _normalize_num(val: Any) -> float:
        """Rounds numbers to 4 decimal places, avoiding -0.0."""
        try:
            f = float(val)
            if abs(f) < 1e-9:
                return 0.0
            return round(f, 4)
        except (ValueError, TypeError):
            return 0.0

    @classmethod
    def _normalize_dict(cls, d: Any) -> Any:
        """Recursively normalizes a dictionary or list for canonical serialization."""
        if isinstance(d, dict):
            normalized = {}
            for k in sorted(d.keys()):
                v = d[k]
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    normalized[k] = cls._normalize_num(v)
                elif isinstance(v, (dict, list)):
                    normalized[k] = cls._normalize_dict(v)
                elif v is None:
                    normalized[k] = None
                else:
                    normalized[k] = v
            return normalized
        elif isinstance(d, list):
            return [cls._normalize_dict(x) for x in d]
        elif isinstance(d, (int, float)) and not isinstance(d, bool):
            return cls._normalize_num(d)
        else:
            return d

    def to_canonical_dict(self) -> Dict[str, Any]:
        """
        Produces a canonical, strictly normalized dictionary representation of the timeline.
        Guarantees deterministic ordering, normalized timestamps, and consistent types.
        Does NOT include the recursive 'timeline_hash' field.
        """
        transformed = self.transform_effects()
        active_transformed = [t.to_dict() for t in transformed if t.status != "dropped_content_removed"]
        dropped_transformed = [t.to_dict() for t in transformed if t.status == "dropped_content_removed"]

        # Sort segments canonically by timeline_start, source_start, clip_id
        canon_segments = sorted(
            [s.to_dict() for s in self.segments],
            key=lambda s: (self._normalize_num(s["timeline_start"]), self._normalize_num(s["source_start"]), str(s.get("clip_id", "")))
        )

        # Sort source effects canonically
        canon_source_effects = sorted(
            [e.to_dict() for e in self.effects],
            key=lambda e: (
                self._normalize_num(e["source_start"]),
                self._normalize_num(e["source_end"]),
                str(e.get("type", "")),
                str(e.get("label") or ""),
                str(e.get("effect_id", ""))
            )
        )

        # Sort active transformed effects canonically
        canon_transformed = sorted(
            active_transformed,
            key=lambda t: (
                self._normalize_num(t["timeline_start"]),
                self._normalize_num(t["timeline_end"]),
                str(t.get("type", "")),
                str(t.get("segment_id", "")),
                str(t.get("effect_id", ""))
            )
        )

        # Sort dropped transformed effects canonically
        canon_dropped = sorted(
            dropped_transformed,
            key=lambda t: (
                self._normalize_num(t["source_start"]),
                self._normalize_num(t["source_end"]),
                str(t.get("type", "")),
                str(t.get("effect_id", ""))
            )
        )

        raw_canonical = {
            "source_id": str(self.source_id).strip(),
            "source_duration": self._normalize_num(self.source_duration),
            "timeline_duration": self._normalize_num(self.total_duration),
            "fps": self._normalize_num(self.fps),
            "segment_count": len(canon_segments),
            "segments": canon_segments,
            "source_effects": canon_source_effects,
            "transformed_effects": canon_transformed,
            "dropped_effects": canon_dropped,
            "applied_cuts": self._normalize_dict(self.applied_cuts),
            "notifications": sorted(list(set(self.notifications))),
            "warnings": sorted(list(set(self.warnings))),
            "summary": {
                "active_effects_count": len(canon_transformed),
                "dropped_effects_count": len(canon_dropped),
                "notifications_count": len(self.notifications),
                "warnings_count": len(self.warnings),
                "is_reordered": any(i > 0 and self.segments[i].source_start < self.segments[i-1].source_start for i in range(len(self.segments))),
                "has_speed_change": any(abs(s.speed - 1.0) > 1e-4 for s in self.segments),
                "has_cuts": len(self.segments) > 1 or (len(self.segments) == 1 and self.segments[0].source_duration < self.source_duration - 1e-4),
            }
        }

        return self._normalize_dict(raw_canonical)

    def to_canonical_json(self) -> str:
        """
        Serializes the canonical dictionary to an RFC 8785 compliant canonical JSON string.
        Keys are sorted alphabetically, whitespace is compact (separators=(',', ':')), and ASCII-encoded.
        """
        canon_dict = self.to_canonical_dict()
        return json.dumps(canon_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

    @property
    def timeline_hash(self) -> str:
        """
        Deterministic SHA-256 cryptographic hash of the canonical timeline JSON.
        Guarantees that identical inputs and edit operations always produce identical hashes.
        """
        return hashlib.sha256(self.to_canonical_json().encode('utf-8')).hexdigest()

    @property
    def canonical_json(self) -> str:
        return self.to_canonical_json()

    def get_timeline_hash(self) -> str:
        return self.timeline_hash

    def get_canonical_json(self) -> str:
        return self.to_canonical_json()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes timeline, segments, and content-aware effects for API / Receipts.
        Includes the deterministic timeline_hash.
        """
        canon = self.to_canonical_dict()
        canon["timeline_hash"] = self.timeline_hash
        return canon

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Timeline":
        """Reconstructs Timeline from dictionary representation."""
        source_dur = float(data.get("source_duration", 0.0))
        source_id = str(data.get("source_id", "src_original"))
        fps = float(data.get("fps", 30.0))
        tl = cls(source_duration=source_dur, source_id=source_id, fps=fps)

        if "segments" in data and data["segments"]:
            tl.segments = [TimelineSegment.from_dict(s) for s in data["segments"]]
            tl._recalculate_timeline()

        if "source_effects" in data and data["source_effects"]:
            tl.effects = [ContentAwareEffect.from_dict(e) for e in data["source_effects"]]

        if "applied_cuts" in data and isinstance(data["applied_cuts"], list):
            tl.applied_cuts = list(data["applied_cuts"])

        if "notifications" in data and isinstance(data["notifications"], list):
            tl.notifications = list(data["notifications"])

        if "warnings" in data and isinstance(data["warnings"], list):
            tl.warnings = list(data["warnings"])

        return tl
