"""
ClipPilot AI - Undo/Redo & Edit-State Management Service (Feature 6)
=====================================================================
Provides reliable, non-destructive undo and redo capabilities for video editing jobs.

Key Guarantees:
1. Undo restores the previous edit state; redo reapplies it.
2. A new edit after undo clears the redo branch (branch pruning).
3. Canonical timeline and edit plan consistency with deterministic timeline_hash.
4. Prevents duplicate states or invalid negative/out-of-bounds history indices.
5. Absolute non-destructive preservation: original source media is never modified.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Union

from app.database.models import JobModel
from app.schemas.edit_plan import EditPlan
from app.services.timeline_model import Timeline
from app.schemas.job import MediaMetadata


class UndoRedoManager:
    """
    Manages the edit decision list (EDL) / undo-redo history stack for a job.
    """

    @classmethod
    def _create_state_snapshot(
        cls,
        plan_dict: Dict[str, Any],
        description: str,
        state_id: str,
        source_duration: float = 10.0,
        fps: float = 30.0
    ) -> Dict[str, Any]:
        """Creates a standardized, normalized snapshot of an edit state."""
        # Ensure timeline exists and has a deterministic timeline_hash
        tl_dict = plan_dict.get("timeline")
        if tl_dict and isinstance(tl_dict, dict):
            tl = Timeline.from_dict(tl_dict)
        else:
            tl = Timeline(source_duration=source_duration, source_id="src_original", fps=fps)

        tl_canonical = tl.to_dict()
        tl_hash = tl.timeline_hash
        plan_dict["timeline"] = tl_canonical
        plan_dict["timeline_hash"] = tl_hash

        ops = list(plan_dict.get("operations", []))
        prompt_str = str(plan_dict.get("prompt", "") or description)

        return {
            "state_id": state_id,
            "description": description or f"State {state_id}",
            "prompt": prompt_str,
            "plan": plan_dict,
            "timeline": tl_canonical,
            "timeline_hash": tl_hash,
            "operations": ops,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def _parse_history_data(cls, job: JobModel) -> Tuple[List[Dict[str, Any]], int]:
        """
        Parses job.edit_history_json into (states_list, current_index).
        Gracefully handles legacy list-only formats and uninitialized jobs.
        """
        if not job.edit_history_json:
            # Initialize with base state from current job plan
            dur = 10.0
            fps = 30.0
            if job.input_metadata_json:
                try:
                    meta = json.loads(job.input_metadata_json)
                    dur = float(meta.get("duration", 10.0))
                    fps = float(meta.get("fps", 30.0))
                except Exception:
                    pass

            plan_dict = {}
            if job.edit_plan_json:
                try:
                    plan_dict = json.loads(job.edit_plan_json)
                except Exception:
                    plan_dict = {}

            base_state = cls._create_state_snapshot(
                plan_dict=plan_dict,
                description="Initial Video Import",
                state_id="state_0",
                source_duration=dur,
                fps=fps
            )
            return [base_state], 0

        try:
            raw = json.loads(job.edit_history_json)
            if isinstance(raw, dict) and "states" in raw:
                states = raw["states"]
                curr_idx = int(raw.get("current_index", len(states) - 1))
                curr_idx = max(0, min(curr_idx, len(states) - 1))
                return states, curr_idx
            elif isinstance(raw, list):
                # Legacy list format: normalize each entry
                dur = 10.0
                fps = 30.0
                if job.input_metadata_json:
                    try:
                        meta = json.loads(job.input_metadata_json)
                        dur = float(meta.get("duration", 10.0))
                        fps = float(meta.get("fps", 30.0))
                    except Exception:
                        pass

                normalized_states = []
                for i, item in enumerate(raw):
                    if isinstance(item, dict):
                        if "plan" in item and "state_id" in item:
                            normalized_states.append(item)
                        else:
                            st = cls._create_state_snapshot(
                                plan_dict=dict(item),
                                description=f"Edit Step {i}",
                                state_id=f"state_{i}",
                                source_duration=dur,
                                fps=fps
                            )
                            normalized_states.append(st)

                if not normalized_states:
                    base_state = cls._create_state_snapshot(
                        plan_dict={},
                        description="Initial Video Import",
                        state_id="state_0",
                        source_duration=dur,
                        fps=fps
                    )
                    normalized_states = [base_state]

                return normalized_states, len(normalized_states) - 1
        except Exception:
            pass

        # Fallback
        base_state = cls._create_state_snapshot(
            plan_dict={},
            description="Initial Video Import",
            state_id="state_0"
        )
        return [base_state], 0

    @classmethod
    def get_history(cls, job: JobModel) -> Dict[str, Any]:
        """Returns the full edit history stack, current index, and navigation flags."""
        states, current_idx = cls._parse_history_data(job)
        current_state = states[current_idx] if 0 <= current_idx < len(states) else None

        return {
            "job_id": job.id,
            "current_index": current_idx,
            "history_length": len(states),
            "can_undo": current_idx > 0,
            "can_redo": current_idx < (len(states) - 1),
            "current_state": current_state,
            "states": states
        }

    @classmethod
    def push_state(
        cls,
        job: JobModel,
        plan_or_dict: Union[EditPlan, Dict[str, Any], str],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Pushes a new edit state to the history stack.
        Ensures:
        1. A new edit after undo clears the redo stack (branch pruning).
        2. Duplicate identical states are ignored (preventing clutter).
        3. Persists updated edit_history_json and edit_plan_json.
        """
        if isinstance(plan_or_dict, str):
            try:
                plan_dict = json.loads(plan_or_dict)
            except Exception:
                plan_dict = {}
        elif isinstance(plan_or_dict, EditPlan):
            plan_dict = plan_or_dict.model_dump()
        else:
            plan_dict = dict(plan_or_dict)
        states, current_idx = cls._parse_history_data(job)

        dur = 10.0
        fps = 30.0
        if job.input_metadata_json:
            try:
                meta = json.loads(job.input_metadata_json)
                dur = float(meta.get("duration", 10.0))
                fps = float(meta.get("fps", 30.0))
            except Exception:
                pass

        new_snapshot = cls._create_state_snapshot(
            plan_dict=plan_dict,
            description=description or plan_dict.get("prompt", "New Edit"),
            state_id=f"state_{len(states)}",
            source_duration=dur,
            fps=fps
        )

        # Duplicate check: don't push if identical to current active state
        if states and 0 <= current_idx < len(states):
            curr_state = states[current_idx]
            if (
                curr_state.get("timeline_hash") == new_snapshot["timeline_hash"]
                and curr_state.get("operations") == new_snapshot["operations"]
            ):
                return {
                    "status": "duplicate_ignored",
                    "job_id": job.id,
                    "current_index": current_idx,
                    "history_length": len(states),
                    "can_undo": current_idx > 0,
                    "can_redo": current_idx < (len(states) - 1),
                    "current_plan": curr_state["plan"],
                    "timeline": curr_state["timeline"],
                    "timeline_hash": curr_state["timeline_hash"],
                    "description": curr_state["description"]
                }

        # Branch pruning: discard any forward redo history if we were in the middle of the stack
        pruned_states = states[:current_idx + 1]

        # Re-number state_id deterministically
        new_snapshot["state_id"] = f"state_{len(pruned_states)}"
        pruned_states.append(new_snapshot)
        new_idx = len(pruned_states) - 1

        # Persist to job model
        job.edit_history_json = json.dumps({"states": pruned_states, "current_index": new_idx})
        job.edit_plan_json = json.dumps(new_snapshot["plan"])
        if new_snapshot.get("prompt"):
            job.prompt = new_snapshot["prompt"]

        return {
            "status": "applied",
            "job_id": job.id,
            "current_index": new_idx,
            "history_length": len(pruned_states),
            "can_undo": new_idx > 0,
            "can_redo": False,  # Redo stack is explicitly cleared after a new edit
            "current_plan": new_snapshot["plan"],
            "timeline": new_snapshot["timeline"],
            "timeline_hash": new_snapshot["timeline_hash"],
            "description": new_snapshot["description"]
        }

    @classmethod
    def undo(cls, job: JobModel) -> Dict[str, Any]:
        """
        Restores the previous edit state.
        If already at the initial state (index 0), performs a safe no-op.
        """
        states, current_idx = cls._parse_history_data(job)

        if current_idx <= 0:
            active_state = states[0] if states else {}
            return {
                "status": "noop",
                "message": "Already at the earliest edit state. Cannot undo further.",
                "job_id": job.id,
                "current_index": 0,
                "history_length": len(states),
                "can_undo": False,
                "can_redo": len(states) > 1,
                "current_plan": active_state.get("plan"),
                "timeline": active_state.get("timeline"),
                "timeline_hash": active_state.get("timeline_hash"),
                "description": active_state.get("description", "Initial State")
            }

        new_idx = current_idx - 1
        restored_state = states[new_idx]

        # Persist updated index and restored plan
        job.edit_history_json = json.dumps({"states": states, "current_index": new_idx})
        job.edit_plan_json = json.dumps(restored_state["plan"])
        if restored_state.get("prompt"):
            job.prompt = restored_state["prompt"]

        return {
            "status": "undone",
            "message": f"Restored previous state: {restored_state.get('description', '')}",
            "job_id": job.id,
            "current_index": new_idx,
            "history_length": len(states),
            "can_undo": new_idx > 0,
            "can_redo": True,
            "current_plan": restored_state["plan"],
            "timeline": restored_state["timeline"],
            "timeline_hash": restored_state["timeline_hash"],
            "description": restored_state.get("description", "")
        }

    @classmethod
    def redo(cls, job: JobModel) -> Dict[str, Any]:
        """
        Reapplies the next edit state from the redo stack.
        If already at the latest state, performs a safe no-op.
        """
        states, current_idx = cls._parse_history_data(job)

        if current_idx >= len(states) - 1:
            active_state = states[current_idx] if 0 <= current_idx < len(states) else {}
            return {
                "status": "noop",
                "message": "Already at the latest edit state. Cannot redo further.",
                "job_id": job.id,
                "current_index": current_idx,
                "history_length": len(states),
                "can_undo": current_idx > 0,
                "can_redo": False,
                "current_plan": active_state.get("plan"),
                "timeline": active_state.get("timeline"),
                "timeline_hash": active_state.get("timeline_hash"),
                "description": active_state.get("description", "Latest State")
            }

        new_idx = current_idx + 1
        restored_state = states[new_idx]

        # Persist updated index and reapplied plan
        job.edit_history_json = json.dumps({"states": states, "current_index": new_idx})
        job.edit_plan_json = json.dumps(restored_state["plan"])
        if restored_state.get("prompt"):
            job.prompt = restored_state["prompt"]

        return {
            "status": "redone",
            "message": f"Reapplied edit state: {restored_state.get('description', '')}",
            "job_id": job.id,
            "current_index": new_idx,
            "history_length": len(states),
            "can_undo": True,
            "can_redo": new_idx < len(states) - 1,
            "current_plan": restored_state["plan"],
            "timeline": restored_state["timeline"],
            "timeline_hash": restored_state["timeline_hash"],
            "description": restored_state.get("description", "")
        }
