import json
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from app.database.session import Base
from app.schemas.job import JobResponse, JobStatus, MediaMetadata, SilenceSegment
from app.schemas.edit_plan import EditPlan

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
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
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
