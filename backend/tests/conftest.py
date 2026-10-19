import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend and workspace root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(WORKSPACE_DIR))

from app.main import app
from app.database.session import SessionLocal, init_db
from app.core.config import settings
from scripts.generate_sample_videos import generate_sample_videos

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    init_db()
    generate_sample_videos()
    yield

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
