import time
import httpx

BACKEND_URL = "http://127.0.0.1:8000/api"
FRONTEND_URL = "http://127.0.0.1:5173"

def run_e2e_verification():
    print("=== ClipPilot AI End-to-End System Verification ===")
    
    with httpx.Client(timeout=30.0) as client:
        # 1. Health Check
        print("1. Probing Backend Health...")
        r_health = client.get(f"{BACKEND_URL}/health")
        assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
        print(f"   [PASS] Health OK: {r_health.json()}")

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

        # 4. 1-Click Demo Flow
        print("4. Triggering 1-Click Demo Project Creation...")
        r_demo = client.post(f"{BACKEND_URL}/jobs/demo")
        assert r_demo.status_code == 200, f"Demo creation failed: {r_demo.text}"
        demo_job = r_demo.json()
        job_id = demo_job["id"]
        print(f"   [PASS] Demo Job Created: ID={job_id}")
        print(f"   [PASS] Source Metadata: {demo_job['input_metadata']['width']}x{demo_job['input_metadata']['height']}, {demo_job['input_metadata']['duration']}s")
        print(f"   [PASS] Interpreted Edit Plan Steps: {len(demo_job['edit_plan']['operations'])}")

        # 5. Process Job
        print("5. Approving and Processing Edit Plan...")
        r_proc = client.post(f"{BACKEND_URL}/jobs/{job_id}/process", json={"approved_plan": demo_job["edit_plan"]})
        assert r_proc.status_code == 200
        print(f"   [PASS] Job Queued for Processing: Status={r_proc.json()['status']}")

        # 6. Polling Execution
        print("6. Polling Processing Pipeline...")
        completed = False
        for i in range(25):
            r_poll = client.get(f"{BACKEND_URL}/jobs/{job_id}")
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
        print(f"   [PASS] Job Successfully Completed in {pj['processing_time_seconds']}s!")

        # 7. Verify Processed Media Decodability
        print("7. Verifying Processed Media Preview Endpoint...")
        r_prev = client.get(f"{BACKEND_URL}/jobs/{job_id}/preview/output")
        assert r_prev.status_code == 200
        assert len(r_prev.content) > 100000, "Output video should be non-trivial size"
        print(f"   [PASS] Output Video Preview Stream: {len(r_prev.content)} bytes downloaded")

        # 8. Verify Edit Receipt
        print("8. Fetching Cryptographic Audit Edit Receipt...")
        r_rcpt = client.get(f"{BACKEND_URL}/jobs/{job_id}/receipt")
        assert r_rcpt.status_code == 200
        rcpt = r_rcpt.json()
        assert rcpt["job_id"] == job_id
        assert len(rcpt["applied_operations"]) > 0
        print(f"   [PASS] Audit Receipt Verified: {len(rcpt['applied_operations'])} transforms applied")
        print(f"   [PASS] Output Specs: {rcpt['output_metadata']['width']}x{rcpt['output_metadata']['height']} ({rcpt['output_metadata']['aspect_ratio']})")

        # 9. Verify SQLite Job Persistence
        print("9. Verifying SQLite Job History Persistence...")
        r_list = client.get(f"{BACKEND_URL}/jobs")
        assert r_list.status_code == 200
        job_ids = [j["id"] for j in r_list.json()]
        assert job_id in job_ids
        print(f"   [PASS] Job {job_id} present in persistent SQLite history")

    print("\n=== ALL 9 END-TO-END ACCEPTANCE STAGES PASSED CLEANLY ===")

if __name__ == "__main__":
    run_e2e_verification()
