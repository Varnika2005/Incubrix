import os
from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from app.core.config import settings
from app.database.session import SessionLocal
from app.services.ffmpeg_finder import FFmpegFinder

router = APIRouter()

@router.get("/health")
def health_check():
    """Liveness probe: reports whether the service process is alive."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/ready")
def readiness_check(response: Response):
    """
    Readiness probe: verifies essential dependencies are functional:
    - Database connection
    - Storage directories writable
    - FFmpeg executable available
    - S3 / MinIO connectivity if enabled
    """
    checks = {}
    is_ready = True

    # 1. Database Check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = {"status": "ok"}
    except Exception as e:
        is_ready = False
        checks["database"] = {"status": "error", "message": str(e)}

    # 2. Local Storage Writable Check
    try:
        test_file = settings.TEMP_DIR / f".readiness_test_{os.getpid()}"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        checks["storage"] = {"status": "ok", "path": str(settings.STORAGE_DIR)}
    except Exception as e:
        is_ready = False
        checks["storage"] = {"status": "error", "message": str(e)}

    # 3. FFmpeg Check
    try:
        is_ok, ver, _ = FFmpegFinder.verify()
        if is_ok:
            checks["ffmpeg"] = {"status": "ok", "version": ver[:50]}
        else:
            is_ready = False
            checks["ffmpeg"] = {"status": "error", "message": ver}
    except Exception as e:
        is_ready = False
        checks["ffmpeg"] = {"status": "error", "message": str(e)}

    # 4. S3 Object Storage (if enabled)
    if settings.ENABLE_S3_STORAGE:
        try:
            from app.services.storage_service import StorageService
            client = StorageService.get_s3_client()
            if client:
                checks["s3_storage"] = {"status": "ok", "bucket": settings.S3_BUCKET_NAME}
            else:
                checks["s3_storage"] = {"status": "degraded", "message": "S3 enabled but client not connected"}
        except Exception as e:
            checks["s3_storage"] = {"status": "error", "message": str(e)}

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }
