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
    
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("UserModel", back_populates="jobs")

    def to_response(self) -> JobResponse:
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

        return JobResponse(
            id=self.id,
            user_id=self.user_id,
            is_demo=bool(self.is_demo),
            status=JobStatus(self.status),
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
            output_available=bool(self.output_path and self.status == JobStatus.COMPLETED.value),
            processing_time_seconds=self.processing_time_seconds
        )
