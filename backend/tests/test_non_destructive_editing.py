import time
import hashlib
from pathlib import Path
import pytest
from app.core.config import settings
from app.services.hash_utils import calculate_file_sha256, verify_file_integrity

def get_auth_headers(client):
    email = f"test_user_{int(time.time() * 1000)}@example.com"
    res = client.post("/api/auth/signup", json={
        "full_name": "Test User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res.status_code == 201
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_import_records_sha256_hash(client):
    """Requirement: Calculate and store SHA-256 immediately after import/demo creation."""
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]

    assert job["original_file_hash"] is not None
    assert len(job["original_file_hash"]) == 64  # Valid SHA-256 hex digest
    assert job["original_file_size"] is not None
    assert job["original_file_size"] > 0

    # Verify against actual disk file
    upload_file = settings.UPLOAD_DIR / job_id / "original_sample_talking_head.mp4"
    assert upload_file.exists(), f"Source file should exist at {upload_file}"

    disk_hash = calculate_file_sha256(upload_file)
    assert job["original_file_hash"] == disk_hash, "Stored hash must match original file on disk"

def test_non_destructive_edits_and_rendering(client):
    """
    Requirements:
    - Apply at least three different edits.
    - Render the edited video.
    - Verify that original hash remains identical.
    - Verify that rendered output is a separate file.
    """
    # 1. Create Job
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]
    initial_hash = job["original_file_hash"]

    # 2. Apply at least three different edits on timeline/EDL
    # Edit 1: trim_start
    # Edit 2: aspect_ratio 9:16
    # Edit 3: audio_volume +3dB
    three_edits_plan = {
        "prompt": "Trim start 1s, convert to 9:16 vertical, boost audio +3dB",
        "operations": [
            {
                "type": "trim_start",
                "seconds": 1.0,
                "description": "Trim first 1.0s of video"
            },
            {
                "type": "aspect_ratio",
                "target_ratio": "9:16",
                "mode": "crop",
                "description": "Format for 9:16 vertical reels"
            },
            {
                "type": "audio_volume",
                "gain_db": 3.0,
                "description": "Increase audio loudness by +3.0dB"
            }
        ],
        "warnings": [],
        "requires_confirmation": False
    }

    upload_file = settings.UPLOAD_DIR / job_id / "original_sample_talking_head.mp4"
    assert upload_file.exists()
    pre_render_hash = calculate_file_sha256(upload_file)
    assert pre_render_hash == initial_hash

    # 3. Process/Render Job
    proc_res = client.post(f"/api/jobs/{job_id}/process", json={"approved_plan": three_edits_plan})
    assert proc_res.status_code == 200

    # Poll until completed
    completed = False
    for _ in range(30):
        poll_res = client.get(f"/api/jobs/{job_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            completed = True
            break
        elif poll_data["status"] == "failed":
            pytest.fail(f"Rendering failed: {poll_data.get('error_message')}")
        time.sleep(1)

    assert completed is True, "Render should complete successfully"

    # 4. Verify original hash remains 100% identical after render
    post_render_hash = calculate_file_sha256(upload_file)
    assert post_render_hash == initial_hash, "Original video must remain byte-for-byte immutable"

    # 5. Verify rendered output is a SEPARATE file
    out_dir = settings.OUTPUT_DIR / job_id
    output_files = list(out_dir.glob("clippilot_edited_*.mp4"))
    assert len(output_files) >= 1, "Rendered output file must exist"
    output_file = output_files[0]

    assert output_file != upload_file, "Output file must be distinct from source video"
    assert output_file.stat().st_size > 0, "Rendered output must have non-zero size"
    output_hash = calculate_file_sha256(output_file)
    assert output_hash != initial_hash, "Rendered output content must differ from source"

    # 6. Verify Edit Receipt contains source integrity verification
    receipt_res = client.get(f"/api/jobs/{job_id}/receipt")
    assert receipt_res.status_code == 200
    receipt = receipt_res.json()
    assert "source_integrity" in receipt
    integrity = receipt["source_integrity"]
    assert integrity["original_hash"] == initial_hash
    assert integrity["final_hash"] == initial_hash
    assert integrity["verified_identical"] is True
    assert integrity["non_destructive"] is True
    assert integrity["status"] in ["verified", "verified_immutable"]

def test_undo_and_redo_do_not_modify_original(client):
    """
    Requirements:
    - Undoing or redoing edits must never modify the original source file.
    - Persistent edit history storage and recovery.
    """
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]
    initial_hash = job["original_file_hash"]

    upload_file = settings.UPLOAD_DIR / job_id / "original_sample_talking_head.mp4"
    assert upload_file.exists()

    # Plan A: 1 edit
    plan_a = {
        "prompt": "Trim start 1s",
        "operations": [{"type": "trim_start", "seconds": 1.0, "description": "Trim 1s"}],
        "warnings": [],
        "requires_confirmation": False
    }

    # Plan B: 2 edits
    plan_b = {
        "prompt": "Trim start 1s and mute audio",
        "operations": [
            {"type": "trim_start", "seconds": 1.0, "description": "Trim 1s"},
            {"type": "audio_volume", "gain_db": -60.0, "description": "Mute audio"}
        ],
        "warnings": [],
        "requires_confirmation": False
    }

    # Plan C: 3 edits
    plan_c = {
        "prompt": "Trim start 1s, mute audio, and aspect ratio 1:1",
        "operations": [
            {"type": "trim_start", "seconds": 1.0, "description": "Trim 1s"},
            {"type": "audio_volume", "gain_db": -60.0, "description": "Mute audio"},
            {"type": "aspect_ratio", "target_ratio": "1:1", "mode": "crop", "description": "Square"}
        ],
        "warnings": [],
        "requires_confirmation": False
    }

    history_stack = [plan_a, plan_b, plan_c]

    # Save history (Push edits)
    save_res = client.post(
        f"/api/jobs/{job_id}/history",
        json={"history": history_stack, "current_plan": plan_c}
    )
    assert save_res.status_code == 200
    assert calculate_file_sha256(upload_file) == initial_hash, "Original file must not change on save"

    # Simulate Undo to Plan B
    undo_res = client.post(
        f"/api/jobs/{job_id}/history",
        json={"history": history_stack, "current_plan": plan_b}
    )
    assert undo_res.status_code == 200
    assert calculate_file_sha256(upload_file) == initial_hash, "Original file must not change on undo"

    # Simulate Undo to Plan A
    undo_res2 = client.post(
        f"/api/jobs/{job_id}/history",
        json={"history": history_stack, "current_plan": plan_a}
    )
    assert undo_res2.status_code == 200
    assert calculate_file_sha256(upload_file) == initial_hash, "Original file must not change on second undo"

    # Simulate Redo back to Plan C
    redo_res = client.post(
        f"/api/jobs/{job_id}/history",
        json={"history": history_stack, "current_plan": plan_c}
    )
    assert redo_res.status_code == 200
    assert calculate_file_sha256(upload_file) == initial_hash, "Original file must not change on redo"

    # Verify project reopening (fetching job returns persisted history stack)
    get_res = client.get(f"/api/jobs/{job_id}")
    assert get_res.status_code == 200
    recovered_job = get_res.json()
    assert recovered_job["edit_history"] is not None
    assert len(recovered_job["edit_history"]) == 3
    assert recovered_job["edit_plan"]["operations"] == plan_c["operations"]

def test_integrity_check_endpoint(client):
    """Test dedicated source integrity check endpoint before rendering."""
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job_id = res.json()["id"]

    check_res = client.get(f"/api/jobs/{job_id}/verify-integrity")
    assert check_res.status_code == 200
    data = check_res.json()
    assert data["verified"] is True
    assert data["original_hash"] == data["current_hash"]
    assert data["status"] == "verified_immutable"

def test_corrupted_hash_stops_processing(client):
    """
    Requirement 8:
    If the hash changes unexpectedly, stop the affected operation and report a clear error.
    """
    # 1. Create a demo job
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]
    original_hash = job["original_file_hash"]
    assert original_hash is not None

    # 2. Deliberately tamper with the source file on disk
    source_on_disk = settings.UPLOAD_DIR / job_id / "original_sample_talking_head.mp4"
    assert source_on_disk.exists()
    source_on_disk.write_bytes(b"\x00\x00\x00\x18ftypmp42_TAMPERED_BYTES_1234567890")

    # 3. Check integrity endpoint reports violation
    verify_res = client.get(f"/api/jobs/{job_id}/verify-integrity")
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["verified"] is False
    assert verify_data["status"] in ["tampered", "integrity_violation"]

    # 4. Attempt rendering - must stop and fail with clear error
    plan = {
        "prompt": "Mute audio",
        "operations": [{"type": "audio_volume", "gain_db": -60.0}],
        "warnings": [],
        "requires_confirmation": False
    }
    proc_res = client.post(f"/api/jobs/{job_id}/process", json={"approved_plan": plan})
    assert proc_res.status_code == 200

    # Poll to confirm job transitioned to failed with clear integrity error
    failed = False
    for _ in range(15):
        poll_res = client.get(f"/api/jobs/{job_id}")
        poll_data = poll_res.json()
        if poll_data["status"] == "failed":
            failed = True
            assert "Source integrity violation" in poll_data["error_message"]
            assert "Operation aborted" in poll_data["error_message"]
            break
        time.sleep(0.5)

    assert failed is True, "Processing must fail when source file hash changes unexpectedly"
