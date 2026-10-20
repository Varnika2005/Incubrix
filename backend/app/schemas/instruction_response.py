import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class InstructionStatus(str, Enum):
    APPLIED = "APPLIED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECTED = "REJECTED"

class InstructionOutcome(BaseModel):
    status: InstructionStatus = Field(..., description="Strict 3-way outcome: APPLIED, NEEDS_CLARIFICATION, or REJECTED")
    instruction: str = Field(..., description="Original user editing instruction")
    operation: Optional[Dict[str, Any]] = Field(default=None, description="Normalized operation payload")
    message: str = Field(..., description="Explanation, question for clarification, or rejection reason")
    operationId: str = Field(default_factory=lambda: f"op_{uuid.uuid4().hex[:12]}", description="Unique operation identifier")
    operation_id: Optional[str] = Field(default=None, description="Snake_case alias for operationId")
    timeline: Optional[Dict[str, Any]] = Field(default=None, description="Transformed timeline state if applied")
    clarification_prompt: Optional[str] = Field(default=None, description="Specific follow-up question when clarification is needed")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code if rejected or needs clarification")
    rollback_performed: bool = Field(default=False, description="True if operation failed midway and rollback was executed")
    time_reference: Optional[str] = Field(default=None, description="Resolved timestamp policy: 'timeline' or 'source'")
    converted_timestamps: Optional[Dict[str, Any]] = Field(default=None, description="Timestamp conversion mappings between timeline and source")
    options: Optional[List[str]] = Field(default=None, description="Selectable options for clarification")
    candidate_matches: Optional[List[Dict[str, Any]]] = Field(default=None, description="Candidate transcript passages with timestamps and confidence scores")
    parts: Optional[List[Dict[str, Any]]] = Field(default=None, description="Detailed outcomes for each sub-instruction in a multi-part instruction")
    warnings: Optional[List[str]] = Field(default=None, description="Operational warnings or notices (e.g. caption removed, speed readability adjusted)")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.operation_id:
            self.operation_id = self.operationId

class ProcessInstructionRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=1000, description="Natural language editing instruction or command")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional explicit pre-normalized parameters")
    time_reference: Optional[str] = Field(default=None, description="Explicit timestamp policy: 'timeline' or 'source'")
    simulate_failure: bool = Field(default=False, description="For testing: simulate midway engine failure to verify rollback")
    transcript: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional transcript for semantic search")
