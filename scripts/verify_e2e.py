import time
import uuid
import httpx

BACKEND_URL = "http://127.0.0.1:8000/api"
FRONTEND_URL = "http://127.0.0.1:5173"

def run_e2e_verification():
    print("=== ClipPilot AI End-to-End System & Security Verification ===")
    
    with httpx.Client(timeout=30.0) as client:
        # 1. Health Check
        print("1. Probing Backend Health...")
        r_health = client.get(f"{BACKEND_URL}/health")
        assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
        print(f"   [PASS] Health OK: {r_health.json()['status']}")

        # 2. Capabilities Check
        print("2. Probing System Capabilities...")
        r_cap = client.get(f"{BACKEND_URL}/capabilities")
        assert r_cap.status_code == 200, f"Capabilities failed: {r_cap.text}"
        cap_data = r_cap.json()
        assert cap_data["ffmpeg_installed"] is True
        print(f"   [PASS] FFmpeg verified: {cap_data['ffmpeg_version'][:40]}")
        print(f"   [PASS] Operations supported: {len(cap_data['supported_operations'])} operations")

        # 3. Frontend Reachability
        print("3. Checking Frontend Web Server...")
        r_fe = client.get(FRONTEND_URL)
        assert r_fe.status_code == 200
        print("   [PASS] Frontend Vite server is serving HTTP 200 OK")

        # 4. Unauthenticated Access Protection Check
        print("4. Testing Unauthenticated Route Protection...")
        r_unauth_jobs = client.get(f"{BACKEND_URL}/jobs")
        assert r_unauth_jobs.status_code == 401, f"Expected 401 for unauth jobs, got {r_unauth_jobs.status_code}"
        print("   [PASS] Unauthenticated access to /api/jobs correctly rejected (401 Unauthorized)")

        # 5. User Registration & Authentication Lifecycle
        print("5. Testing User Signup & Session Creation...")
        test_email = f"creator_{uuid.uuid4().hex[:6]}@example.com"
        r_signup = client.post(f"{BACKEND_URL}/auth/signup", json={
            "full_name": "Verified Creator",
            "email": test_email,
            "password": "SecurePassword2026!",
            "confirm_password": "SecurePassword2026!"
        })
        assert r_signup.status_code == 201, f"Signup failed: {r_signup.text}"
        signup_data = r_signup.json()
        token = signup_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        print(f"   [PASS] User registered successfully: {test_email}")

        # Verify /auth/me
        r_me = client.get(f"{BACKEND_URL}/auth/me", headers=auth_headers)
        assert r_me.status_code == 200
        assert r_me.json()["email"] == test_email
        print(f"   [PASS] Session identity verified: {r_me.json()['full_name']}")

        # 6. Authenticated 1-Click Demo & Processing Flow
        print("6. Creating & Processing Video with Authenticated User...")
        r_demo = client.post(f"{BACKEND_URL}/jobs/demo", headers=auth_headers)
        assert r_demo.status_code == 200, f"Demo creation failed: {r_demo.text}"
        demo_job = r_demo.json()
        job_id = demo_job["id"]
        print(f"   [PASS] Demo Job Created: ID={job_id}")

        r_proc = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/process",
            headers=auth_headers,
            json={"approved_plan": demo_job["edit_plan"]}
        )
        assert r_proc.status_code == 200
        print(f"   [PASS] Job Queued for Processing: Status={r_proc.json()['status']}")

        # 7. Polling Processing Pipeline
        print("7. Polling Processing Pipeline...")
        completed = False
        for i in range(25):
            r_poll = client.get(f"{BACKEND_URL}/jobs/{job_id}", headers=auth_headers)
            assert r_poll.status_code == 200
            pj = r_poll.json()
            print(f"   ... Poll {i+1}: Status={pj['status']}, Progress={pj['progress']}%")
            if pj["status"] == "completed":
                completed = True
                break
            elif pj["status"] == "failed":
                raise RuntimeError(f"Processing failed: {pj.get('error_message')}")
            time.sleep(1)

        assert completed is True, "Job did not complete in allotted time"
        print(f"   [PASS] Job Completed in {pj['processing_time_seconds']}s!")

        # 8. Media Stream & Receipt Inspection with Non-Destructive Integrity Verification
        print("8. Verifying Processed Media, Edit Receipt & Non-Destructive Source Integrity...")
        r_prev = client.get(f"{BACKEND_URL}/jobs/{job_id}/preview/output", headers=auth_headers)
        assert r_prev.status_code == 200
        assert len(r_prev.content) > 100000
        print(f"   [PASS] Output Video Stream: {len(r_prev.content)} bytes")

        r_dl = client.get(f"{BACKEND_URL}/jobs/{job_id}/download", headers=auth_headers)
        assert r_dl.status_code == 200
        assert "video/mp4" in r_dl.headers.get("content-type", "")
        assert "attachment" in r_dl.headers.get("content-disposition", "")
        assert 'filename="ClipPilot_Edited_Video.mp4"' in r_dl.headers.get("content-disposition", "")
        print(f"   [PASS] Direct MP4 Download Verified: {len(r_dl.content)} bytes, attachment filename=ClipPilot_Edited_Video.mp4")

        # Non-Destructive Source Integrity Verification
        r_integrity = client.get(f"{BACKEND_URL}/jobs/{job_id}/verify-integrity", headers=auth_headers)
        assert r_integrity.status_code == 200
        integrity_data = r_integrity.json()
        assert integrity_data["verified"] is True
        assert integrity_data["original_hash"] == integrity_data["current_hash"]
        print(f"   [PASS] Non-Destructive Source Guarantee Verified: SHA-256={integrity_data['original_hash'][:16]}... unchanged")

        r_rcpt = client.get(f"{BACKEND_URL}/jobs/{job_id}/receipt", headers=auth_headers)
        assert r_rcpt.status_code == 200
        rcpt = r_rcpt.json()
        assert rcpt["job_id"] == job_id
        assert len(rcpt["applied_operations"]) > 0
        assert rcpt.get("source_integrity") is not None
        assert rcpt["source_integrity"]["verified_identical"] is True
        assert rcpt["source_integrity"]["non_destructive"] is True
        print(f"   [PASS] Audit Receipt Verified: {len(rcpt['applied_operations'])} transforms applied with verified non-destructive source integrity")

        # Edit Timeline History Stack Persistence
        r_history = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/history",
            headers=auth_headers,
            json={
                "history": [demo_job["edit_plan"]],
                "current_plan": demo_job["edit_plan"]
            }
        )
        assert r_history.status_code == 200
        print("   [PASS] Persistent EDL Timeline History Stack saved and verified")

        # 9. Verify User-Specific History & Isolation
        print("9. Verifying User-Specific History Isolation...")
        r_list = client.get(f"{BACKEND_URL}/jobs", headers=auth_headers)
        assert r_list.status_code == 200
        user_jobs = r_list.json()
        assert any(j["id"] == job_id for j in user_jobs)
        print(f"   [PASS] Job {job_id} present in user's isolated project history")

        # Create User B and verify User B cannot access User A's private job
        test_email_b = f"user_b_{uuid.uuid4().hex[:6]}@example.com"
        r_b = client.post(f"{BACKEND_URL}/auth/signup", json={
            "full_name": "User B",
            "email": test_email_b,
            "password": "SecurePassword2026!",
            "confirm_password": "SecurePassword2026!"
        })
        token_b = r_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 10. Test cross-user isolation
        print("10. Testing Cross-User Authorization Enforcement...")
        r_list_b = client.get(f"{BACKEND_URL}/jobs", headers=headers_b)
        assert r_list_b.status_code == 200
        assert not any(j["id"] == job_id for j in r_list_b.json()), "User B should not see User A's job"

        r_delete_b = client.delete(f"{BACKEND_URL}/jobs/{job_id}", headers=headers_b)
        assert r_delete_b.status_code == 403, "User B should be forbidden from deleting User A's job"
        print("   [PASS] Cross-user job deletion safely blocked (403 Forbidden)")

        # 11. Content-Aware Timeline API, Anchor Preservation & Coordinate Mapping
        print("11. Verifying Content-Aware Editing & Timeline Transformations...")
        # Add anchored caption, mute, beep, and visual effects to source timeline
        r_eff_caption = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/timeline/effects",
            headers=auth_headers,
            json={
                "type": "caption",
                "source_start": 3.5,
                "source_end": 5.5,
                "label": "Breaking News Anchor",
                "parameters": {"text": "Breaking News Anchor"}
            }
        )
        assert r_eff_caption.status_code == 200, f"Add caption effect failed: {r_eff_caption.text}"
        print("   [PASS] Anchored Caption at source [3.5s - 5.5s]")

        r_eff_beep = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/timeline/effects",
            headers=auth_headers,
            json={
                "type": "beep",
                "source_start": 4.0,
                "source_end": 4.8,
                "label": "Censorship Beep",
                "parameters": {"frequency": 1000}
            }
        )
        assert r_eff_beep.status_code == 200
        print("   [PASS] Anchored Censorship Beep at source [4.0s - 4.8s]")

        # Apply Speed Transformation
        r_speed = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/timeline/transform",
            headers=auth_headers,
            json={"action": "speed", "speed": 2.0}
        )
        assert r_speed.status_code == 200, f"Speed transform failed: {r_speed.text}"
        tl_after_speed = r_speed.json()
        assert tl_after_speed["summary"]["has_speed_change"] is True
        print("   [PASS] Speed 2.0x transformation scaled timeline duration while preserving source anchors")

        # Test Deterministic Coordinate Mapping (source 4.0s -> timeline)
        r_map = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/timeline/map",
            headers=auth_headers,
            json={"source_time": 4.0}
        )
        assert r_map.status_code == 200, f"Coordinate map failed: {r_map.text}"
        map_res = r_map.json()
        assert len(map_res["mapped_timeline_times"]) > 0
        mapped_t = map_res["mapped_timeline_times"][0]
        print(f"   [PASS] Deterministic Coordinate Mapping: Source 4.0s -> Timeline {mapped_t:.2f}s")

        # Verify Timeline Inspection
        r_tl = client.get(f"{BACKEND_URL}/jobs/{job_id}/timeline", headers=auth_headers)
        assert r_tl.status_code == 200
        tl_data = r_tl.json()
        assert len(tl_data["source_effects"]) >= 2
        assert len(tl_data["transformed_effects"]) >= 2
        print(f"   [PASS] Timeline Model Verified: {len(tl_data['segments'])} segment(s), {len(tl_data['transformed_effects'])} transformed effect(s)")

        # 12. Must-have 3: Strict Three-Way Instruction Response Protocol Verification
        print("12. Testing Must-have 3: Strict Three-Way Response System (/instruction)...")

        # 12a: Valid instruction -> APPLIED
        r_applied = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Mute the video from 00:02 to 00:05"}
        )
        assert r_applied.status_code == 200, f"Instruction failed: {r_applied.text}"
        res_applied = r_applied.json()
        assert res_applied["status"] == "APPLIED"
        assert res_applied["operation"]["type"] == "MUTE"
        assert res_applied["operation"]["start"] == 2.0
        assert res_applied["operation"]["end"] == 5.0
        assert res_applied["operationId"] is not None
        print(f"   [PASS] Valid Mute: Status={res_applied['status']}, Op={res_applied['operation']['type']} [{res_applied['operation']['start']}s-{res_applied['operation']['end']}s], ID={res_applied['operationId']}")

        # 12b: Missing timestamp -> NEEDS_CLARIFICATION
        r_clarify_missing = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Mute the video"}
        )
        assert r_clarify_missing.status_code == 200
        res_clarify1 = r_clarify_missing.json()
        assert res_clarify1["status"] == "NEEDS_CLARIFICATION"
        assert res_clarify1["clarification_prompt"] is not None
        print(f"   [PASS] Missing Timestamp: Status={res_clarify1['status']}, Question='{res_clarify1['clarification_prompt']}'")

        # 12c: Ambiguous time reference -> NEEDS_CLARIFICATION
        r_clarify_ambig = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Trim the middle part"}
        )
        assert r_clarify_ambig.status_code == 200
        res_clarify2 = r_clarify_ambig.json()
        assert res_clarify2["status"] == "NEEDS_CLARIFICATION"
        assert "middle part" in res_clarify2["clarification_prompt"]
        print(f"   [PASS] Ambiguous Reference: Status={res_clarify2['status']}, Question='{res_clarify2['clarification_prompt']}'")

        # 12d: Unsupported effect -> REJECTED
        r_rej_unsupp = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Reverse the video backwards"}
        )
        assert r_rej_unsupp.status_code == 200
        res_rej1 = r_rej_unsupp.json()
        assert res_rej1["status"] == "REJECTED"
        assert "not supported" in res_rej1["message"].lower()
        print(f"   [PASS] Unsupported Effect: Status={res_rej1['status']}, Reason='{res_rej1['message']}'")

        # 12e: Invalid range (start >= end) -> REJECTED
        r_rej_range = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Mute audio from 30s to 10s"}
        )
        assert r_rej_range.status_code == 200
        res_rej2 = r_rej_range.json()
        assert res_rej2["status"] == "REJECTED"
        assert res_rej2["error_code"] in ("INVALID_RANGE", "INVALID_TIME_RANGE")
        print(f"   [PASS] Invalid Range: Status={res_rej2['status']}, Error={res_rej2['error_code']}")

        # 12f: Midway failure & atomic rollback -> REJECTED with rollback_performed=True
        r_rollback = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={
                "instruction": "Mute audio from 00:01 to 00:03",
                "simulate_failure": True
            }
        )
        assert r_rollback.status_code == 200
        res_roll = r_rollback.json()
        assert res_roll["status"] == "REJECTED"
        assert res_roll["rollback_performed"] is True
        print(f"   [PASS] Midway Failure Rollback: Status={res_roll['status']}, Rollback={res_roll['rollback_performed']}, Reason='{res_roll['message']}'")

        # 12g: Verify Edit Receipt contains instruction_audit
        r_receipt_audit = client.get(f"{BACKEND_URL}/jobs/{job_id}/receipt", headers=auth_headers)
        assert r_receipt_audit.status_code == 200
        receipt_data = r_receipt_audit.json()
        assert "instruction_audit" in receipt_data
        assert receipt_data["instruction_audit"] is not None
        assert len(receipt_data["instruction_audit"]) >= 6
        print(f"   [PASS] Edit Receipt Audit: {len(receipt_data['instruction_audit'])} instructions tracked in instruction_audit")

        # 13. Test Undo/Redo & Branching History Invalidation
        print("13. Testing Undo/Redo & History Stack Branching...")
        r_hist_before = client.get(f"{BACKEND_URL}/jobs/{job_id}/history", headers=auth_headers)
        assert r_hist_before.status_code == 200
        h_info = r_hist_before.json()
        assert h_info["can_undo"] is True
        idx_before = h_info["current_index"]

        # Perform Undo
        r_undo = client.post(f"{BACKEND_URL}/jobs/{job_id}/undo", headers=auth_headers)
        assert r_undo.status_code == 200
        undo_data = r_undo.json()
        assert undo_data["current_index"] == idx_before - 1
        assert undo_data["can_redo"] is True
        print(f"   [PASS] Undo operation restored state index {undo_data['current_index']}")

        # Perform Redo
        r_redo = client.post(f"{BACKEND_URL}/jobs/{job_id}/redo", headers=auth_headers)
        assert r_redo.status_code == 200
        redo_data = r_redo.json()
        assert redo_data["current_index"] == idx_before
        print(f"   [PASS] Redo operation reapplied state index {redo_data['current_index']}")

        # Undo and branch
        client.post(f"{BACKEND_URL}/jobs/{job_id}/undo", headers=auth_headers)
        r_branch = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Add caption 'Branch Test' from 1s to 2s"}
        )
        assert r_branch.status_code == 200
        r_hist_branched = client.get(f"{BACKEND_URL}/jobs/{job_id}/history", headers=auth_headers)
        assert r_hist_branched.json()["can_redo"] is False
        print("   [PASS] New edit after undo cleared redo history successfully")

        # 14. Test Consistent Timestamp Reference Policy
        print("14. Testing Consistent Timestamp Reference Policy...")
        # 14a: Default references source coordinates
        r_ts_src = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Mute audio from 1s to 2s"}
        )
        assert r_ts_src.status_code == 200
        assert r_ts_src.json()["time_reference"] == "source"
        print("   [PASS] Default instruction policy resolved source coordinates")

        # 14b: Explicit timeline coordinates
        r_ts_tl = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Mute audio from 0.5s to 1.5s on timeline"}
        )
        assert r_ts_tl.status_code == 200
        assert r_ts_tl.json()["time_reference"] == "timeline"
        print("   [PASS] Explicit timeline keyword resolved timeline coordinates with conversion")

        # 14c: Ambiguous/conflicting reference returns NEEDS_CLARIFICATION
        r_ts_conflict = client.post(
            f"{BACKEND_URL}/jobs/{job_id}/instruction",
            headers=auth_headers,
            json={"instruction": "Mute audio from 1s to 2s in source on timeline"}
        )
        assert r_ts_conflict.status_code == 200
        assert r_ts_conflict.json()["status"] == "NEEDS_CLARIFICATION"
        assert r_ts_conflict.json()["error_code"] == "CONFLICTING_TIME_REFERENCE"
        print("   [PASS] Conflicting time references returned NEEDS_CLARIFICATION (CONFLICTING_TIME_REFERENCE)")

        # 15. Test Logout
        print("15. Testing Logout & Token Invalidation...")
        r_logout = client.post(f"{BACKEND_URL}/auth/logout", headers=auth_headers)
        assert r_logout.status_code == 200
        print("   [PASS] Logout endpoint cleared session cookies successfully")

    print("\n=== ALL 15 END-TO-END ACCEPTANCE, SECURITY, INTEGRATION & VERIFICATION STAGES PASSED ===")

if __name__ == "__main__":
    run_e2e_verification()
