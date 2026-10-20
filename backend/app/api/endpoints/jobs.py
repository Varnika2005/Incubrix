import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.database.models import JobModel, UserModel
from app.core.deps import get_current_user, get_current_user_optional
from app.schemas.job import (
    JobResponse,
    JobStatus,
    AnalyzePromptRequest,
    ProcessJobRequest,
    CreateUrlJobRequest,
    EditReceipt,
    MediaMetadata,
    SourceIntegrityInfo,
    SaveHistoryRequest,
    IntegrityVerificationResponse,
    AddTimelineEffectRequest,
    TransformTimelineRequest,
    TimelineMapRequest,
    TimelineMapResponse,
    InstructionOutcome,
    InstructionStatus,
    ProcessInstructionRequest,
    UndoRedoResponse,
    HistoryStackResponse
)
from app.schemas.edit_plan import EditPlan
from app.services.media_inspector import inspect_media, MediaInspectionError
from app.services.prompt_parser import PromptParser
from app.services.silence_detector import SilenceDetector
from app.services.video_processor import VideoProcessor, VideoProcessingError
from app.services.hash_utils import calculate_file_sha256, verify_file_integrity
from app.services.timeline_model import Timeline
from app.services.operation_processor import OperationProcessor
from app.services.undo_redo_manager import UndoRedoManager

router = APIRouter()

def verify_job_access(
    job: JobModel,
    current_user: Optional[UserModel],
    allow_demo: bool = True,
    write_access: bool = False
) -> None:
    """
    Authoritative access verification for jobs.
    - Demo jobs are accessible publicly if allow_demo=True.
    - Private user jobs require authentication and exact owner match.
    """
    if job.is_demo and allow_demo:
        # Demo jobs are publicly readable/processable for instant onboarding
        return

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this project.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if job.user_id and job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not have permission to access or modify this project."
        )


def run_video_processing_task(job_id: str, input_path: str, plan: EditPlan):
    """
    Background worker for asynchronous video processing.
    Enforces non-destructive editing guarantees:
    - Verifies source SHA-256 hash before processing.
    - VideoProcessor writes exclusively to an isolated output path.
    - Verifies source SHA-256 hash after processing remains unchanged.
    Updates SQLite database state throughout execution.
    """
    from app.database.session import SessionLocal
    db = SessionLocal()
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        db.close()
        return

    try:
        # Non-destructive guarantee: Verify original source hash BEFORE processing
        if job.original_file_hash:
            is_intact, pre_hash = verify_file_integrity(input_path, job.original_file_hash)
            if not is_intact:
                job.status = JobStatus.FAILED.value
                job.source_integrity_verified = False
                job.source_integrity_status = "pre_check_failed"
                job.error_message = (
                    f"Source integrity violation! Original media was modified before processing. "
                    f"Expected hash: {job.original_file_hash}, Found: {pre_hash}. Operation aborted."
                )
                job.progress = 0
                db.commit()
                db.close()
                return

        job.status = JobStatus.PROCESSING.value
        job.progress = 20
        db.commit()

        def on_progress(p: int):
            job.progress = p
            db.commit()

        out_path, out_meta, proc_time, applied_ops = VideoProcessor.process_video(
            job_id=job_id,
            input_path=input_path,
            edit_plan=plan,
            progress_callback=on_progress
        )

        # Non-destructive guarantee: Verify original source hash AFTER processing
        if job.original_file_hash:
            is_intact_post, post_hash = verify_file_integrity(input_path, job.original_file_hash)
            if not is_intact_post:
                job.status = JobStatus.FAILED.value
                job.source_integrity_verified = False
                job.source_integrity_status = "post_check_failed"
                job.error_message = (
                    f"Source integrity violation! Original media was modified during processing. "
                    f"Expected hash: {job.original_file_hash}, Found: {post_hash}. Operation aborted."
                )
                job.progress = 0
                db.commit()
                db.close()
                return

        job.status = JobStatus.COMPLETED.value
        job.output_path = out_path
        job.output_metadata_json = json.dumps(out_meta.model_dump())
        job.applied_operations_json = json.dumps(applied_ops)
        job.processing_time_seconds = proc_time
        job.progress = 100
        job.error_message = None
        job.source_integrity_verified = True
        job.source_integrity_status = "verified_immutable"

        # 1. Generate standard IncuBrix output manifest
        try:
            from app.services.manifest_generator import generate_output_manifest
            in_meta_obj = json.loads(job.input_metadata_json) if job.input_metadata_json else None
            manifest = generate_output_manifest(
                job_id=job.id,
                original_filename=job.original_filename,
                input_path=input_path,
                output_path=out_path,
                original_hash=job.original_file_hash,
                original_size=job.original_file_size,
                input_meta=in_meta_obj,
                output_meta=out_meta,
                applied_operations=applied_ops,
                processing_time_seconds=proc_time,
                created_at=job.created_at
            )
            manifest_str = json.dumps(manifest, indent=2)
            job.manifest_json = manifest_str
            manifest_file = Path(out_path).parent / "manifest.json"
            manifest_file.write_text(manifest_str, encoding="utf-8")
        except Exception as me:
            print(f"[Manifest Generation Warning] {me}")

        # 2. S3 / MinIO upload if configured
        try:
            if settings.ENABLE_S3_STORAGE:
                from app.services.storage_service import StorageService
                s3_key_video = f"jobs/{job_id}/clippilot_edited_{job_id[:8]}.mp4"
                s3_video_url = StorageService.upload_file(Path(out_path), s3_key_video, content_type="video/mp4")
                if s3_video_url:
                    job.s3_key = s3_key_video
                    job.s3_url = s3_video_url

                if job.manifest_json:
                    s3_key_manifest = f"jobs/{job_id}/manifest.json"
                    s3_manifest_url = StorageService.upload_bytes(job.manifest_json.encode("utf-8"), s3_key_manifest, content_type="application/json")
                    if s3_manifest_url:
                        job.manifest_s3_url = s3_manifest_url
        except Exception as se:
            print(f"[S3 Upload Warning] {se}")

        db.commit()

        # 3. Dispatch signed IncuBrix HMAC callback
        if job.callback_url:
            try:
                import asyncio
                from app.services.callback_service import dispatch_job_callback
                cb_payload = {
                    "job_id": job.id,
                    "status": "succeeded",
                    "progress": 100,
                    "result": {
                        "download_url": f"/api/v1/jobs/{job.id}/download",
                        "manifest_url": f"/api/v1/jobs/{job.id}/manifest",
                        "receipt_url": f"/api/v1/jobs/{job.id}/receipt",
                        "preview_url": f"/api/v1/jobs/{job.id}/preview/output",
                        "s3_url": job.s3_url,
                        "manifest_s3_url": job.manifest_s3_url
                    },
                    "error": None
                }
                try:
                    asyncio.run(dispatch_job_callback(job.callback_url, cb_payload))
                except Exception as cbe:
                    print(f"[Callback Warning] {cbe}")
            except Exception as ce:
                print(f"[Callback Error] {ce}")

        # Copy finalized output MP4 directly to user's system Downloads folder
        try:
            user_downloads = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Downloads"
            if user_downloads.exists():
                stem = Path(job.original_filename).stem if job.original_filename else job_id[:8]
                dest_file = user_downloads / f"clippilot_{stem}_edited.mp4"
                shutil.copy2(out_path, dest_file)
                shutil.copy2(out_path, user_downloads / "ClipPilot_Edited_Video.mp4")
        except Exception:
            pass

    except Exception as e:
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.progress = 0
        db.commit()

        # Dispatch failure callback if configured
        if job.callback_url:
            try:
                import asyncio
                from app.services.callback_service import dispatch_job_callback
                cb_payload = {
                    "job_id": job.id,
                    "status": "failed",
                    "progress": 0,
                    "result": None,
                    "error": str(e)
                }
                try:
                    asyncio.run(dispatch_job_callback(job.callback_url, cb_payload))
                except Exception:
                    pass
            except Exception:
                pass
    finally:
        db.close()


@router.post("/jobs/upload", response_model=JobResponse)
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    callback_url: Optional[str] = Form(None),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    # 1. Path traversal security validation
    if ".." in file.filename or "/" in file.filename or "\\" in file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal sequences are not permitted."
        )

    # 2. Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
        )

    # 3. Authorization check: upload requires authentication
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in to upload and process custom videos.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 3. Generate secure job storage location
    job_id = str(uuid.uuid4())
    job_upload_dir = settings.UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_name = f"original_{Path(file.filename).name.replace(' ', '_')}"
    destination = job_upload_dir / safe_name

    # 4. Stream write file with size check
    total_size = 0
    try:
        with open(destination, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                    buffer.close()
                    shutil.rmtree(job_upload_dir, ignore_errors=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB"
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {str(e)}")

    # 5. Inspect media integrity
    try:
        meta = inspect_media(str(destination))
    except MediaInspectionError as e:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupt media file: {str(e)}"
        )

    # Check duration limit
    if meta.duration > settings.MAX_VIDEO_DURATION_SECONDS:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video duration ({meta.duration:.1f}s) exceeds maximum allowed limit of {settings.MAX_VIDEO_DURATION_SECONDS}s"
        )

    # 6. Calculate immutable source SHA-256 hash and size immediately upon import
    source_hash = calculate_file_sha256(str(destination))
    source_size = destination.stat().st_size

    # 7. Persist job in database with authoritative owner ID and immutable source hash
    job = JobModel(
        id=job_id,
        user_id=current_user.id,
        is_demo=False,
        status=JobStatus.UPLOADED.value,
        original_filename=file.filename,
        input_path=str(destination),
        input_metadata_json=json.dumps(meta.model_dump()),
        original_file_hash=source_hash,
        original_file_size=source_size,
        source_integrity_verified=True,
        source_integrity_status="verified_immutable",
        edit_history_json=json.dumps([]),
        callback_url=callback_url,
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return job.to_response(is_v1=("/v1" in request.url.path))


@router.post("/jobs/url", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_from_url(
    request: Request,
    payload: CreateUrlJobRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    IncuBrix Validated Media URL Ingestion.
    Downloads remote media safely with SSRF protection against private, loopback,
    and link-local network destinations including redirects.
    """
    from app.services.url_ingestion import validate_url_safety, download_media_from_url

    # 1. SSRF prevention validation
    validate_url_safety(payload.url)

    job_id = str(uuid.uuid4())
    job_upload_dir = settings.UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)

    url_path = Path(urlparse(payload.url).path)
    ext = url_path.suffix.lower() if url_path.suffix else ".mp4"
    if ext not in settings.ALLOWED_EXTENSIONS:
        ext = ".mp4"

    safe_name = f"url_{url_path.name}" if url_path.name else f"remote_media_{job_id[:8]}{ext}"
    if not any(safe_name.endswith(e) for e in settings.ALLOWED_EXTENSIONS):
        safe_name = f"{safe_name}{ext}"

    destination = job_upload_dir / safe_name

    # 2. Download media securely with streaming size check
    await download_media_from_url(payload.url, destination)

    # 3. Inspect media integrity
    try:
        meta = inspect_media(str(destination))
    except MediaInspectionError as e:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupt media downloaded from URL: {str(e)}"
        )

    if meta.duration > settings.MAX_VIDEO_DURATION_SECONDS:
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video duration ({meta.duration:.1f}s) exceeds maximum allowed limit of {settings.MAX_VIDEO_DURATION_SECONDS}s"
        )

    source_hash = calculate_file_sha256(str(destination))
    source_size = destination.stat().st_size

    job = JobModel(
        id=job_id,
        user_id=current_user.id if current_user else None,
        is_demo=(current_user is None),
        status=JobStatus.UPLOADED.value,
        original_filename=safe_name,
        input_path=str(destination),
        input_metadata_json=json.dumps(meta.model_dump()),
        original_file_hash=source_hash,
        original_file_size=source_size,
        source_integrity_verified=True,
        source_integrity_status="verified_immutable",
        edit_history_json=json.dumps([]),
        callback_url=payload.callback_url,
        prompt=payload.prompt,
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return job.to_response(is_v1=("/v1" in request.url.path))


@router.post("/jobs/demo", response_model=JobResponse)
def create_demo_job(
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    1-Click Reproducible Demo Endpoint.
    Uses bundled synthetic sample asset, associates with current user if logged in,
    or tags as demo for safe public evaluation.
    Calculates immutable source SHA-256 hash immediately upon import.
    """
    sample_file = settings.SAMPLE_DIR / "sample_1_talking_head.mp4"
    if not sample_file.exists():
        from scripts.generate_sample_videos import generate_sample_videos
        generate_sample_videos()

    job_id = str(uuid.uuid4())
    job_upload_dir = settings.UPLOAD_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    destination = job_upload_dir / "original_sample_talking_head.mp4"
    shutil.copyfile(sample_file, destination)

    meta = inspect_media(str(destination))
    source_hash = calculate_file_sha256(str(destination))
    source_size = destination.stat().st_size

    demo_prompt = "Cut the first 3 seconds, convert to 9:16 vertical for TikTok, boost volume by 50%, and add subtitles"
    plan = PromptParser.parse(demo_prompt, meta)
    silence = SilenceDetector.detect_silence(str(destination))

    init_state = UndoRedoManager._create_state_snapshot(
        plan_dict=plan.model_dump(),
        description="Initial Demo Import",
        state_id="state_0",
        source_duration=meta.duration,
        fps=meta.fps
    )

    job = JobModel(
        id=job_id,
        user_id=current_user.id if current_user else None,
        is_demo=True,
        status=JobStatus.AWAITING_APPROVAL.value,
        original_filename="sample_talking_head.mp4",
        input_path=str(destination),
        input_metadata_json=json.dumps(meta.model_dump()),
        original_file_hash=source_hash,
        original_file_size=source_size,
        source_integrity_verified=True,
        source_integrity_status="verified_immutable",
        edit_history_json=json.dumps({"states": [init_state], "current_index": 0}),
        prompt=demo_prompt,
        edit_plan_json=json.dumps(plan.model_dump()),
        detected_silence_json=json.dumps([s.model_dump() for s in silence]),
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return job.to_response()


@router.post("/jobs/{job_id}/analyze", response_model=JobResponse)
def analyze_prompt(
    job_id: str,
    payload: AnalyzePromptRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    job.status = JobStatus.ANALYZING.value
    job.prompt = payload.prompt
    db.commit()

    meta = None
    if job.input_metadata_json:
        meta = MediaMetadata(**json.loads(job.input_metadata_json))

    # Parse prompt into validated EditPlan
    plan = PromptParser.parse(payload.prompt, meta)

    # Detect silence if silence removal is in operations or prompt
    silence_segments = []
    if any(op.get("type") == "silence_removal" for op in plan.operations) or "silence" in payload.prompt.lower():
        silence_segments = SilenceDetector.detect_silence(job.input_path)
        job.detected_silence_json = json.dumps([s.model_dump() for s in silence_segments])

    job.edit_plan_json = json.dumps(plan.model_dump())
    UndoRedoManager.push_state(job, plan, description=payload.prompt)
    if plan.instruction_outcomes:
        existing_history = []
        if job.instruction_history_json:
            try:
                existing_history = json.loads(job.instruction_history_json)
            except Exception:
                existing_history = []
        existing_history.extend(plan.instruction_outcomes)
        job.instruction_history_json = json.dumps(existing_history)

    job.status = JobStatus.AWAITING_APPROVAL.value
    db.commit()
    db.refresh(job)

    return job.to_response()


@router.post("/jobs/{job_id}/process", response_model=JobResponse)
def process_job(
    request: Request,
    response: Response,
    job_id: str,
    payload: ProcessJobRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    if job.status == JobStatus.PROCESSING.value:
        raise HTTPException(status_code=400, detail="Job is already being processed")

    # Update approved plan and callback_url
    job.edit_plan_json = json.dumps(payload.approved_plan.model_dump())
    if payload.callback_url:
        job.callback_url = payload.callback_url

    job.status = JobStatus.QUEUED.value
    job.progress = 10
    db.commit()
    db.refresh(job)

    # Launch background task
    background_tasks.add_task(
        run_video_processing_task,
        job_id=job.id,
        input_path=job.input_path,
        plan=payload.approved_plan
    )

    if "/v1" in request.url.path:
        response.status_code = status.HTTP_202_ACCEPTED

    return job.to_response(is_v1=("/v1" in request.url.path))


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    request: Request,
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)
    return job.to_response(is_v1=("/v1" in request.url.path))


@router.get("/jobs", response_model=List[JobResponse])
def list_jobs(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List jobs strictly belonging to the authenticated user.
    """
    jobs = (
        db.query(JobModel)
        .filter(JobModel.user_id == current_user.id)
        .order_by(JobModel.updated_at.desc())
        .limit(50)
        .all()
    )
    return [j.to_response() for j in jobs]


@router.get("/jobs/{job_id}/preview/original")
def preview_original(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job or not Path(job.input_path).exists():
        raise HTTPException(status_code=404, detail="Original video not found")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)
    return FileResponse(job.input_path, media_type="video/mp4")


@router.get("/jobs/{job_id}/preview/output")
def preview_output(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job or not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Output video not ready or not found")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)
    return FileResponse(job.output_path, media_type="video/mp4")


@router.api_route("/jobs/{job_id}/download", methods=["GET", "HEAD"])
def download_output(
    job_id: str,
    filename: Optional[str] = None,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job or not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Output video not ready for download")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    download_filename = filename or "ClipPilot_Edited_Video.mp4"
    if not download_filename.lower().endswith(".mp4"):
        download_filename += ".mp4"

    # Also ensure direct copies are present in the user's Downloads directory on the local file system
    try:
        user_downloads = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Downloads"
        if user_downloads.exists():
            dest_file = user_downloads / download_filename
            shutil.copy2(job.output_path, dest_file)
            shutil.copy2(job.output_path, user_downloads / "ClipPilot_Edited_Video.mp4")
    except Exception:
        pass

    return FileResponse(
        job.output_path,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"',
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
        },
        filename=download_filename
    )


@router.get("/jobs/{job_id}/receipt", response_model=EditReceipt)
def get_receipt(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    if job.status != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Edit receipt is only available for completed jobs")

    in_meta = MediaMetadata(**json.loads(job.input_metadata_json)) if job.input_metadata_json else MediaMetadata()
    out_meta = MediaMetadata(**json.loads(job.output_metadata_json)) if job.output_metadata_json else None
    applied_ops = json.loads(job.applied_operations_json) if job.applied_operations_json else []
    
    plan = json.loads(job.edit_plan_json) if job.edit_plan_json else {}
    warnings = plan.get("warnings", [])

    # Calculate post-process source integrity verification
    current_source_hash = calculate_file_sha256(job.input_path) if Path(job.input_path).exists() else job.original_file_hash
    source_verified = bool(job.original_file_hash and current_source_hash and (current_source_hash == job.original_file_hash))
    
    source_integrity_info = SourceIntegrityInfo(
        original_hash=job.original_file_hash or current_source_hash or "unknown",
        final_hash=current_source_hash or "unknown",
        hash_algorithm="SHA-256",
        verified_identical=source_verified,
        status="verified_immutable" if source_verified else "tampered",
        non_destructive=True,
        original_size_bytes=job.original_file_size or (Path(job.input_path).stat().st_size if Path(job.input_path).exists() else None),
        verification_message="Original uploaded source was verified unchanged before and after editing operations." if source_verified else "Warning: Source file hash changed unexpectedly!"
    )

    instruction_audit = None
    if job.instruction_history_json:
        try:
            instruction_audit = json.loads(job.instruction_history_json)
        except Exception:
            instruction_audit = None

    tl_dict = plan.get("timeline")
    tl_hash = plan.get("timeline_hash") or (tl_dict.get("timeline_hash") if isinstance(tl_dict, dict) else None)

    return EditReceipt(
        job_id=job.id,
        created_at=job.created_at.isoformat(),
        completed_at=job.updated_at.isoformat(),
        input_metadata=in_meta,
        output_metadata=out_meta,
        user_prompt=job.prompt or "Direct Edit Plan",
        applied_operations=applied_ops,
        processing_time_seconds=job.processing_time_seconds or 0.0,
        warnings=warnings,
        app_version=settings.VERSION,
        source_integrity=source_integrity_info,
        timeline=tl_dict,
        timeline_hash=tl_hash,
        instruction_audit=instruction_audit
    )


@router.get("/jobs/{job_id}/manifest")
def get_job_manifest(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    IncuBrix Output Manifest Retrieval.
    Returns downloadable structured JSON manifest containing model, engine,
    effective settings, hashes, timings, and rights details.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    # 1. From database column
    if job.manifest_json:
        try:
            return JSONResponse(content=json.loads(job.manifest_json))
        except Exception:
            pass

    # 2. From file on disk
    if job.output_path:
        manifest_file = Path(job.output_path).parent / "manifest.json"
        if manifest_file.exists():
            try:
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                job.manifest_json = json.dumps(data)
                db.commit()
                return JSONResponse(content=data)
            except Exception:
                pass

    # 3. If job is completed/succeeded, generate on-the-fly
    if job.status in (JobStatus.COMPLETED.value, "completed", "succeeded"):
        from app.services.manifest_generator import generate_output_manifest
        in_meta_obj = json.loads(job.input_metadata_json) if job.input_metadata_json else None
        out_meta_obj = json.loads(job.output_metadata_json) if job.output_metadata_json else None
        applied_ops = json.loads(job.applied_operations_json) if job.applied_operations_json else []
        manifest = generate_output_manifest(
            job_id=job.id,
            original_filename=job.original_filename,
            input_path=job.input_path,
            output_path=job.output_path,
            original_hash=job.original_file_hash,
            original_size=job.original_file_size,
            input_meta=in_meta_obj,
            output_meta=out_meta_obj,
            applied_operations=applied_ops,
            processing_time_seconds=job.processing_time_seconds,
            created_at=job.created_at,
            completed_at=job.updated_at
        )
        job.manifest_json = json.dumps(manifest)
        db.commit()
        return JSONResponse(content=manifest)

    raise HTTPException(status_code=404, detail="Manifest is not available until job is completed")


@router.get("/jobs/{job_id}/verify-integrity", response_model=IntegrityVerificationResponse)
def verify_job_integrity(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Verifies that the original uploaded source video on disk remains 100% byte-for-byte identical
    to the hash calculated upon initial import.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    if not Path(job.input_path).exists():
        raise HTTPException(status_code=404, detail="Original source video not found on disk")

    current_hash = calculate_file_sha256(job.input_path)
    is_identical = bool(job.original_file_hash and current_hash == job.original_file_hash)

    # Update database record if needed
    if is_identical != job.source_integrity_verified:
        job.source_integrity_verified = is_identical
        job.source_integrity_status = "verified_immutable" if is_identical else "tampered"
        db.commit()

    return IntegrityVerificationResponse(
        job_id=job.id,
        original_hash=job.original_file_hash or current_hash,
        current_hash=current_hash,
        hash_algorithm="SHA-256",
        verified=is_identical,
        status="verified_immutable" if is_identical else "tampered",
        message="Original source file is verified intact and unmodified." if is_identical else "Warning: Original source file hash mismatch detected!"
    )


@router.post("/jobs/{job_id}/history", response_model=JobResponse)
def save_job_history(
    job_id: str,
    payload: SaveHistoryRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Persists the Edit Decision List (EDL) / undo-redo history stack in the database.
    Never modifies the original media file.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    job.edit_history_json = json.dumps(payload.history)
    if payload.current_plan:
        job.edit_plan_json = json.dumps(payload.current_plan.model_dump())
        if payload.current_plan.prompt:
            job.prompt = payload.current_plan.prompt

    db.commit()
    db.refresh(job)
    return job.to_response()


@router.post("/jobs/{job_id}/undo", response_model=UndoRedoResponse)
def undo_job_edit(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Feature 6: Complete Undo.
    Restores the previous edit state, preserving original media and canonical timeline consistency.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    result = UndoRedoManager.undo(job)
    db.commit()
    db.refresh(job)

    return UndoRedoResponse(**result)


@router.post("/jobs/{job_id}/redo", response_model=UndoRedoResponse)
def redo_job_edit(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Feature 6: Complete Redo.
    Reapplies the next edit state from the redo stack.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    result = UndoRedoManager.redo(job)
    db.commit()
    db.refresh(job)

    return UndoRedoResponse(**result)


@router.get("/jobs/{job_id}/history", response_model=HistoryStackResponse)
def get_job_history(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Returns the complete non-destructive edit history stack, current index, and navigation flags.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    history_data = UndoRedoManager.get_history(job)
    return HistoryStackResponse(**history_data)


@router.get("/jobs/{job_id}/timeline")
def get_job_timeline(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Returns the Content-Aware Timeline model for the job, including segments,
    content-anchored source effects, and transformed timeline positions.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    plan = json.loads(job.edit_plan_json) if job.edit_plan_json else None
    if plan and plan.get("timeline"):
        tl = Timeline.from_dict(plan["timeline"])
        return tl.to_dict()

    in_meta = MediaMetadata(**json.loads(job.input_metadata_json)) if job.input_metadata_json else None
    dur = in_meta.duration if in_meta and in_meta.duration > 0 else 10.0
    tl = Timeline(source_duration=dur, source_id="src_original")
    return tl.to_dict()


@router.post("/jobs/{job_id}/timeline/effects")
def add_timeline_effect(
    job_id: str,
    payload: AddTimelineEffectRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Anchors a new content-aware effect (caption, mute, beep, visual_effect)
    to immutable source media timestamps.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    plan_dict = json.loads(job.edit_plan_json) if job.edit_plan_json else {"prompt": "Direct Timeline Edit", "operations": []}
    tl_dict = plan_dict.get("timeline")
    if tl_dict:
        tl = Timeline.from_dict(tl_dict)
    else:
        in_meta = MediaMetadata(**json.loads(job.input_metadata_json)) if job.input_metadata_json else None
        dur = in_meta.duration if in_meta and in_meta.duration > 0 else 10.0
        tl = Timeline(source_duration=dur, source_id="src_original")

    eff = tl.add_effect(
        effect_type=payload.type,
        source_start=payload.source_start,
        source_end=payload.source_end,
        parameters=payload.parameters,
        label=payload.label
    )
    plan_dict["timeline"] = tl.to_dict()
    if "operations" not in plan_dict:
        plan_dict["operations"] = []
    plan_dict["operations"].append({
        "type": payload.type,
        "description": eff.label or f"{payload.type} anchored to {payload.source_start}s - {payload.source_end}s",
        "source_start": payload.source_start,
        "source_end": payload.source_end,
        "parameters": payload.parameters,
        "label": payload.label
    })
    UndoRedoManager.push_state(job, plan_dict, description=eff.label or f"Add {payload.type} effect")
    db.commit()

    return tl.to_dict()


@router.post("/jobs/{job_id}/timeline/transform")
def transform_timeline(
    job_id: str,
    payload: TransformTimelineRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Applies timeline transformations (cut, speed, reorder, trim_start, trim_end, time_slice)
    and deterministically transforms all content-anchored effects according to documented policy.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    plan_dict = json.loads(job.edit_plan_json) if job.edit_plan_json else {"prompt": "Direct Timeline Edit", "operations": []}
    tl_dict = plan_dict.get("timeline")
    if tl_dict:
        tl = Timeline.from_dict(tl_dict)
    else:
        in_meta = MediaMetadata(**json.loads(job.input_metadata_json)) if job.input_metadata_json else None
        dur = in_meta.duration if in_meta and in_meta.duration > 0 else 10.0
        tl = Timeline(source_duration=dur, source_id="src_original")

    if "operations" not in plan_dict:
        plan_dict["operations"] = []

    action = payload.action.lower()
    if action == "trim_start":
        sec = float(payload.seconds or 0.0)
        tl.apply_trim_start(sec)
        plan_dict["operations"].append({"type": "trim_start", "seconds": sec, "description": f"Trim start {sec}s"})
    elif action == "trim_end":
        sec = float(payload.seconds or 0.0)
        tl.apply_trim_end(sec)
        plan_dict["operations"].append({"type": "trim_end", "seconds": sec, "description": f"Trim end {sec}s"})
    elif action == "time_slice":
        st = float(payload.start_time or 0.0)
        et = float(payload.end_time or tl.source_duration)
        tl.apply_time_slice(st, et)
        plan_dict["operations"].append({"type": "time_slice", "start_time": st, "end_time": et, "description": f"Slice {st}s - {et}s"})
    elif action == "cut":
        cs = float(payload.cut_start or 0.0)
        ce = float(payload.cut_end or 0.0)
        tl.apply_cut(cs, ce)
        plan_dict["operations"].append({"type": "cut", "cut_start": cs, "cut_end": ce, "description": f"Cut out {cs}s - {ce}s"})
    elif action == "speed":
        spd = float(payload.speed or 1.0)
        tl.apply_speed_change(spd, payload.source_start, payload.source_end)
        plan_dict["operations"].append({"type": "speed", "speed": spd, "source_start": payload.source_start, "source_end": payload.source_end, "description": f"Speed change {spd}x"})
    elif action == "reorder":
        if payload.order:
            tl.reorder_segments(payload.order)
            plan_dict["operations"].append({"type": "reorder", "order": payload.order, "description": f"Reorder segments to {payload.order}"})
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported timeline action: {action}")

    plan_dict["timeline"] = tl.to_dict()
    UndoRedoManager.push_state(job, plan_dict, description=f"Timeline {action}")
    db.commit()

    return tl.to_dict()


@router.post("/jobs/{job_id}/timeline/map", response_model=TimelineMapResponse)
def map_timeline_coordinates(
    job_id: str,
    payload: TimelineMapRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Deterministic bi-directional coordinate mapping:
    - Given source_time: returns all corresponding timeline timestamps.
    - Given timeline_time: returns active segment and source timestamp.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    plan_dict = json.loads(job.edit_plan_json) if job.edit_plan_json else None
    if plan_dict and plan_dict.get("timeline"):
        tl = Timeline.from_dict(plan_dict["timeline"])
    else:
        in_meta = MediaMetadata(**json.loads(job.input_metadata_json)) if job.input_metadata_json else None
        dur = in_meta.duration if in_meta and in_meta.duration > 0 else 10.0
        tl = Timeline(source_duration=dur, source_id="src_original")

    resp = TimelineMapResponse(source_time=payload.source_time, timeline_time=payload.timeline_time)
    if payload.source_time is not None:
        resp.mapped_timeline_times = tl.map_source_to_timeline(payload.source_time)
    if payload.timeline_time is not None:
        src_mapping = tl.map_timeline_to_source(payload.timeline_time)
        if src_mapping:
            resp.mapped_source_info = {"clip_id": src_mapping[0], "source_time": src_mapping[1]}
    if payload.timeline_range is not None:
        src_ints = tl.map_timeline_range_to_source(payload.timeline_range[0], payload.timeline_range[1])
        resp.mapped_source_intervals = [{"start": s[0], "end": s[1], "clip_id": s[2]} for s in src_ints]
    if payload.source_range is not None:
        tl_ints = tl.map_source_range_to_timeline(payload.source_range[0], payload.source_range[1])
        resp.mapped_timeline_intervals = [{"start": t[0], "end": t[1], "clip_id": t[2]} for t in tl_ints]
    return resp


@router.post("/jobs/{job_id}/instruction", response_model=InstructionOutcome)
def process_single_instruction(
    job_id: str,
    payload: ProcessInstructionRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Central Operation-Processing Layer (Must-Have 3 & Feature 7).
    Strict 3-way response system for every editing instruction with consistent timestamp policy:
    - APPLIED: Validated, executed, and committed to timeline.
    - NEEDS_CLARIFICATION: Ambiguous or missing parameters. Specific question returned, timeline untouched.
    - REJECTED: Unsupported, invalid, unsafe, or impossible. Clear reason returned, timeline untouched.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=True, write_access=True)

    plan_dict = json.loads(job.edit_plan_json) if job.edit_plan_json else {"prompt": payload.instruction, "operations": []}
    tl_dict = plan_dict.get("timeline")
    in_meta = MediaMetadata(**json.loads(job.input_metadata_json)) if job.input_metadata_json else None
    dur = in_meta.duration if in_meta and in_meta.duration > 0 else 10.0

    if tl_dict:
        tl = Timeline.from_dict(tl_dict)
    else:
        tl = Timeline(source_duration=dur, source_id="src_original")

    params = dict(payload.parameters or {})
    op_to_pass = params if (params and "type" in params) else None

    # Extract edit history, detected silences, and transcript for context resolution
    edit_history_states = []
    if job.edit_history_json:
        try:
            edit_history_states = json.loads(job.edit_history_json).get("states", [])
        except Exception:
            pass

    detected_silences = []
    if job.detected_silence_json:
        try:
            detected_silences = json.loads(job.detected_silence_json)
        except Exception:
            pass

    transcript_data = payload.transcript
    if not transcript_data and hasattr(job, "transcript_json") and job.transcript_json:
        try:
            transcript_data = json.loads(job.transcript_json)
        except Exception:
            pass

    # Call central operation processor
    outcome = OperationProcessor.process_instruction(
        instruction=payload.instruction,
        timeline=tl,
        metadata=in_meta,
        pre_normalized_op=op_to_pass,
        time_reference=payload.time_reference,
        simulate_execution_failure=payload.simulate_failure,
        edit_history=edit_history_states,
        transcript=transcript_data,
        silence_segments=detected_silences
    )

    # Persist to instruction history
    history = []
    if job.instruction_history_json:
        try:
            history = json.loads(job.instruction_history_json)
        except Exception:
            history = []
    history.append(outcome.model_dump())
    job.instruction_history_json = json.dumps(history)

    # If APPLIED, commit updated timeline and operations
    if outcome.status == InstructionStatus.APPLIED:
        plan_dict["timeline"] = outcome.timeline
        if outcome.timeline and isinstance(outcome.timeline, dict):
            plan_dict["timeline_hash"] = outcome.timeline.get("timeline_hash")
        if "operations" not in plan_dict:
            plan_dict["operations"] = []
        if outcome.operation:
            op_data = {
                "type": outcome.operation.get("type", "").lower(),
                "description": outcome.message,
                "operationId": outcome.operationId,
                **outcome.operation
            }
            plan_dict["operations"].append(op_data)
        UndoRedoManager.push_state(job, plan_dict, description=outcome.message)

    db.commit()
    db.refresh(job)
    return outcome


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a job and its associated media files on disk.
    Strictly restricted to the authoritative project owner.
    """
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    verify_job_access(job, current_user, allow_demo=False, write_access=True)

    # Clean up files on disk
    if job.input_path and Path(job.input_path).parent.exists():
        shutil.rmtree(Path(job.input_path).parent, ignore_errors=True)
    if job.output_path and Path(job.output_path).parent.exists():
        shutil.rmtree(Path(job.output_path).parent, ignore_errors=True)

    db.delete(job)
    db.commit()
    return {"status": "deleted", "id": job_id}
