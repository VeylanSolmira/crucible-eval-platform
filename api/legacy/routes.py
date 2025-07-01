"""
FastAPI routes with Pydantic schema validation.

This module defines all API endpoints using proper request/response models.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from storage.schemas import (
    EvaluationCreate,
    EvaluationCreateResponse,
    EvaluationResponse,
    EvaluationStatusResponse,
    EvaluationListResponse,
    EvaluationSummary,
    QueueStatusResponse,
    PlatformStatusResponse
)
from storage.database import get_db
from storage.manager import StorageManager
from api.api import APIService
import uuid


# Create router
router = APIRouter(prefix="/api", tags=["evaluations"])

# We'll inject these dependencies
api_service: Optional[APIService] = None
storage_manager: Optional[StorageManager] = None


def get_storage_manager(db: AsyncSession = Depends(get_db)) -> StorageManager:
    """Dependency to get storage manager with DB session."""
    global storage_manager
    if not storage_manager:
        storage_manager = StorageManager(db_session=db)
    else:
        storage_manager.db = db
    return storage_manager


@router.post("/evaluations", response_model=EvaluationCreateResponse)
async def create_evaluation(
    request: EvaluationCreate,
    storage: StorageManager = Depends(get_storage_manager)
):
    """Submit code for evaluation."""
    if not api_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Generate eval ID
    eval_id = f"eval_{uuid.uuid4().hex[:8]}"
    
    # Store in database
    await storage.create_evaluation(eval_id, request.code)
    
    # Submit to evaluation platform
    api_response = api_service.evaluate_code(request.code)
    
    return EvaluationCreateResponse(
        eval_id=eval_id,
        status="queued",
        message="Evaluation queued for processing"
    )


@router.get("/evaluations/{eval_id}", response_model=EvaluationResponse)
async def get_evaluation(
    eval_id: str = Path(..., description="Evaluation ID"),
    storage: StorageManager = Depends(get_storage_manager)
):
    """Get full evaluation details."""
    evaluation_data = await storage.get_evaluation(eval_id)
    
    if not evaluation_data:
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation {eval_id} not found"
        )
    
    return EvaluationResponse(**evaluation_data)


@router.get("/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status: Optional[str] = Query(None, description="Filter by status"),
    storage: StorageManager = Depends(get_storage_manager)
):
    """List evaluations with pagination."""
    evaluations = await storage.list_evaluations(
        limit=limit,
        offset=offset,
        status=status
    )
    
    # Get total count (simplified for now)
    total = len(evaluations) + offset  # This is approximate
    
    return EvaluationListResponse(
        evaluations=[EvaluationSummary(**e) for e in evaluations],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/queue-status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get current queue statistics."""
    if not api_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    queue_data = api_service.get_queue_status()
    
    # Transform to match schema
    return QueueStatusResponse(
        queue=queue_data.get('queue', {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'workers': 0
        }),
        evaluations=queue_data.get('evaluations', {
            'total': 0,
            'by_status': {}
        })
    )


@router.get("/status", response_model=PlatformStatusResponse)
async def get_platform_status():
    """Get platform health and status."""
    if not api_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    status_data = api_service.get_platform_status()
    
    # Get queue status for nested field
    queue_status = api_service.get_queue_status()
    
    return PlatformStatusResponse(
        healthy=status_data.get('healthy', False),
        platform=status_data.get('platform', 'Unknown'),
        version=status_data.get('version', '0.0.0'),
        engine=status_data.get('engine', 'Unknown'),
        uptime=status_data.get('uptime'),
        queue_status=QueueStatusResponse(
            queue=queue_status.get('queue', {}),
            evaluations=queue_status.get('evaluations', {})
        )
    )


# Legacy endpoints for backward compatibility
@router.post("/eval", response_model=EvaluationCreateResponse)
async def create_evaluation_legacy(
    request: dict,
    storage: StorageManager = Depends(get_storage_manager)
):
    """Legacy evaluation endpoint."""
    if 'code' not in request:
        raise HTTPException(status_code=400, detail="Missing 'code' field")
    
    return await create_evaluation(
        EvaluationCreate(code=request['code']),
        storage
    )


@router.get("/eval-status/{eval_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status_legacy(
    eval_id: str,
    storage: StorageManager = Depends(get_storage_manager)
):
    """Legacy status check endpoint."""
    evaluation_data = await storage.get_evaluation(eval_id)
    
    if not evaluation_data:
        raise HTTPException(status_code=404, detail=f"Evaluation {eval_id} not found")
    
    # Transform to legacy format
    return EvaluationStatusResponse(
        eval_id=eval_id,
        status=evaluation_data['status'],
        result={
            'id': evaluation_data['id'],
            'status': evaluation_data['status'],
            'output': evaluation_data.get('output'),
            'error': evaluation_data.get('error')
        },
        events=[]  # TODO: Load actual events
    )


def set_api_service(service: APIService):
    """Set the API service instance (called from app startup)."""
    global api_service
    api_service = service