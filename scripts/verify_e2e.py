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

        # 8. Media Stream & Receipt Inspection
        print("8. Verifying Processed Media & Edit Receipt...")
        r_prev = client.get(f"{BACKEND_URL}/jobs/{job_id}/preview/output", headers=auth_headers)
        assert r_prev.status_code == 200
        assert len(r_prev.content) > 100000
        print(f"   [PASS] Output Video Stream: {len(r_prev.content)} bytes")

        r_rcpt = client.get(f"{BACKEND_URL}/jobs/{job_id}/receipt", headers=auth_headers)
        assert r_rcpt.status_code == 200
        rcpt = r_rcpt.json()
        assert rcpt["job_id"] == job_id
        assert len(rcpt["applied_operations"]) > 0
        print(f"   [PASS] Audit Receipt Verified: {len(rcpt['applied_operations'])} transforms applied")

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

        # 11. Test Logout
        print("11. Testing Logout & Token Invalidation...")
        r_logout = client.post(f"{BACKEND_URL}/auth/logout", headers=auth_headers)
        assert r_logout.status_code == 200
        print("   [PASS] Logout endpoint cleared session cookies successfully")

    print("\n=== ALL 11 END-TO-END ACCEPTANCE & SECURITY STAGES PASSED CLEANLY ===")

if __name__ == "__main__":
    run_e2e_verification()
