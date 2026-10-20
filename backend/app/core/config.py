import os
from pathlib import Path
from typing import List, Optional
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
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    API_V1_PREFIX: str = "/api/v1"
    LEGACY_API_PREFIX: str = "/api"

    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "clippilot-insecure-dev-secret-key-change-in-production-min32")
    CALLBACK_SECRET: str = os.getenv("CALLBACK_SECRET", os.getenv("SECRET_KEY", "clippilot-callback-secret-key-2026"))
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    REMEMBER_ME_EXPIRE_DAYS: int = int(os.getenv("REMEMBER_ME_EXPIRE_DAYS", "30"))

    # Storage Paths
    STORAGE_DIR: Path = STORAGE_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    OUTPUT_DIR: Path = OUTPUT_DIR
    TEMP_DIR: Path = TEMP_DIR
    SAMPLE_DIR: Path = SAMPLE_DIR

    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{STORAGE_DIR / 'clippilot.db'}")

    # S3 / MinIO Object Storage
    ENABLE_S3_STORAGE: bool = os.getenv("ENABLE_S3_STORAGE", "false").lower() in ("true", "1", "yes")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "clippilot")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_PUBLIC_URL_PREFIX: Optional[str] = os.getenv("S3_PUBLIC_URL_PREFIX", None)

    # Media Limits & Validation
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "250"))
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "250")) * 1024 * 1024
    MAX_URL_DOWNLOAD_SIZE_BYTES: int = int(os.getenv("MAX_URL_DOWNLOAD_SIZE_MB", "250")) * 1024 * 1024
    MAX_VIDEO_DURATION_SECONDS: float = float(os.getenv("MAX_DURATION_SECONDS", "600.0"))
    ALLOWED_EXTENSIONS: set = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

    # Timeouts
    URL_FETCH_TIMEOUT_SECONDS: float = float(os.getenv("URL_FETCH_TIMEOUT_SECONDS", "30.0"))
    PROCESSING_TIMEOUT_SECONDS: float = float(os.getenv("PROCESSING_TIMEOUT_SECONDS", "600.0"))
    IDEMPOTENCY_EXPIRY_HOURS: int = int(os.getenv("IDEMPOTENCY_EXPIRY_HOURS", "24"))

    # Processing Defaults
    DEFAULT_VIDEO_CODEC: str = os.getenv("DEFAULT_VIDEO_CODEC", "libx264")
    DEFAULT_AUDIO_CODEC: str = os.getenv("DEFAULT_AUDIO_CODEC", "aac")
    DEFAULT_PRESET: str = os.getenv("DEFAULT_PRESET", "fast")
    DEFAULT_CRF: int = int(os.getenv("DEFAULT_CRF", "22"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

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
