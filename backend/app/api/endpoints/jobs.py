import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
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
    EditReceipt,
    MediaMetadata
)
from app.schemas.edit_plan import EditPlan
from app.services.media_inspector import inspect_media, MediaInspectionError
from app.services.prompt_parser import PromptParser
from app.services.silence_detector import SilenceDetector
from app.services.video_processor import VideoProcessor, VideoProcessingError

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
    Updates SQLite database state throughout execution.
    """
    from app.database.session import SessionLocal
    db = SessionLocal()
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        db.close()
        return

    try:
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

        job.status = JobStatus.COMPLETED.value
        job.output_path = out_path
        job.output_metadata_json = json.dumps(out_meta.model_dump())
        job.applied_operations_json = json.dumps(applied_ops)
        job.processing_time_seconds = proc_time
        job.progress = 100
        job.error_message = None
        db.commit()

    except Exception as e:
        job.status = JobStatus.FAILED.value
        job.error_message = str(e)
        job.progress = 0
        db.commit()
    finally:
        db.close()


@router.post("/jobs/upload", response_model=JobResponse)
async def upload_video(
    file: UploadFile = File(...),
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

    # 6. Persist job in database with authoritative owner ID
    job = JobModel(
        id=job_id,
        user_id=current_user.id,
        is_demo=False,
        status=JobStatus.UPLOADED.value,
        original_filename=file.filename,
        input_path=str(destination),
        input_metadata_json=json.dumps(meta.model_dump()),
        progress=0
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return job.to_response()


@router.post("/jobs/demo", response_model=JobResponse)
def create_demo_job(
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    1-Click Reproducible Demo Endpoint.
    Uses bundled synthetic sample asset, associates with current user if logged in,
    or tags as demo for safe public evaluation.
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
    demo_prompt = "Cut the first 3 seconds, convert to 9:16 vertical for TikTok, boost volume by 50%, and add subtitles"
    plan = PromptParser.parse(demo_prompt, meta)
    silence = SilenceDetector.detect_silence(str(destination))

    job = JobModel(
        id=job_id,
        user_id=current_user.id if current_user else None,
        is_demo=True,
        status=JobStatus.AWAITING_APPROVAL.value,
        original_filename="sample_talking_head.mp4",
        input_path=str(destination),
        input_metadata_json=json.dumps(meta.model_dump()),
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
    job.status = JobStatus.AWAITING_APPROVAL.value
    db.commit()
    db.refresh(job)

    return job.to_response()


@router.post("/jobs/{job_id}/process", response_model=JobResponse)
def process_job(
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

    # Update approved plan and queue job
    job.edit_plan_json = json.dumps(payload.approved_plan.model_dump())
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

    return job.to_response()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)
    return job.to_response()


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


@router.get("/jobs/{job_id}/download")
def download_output(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job or not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(status_code=404, detail="Output video not ready for download")
    
    verify_job_access(job, current_user, allow_demo=True, write_access=False)

    download_filename = f"clippilot_{Path(job.original_filename).stem}_edited.mp4"
    return FileResponse(
        job.output_path,
        media_type="video/mp4",
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
        app_version=settings.VERSION
    )


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
