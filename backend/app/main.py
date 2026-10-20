import os
import sys
import uuid
import yaml
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.core.logging_config import setup_logging, correlation_id_ctx
from app.core.idempotency import IdempotencyMiddleware
from app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.database.session import init_db
from app.services.ffmpeg_finder import FFmpegFinder
from app.api.endpoints.health import router as health_router
from app.api.endpoints.capabilities import router as capabilities_router
from app.api.endpoints.jobs import router as jobs_router
from app.api.endpoints.auth import router as auth_router

# Setup structured logging
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables and initial buckets are created
    init_db()
    # Verify FFmpeg
    is_ok, ffmpeg_ver, _ = FFmpegFinder.verify()
    if is_ok:
        print(f"[ClipPilot Backend] FFmpeg verified: {ffmpeg_ver[:50]}")
    else:
        print(f"[ClipPilot Backend WARNING] FFmpeg not found: {ffmpeg_ver}")

    # Initialize S3 bucket if enabled
    if settings.ENABLE_S3_STORAGE:
        try:
            from app.services.storage_service import StorageService
            StorageService.get_s3_client()
        except Exception as e:
            print(f"[ClipPilot Backend S3] Storage init warning: {e}")

    yield
    # Shutdown
    print("[ClipPilot Backend] Shutting down gracefully.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Prompt-to-Video Editing Studio Engine — IncuBrix Container Integration",
    lifespan=lifespan
)

# 1. Correlation ID Middleware (X-Correlation-ID)
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = correlation_id_ctx.set(corr_id)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id
        return response
    finally:
        correlation_id_ctx.reset(token)

# 2. Idempotency Middleware for Safe Retries
app.add_middleware(IdempotencyMiddleware)

# 3. CORS configuration
safe_cors_origins = [origin for origin in settings.CORS_ORIGINS if origin.strip() and origin.strip() != "*"]
if not safe_cors_origins:
    safe_cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=safe_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length", "Accept-Ranges", "X-Correlation-ID", "X-Idempotent-Replay"],
)

# 4. Consistent JSON Exception Handlers (Requirement 5)
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# 5. Root Liveness & Readiness Probes (Requirement 8)
app.include_router(health_router, tags=["Health"])

# 6. IncuBrix Documented API Routes under /api/v1/ (Requirement 2)
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(capabilities_router, prefix="/api/v1", tags=["Capabilities"])
app.include_router(jobs_router, prefix="/api/v1", tags=["Jobs"])

# 7. Backward-Compatible Routes under /api (Existing Frontend & Tests)
app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(capabilities_router, prefix="/api", tags=["Capabilities"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])

# 8. OpenAPI 3.1 YAML Specification Endpoint (Requirement 2)
@app.get("/api/v1/openapi.yaml", include_in_schema=False)
@app.get("/openapi.yaml", include_in_schema=False)
def get_openapi_yaml():
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        description=app.description,
        routes=app.routes,
    )
    yaml_content = yaml.dump(schema, sort_keys=False, allow_unicode=True)
    return Response(content=yaml_content, media_type="text/yaml")

# 9. Static Frontend Asset Serving
possible_dist_dirs = [
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
    Path(__file__).resolve().parent.parent / "frontend" / "dist",
    Path("/app/frontend/dist"),
    Path(__file__).resolve().parent.parent.parent / "static",
]
dist_dir = next((p for p in possible_dist_dirs if (p / "index.html").exists()), None)

if dist_dir:
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    if (dist_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(dist_dir / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if (
            full_path.startswith("api")
            or full_path.startswith("docs")
            or full_path.startswith("openapi")
            or full_path.startswith("health")
            or full_path.startswith("ready")
        ):
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Endpoint '/{full_path}' not found.",
                        "retryable": False,
                        "details": {}
                    }
                }
            )
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "openapi_yaml": "/api/v1/openapi.yaml",
            "health": "/health",
            "ready": "/ready",
            "api_v1_jobs": "/api/v1/jobs"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
