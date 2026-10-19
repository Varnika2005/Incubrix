import uuid
import pytest
from app.database.models import UserModel, JobModel

def generate_unique_email(prefix="creator"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"

def test_successful_signup_and_token(client):
    email = generate_unique_email("alex")
    res = client.post("/api/auth/signup", json={
        "full_name": "Alex Creator",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email
    assert data["user"]["full_name"] == "Alex Creator"

def test_signup_validation_errors(client):
    # 1. Passwords mismatch
    res = client.post("/api/auth/signup", json={
        "full_name": "Invalid User",
        "email": generate_unique_email("test"),
        "password": "Password123!",
        "confirm_password": "DifferentPassword!"
    })
    assert res.status_code == 422

    # 2. Short password
    res = client.post("/api/auth/signup", json={
        "full_name": "Invalid User",
        "email": generate_unique_email("test"),
        "password": "short",
        "confirm_password": "short"
    })
    assert res.status_code == 422

    # 3. Password without digits
    res = client.post("/api/auth/signup", json={
        "full_name": "Invalid User",
        "email": generate_unique_email("test"),
        "password": "NoDigitsPassword!",
        "confirm_password": "NoDigitsPassword!"
    })
    assert res.status_code == 422

def test_duplicate_signup_conflict(client):
    email = generate_unique_email("dup")
    signup_payload = {
        "full_name": "Original User",
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    }
    res1 = client.post("/api/auth/signup", json=signup_payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/signup", json=signup_payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]

def test_successful_login_and_me(client):
    email = generate_unique_email("login")
    password = "SecurePassword2026!"
    client.post("/api/auth/signup", json={
        "full_name": "Login Tester",
        "email": email,
        "password": password,
        "confirm_password": password
    })

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
        "remember_me": True
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token

    # Check /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

def test_invalid_credentials_returns_generic_401(client):
    res = client.post("/api/auth/login", json={
        "email": "nonexistent_user_123456@example.com",
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_logout(client):
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert res.json()["status"] == "logged_out"

def test_unauthenticated_access_to_protected_routes(client):
    # Unauthenticated /jobs history
    res = client.get("/api/jobs")
    assert res.status_code == 401

def test_cross_user_isolation(client, db):
    # Create User A
    email_a = generate_unique_email("user_a")
    res_a = client.post("/api/auth/signup", json={
        "full_name": "User A",
        "email": email_a,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    token_a = res_a.json()["access_token"]
    user_a_id = res_a.json()["user"]["id"]

    # Create User B
    email_b = generate_unique_email("user_b")
    res_b = client.post("/api/auth/signup", json={
        "full_name": "User B",
        "email": email_b,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    token_b = res_b.json()["access_token"]

    # Manually create a private job owned by User A
    job_id = f"test-job-{uuid.uuid4().hex[:6]}"
    private_job = JobModel(
        id=job_id,
        user_id=user_a_id,
        is_demo=False,
        original_filename="user_a_secret_clip.mp4",
        input_path="storage/sample_placeholder.mp4",
        status="uploaded"
    )
    db.add(private_job)
    db.commit()

    # User A can access own job
    get_res_a = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_res_a.status_code == 200

    # User B CANNOT access User A's job -> 403 Forbidden
    get_res_b = client.get(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_res_b.status_code == 403

    # Unauthenticated user cannot access private job -> 401
    client.cookies.clear()
    get_res_anon = client.get(f"/api/jobs/{job_id}")
    assert get_res_anon.status_code == 401

    # User B CANNOT delete User A's job -> 403 Forbidden
    del_res_b = client.delete(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_res_b.status_code == 403

    # User A's job appears in User A's list
    list_res_a = client.get("/api/jobs", headers={"Authorization": f"Bearer {token_a}"})
    assert list_res_a.status_code == 200
    job_ids_a = [j["id"] for j in list_res_a.json()]
    assert job_id in job_ids_a

    # User A's job does NOT appear in User B's list
    list_res_b = client.get("/api/jobs", headers={"Authorization": f"Bearer {token_b}"})
    assert list_res_b.status_code == 200
    job_ids_b = [j["id"] for j in list_res_b.json()]
    assert job_id not in job_ids_b

    # Clean up test job
    db.delete(private_job)
    db.commit()
