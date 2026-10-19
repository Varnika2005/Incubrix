import os
from pathlib import Path
from typing import List
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OUTPUT_DIR = STORAGE_DIR / "outputs"
TEMP_DIR = STORAGE_DIR / "temp"
SAMPLE_DIR = BASE_DIR / "sample_assets"

# Ensure essential directories exist
for folder in [STORAGE_DIR, UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR, SAMPLE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "ClipPilot AI"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Storage
    STORAGE_DIR: Path = STORAGE_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    OUTPUT_DIR: Path = OUTPUT_DIR
    TEMP_DIR: Path = TEMP_DIR
    SAMPLE_DIR: Path = SAMPLE_DIR
    
    DATABASE_URL: str = f"sqlite:///{STORAGE_DIR / 'clippilot.db'}"
    
    # Media Limits
    MAX_UPLOAD_SIZE_BYTES: int = 250 * 1024 * 1024  # 250 MB
    MAX_VIDEO_DURATION_SECONDS: float = 600.0  # 10 minutes
    ALLOWED_EXTENSIONS: set = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    
    # Processing
    DEFAULT_VIDEO_CODEC: str = "libx264"
    DEFAULT_AUDIO_CODEC: str = "aac"
    DEFAULT_PRESET: str = "fast"
    DEFAULT_CRF: int = 22
    
    # Security & CORS
    CORS_ORIGINS: List[str] = (
        [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
        if os.getenv("CORS_ORIGINS")
        else [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000"
        ]
    )
    
    # Optional LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

settings = Settings()
