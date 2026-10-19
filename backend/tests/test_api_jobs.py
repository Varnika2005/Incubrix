import time
from pathlib import Path
from app.core.config import settings

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ClipPilot AI"

def test_capabilities_endpoint(client):
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["ffmpeg_installed"] is True
    assert len(data["supported_operations"]) >= 5

def test_1_click_demo_lifecycle(client):
    # 1. Create Demo Job
    res = client.post("/api/jobs/demo")
    assert res.status_code == 200
    job = res.json()
    job_id = job["id"]
    assert job["status"] == "awaiting_approval"
    assert job["edit_plan"] is not None

    # 2. Process Job
    proc_res = client.post(f"/api/jobs/{job_id}/process", json={"approved_plan": job["edit_plan"]})
    assert proc_res.status_code == 200
    assert proc_res.json()["status"] in ["queued", "processing"]

    # 3. Poll until completed (timeout 25s)
    completed = False
    for _ in range(25):
        poll_res = client.get(f"/api/jobs/{job_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            completed = True
            break
        elif poll_data["status"] == "failed":
            pytest.fail(f"Job failed: {poll_data.get('error_message')}")
        time.sleep(1)

    assert completed is True, "Job should complete within timeout"

    # 4. Preview Original and Output
    orig_res = client.get(f"/api/jobs/{job_id}/preview/original")
    assert orig_res.status_code == 200

    out_res = client.get(f"/api/jobs/{job_id}/preview/output")
    assert out_res.status_code == 200

    # 5. Download Endpoint
    dl_res = client.get(f"/api/jobs/{job_id}/download")
    assert dl_res.status_code == 200

    # 6. Edit Receipt
    rcpt_res = client.get(f"/api/jobs/{job_id}/receipt")
    assert rcpt_res.status_code == 200
    rcpt = rcpt_res.json()
    assert rcpt["job_id"] == job_id
    assert len(rcpt["applied_operations"]) > 0

def test_upload_invalid_extension(client):
    res = client.post(
        "/api/jobs/upload",
        files={"file": ("malicious.exe", b"MZ fake binary", "application/x-msdownload")}
    )
    assert res.status_code == 400
    assert "Unsupported format" in res.json()["detail"]
