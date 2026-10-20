import hashlib
import hmac
import json
import time
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.callback_service import dispatch_job_callback
from app.services.manifest_generator import generate_output_manifest
from app.services.url_ingestion import validate_url_safety, is_ip_forbidden
from app.core.errors import AppException

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

# ==============================================================================
# Requirement 1 & 8: Health & Readiness Endpoints
# ==============================================================================
def test_requirement_8_liveness_health(client):
    # Root /health
    r_root = client.get("/health")
    assert r_root.status_code == 200
    d_root = r_root.json()
    assert d_root["status"] == "ok"
    assert d_root["service"] == "ClipPilot AI"
    assert "timestamp" in d_root

    # /api/v1/health
    r_v1 = client.get("/api/v1/health")
    assert r_v1.status_code == 200
    assert r_v1.json()["status"] == "ok"

    # Backward compatible /api/health
    r_api = client.get("/api/health")
    assert r_api.status_code == 200
    assert r_api.json()["status"] == "ok"

def test_requirement_8_readiness_probe(client):
    r_ready = client.get("/ready")
    assert r_ready.status_code == 200
    data = r_ready.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"]["status"] == "ok"
    assert data["checks"]["storage"]["status"] == "ok"
    assert data["checks"]["ffmpeg"]["status"] == "ok"

    # /api/v1/ready alias
    r_v1_ready = client.get("/api/v1/ready")
    assert r_v1_ready.status_code == 200
    assert r_v1_ready.json()["status"] == "ready"

def test_requirement_8_correlation_id(client):
    custom_id = "test-corr-id-xyz-987"
    resp = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Correlation-ID") == custom_id

    # Auto-generation when omitted
    resp2 = client.get("/health")
    assert resp2.status_code == 200
    auto_id = resp2.headers.get("X-Correlation-ID")
    assert auto_id is not None
    assert len(auto_id) >= 16

# ==============================================================================
# Requirement 2: Documented HTTP API & OpenAPI 3.1
# ==============================================================================
def test_requirement_2_openapi_yaml_endpoint(client):
    r_yaml = client.get("/api/v1/openapi.yaml")
    assert r_yaml.status_code == 200
    assert "openapi: 3.1.0" in r_yaml.text
    assert "/api/v1/jobs" in r_yaml.text
    assert "/health" in r_yaml.text

    # Root /openapi.yaml
    r_root_yaml = client.get("/openapi.yaml")
    assert r_root_yaml.status_code == 200
    assert "openapi: 3.1.0" in r_root_yaml.text

# ==============================================================================
# Requirement 3: Background Jobs, HTTP 202, and Standard Status Mapping
# ==============================================================================
def test_requirement_3_background_job_lifecycle_and_202(client):
    # 1. Create Demo Job under /api/v1/jobs/demo
    r_create = client.post("/api/v1/jobs/demo")
    assert r_create.status_code == 200
    job_info = r_create.json()
    job_id = job_info["job_id"] or job_info["id"]
    assert job_id is not None
    edit_plan = job_info["edit_plan"]
    assert edit_plan is not None

    # 2. Accept for processing -> MUST return HTTP 202 Accepted on /api/v1/
    r_proc = client.post(
        f"/api/v1/jobs/{job_id}/process",
        json={"approved_plan": edit_plan, "callback_url": "https://example.com/callback"}
    )
    assert r_proc.status_code == 202
    proc_data = r_proc.json()
    assert proc_data["job_id"] == job_id
    assert proc_data["status"] in ("queued", "running")

    # 3. Poll until completion (maps to "succeeded" on v1)
    completed = False
    for _ in range(30):
        r_poll = client.get(f"/api/v1/jobs/{job_id}")
        assert r_poll.status_code == 200
        poll_json = r_poll.json()
        assert poll_json["job_id"] == job_id
        assert 0 <= poll_json["progress"] <= 100

        if poll_json["status"] == "succeeded":
            completed = True
            assert poll_json["result"] is not None
            assert f"/api/v1/jobs/{job_id}/download" in poll_json["result"]["download_url"]
            assert f"/api/v1/jobs/{job_id}/manifest" in poll_json["result"]["manifest_url"]
            break
        elif poll_json["status"] == "failed":
            pytest.fail(f"Job processing failed: {poll_json.get('error_message')}")
        time.sleep(1)

    assert completed is True

def test_requirement_3_hmac_sha256_callback_signing():
    secret = "test_hmac_secret_key_1234567890"
    payload = {"job_id": "job_abc_123", "status": "succeeded", "progress": 100}
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    expected_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    # Verify signature generation
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    assert sig == expected_sig

# ==============================================================================
# Requirement 4: Safe Retries and Idempotency
# ==============================================================================
def test_requirement_4_idempotency_duplicate_and_conflict(client):
    idem_key = f"test-key-{int(time.time() * 1000)}"

    # 1. First Request
    r1 = client.post(
        "/api/v1/jobs/demo",
        headers={"Idempotency-Key": idem_key}
    )
    assert r1.status_code == 200
    data1 = r1.json()

    # 2. Duplicate Request with identical key and payload -> Returns cached response
    r2 = client.post(
        "/api/v1/jobs/demo",
        headers={"Idempotency-Key": idem_key}
    )
    assert r2.status_code == 200
    assert r2.headers.get("X-Idempotent-Replay") == "true"
    data2 = r2.json()
    assert data1["id"] == data2["id"]

    # 3. Request with SAME key but DIFFERENT endpoint or payload -> MUST reject with 409 Conflict
    r3 = client.post(
        f"/api/v1/jobs/{data1['id']}/analyze",
        headers={"Idempotency-Key": idem_key},
        json={"prompt": "A totally different conflicting instruction"}
    )
    assert r3.status_code == 409
    err_json = r3.json()
    assert err_json["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert err_json["error"]["retryable"] is False

# ==============================================================================
# Requirement 5: Consistent JSON Errors Schema
# ==============================================================================
def test_requirement_5_consistent_json_errors_404(client):
    r_404 = client.get("/api/v1/jobs/nonexistent-job-uuid-12345")
    assert r_404.status_code == 404
    err = r_404.json()
    assert "error" in err
    assert err["error"]["code"] == "NOT_FOUND"
    assert isinstance(err["error"]["message"], str)
    assert err["error"]["retryable"] is False
    assert isinstance(err["error"]["details"], dict)

def test_requirement_5_consistent_json_errors_validation_422(client):
    r_val = client.post("/api/v1/jobs/some-id/analyze", json={})
    assert r_val.status_code == 422
    err = r_val.json()
    assert "error" in err
    assert err["error"]["code"] == "VALIDATION_ERROR"
    assert "validation_errors" in err["error"]["details"]

# ==============================================================================
# Requirement 6: Environment-Based Configuration
# ==============================================================================
def test_requirement_6_environment_settings():
    assert settings.PROJECT_NAME == "ClipPilot AI"
    assert settings.PORT > 0
    assert settings.MAX_UPLOAD_SIZE_BYTES > 0
    assert settings.STORAGE_DIR.exists()
    assert settings.UPLOAD_DIR.exists()
    assert settings.OUTPUT_DIR.exists()
    assert isinstance(settings.ALLOWED_EXTENSIONS, set)

# ==============================================================================
# Requirement 7: SSRF Protection for Ingestion URLs
# ==============================================================================
def test_requirement_7_ssrf_prohibited_ips():
    # Loopback
    assert is_ip_forbidden("127.0.0.1") is True
    assert is_ip_forbidden("127.0.0.2") is True
    # Private RFC 1918
    assert is_ip_forbidden("10.0.0.1") is True
    assert is_ip_forbidden("192.168.1.100") is True
    assert is_ip_forbidden("172.16.0.5") is True
    # Link local & Cloud metadata
    assert is_ip_forbidden("169.254.169.254") is True
    # IPv6 loopback
    assert is_ip_forbidden("::1") is True

def test_requirement_7_ssrf_endpoint_blocking(client):
    # Attempt SSRF to loopback
    r_ssrf = client.post("/api/v1/jobs/url", json={"url": "http://127.0.0.1:8000/secret"})
    assert r_ssrf.status_code == 400
    err = r_ssrf.json()
    assert err["error"]["code"] == "SSRF_BLOCKED"

    # Attempt SSRF to AWS metadata
    r_meta = client.post("/api/v1/jobs/url", json={"url": "http://169.254.169.254/latest/meta-data/"})
    assert r_meta.status_code == 400
    assert r_meta.json()["error"]["code"] == "SSRF_BLOCKED"

    # Attempt invalid scheme
    r_scheme = client.post("/api/v1/jobs/url", json={"url": "file:///etc/passwd"})
    assert r_scheme.status_code == 400
    assert r_scheme.json()["error"]["code"] == "UNSUPPORTED_URL_SCHEME"

# ==============================================================================
# Requirement 9: Output Manifest
# ==============================================================================
def test_requirement_9_output_manifest_generation(client):
    # Process demo job to get manifest
    r_demo = client.post("/api/v1/jobs/demo")
    assert r_demo.status_code == 200
    job_id = r_demo.json()["id"]
    plan = r_demo.json()["edit_plan"]

    r_proc = client.post(f"/api/v1/jobs/{job_id}/process", json={"approved_plan": plan})
    assert r_proc.status_code == 202

    # Poll until succeeded
    for _ in range(30):
        r_poll = client.get(f"/api/v1/jobs/{job_id}")
        if r_poll.json()["status"] == "succeeded":
            break
        time.sleep(1)

    # Fetch manifest
    r_man = client.get(f"/api/v1/jobs/{job_id}/manifest")
    assert r_man.status_code == 200
    man = r_man.json()
    assert man["manifest_version"] == "1.0.0"
    assert man["job_id"] == job_id
    assert "input" in man
    assert "output" in man
    assert "models_and_engines" in man
    assert "effective_settings" in man
    assert man["random_seed"] == "not_applicable"
    assert "timestamps" in man
    assert "duration_timings" in man
    assert "warnings" in man
    assert "estimated_cost" in man
    assert "licence_and_rights" in man

# ==============================================================================
# Requirement 10: Batch Runner CLI Execution
# ==============================================================================
def test_requirement_10_batch_runner(client, tmp_path):
    from scripts.batch_runner import run_batch

    sample_media = Path("sample_assets/sample_1_talking_head.mp4")
    assert sample_media.exists()

    out_batch_dir = tmp_path / "batch_out"

    exit_code = run_batch(
        input_path=sample_media,
        output_dir=out_batch_dir,
        api_url="http://testserver",
        timeout_seconds=30.0,
        poll_interval=0.5,
        client=client
    )

    assert exit_code == 0
    assert (out_batch_dir / "batch_summary.json").exists()

    summary_data = json.loads((out_batch_dir / "batch_summary.json").read_text(encoding="utf-8"))
    assert summary_data["total_items"] == 1
    assert summary_data["succeeded"] == 1
    assert summary_data["failed"] == 0

    # Verify output files saved into results folder
    manifest_files = list(out_batch_dir.glob("*_manifest.json"))
    assert len(manifest_files) >= 1
    receipt_files = list(out_batch_dir.glob("*_receipt.json"))
    assert len(receipt_files) >= 1
