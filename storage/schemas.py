"""
Pydantic schemas for API serialization.

These schemas define the contract between backend and frontend.
FastAPI uses these to:
1. Validate request/response data
2. Generate OpenAPI documentation
3. Enable TypeScript type generation
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# Enums
class EvaluationStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Base schemas
class EvaluationBase(BaseModel):
    """Base fields for evaluation."""

    status: str = Field(..., description="Current status of the evaluation")
    engine: Optional[str] = Field(None, description="Execution engine used")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Request schemas
class EvaluationCreate(BaseModel):
    """Request body for creating an evaluation."""

    code: str = Field(..., description="Python code to execute")

    class Config:
        json_schema_extra = {"example": {"code": "print('Hello, World!')"}}


# Response schemas
class EvaluationResponse(EvaluationBase):
    """Full evaluation response with all fields."""

    id: str
    code_hash: str
    created_at: datetime
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    runtime_ms: Optional[int] = None
    memory_used_mb: Optional[int] = None
    exit_code: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
    output_size_bytes: Optional[int] = None

    class Config:
        from_attributes = True  # Allow creating from SQLAlchemy models
        json_schema_extra = {
            "example": {
                "id": "eval_123abc",
                "code_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00Z",
                "runtime_ms": 1234,
                "output": "Hello, World!",
            }
        }


class EvaluationSummary(BaseModel):
    """Summary view for listing evaluations."""

    id: str
    status: str
    created_at: datetime
    runtime_ms: Optional[int] = None
    engine: Optional[str] = None

    class Config:
        from_attributes = True


class EvaluationCreateResponse(BaseModel):
    """Response after creating an evaluation."""

    eval_id: str = Field(..., description="Unique evaluation ID")
    status: str = Field(..., description="Initial status (usually 'queued')")
    message: str = Field(..., description="Human-readable status message")

    class Config:
        json_schema_extra = {
            "example": {
                "eval_id": "eval_123abc",
                "status": "queued",
                "message": "Evaluation queued for processing",
            }
        }


class EvaluationStatusResponse(BaseModel):
    """Response for evaluation status check."""

    eval_id: str
    status: str
    result: Optional[Dict[str, Any]] = Field(None, description="Evaluation result if completed")
    events: List["EvaluationEvent"] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "eval_id": "eval_123abc",
                "status": "completed",
                "result": {"id": "eval_123abc", "status": "completed", "output": "Hello, World!"},
                "events": [],
            }
        }


# Event schemas
class EvaluationEvent(BaseModel):
    """Event in evaluation lifecycle."""

    id: Optional[int] = None
    evaluation_id: str
    timestamp: datetime
    event_type: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Metric schemas
class EvaluationMetric(BaseModel):
    """Performance metric for an evaluation."""

    id: Optional[int] = None
    evaluation_id: str
    metric_name: str
    metric_value: float
    timestamp: datetime
    unit: Optional[str] = None

    class Config:
        from_attributes = True


# Queue status schemas
class QueueStats(BaseModel):
    """Queue statistics."""

    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    workers: int = 0


class EvaluationStats(BaseModel):
    """Evaluation statistics."""

    total: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)


class QueueStatusResponse(BaseModel):
    """Queue status response."""

    queue: QueueStats
    evaluations: EvaluationStats

    class Config:
        json_schema_extra = {
            "example": {
                "queue": {"queued": 5, "running": 2, "completed": 100, "failed": 3, "workers": 4},
                "evaluations": {
                    "total": 110,
                    "by_status": {"queued": 5, "running": 2, "completed": 100, "failed": 3},
                },
            }
        }


# Platform status schemas
class PlatformStatusResponse(BaseModel):
    """Platform health and status."""

    healthy: bool
    platform: str
    version: str
    engine: str
    uptime: Optional[float] = None
    queue_status: Optional[QueueStatusResponse] = None

    class Config:
        json_schema_extra = {
            "example": {
                "healthy": True,
                "platform": "QueuedEvaluationPlatform",
                "version": "1.0.0",
                "engine": "Docker (Containerized - Network isolated)",
                "uptime": 3600.0,
            }
        }


# List response with pagination
class EvaluationListResponse(BaseModel):
    """Paginated list of evaluations."""

    evaluations: List[EvaluationSummary]
    total: int
    limit: int
    offset: int

    class Config:
        json_schema_extra = {
            "example": {
                "evaluations": [
                    {
                        "id": "eval_123",
                        "status": "completed",
                        "created_at": "2024-01-01T00:00:00Z",
                        "runtime_ms": 1234,
                    }
                ],
                "total": 100,
                "limit": 10,
                "offset": 0,
            }
        }


# Error response
class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None
    path: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Evaluation not found",
                "detail": "No evaluation with ID 'eval_xyz' exists",
                "path": "/api/evaluations/eval_xyz",
            }
        }
