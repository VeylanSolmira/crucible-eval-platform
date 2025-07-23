"""
Storage Service Models
Pydantic models for request/response validation.
Separated from runtime dependencies for clean schema generation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# Import shared types
from shared.generated.python import EvaluationStatus


# Request/Response models
class EvaluationCreate(BaseModel):
    id: str = Field(..., description="Evaluation ID")
    code: str = Field(..., description="Code to be evaluated")
    language: str = Field(default="python", description="Programming language")
    status: str = Field(default=EvaluationStatus.QUEUED.value, description="Initial status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EvaluationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="New status")
    output: Optional[str] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata to merge")
    # Celery-specific fields
    celery_task_id: Optional[str] = Field(None, description="Celery task ID if using Celery")
    retries: Optional[int] = Field(None, description="Number of retry attempts")
    final_failure: Optional[bool] = Field(None, description="Whether task failed after all retries")
    # Executor fields for real-time tracking
    executor_id: Optional[str] = Field(None, description="ID of executor running this evaluation")
    container_id: Optional[str] = Field(None, description="Docker container ID")


class EvaluationResponse(BaseModel):
    id: str
    code: Optional[str] = None
    language: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    output_truncated: bool = False
    error_truncated: bool = False
    runtime_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Storage info (only included when requested)
    storage_info: Optional[Dict[str, Any]] = Field(None, exclude=True)


class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class EventCreate(BaseModel):
    type: str = Field(..., description="Event type")
    message: str = Field(..., description="Event message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class EventResponse(BaseModel):
    type: str
    timestamp: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StatisticsResponse(BaseModel):
    total_evaluations: int
    by_status: Dict[str, int]
    by_language: Dict[str, int]
    average_runtime_ms: Optional[float] = None
    success_rate: float
    last_24h_count: int
    peak_hour: Optional[str] = None
    storage_info: Dict[str, Any] = Field(default_factory=dict)


class StorageInfoResponse(BaseModel):
    primary_backend: str
    fallback_backend: Optional[str] = None
    cache_enabled: bool
    large_output_storage: str = Field(description="Where outputs >100KB are stored")
    storage_thresholds: Dict[str, int]
    backends_available: List[str]


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    storage_available: bool
    redis_available: bool


class RunningEvaluationInfo(BaseModel):
    eval_id: str
    started_at: str
    executor_id: Optional[str] = None
    container_id: Optional[str] = None
    job_name: Optional[str] = None


class RunningEvaluationsResponse(BaseModel):
    running_evaluations: List[RunningEvaluationInfo]
    count: int