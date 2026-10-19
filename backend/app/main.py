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
from app.api.endpoints.auth import router as auth_router

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
app.include_router(auth_router, prefix="/api", tags=["Auth"])
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(capabilities_router, prefix="/api", tags=["Capabilities"])
app.include_router(jobs_router, prefix="/api", tags=["Jobs"])

# Check for built frontend static assets (for Docker / Unified Cloud deployment)
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
STATIC_DIR = BASE_DIR / "static"
dist_dir = FRONTEND_DIST if (FRONTEND_DIST / "index.html").exists() else (STATIC_DIR if (STATIC_DIR / "index.html").exists() else None)

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
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
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
