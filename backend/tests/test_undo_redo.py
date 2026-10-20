import json
import pytest
from app.services.hash_utils import calculate_file_sha256
from app.schemas.job import InstructionStatus

def test_initial_history_state(client):
    """
    Verifies that a newly created job initializes with an authoritative initial state (state 0),
    with can_undo=False and can_redo=False.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]

    hist_res = client.get(f"/api/jobs/{job_id}/history")
    assert hist_res.status_code == 200
    hist = hist_res.json()

    assert hist["job_id"] == job_id
    assert hist["current_index"] == 0
    assert hist["history_length"] >= 1
    assert hist["can_undo"] is False
    assert hist["can_redo"] is False
    assert hist["current_state"] is not None
    assert hist["current_state"]["state_id"] == "state_0"
    assert "timeline" in hist["current_state"]
    assert "timeline_hash" in hist["current_state"]


def test_multiple_edits_history_stack(client):
    """
    Applies multiple distinct editing operations and verifies that each successfully
    pushes an immutable state snapshot with matching timeline, plan, and hash.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Edit 1: Trim start
    op1_res = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Trim start 2 seconds"}
    )
    assert op1_res.status_code == 200
    assert op1_res.json()["status"] == InstructionStatus.APPLIED.value

    # Check history after edit 1
    hist1 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist1["current_index"] == 1
    assert hist1["history_length"] == 2
    assert hist1["can_undo"] is True
    assert hist1["can_redo"] is False

    # Edit 2: Speed change
    op2_res = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Speed up by 2x"}
    )
    assert op2_res.status_code == 200
    assert op2_res.json()["status"] == InstructionStatus.APPLIED.value

    # Check history after edit 2
    hist2 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist2["current_index"] == 2
    assert hist2["history_length"] == 3
    assert hist2["can_undo"] is True
    assert hist2["can_redo"] is False

    # Edit 3: Cut interval
    op3_res = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Cut from 3 to 5 seconds"}
    )
    assert op3_res.status_code == 200
    assert op3_res.json()["status"] == InstructionStatus.APPLIED.value

    # Check history after edit 3
    hist3 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist3["current_index"] == 3
    assert hist3["history_length"] == 4
    assert hist3["can_undo"] is True
    assert hist3["can_redo"] is False


def test_repeated_undo_and_boundary_guards(client):
    """
    Performs multiple undos, verifying canonical timeline and hash restoration at each step,
    and checks boundary behavior when attempting to undo past index 0 (safe no-op).
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Record state 0 hash
    hist0 = client.get(f"/api/jobs/{job_id}/history").json()
    hash_state_0 = hist0["current_state"]["timeline_hash"]

    # Apply Edit 1: Trim start past the 3.0s boundary
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Trim start 4 seconds"})
    hist1 = client.get(f"/api/jobs/{job_id}/history").json()
    hash_state_1 = hist1["current_state"]["timeline_hash"]
    assert hash_state_1 != hash_state_0

    # Apply Edit 2
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Speed up by 1.5x"})
    hist2 = client.get(f"/api/jobs/{job_id}/history").json()
    hash_state_2 = hist2["current_state"]["timeline_hash"]
    assert hash_state_2 != hash_state_1

    # Undo 1: From State 2 back to State 1
    undo1_res = client.post(f"/api/jobs/{job_id}/undo")
    assert undo1_res.status_code == 200
    u1 = undo1_res.json()
    assert u1["status"] == "undone"
    assert u1["current_index"] == 1
    assert u1["timeline_hash"] == hash_state_1
    assert u1["can_undo"] is True
    assert u1["can_redo"] is True

    # Undo 2: From State 1 back to State 0
    undo2_res = client.post(f"/api/jobs/{job_id}/undo")
    assert undo2_res.status_code == 200
    u2 = undo2_res.json()
    assert u2["status"] == "undone"
    assert u2["current_index"] == 0
    assert u2["timeline_hash"] == hash_state_0
    assert u2["can_undo"] is False
    assert u2["can_redo"] is True

    # Undo 3 (Boundary Guard): Already at State 0
    undo3_res = client.post(f"/api/jobs/{job_id}/undo")
    assert undo3_res.status_code == 200
    u3 = undo3_res.json()
    assert u3["status"] == "noop"
    assert u3["current_index"] == 0
    assert u3["timeline_hash"] == hash_state_0
    assert u3["can_undo"] is False
    assert u3["can_redo"] is True
    assert "earliest" in u3["message"].lower()


def test_repeated_redo_and_boundary_guards(client):
    """
    Performs multiple redos, verifying state reapplying, and checks boundary behavior
    when attempting to redo past the latest state (safe no-op).
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Two edits
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Trim start 2 seconds"})
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Speed up by 2x"})

    hist_full = client.get(f"/api/jobs/{job_id}/history").json()
    hash_step_1 = hist_full["states"][1]["timeline_hash"]
    hash_step_2 = hist_full["states"][2]["timeline_hash"]

    # Undo back to state 0
    client.post(f"/api/jobs/{job_id}/undo")
    client.post(f"/api/jobs/{job_id}/undo")

    # Redo 1: to state 1
    redo1_res = client.post(f"/api/jobs/{job_id}/redo")
    assert redo1_res.status_code == 200
    r1 = redo1_res.json()
    assert r1["status"] == "redone"
    assert r1["current_index"] == 1
    assert r1["timeline_hash"] == hash_step_1
    assert r1["can_undo"] is True
    assert r1["can_redo"] is True

    # Redo 2: to state 2
    redo2_res = client.post(f"/api/jobs/{job_id}/redo")
    assert redo2_res.status_code == 200
    r2 = redo2_res.json()
    assert r2["status"] == "redone"
    assert r2["current_index"] == 2
    assert r2["timeline_hash"] == hash_step_2
    assert r2["can_undo"] is True
    assert r2["can_redo"] is False

    # Redo 3 (Boundary Guard): Already at latest state
    redo3_res = client.post(f"/api/jobs/{job_id}/redo")
    assert redo3_res.status_code == 200
    r3 = redo3_res.json()
    assert r3["status"] == "noop"
    assert r3["current_index"] == 2
    assert r3["can_redo"] is False
    assert "latest" in r3["message"].lower()


def test_new_edit_after_undo_clears_redo_stack(client):
    """
    CRITICAL REQUIREMENT: A new edit after undo clears the redo stack (branch pruning).
    - Initial: [State 0]
    - Edit 1: [State 0, State 1]
    - Edit 2: [State 0, State 1, State 2]
    - Undo: Back to State 1. (Redo stack contains State 2)
    - Edit 3 (New): [State 0, State 1, State 2_new]
    - Verify: Redo stack is EMPTY, can_redo is False, calling redo is a no-op.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # 1. Edit 1
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Trim start 1 second"})
    # 2. Edit 2
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Speed up by 2x"})

    hist_before = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist_before["history_length"] == 3
    assert hist_before["current_index"] == 2
    old_state_2_desc = hist_before["states"][2]["description"]

    # 3. Undo to state 1
    undo_res = client.post(f"/api/jobs/{job_id}/undo")
    assert undo_res.status_code == 200
    assert undo_res.json()["current_index"] == 1
    assert undo_res.json()["can_redo"] is True

    # 4. New Edit: Cut 2 to 4 seconds (branch branch diversion)
    new_edit_res = client.post(
        f"/api/jobs/{job_id}/instruction",
        json={"instruction": "Cut from 2 to 4 seconds"}
    )
    assert new_edit_res.status_code == 200
    assert new_edit_res.json()["status"] == InstructionStatus.APPLIED.value

    # 5. Verify Redo stack is cleared
    hist_after = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist_after["history_length"] == 3  # state 0, state 1, state 2_new
    assert hist_after["current_index"] == 2
    assert hist_after["can_undo"] is True
    assert hist_after["can_redo"] is False  # Redo MUST be cleared!

    # Verify that the new state 2 has the new edit description, NOT the old speed up
    assert hist_after["states"][2]["description"] != old_state_2_desc
    assert "cut" in hist_after["states"][2]["description"].lower()

    # Attempting to redo now must return noop
    redo_res = client.post(f"/api/jobs/{job_id}/redo")
    assert redo_res.status_code == 200
    assert redo_res.json()["status"] == "noop"
    assert redo_res.json()["can_redo"] is False


def test_timeline_transform_and_effects_undo_redo(client):
    """
    Verifies that direct timeline transformations and effects also participate
    reliably in the undo/redo history stack.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Direct timeline cut
    cut_res = client.post(
        f"/api/jobs/{job_id}/timeline/transform",
        json={"action": "cut", "cut_start": 1.0, "cut_end": 3.0}
    )
    assert cut_res.status_code == 200

    hist1 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist1["current_index"] == 1
    assert "cut" in hist1["current_state"]["description"].lower()

    # Direct effect addition
    eff_res = client.post(
        f"/api/jobs/{job_id}/timeline/effects",
        json={
            "type": "caption",
            "source_start": 3.5,
            "source_end": 5.5,
            "parameters": {"text": "Hello World"}
        }
    )
    assert eff_res.status_code == 200

    hist2 = client.get(f"/api/jobs/{job_id}/history").json()
    assert hist2["current_index"] == 2
    assert "caption" in hist2["current_state"]["description"].lower()

    # Undo effect
    u_eff = client.post(f"/api/jobs/{job_id}/undo").json()
    assert u_eff["status"] == "undone"
    assert u_eff["current_index"] == 1
    assert "cut" in u_eff["description"].lower()

    # Undo cut
    u_cut = client.post(f"/api/jobs/{job_id}/undo").json()
    assert u_cut["status"] == "undone"
    assert u_cut["current_index"] == 0

    # Redo cut
    r_cut = client.post(f"/api/jobs/{job_id}/redo").json()
    assert r_cut["status"] == "redone"
    assert r_cut["current_index"] == 1

    # Redo effect
    r_eff = client.post(f"/api/jobs/{job_id}/redo").json()
    assert r_eff["status"] == "redone"
    assert r_eff["current_index"] == 2


def test_non_destructive_media_immutability_throughout_undo_redo(client):
    """
    Verifies that through multiple edits, undos, redos, and branch prunings,
    the original media file on disk is NEVER modified and its SHA-256 hash remains unchanged.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]

    # Verify initial source file integrity
    verify_res = client.get(f"/api/jobs/{job_id}/verify-integrity")
    assert verify_res.status_code == 200
    original_hash = verify_res.json()["original_hash"]

    # Series of edits, undos, and redos
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Trim start 1 second"})
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Speed up by 2x"})
    client.post(f"/api/jobs/{job_id}/undo")
    client.post(f"/api/jobs/{job_id}/instruction", json={"instruction": "Cut from 2 to 4 seconds"})
    client.post(f"/api/jobs/{job_id}/undo")
    client.post(f"/api/jobs/{job_id}/redo")

    # Re-verify integrity
    final_verify = client.get(f"/api/jobs/{job_id}/verify-integrity")
    assert final_verify.status_code == 200
    assert final_verify.json()["verified"] is True
    assert final_verify.json()["current_hash"] == original_hash


def test_prevent_duplicate_states(client):
    """
    Verifies that calling push_state with identical timeline hash and operations
    does not create duplicate states in the history stack.
    """
    from app.database.session import SessionLocal
    from app.database.models import JobModel
    from app.services.undo_redo_manager import UndoRedoManager

    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    db = SessionLocal()
    job = db.query(JobModel).filter(JobModel.id == job_id).first()

    # Initial history length
    h_before = UndoRedoManager.get_history(job)
    init_len = h_before["history_length"]

    # Push state with the same current plan
    dup_res = UndoRedoManager.push_state(job, job.edit_plan_json, "Duplicate Push")
    assert dup_res["status"] == "duplicate_ignored"

    # Verify history length did not increase
    h_after = UndoRedoManager.get_history(job)
    assert h_after["history_length"] == init_len
    db.close()


def test_backward_compatibility_with_legacy_history_endpoint(client):
    """
    Verifies that jobs with legacy edit_history format (list of plan dicts)
    can still be read, undone, redone, and queried via GET /api/jobs/{job_id}/history.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    # Save legacy list format
    plan_a = {"prompt": "Step A", "operations": [{"type": "trim_start", "seconds": 1.0}]}
    plan_b = {"prompt": "Step B", "operations": [{"type": "speed", "speed": 1.5}]}
    legacy_list = [plan_a, plan_b]

    save_res = client.post(
        f"/api/jobs/{job_id}/history",
        json={"history": legacy_list, "current_plan": plan_b}
    )
    assert save_res.status_code == 200

    # GET /history should transparently parse and normalize it
    hist_res = client.get(f"/api/jobs/{job_id}/history")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert hist["history_length"] == 2
    assert hist["current_index"] == 1
    assert hist["can_undo"] is True

    # Undo should restore Step A
    undo_res = client.post(f"/api/jobs/{job_id}/undo")
    assert undo_res.status_code == 200
    assert undo_res.json()["status"] == "undone"
    assert undo_res.json()["current_index"] == 0

