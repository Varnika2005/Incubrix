import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.database.session import init_db
from app.services.ffmpeg_finder import FFmpegFinder
from app.api.endpoints.health import router as health_router
from app.api.endpoints.capabilities import router as capabilities_router
from app.api.endpoints.jobs import router as jobs_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database tables are created
    init_db()
    # Verify FFmpeg
    is_ok, ffmpeg_ver, _ = FFmpegFinder.verify()
    if is_ok:
        print(f"[ClipPilot Backend] FFmpeg verified: {ffmpeg_ver[:50]}")
    else:
        print(f"[ClipPilot Backend WARNING] FFmpeg not found: {ffmpeg_ver}")
    yield
    # Shutdown
    print("[ClipPilot Backend] Shutting down gracefully.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Prompt-to-Video Editing Studio Engine — PS2 IncuBrix Submission",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers under /api
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(capabilities_router, prefix="/api", tags=["Capabilities"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "api_health": "/api/health",
        "api_capabilities": "/api/capabilities",
        "jobs": "/api/jobs"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
