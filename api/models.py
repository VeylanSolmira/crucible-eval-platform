"""
API Models
Pydantic models for request/response validation.
Separated from runtime dependencies for clean schema generation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Import shared types
from shared.generated.python import EvaluationStatus

# Constants - These are duplicated here to avoid importing the main module
MAX_CODE_SIZE = 1 * 1024 * 1024  # 1MB limit
MIN_TIMEOUT = 1
MAX_TIMEOUT = 300
SUPPORTED_LANGUAGES = ["python"]


class EvaluationRequest(BaseModel):
    code: str = Field(..., description="Code to execute")
    language: str = Field("python", description="Programming language")
    engine: str = Field("docker", description="Execution engine")
    timeout: int = Field(30, description="Timeout in seconds", ge=MIN_TIMEOUT, le=MAX_TIMEOUT)
    priority: int = Field(0, description="Numeric priority (0-2000+, higher = more important)")
    memory_limit: Optional[str] = Field(None, description="Memory limit (e.g., 128Mi, 512Mi, 1Gi)")
    cpu_limit: Optional[str] = Field(None, description="CPU limit (e.g., 100m, 500m, 1)")
    executor_image: Optional[str] = Field(None, description="Executor image name (e.g., 'python-base') or full image path")
    debug: bool = Field(False, description="Preserve pod for debugging if it fails")
    expect_failure: bool = Field(False, description="If True, job will use backoffLimit=0 (no retries)")
    
    @validator('code')
    def validate_code_size(cls, v):
        """Validate code size to prevent DoS attacks."""
        if len(v.encode('utf-8')) > MAX_CODE_SIZE:
            raise ValueError(f"Code size exceeds maximum allowed size of {MAX_CODE_SIZE} bytes")
        if not v.strip():
            raise ValueError("Code cannot be empty")
        return v
    
    @validator('language')
    def validate_language(cls, v):
        """Validate that language is supported."""
        if v.lower() not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language '{v}' is not supported. Supported languages: {', '.join(SUPPORTED_LANGUAGES)}")
        return v.lower()
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout is within acceptable range."""
        if v < MIN_TIMEOUT:
            raise ValueError(f"Timeout must be at least {MIN_TIMEOUT} seconds")
        if v > MAX_TIMEOUT:
            raise ValueError(f"Timeout cannot exceed {MAX_TIMEOUT} seconds")
        return v


class EvaluationSubmitResponse(BaseModel):
    eval_id: str
    status: EvaluationStatus = EvaluationStatus.QUEUED
    message: str = "Evaluation queued for processing"
    queue_position: Optional[int] = None


class BatchEvaluationRequest(BaseModel):
    evaluations: List[EvaluationRequest]


class BatchEvaluationResponse(BaseModel):
    evaluations: List[EvaluationSubmitResponse]
    total: int
    queued: int
    failed: int


class EvaluationStatusResponse(BaseModel):
    eval_id: str
    status: EvaluationStatus
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: str = ""
    error: str = ""
    success: bool = False


class QueueStatusResponse(BaseModel):
    queued: int = 0
    processing: int = 0
    queue_length: int = 0
    total_tasks: int = 0
    error: Optional[str] = None


class ServiceHealthInfo(BaseModel):
    gateway: str = "healthy"
    queue: str = "healthy"
    storage: str = "healthy"
    executor: str = "healthy"


class StatusResponse(BaseModel):
    platform: str = "healthy"
    mode: str = "microservices"
    services: ServiceHealthInfo
    queue: QueueStatusResponse
    storage: Dict[str, Any] = {}
    celery: Optional[Dict[str, Any]] = None
    version: str = "2.0.0"


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str
    services: ServiceHealthInfo