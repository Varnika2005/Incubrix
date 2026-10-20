import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base
from app.schemas.job import JobResponse, JobStatus, MediaMetadata, SilenceSegment
from app.schemas.edit_plan import EditPlan

def utc_now():
    return datetime.now(timezone.utc)

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    jobs = relationship("JobModel", back_populates="owner", cascade="all, delete-orphan")

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    is_demo = Column(Boolean, default=False, nullable=False)

    status = Column(String(32), default=JobStatus.UPLOADED.value, nullable=False)
    original_filename = Column(String(255), nullable=False)
    input_path = Column(String(512), nullable=False)
    output_path = Column(String(512), nullable=True)
    prompt = Column(Text, nullable=True)
    
    # JSON-encoded fields
    input_metadata_json = Column(Text, nullable=True)
    output_metadata_json = Column(Text, nullable=True)
    edit_plan_json = Column(Text, nullable=True)
    detected_silence_json = Column(Text, nullable=True)
    applied_operations_json = Column(Text, nullable=True)
    
    # Non-destructive source tracking & persistent edit history
    original_file_hash = Column(String(64), nullable=True)
    original_file_size = Column(Integer, nullable=True)
    edit_history_json = Column(Text, nullable=True)
    instruction_history_json = Column(Text, nullable=True)
    source_integrity_verified = Column(Boolean, default=True)
    source_integrity_status = Column(String(64), default="verified_immutable")
    
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)

    # IncuBrix Integration fields
    callback_url = Column(String(512), nullable=True)
    manifest_json = Column(Text, nullable=True)
    s3_key = Column(String(512), nullable=True)
    s3_url = Column(String(512), nullable=True)
    manifest_s3_url = Column(String(512), nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("UserModel", back_populates="jobs")

    def to_response(self, is_v1: bool = False) -> JobResponse:
        in_meta = None
        if self.input_metadata_json:
            try:
                in_meta = MediaMetadata(**json.loads(self.input_metadata_json))
            except Exception:
                pass

        out_meta = None
        if self.output_metadata_json:
            try:
                out_meta = MediaMetadata(**json.loads(self.output_metadata_json))
            except Exception:
                pass

        plan = None
        if self.edit_plan_json:
            try:
                plan = EditPlan(**json.loads(self.edit_plan_json))
            except Exception:
                pass

        silence = None
        if self.detected_silence_json:
            try:
                silence_list = json.loads(self.detected_silence_json)
                silence = [SilenceSegment(**s) for s in silence_list]
            except Exception:
                pass

        history = None
        if self.edit_history_json:
            try:
                raw_hist = json.loads(self.edit_history_json)
                if isinstance(raw_hist, dict) and "states" in raw_hist:
                    history = raw_hist["states"]
                elif isinstance(raw_hist, list):
                    history = raw_hist
            except Exception:
                pass

        timeline = None
        if plan and plan.timeline:
            timeline = plan.timeline

        instruction_history = None
        if self.instruction_history_json:
            try:
                instruction_history = json.loads(self.instruction_history_json)
            except Exception:
                pass

        # IncuBrix standard status mapping: queued, running, succeeded, or failed
        if self.status in (JobStatus.COMPLETED.value, "completed", "succeeded"):
            standard_st = "succeeded"
        elif self.status in (JobStatus.FAILED.value, "failed"):
            standard_st = "failed"
        elif self.status in (JobStatus.QUEUED.value, "queued"):
            standard_st = "queued"
        else:
            standard_st = "running"

        status_value = standard_st if is_v1 else self.status

        download_url = f"/api/v1/jobs/{self.id}/download" if self.output_path else None
        manifest_url = f"/api/v1/jobs/{self.id}/manifest" if (self.output_path or self.manifest_json) else None
        receipt_url = f"/api/v1/jobs/{self.id}/receipt"
        preview_url = f"/api/v1/jobs/{self.id}/preview/output" if self.output_path else None

        result_payload = None
        if self.output_path or self.status in (JobStatus.COMPLETED.value, "completed", "succeeded"):
            result_payload = {
                "download_url": download_url,
                "manifest_url": manifest_url,
                "receipt_url": receipt_url,
                "preview_url": preview_url,
                "s3_url": self.s3_url,
                "manifest_s3_url": self.manifest_s3_url
            }

        return JobResponse(
            id=self.id,
            job_id=self.id,
            user_id=self.user_id,
            is_demo=bool(self.is_demo),
            status=status_value,
            standard_status=standard_st,
            original_filename=self.original_filename,
            created_at=self.created_at,
            updated_at=self.updated_at,
            prompt=self.prompt,
            input_metadata=in_meta,
            output_metadata=out_meta,
            edit_plan=plan,
            detected_silence=silence,
            progress=self.progress,
            error_message=self.error_message,
            errors=[self.error_message] if self.error_message else None,
            output_available=bool(self.output_path and self.status in (JobStatus.COMPLETED.value, "completed", "succeeded")),
            processing_time_seconds=self.processing_time_seconds,
            original_file_hash=self.original_file_hash,
            original_file_size=self.original_file_size,
            source_integrity_verified=self.source_integrity_verified if self.source_integrity_verified is not None else True,
            source_integrity_status=self.source_integrity_status or "verified_immutable",
            edit_history=history,
            timeline=timeline,
            instruction_history=instruction_history,
            callback_url=self.callback_url,
            download_url=download_url,
            manifest_url=manifest_url,
            receipt_url=receipt_url,
            preview_url=preview_url,
            result=result_payload
        )

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key = Column(String(128), primary_key=True)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=False)
    response_headers = Column(Text, nullable=True)
    response_body = Column(Text, nullable=False)
    job_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
