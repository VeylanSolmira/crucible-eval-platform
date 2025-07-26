"""
API Service - Routes requests and handles storage
This replaces the monolithic app.py when running in microservices mode
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import httpx
import asyncio
from pathlib import Path

# Import shared types
from shared.generated.python import EvaluationStatus, EvaluationResponse

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uvicorn

# Import models
from .models import (
    EvaluationRequest,
    EvaluationSubmitResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationStatusResponse,
    QueueStatusResponse,
    StatusResponse,
    HealthResponse,
    ServiceHealthInfo
)

# Import Redis for event publishing
import redis.asyncio as redis

# Import Celery client for dual-write
from api.celery_client import submit_evaluation_to_celery, CELERY_ENABLED, cancel_celery_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Pydantic Settings
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

# Configuration using Pydantic Settings
class Settings(BaseSettings):
    model_config = ConfigDict(
        case_sensitive=False,
        # Don't load .env file - only use actual environment variables
    )
    
    queue_service_url: str
    storage_service_url: str
    dispatcher_service_url: str
    redis_url: str
    internal_api_key: str

# Create settings instance - lazy initialization for OpenAPI generation
try:
    settings = Settings()
except Exception as e:
    # During OpenAPI generation, env vars might not be set
    # Create a dummy settings object to allow schema generation
    logger.warning(f"Failed to load settings: {e}. Using defaults for OpenAPI generation.")
    settings = None

# Security validation constants
# These limits prevent DoS attacks and resource exhaustion
# Implemented as part of Week 4 security hardening
MAX_CODE_SIZE = 1 * 1024 * 1024  # 1MB limit - prevents memory exhaustion
MIN_TIMEOUT = 1  # 1 second minimum - prevents instant timeout abuse
MAX_TIMEOUT = 900  # 15 minutes maximum - prevents long-running resource locks
SUPPORTED_LANGUAGES = ["python"]  # Explicitly allowlist supported languages

# Create FastAPI app
app = FastAPI(
    title="Crucible API Gateway",
    description="Main API gateway for Crucible evaluation platform (microservices mode)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request size limiting middleware
# Provides defense-in-depth against DoS attacks by limiting total request size
# Works in conjunction with code size validation in EvaluationRequest
# Returns 413 (Request Entity Too Large) for oversized requests
class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 2 * 1024 * 1024):  # 2MB total request size
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Only apply size limit to API endpoints
        if request.url.path.startswith("/api/"):
            if request.headers.get("content-length"):
                content_length = int(request.headers["content-length"])
                if content_length > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request entity too large"}
                    )
        
        response = await call_next(request)
        return response

# Add request size limiting
app.add_middleware(RequestSizeLimitMiddleware, max_size=2 * 1024 * 1024)

# Create HTTP client factory function instead of global client
def create_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Create an HTTP client with proper headers and timeout"""
    return httpx.AsyncClient(
        headers={"X-API-Key": settings.internal_api_key} if settings.internal_api_key else {},
        timeout=timeout
    )

# Redis client will be initialized in startup event
redis_client = None

# Import resilient connection utilities
from shared.utils.resilient_connections import get_async_redis_client
from shared.utils import generate_evaluation_id

logger.info(f"Storage service URL: {settings.storage_service_url}")

# Status enum now imported from shared contracts
# See: shared/types/evaluation-status.yaml

# Models are now imported from .models module for clean schema separation
# This allows OpenAPI generation without runtime dependencies


# Health tracking
service_health = {
    "gateway": True,
    "queue": False,
    "redis": False,
    "storage": False,
    "last_check": None,
}


async def check_service_health():
    """Periodic health check of downstream services"""
    while True:
        async with create_http_client(timeout=5.0) as health_client:
            # Queue service deactivated - all traffic through Celery
            service_health["queue"] = True  # Always healthy since we're using Celery

            try:
                # Check storage service
                response = await health_client.get(f"{settings.storage_service_url}/health")
                service_health["storage"] = response.status_code == 200
            except Exception as e:
                logger.error(f"Storage health check failed: {e}")
                service_health["storage"] = False

        # Check Redis
        try:
            await redis_client.ping()
            service_health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            service_health["redis"] = False

        service_health["last_check"] = datetime.now(timezone.utc).isoformat()

        # More frequent checks during startup (first 2 minutes)
        startup_time = 120  # seconds
        if hasattr(check_service_health, "start_time"):
            elapsed = (datetime.now(timezone.utc) - check_service_health.start_time).total_seconds()
            if elapsed < startup_time:
                await asyncio.sleep(5)  # Check every 5 seconds during startup
            else:
                await asyncio.sleep(30)  # Normal 30 second interval
        else:
            check_service_health.start_time = datetime.now(timezone.utc)
            await asyncio.sleep(5)


async def check_service_health_once():
    """Run a single health check of all services"""
    async with create_http_client(timeout=5.0) as health_client:
        # Queue service deactivated - all traffic through Celery
        service_health["queue"] = True  # Always healthy since we're using Celery

        try:
            # Check storage service
            response = await health_client.get(f"{settings.storage_service_url}/health")
            service_health["storage"] = response.status_code == 200
        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            service_health["storage"] = False

    # Check Redis
    try:
        await redis_client.ping()
        service_health["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        service_health["redis"] = False

    service_health["last_check"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"Initial health check complete: {service_health}")


# Event publishing functions
async def publish_evaluation_event(channel: str, data: Dict[str, Any]):
    """Publish evaluation event to Redis"""
    try:
        message = json.dumps(data)
        await redis_client.publish(channel, message)
        logger.info(f"Published event to {channel}: {data.get('eval_id', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to publish event to {channel}: {e}")


# Background task to poll queue for completed evaluations
async def poll_completed_evaluations():
    """Poll queue service for completed evaluations and store results"""
    while True:
        try:
            # This would be replaced by proper event system in production
            # For now, we'll rely on the queue-worker to update evaluations
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error polling evaluations: {e}")
            await asyncio.sleep(30)


@app.on_event("startup")
async def startup():
    """Start background tasks"""
    global redis_client, settings
    
    # Validate settings on startup
    if settings is None:
        try:
            settings = Settings()
            logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load required settings: {e}")
            raise RuntimeError(f"Missing required environment variables: {e}")
    
    # Initialize async Redis client with retry logic
    redis_client = await get_async_redis_client(settings.redis_url)
    logger.info("Connected to async Redis for event publishing with retry logic")
    
    # Run initial health check immediately
    await check_service_health_once()

    # Then start periodic checks
    asyncio.create_task(check_service_health())
    asyncio.create_task(poll_completed_evaluations())

    # Auto-export disabled in containers due to read-only filesystem
    # To update OpenAPI spec:
    # - Locally: Run scripts/update-openapi-spec.sh
    # - CI/CD: GitHub Actions workflow generate-openapi-spec.yml creates artifacts
    # - Or: Run python api/scripts/export-openapi-spec.py

    logger.info("API Service started in microservices mode")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await redis_client.close()


@app.get("/")
async def root():
    """Root endpoint with HTML interface"""
    # For now, return simple JSON. Frontend container serves the UI
    return {
        "service": "Crucible API Service",
        "mode": "microservices",
        "version": "2.0.0",
        "endpoints": {
            "evaluate": "/api/eval",
            "evaluate_batch": "/api/eval-batch",
            "status": "/api/eval/{eval_id}",
            "evaluations": "/api/evaluations",
            "queue": "/api/queue/status",
            "platform": "/api/status",
            "statistics": "/api/statistics",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    """Gateway health check"""
    all_healthy = all(
        [service_health["gateway"], service_health["queue"], service_health["storage"]]
    )
    
    # Simple response for Kubernetes health checks
    if all_healthy:
        return {"status": "healthy"}
    else:
        # Return 503 for unhealthy state
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "services": service_health}
        )


async def _submit_evaluation(request: EvaluationRequest, eval_id: Optional[str] = None) -> EvaluationResponse:
    """Core evaluation submission logic - shared between single and batch endpoints"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")

    # Generate eval ID if not provided
    if not eval_id:
        eval_id = generate_evaluation_id()

    try:
        # Publish event for storage worker to handle - this is now "queued" since we're submitting to Celery
        await publish_evaluation_event(
            "evaluation:queued",
            {
                "eval_id": eval_id,
                "code": request.code,
                "language": request.language,
                "engine": request.engine,
                "metadata": {
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "timeout": request.timeout,
                },
            },
        )

        # Submit to Celery (100% traffic now)
        logger.info(f"Submitting to Celery with timeout={request.timeout}")
        celery_task_id = submit_evaluation_to_celery(
            eval_id=eval_id,
            code=request.code,
            language=request.language,
            priority=request.priority,
            timeout=request.timeout,
            executor_image=request.executor_image,
            memory_limit=request.memory_limit,
            cpu_limit=request.cpu_limit,
        )
        if celery_task_id:
            logger.info(f"Submitted evaluation {eval_id} to Celery: {celery_task_id}")
        else:
            logger.error(f"Failed to submit evaluation {eval_id} to Celery")
            raise HTTPException(status_code=503, detail="Failed to submit evaluation to processing queue")

        # Set a pending key in Redis with longer TTL to prevent race conditions
        # This ensures the key exists long enough for the database to be updated
        try:
            await redis_client.setex(f"pending:{eval_id}", 600, "queued")  # 10 minutes
            logger.info(f"Set pending key for {eval_id}")
        except Exception as e:
            logger.error(f"Failed to set pending key for {eval_id}: {e}")

        # Queue position not available with Celery yet
        queue_position = None

        return EvaluationSubmitResponse(
            eval_id=eval_id,
            status=EvaluationStatus.QUEUED,
            message="Evaluation queued successfully",
            queue_position=queue_position,
        )

    except httpx.HTTPError as e:
        logger.error(f"Queue service error: {e}")
        # Publish failure event
        await publish_evaluation_event("evaluation:failed", {"eval_id": eval_id, "error": str(e)})
        raise HTTPException(status_code=502, detail="Failed to queue evaluation")


async def validate_resource_limits(memory_limit: str, cpu_limit: str) -> None:
    """
    Validate that requested resources don't exceed cluster limits.
    Raises HTTPException if validation fails.
    """
    # Import resource parsing utilities
    from shared.utils.resource_parsing import parse_memory, parse_cpu
    
    # Parse requested resources
    requested_memory_mb = parse_memory(memory_limit)
    requested_cpu_mc = parse_cpu(cpu_limit)
    
    # Check with dispatcher's capacity endpoint
    async with create_http_client() as client:
        try:
            response = await client.post(
                f"{settings.dispatcher_service_url}/capacity/check",
                json={
                    "memory_limit": memory_limit,
                    "cpu_limit": cpu_limit
                }
            )
            
            if response.status_code == 200:
                capacity_data = response.json()
                
                # Check if request exceeds total cluster limits
                total_memory_mb = capacity_data.get("total_memory_mb", 0)
                total_cpu_mc = capacity_data.get("total_cpu_millicores", 0)
                
                # If request exceeds total cluster limits, reject immediately
                if requested_memory_mb > total_memory_mb:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Requested memory ({memory_limit}) exceeds total cluster limit ({total_memory_mb}MB)"
                    )
                
                if requested_cpu_mc > total_cpu_mc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Requested CPU ({cpu_limit}) exceeds total cluster limit ({total_cpu_mc}m)"
                    )
                
                # Note: We don't check available capacity here - that's for the dispatcher/scheduler
                # We only validate that the request is theoretically possible
                
        except httpx.HTTPError:
            # If we can't validate, log but don't block submission
            logger.warning("Failed to validate resource limits with dispatcher")
        except HTTPException:
            # Re-raise validation errors
            raise


@app.post("/api/eval", response_model=EvaluationSubmitResponse)
async def evaluate(request: EvaluationRequest):
    """Submit code for evaluation"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")
    
    # Validate resource limits don't exceed cluster capacity
    await validate_resource_limits(request.memory_limit, request.cpu_limit)

    # Generate eval ID and immediately acknowledge with "submitted" status
    eval_id = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    # Publish submitted event first
    await publish_evaluation_event(
        "evaluation:submitted",
        {
            "eval_id": eval_id,
            "code": request.code,
            "language": request.language,
            "engine": request.engine,
            "metadata": {
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "timeout": request.timeout,
                "priority": request.priority,
            },
        },
    )
    
    # Now attempt to queue in Celery
    try:
        return await _submit_evaluation(request, eval_id)
    except Exception as e:
        # If submission fails, update status to failed
        await publish_evaluation_event(
            "evaluation:failed", 
            {"eval_id": eval_id, "error": str(e), "failed_at": "submission"}
        )
        raise


async def _process_batch_async(evaluations: List[EvaluationRequest], eval_ids: List[str]):
    """Process batch evaluations asynchronously in the background"""
    # Rate limiting configuration
    BATCH_SIZE = 5  # Process 5 at a time
    BASE_DELAY = 0.1  # 100ms between items (10/second baseline)
    BATCH_DELAY = 0.5  # 500ms between batches
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2.0  # Exponential backoff multiplier

    # Process evaluations in sub-batches with rate limiting
    for batch_idx in range(0, len(evaluations), BATCH_SIZE):
        batch = evaluations[batch_idx:batch_idx + BATCH_SIZE]
        batch_eval_ids = eval_ids[batch_idx:batch_idx + BATCH_SIZE]
        
        for item_idx, (eval_request, eval_id) in enumerate(zip(batch, batch_eval_ids)):
            # Retry loop with exponential backoff
            retry_count = 0
            delay = BASE_DELAY
            
            while retry_count <= MAX_RETRIES:
                try:
                    # Submit to Celery
                    await _submit_evaluation(eval_request, eval_id)
                    break  # Success, exit retry loop

                except Exception as e:
                    retry_count += 1
                    if retry_count <= MAX_RETRIES:
                        backoff_delay = delay * (BACKOFF_FACTOR ** (retry_count - 1))
                        logger.warning(
                            f"Error submitting {eval_id}: {e}, "
                            f"retry {retry_count}/{MAX_RETRIES} in {backoff_delay:.2f}s"
                        )
                        await asyncio.sleep(backoff_delay)
                        continue
                    else:
                        # Max retries exceeded - publish failure event
                        logger.error(f"Failed to queue {eval_id} after {MAX_RETRIES} retries: {e}")
                        await publish_evaluation_event(
                            "evaluation:failed",
                            {
                                "eval_id": eval_id, 
                                "error": str(e), 
                                "failed_at": "batch_submission"
                            },
                        )
                        break  # Exit retry loop
            
            # Rate limit between items in batch
            if item_idx < len(batch) - 1:
                await asyncio.sleep(delay)
        
        # Delay between batches
        if batch_idx + BATCH_SIZE < len(evaluations):
            await asyncio.sleep(BATCH_DELAY)


@app.post("/api/eval-batch", response_model=BatchEvaluationResponse, status_code=202)
async def evaluate_batch(request: BatchEvaluationRequest, response: Response):
    """Submit multiple evaluations as a batch - returns immediately with 202 Accepted"""
    # Validate batch size
    MAX_BATCH_SIZE = 100
    if len(request.evaluations) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Batch size {len(request.evaluations)} exceeds maximum of {MAX_BATCH_SIZE}"
        )

    # Generate eval IDs and publish submitted events for all evaluations
    results = []
    eval_ids = []
    
    for eval_request in request.evaluations:
        eval_id = generate_evaluation_id()
        eval_ids.append(eval_id)
        
        # Publish submitted event
        await publish_evaluation_event(
            "evaluation:submitted",
            {
                "eval_id": eval_id,
                "code": eval_request.code,
                "language": eval_request.language,
                "engine": eval_request.engine,
                "metadata": {
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                    "timeout": eval_request.timeout,
                    "priority": eval_request.priority,
                    "batch": True,
                },
            },
        )
        
        # Add to results with submitted status
        results.append(
            EvaluationSubmitResponse(
                eval_id=eval_id,
                status=EvaluationStatus.SUBMITTED,
                message="Evaluation accepted for processing",
                queue_position=None,
            )
        )
    
    # Process batch asynchronously in background
    asyncio.create_task(_process_batch_async(request.evaluations, eval_ids))
    
    # Return 202 Accepted immediately
    response.status_code = 202
    return BatchEvaluationResponse(
        evaluations=results,
        total=len(request.evaluations),
        queued=0,  # None queued yet, all are submitted
        failed=0,  # No failures yet
    )



@app.get(
    "/api/eval/{eval_id}/status",
    response_model=EvaluationStatusResponse,
    responses={
        200: {
            "model": EvaluationStatusResponse,
            "description": "Evaluation found with complete status",
        },
        202: {
            "model": EvaluationStatusResponse,
            "description": "Evaluation is pending/in-progress",
        },
        404: {"description": "Evaluation not found"},
        503: {"description": "Storage service unavailable"},
    },
)
async def get_evaluation_status(eval_id: str, response: Response):
    """
    Get evaluation status - checks Redis first for real-time status, falls back to DB.
    This provides instant status updates for running evaluations.
    """
    logger.info(f"Getting evaluation status for {eval_id}")
    try:
        # First, try to get running info from Redis (real-time)
        try:
            async with create_http_client() as redis_client_http:
                response = await redis_client_http.get(
                    f"{settings.storage_service_url}/evaluations/{eval_id}/running"
                )
                if response.status_code == 200:
                    running_info = response.json()
                    # If it's in Redis, it's running
                    # Return 202 for running evaluations
                    response.status_code = 202
                    return EvaluationStatusResponse(
                        eval_id=eval_id,
                        status=EvaluationStatus.RUNNING,
                        created_at=running_info.get("started_at"),
                        completed_at=None,
                        output="",
                        error="",
                        success=False,
                    )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                logger.warning(f"Error checking Redis for {eval_id}: {e}")
            # If 404, evaluation is not in Redis (not running), continue to DB
        
        # Fall back to database for completed/failed evaluations
        logger.info(f"Evaluation {eval_id} not in Redis, checking database")
        async with create_http_client() as db_client:
            response = await db_client.get(
                f"{settings.storage_service_url}/evaluations/{eval_id}"
            )
            response.raise_for_status()
            
            eval_data = response.json()
            
            # Check pending status in Redis if not found in DB
            if eval_data.get("status") == "queued":
                try:
                    pending_status = await redis_client.get(f"pending:{eval_id}")
                    if pending_status:
                        response.status_code = 202
                except Exception as e:
                    logger.debug(f"Failed to check Redis pending status: {e}")
            
            # Return typed response
            return EvaluationStatusResponse(
                eval_id=eval_data.get("id", eval_id),
                status=eval_data.get("status", "unknown"),
                created_at=eval_data.get("created_at"),
                completed_at=eval_data.get("completed_at"),
                output=eval_data.get("output") or "",
                error=eval_data.get("error") or "",
                success=eval_data.get("status") == EvaluationStatus.COMPLETED.value,
            )
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Evaluation {eval_id} not found in database")
            raise HTTPException(status_code=404, detail="Evaluation not found")
        logger.error(f"Error fetching evaluation {eval_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch evaluation")
    except Exception as e:
        logger.error(f"Unexpected error fetching evaluation {eval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/eval/{eval_id}",
    response_model=EvaluationResponse,
    responses={
        200: {
            "model": EvaluationResponse,
            "description": "Full evaluation details including code",
        },
        404: {"description": "Evaluation not found"},
        503: {"description": "Storage service unavailable"},
    },
)
async def get_evaluation(eval_id: str):
    """
    Get full evaluation details including code, output, and all metadata.
    This endpoint returns comprehensive evaluation data from the storage service.
    """
    logger.info(f"Getting full evaluation details for {eval_id}")
    try:
        async with create_http_client() as client:
            response = await client.get(f"{settings.storage_service_url}/evaluations/{eval_id}")
            response.raise_for_status()
            
            eval_data = response.json()
            
            # Map storage service response to our detail response
            return EvaluationResponse(
                eval_id=eval_data.get("id", eval_id),
                code=eval_data.get("code", ""),
                language=eval_data.get("language", "python"),
                status=eval_data.get("status", "unknown"),
                created_at=eval_data.get("created_at"),
                started_at=eval_data.get("started_at"),
                completed_at=eval_data.get("completed_at"),
                output=eval_data.get("output", ""),
                error=eval_data.get("error", ""),
                exit_code=eval_data.get("exit_code"),
                runtime_ms=eval_data.get("runtime_ms"),
                output_truncated=eval_data.get("output_truncated", False),
                error_truncated=eval_data.get("error_truncated", False),
                metadata=eval_data.get("metadata", {}),
            )
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Evaluation {eval_id} not found")
            raise HTTPException(status_code=404, detail="Evaluation not found")
        logger.error(f"Error fetching evaluation {eval_id}: {e}")
        raise HTTPException(status_code=503, detail="Storage service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error fetching evaluation {eval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/eval/{eval_id}/status")
async def update_evaluation_status(eval_id: str, status: str, reason: Optional[str] = None):
    """Admin endpoint to manually update evaluation status"""
    if status not in ["failed", "completed", "cancelled"]:
        raise HTTPException(
            status_code=400, detail="Status must be one of: failed, completed, cancelled"
        )

    try:
        # Update in storage service (uses PUT, not PATCH)
        async with create_http_client() as update_client:
            response = await update_client.put(
                f"{settings.storage_service_url}/evaluations/{eval_id}",
                json={
                    "status": status,
                    "metadata": {
                        "admin_update": True,
                        "admin_updated_at": datetime.now(timezone.utc).isoformat(),
                        "admin_reason": reason or f"Manually set to {status}",
                        "admin_update_type": "status_change",
                    },
                },
            )

        if response.status_code == 200:
            # Publish event for other services
            await publish_evaluation_event(
                f"evaluation:{status}",
                {"eval_id": eval_id, "status": status, "manual_update": True, "reason": reason},
            )

            return {"success": True, "eval_id": eval_id, "new_status": status}
        else:
            raise HTTPException(
                status_code=response.status_code, detail=f"Storage service error: {response.text}"
            )
    except Exception as e:
        logger.error(f"Error updating evaluation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/eval/{eval_id}/logs")
async def get_evaluation_logs(eval_id: str):
    """Get logs for any evaluation - routes through storage service"""
    async with create_http_client() as client:
        try:
            # Route to storage service which handles Redis cache and DB fallback
            response = await client.get(f"{settings.storage_service_url}/evaluations/{eval_id}/logs")

            if response.status_code == 404:
                return JSONResponse(content={"error": "Evaluation not found"}, status_code=404)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Storage service returned {response.status_code} for logs")
                return JSONResponse(
                    content={"error": "Failed to get evaluation logs"},
                    status_code=response.status_code,
                )

        except Exception as e:
            logger.error(f"Failed to get evaluation logs for {eval_id}: {e}")
            return JSONResponse(content={"error": "Failed to get evaluation logs"}, status_code=500)


@app.post("/api/eval/{eval_id}/kill")
async def kill_evaluation(eval_id: str):
    """Kill a running evaluation (Kubernetes version)"""
    # Step 1: Get running info from storage to find the job name
    async with create_http_client() as client:
        try:
            response = await client.get(f"{settings.storage_service_url}/evaluations/{eval_id}/running")
            if response.status_code == 404:
                return JSONResponse(content={"error": "Evaluation not running"}, status_code=404)
            running_info = response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return JSONResponse(content={"error": "Evaluation not running"}, status_code=404)
            raise
        except Exception as e:
            logger.error(f"Failed to get running info for {eval_id}: {e}")
            return JSONResponse(
                content={"error": "Failed to get evaluation status"}, status_code=500
            )

    # Step 2: Delete the Kubernetes job through dispatcher
    job_name = running_info.get("executor_id")  # In K8s, executor_id is the job name
    if not job_name:
        return JSONResponse(content={"error": "Job name not found in running info"}, status_code=500)

    dispatcher_url = os.getenv("DISPATCHER_SERVICE_URL")
    if not dispatcher_url:
        logger.error("DISPATCHER_SERVICE_URL environment variable not set")
        return JSONResponse(
            content={"error": "Service misconfiguration: dispatcher URL not configured"}, 
            status_code=500
        )
    
    async with create_http_client() as dispatcher_client:
        try:
            # Call dispatcher to delete the job
            delete_response = await dispatcher_client.delete(f"{dispatcher_url}/job/{job_name}")
            delete_response.raise_for_status()
            
            result = delete_response.json()
            return {
                "eval_id": eval_id,
                "job_name": result.get("job_name"),
                "status": "killed",
                "message": "Evaluation job deleted successfully"
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return JSONResponse(content={"error": "Job not found"}, status_code=404)
            logger.error(f"Failed to delete job {job_name}: {e}")
            return JSONResponse(
                content={"error": f"Failed to kill evaluation: {str(e)}"}, status_code=500
            )
        except Exception as e:
            logger.error(f"Failed to delete job {job_name}: {e}")
            return JSONResponse(
                content={"error": f"Failed to kill evaluation: {str(e)}"}, status_code=500
            )


@app.post("/api/eval/{eval_id}/cancel")
async def cancel_evaluation(eval_id: str):
    """
    Cancel an evaluation in any state (Kubernetes version).
    
    Non-disjoint semantics:
    - Always works regardless of state
    - If queued: Remove from queue (if using Celery)
    - If running: Delete the Kubernetes job
    - If terminal: Return current status
    
    Handles race conditions by checking status after queue operations.
    """
    # Step 1: Get evaluation status
    async with create_http_client() as client:
        try:
            # Check if evaluation exists
            response = await client.get(f"{settings.storage_service_url}/evaluations/{eval_id}")
            if response.status_code == 404:
                return JSONResponse(content={"error": "Evaluation not found"}, status_code=404)
            
            eval_data = response.json()
            status = eval_data.get("status")
            
            # If already in terminal state, just return success
            if status in ["completed", "failed", "cancelled"]:
                return {
                    "eval_id": eval_id,
                    "status": status,
                    "message": f"Evaluation already in terminal state: {status}"
                }
                
        except Exception as e:
            logger.error(f"Failed to get evaluation info for {eval_id}: {e}")
            return JSONResponse(
                content={"error": "Failed to get evaluation status"}, status_code=500
            )

    # Step 2: If using Celery and evaluation is queued, try to cancel from queue
    if CELERY_ENABLED and status in ["submitted", "queued"]:
        try:
            result = cancel_celery_task(eval_id, terminate=True)
            if not result.get("cancelled"):
                logger.warning(f"Failed to cancel Celery task for {eval_id}: {result}")
        except Exception as e:
            logger.error(f"Error cancelling Celery task: {e}")
        
        # After Celery cancellation, check status again (race condition handling)
        try:
            response = await client.get(f"{settings.storage_service_url}/evaluations/{eval_id}")
            eval_data = response.json()
            status = eval_data.get("status")
            
            # If it transitioned to running/provisioning while we were cancelling, use kill
            if status in ["running", "provisioning"]:
                kill_response = await kill_evaluation(eval_id)
                
                # Check if it's a JSONResponse (error case)
                if isinstance(kill_response, JSONResponse):
                    if kill_response.status_code != 404:
                        logger.error(f"Kill endpoint returned error during race condition handling: {kill_response.status_code}")
                else:
                    # Success case
                    return {
                        "eval_id": eval_id,
                        "job_name": kill_response.get("job_name"),
                        "status": "cancelled",
                        "message": "Evaluation cancelled successfully (was queued, became running)"
                    }
        except Exception as e:
            logger.error(f"Error checking status after queue cancellation: {e}")
    
    # Step 3: If running/provisioning (or became running), use kill endpoint
    elif status in ["running", "provisioning"]:
        # Use our own kill endpoint for consistency
        kill_response = await kill_evaluation(eval_id)
        
        # Check if it's a JSONResponse (error case)
        if isinstance(kill_response, JSONResponse):
            # If it's a 404, the evaluation isn't running, continue to update status
            if kill_response.status_code == 404:
                logger.info(f"Evaluation {eval_id} not in running state, continuing with status update")
            else:
                # Other errors, but we'll still try to update status
                logger.error(f"Kill endpoint returned error: {kill_response.status_code}")
        else:
            # Success case - kill endpoint returned a dict
            return {
                "eval_id": eval_id,
                "job_name": kill_response.get("job_name"),
                "status": "cancelled",
                "message": "Evaluation cancelled successfully"
            }
    
    # Step 5: Update status to cancelled (if not already terminal)
    # This handles cases where: job wasn't found, job deletion failed, or evaluation was just queued
    async with create_http_client() as client:
        try:
            # Final status check to avoid overwriting terminal states
            response = await client.get(f"{settings.storage_service_url}/evaluations/{eval_id}")
            eval_data = response.json()
            current_status = eval_data.get("status")
            
            if current_status not in ["completed", "failed", "cancelled"]:
                await client.put(
                    f"{settings.storage_service_url}/evaluations/{eval_id}",
                    json={"status": "cancelled", "error": "Cancelled by user"},
                )
            
            return {
                "eval_id": eval_id,
                "status": "cancelled",
                "message": "Evaluation cancelled successfully"
            }
        except Exception as e:
            logger.error(f"Failed to update evaluation status: {e}")
            return JSONResponse(
                content={"error": "Failed to update evaluation status"}, status_code=500
            )


@app.get("/api/evaluations")
async def get_evaluations(limit: int = 100, offset: int = 0, status: Optional[str] = None):
    """Get evaluation history from storage service"""
    if not service_health["storage"]:
        return {"evaluations": [], "count": 0, "error": "Storage service unavailable"}

    try:
        # Special handling for running status - use Redis for real-time data
        if status == "running":
            async with create_http_client() as running_client:
                response = await running_client.get(f"{settings.storage_service_url}/evaluations/running")
                if response.status_code == 200:
                    data = response.json()
                    # Transform to match expected format
                    evaluations = []
                    for eval_info in data.get("running_evaluations", []):
                        # Get additional details from DB if needed
                        try:
                            async with create_http_client() as db_client:
                                db_response = await db_client.get(
                                    f"{settings.storage_service_url}/evaluations/{eval_info['eval_id']}"
                                )
                            if db_response.status_code == 200:
                                eval_data = db_response.json()
                                evaluations.append({
                                    "eval_id": eval_info['eval_id'],
                                    "status": "running",
                                    "created_at": eval_data.get("created_at"),
                                    "started_at": eval_info.get("started_at"),
                                    "executor_id": eval_info.get("executor_id"),
                                    "code_preview": (eval_data.get("code") or "")[:100] + "..."
                                    if eval_data.get("code") and len(eval_data.get("code")) > 100
                                    else (eval_data.get("code") or ""),
                                    "success": False,
                                })
                        except Exception as e:
                            logger.warning(f"Failed to get details for {eval_info['eval_id']}: {e}")
                            # Use minimal info from Redis
                            evaluations.append({
                                "eval_id": eval_info['eval_id'],
                                "status": "running",
                                "started_at": eval_info.get("started_at"),
                                "executor_id": eval_info.get("executor_id"),
                                "success": False,
                            })
                    
                    return {
                        "evaluations": evaluations,
                        "count": len(evaluations),
                        "limit": limit,
                        "offset": 0,  # Redis doesn't support pagination
                        "has_more": False,
                    }
        
        # For all other statuses, use the database
        # Build query parameters
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status

        # Proxy to storage service
        async with create_http_client() as storage_client:
            response = await storage_client.get(f"{settings.storage_service_url}/evaluations", params=params)

        if response.status_code == 200:
            data = response.json()
            # Transform response to match our API format
            return {
                "evaluations": [
                    {
                        "eval_id": e.get("id", "unknown"),
                        "status": e.get("status", "unknown"),
                        "created_at": e.get("created_at"),
                        "code_preview": (e.get("code") or "")[:100] + "..."
                        if e.get("code") and len(e.get("code")) > 100
                        else (e.get("code") or ""),
                        "success": e.get("status") == EvaluationStatus.COMPLETED.value,
                    }
                    for e in data.get("evaluations", [])
                ],
                "count": data.get("total", 0),
                "limit": limit,
                "offset": offset,
                "has_more": data.get("has_more", False),
            }
        else:
            logger.error(f"Storage service returned {response.status_code}")
            return {
                "evaluations": [],
                "count": 0,
                "error": f"Storage service error: {response.status_code}",
            }
    except Exception as e:
        logger.error(f"Error listing evaluations: {e}")
        return {"evaluations": [], "count": 0, "error": str(e)}




@app.get("/api/queue/status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get actual queue status from Celery."""
    from api.celery_client import celery_app, CELERY_ENABLED
    
    if not CELERY_ENABLED:
        return QueueStatusResponse(
            queued=0,
            processing=0,
            queue_length=0,
            total_tasks=0,
            error="Celery is not enabled"
        )
    
    try:
        # Get queue information from Celery
        inspect = celery_app.control.inspect()
        
        # Get active tasks (currently processing)
        active = inspect.active()
        active_count = sum(len(tasks) for tasks in (active or {}).values())
        
        # Get reserved tasks (queued but not yet processing)
        reserved = inspect.reserved()
        reserved_count = sum(len(tasks) for tasks in (reserved or {}).values())
        
        # Get scheduled tasks
        scheduled = inspect.scheduled()
        scheduled_count = sum(len(tasks) for tasks in (scheduled or {}).values())
        
        queued_count = reserved_count + scheduled_count
        
        return QueueStatusResponse(
            queued=queued_count,
            processing=active_count,
            queue_length=queued_count,  # Same as queued for backward compatibility
            total_tasks=queued_count + active_count,
            error=None
        )
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return QueueStatusResponse(
            queued=0,
            processing=0,
            queue_length=0,
            total_tasks=0,
            error=str(e)
        )


@app.get("/api/celery-status")
async def get_celery_status_endpoint():
    """Get Celery cluster status including workers, queues, and tasks."""
    from api.celery_client import get_celery_status, CELERY_ENABLED, celery_app

    if not CELERY_ENABLED:
        return {
            "enabled": False,
            "message": "Celery is not enabled. Set CELERY_ENABLED=true to use Celery.",
        }

    try:
        # Get basic status
        status = get_celery_status()

        # Get more detailed info if connected
        if status.get("connected"):
            inspect = celery_app.control.inspect()

            # Get active tasks
            active_tasks = inspect.active()
            active_count = sum(len(tasks) for tasks in (active_tasks or {}).values())

            # Get scheduled tasks
            scheduled_tasks = inspect.scheduled()
            scheduled_count = sum(len(tasks) for tasks in (scheduled_tasks or {}).values())

            # Get registered tasks
            registered = inspect.registered()

            # Get stats
            stats = inspect.stats()

            status.update(
                {
                    "active_tasks": active_count,
                    "scheduled_tasks": scheduled_count,
                    "registered_tasks": list(registered.values())[0] if registered else [],
                    "worker_stats": stats,
                    "queue_details": {"active": active_tasks, "scheduled": scheduled_tasks},
                }
            )

        return status

    except Exception as e:
        logger.error(f"Failed to get Celery status: {e}")
        return {"enabled": True, "connected": False, "error": str(e)}


@app.get("/api/status", response_model=StatusResponse)
async def platform_status():
    """Overall platform status"""
    queue_status = await get_queue_status()

    # Get storage stats from storage service
    storage_stats = {}
    if service_health["storage"]:
        try:
            async with create_http_client() as stats_client:
                response = await stats_client.get(f"{settings.storage_service_url}/statistics")
                if response.status_code == 200:
                    stats_data = response.json()
                    storage_stats = {
                        "total_evaluations": stats_data.get("total_evaluations", 0),
                        "by_status": stats_data.get("by_status", {}),
                        "storage_info": stats_data.get("storage_info", {}),
                    }
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")

    # Get Celery status
    celery_info = {}
    try:
        from api.celery_client import get_celery_status, CELERY_ENABLED

        if CELERY_ENABLED:
            celery_info = get_celery_status()
    except Exception as e:
        logger.error(f"Failed to get Celery status: {e}")
        celery_info = {"enabled": False, "error": str(e)}

    services = ServiceHealthInfo(
        gateway="healthy",
        queue="healthy" if service_health["queue"] else "unhealthy",
        storage="healthy" if service_health["storage"] else "unhealthy",
        executor="healthy",  # Assume healthy if queue is working
    )

    return StatusResponse(
        platform="healthy"
        if all([service_health["queue"], service_health["storage"]])
        else "degraded",
        mode="microservices",
        services=services,
        queue=queue_status,
        storage=storage_stats,
        celery=celery_info if celery_info else None,
        version="2.0.0",
    )


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = ServiceHealthInfo(
        gateway="healthy",
        queue="healthy" if service_health["queue"] else "unhealthy",
        storage="healthy" if service_health["storage"] else "unhealthy",
        executor="healthy",
    )

    return HealthResponse(
        status="ok" if all([service_health["queue"], service_health["storage"]]) else "degraded",
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
    )


# Statistics endpoint (proxy to storage service)
@app.get("/api/statistics")
async def get_statistics():
    """Get aggregated statistics from storage service"""
    if not service_health["storage"]:
        raise HTTPException(status_code=503, detail="Storage service unavailable")

    try:
        async with create_http_client() as stats_client:
            response = await stats_client.get(f"{settings.storage_service_url}/statistics")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail="Failed to get statistics")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# WebSocket for real-time updates (simplified for now)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time evaluation updates"""
    await websocket.accept()
    try:
        while True:
            # Send periodic status updates
            status = {
                "type": "status",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "services": service_health,
            }
            await websocket.send_json(status)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# OpenAPI endpoint
@app.get("/api/openapi.yaml")
async def get_openapi_spec():
    """Serve OpenAPI specification"""
    spec_path = Path(__file__).parent / "openapi.yaml"
    if spec_path.exists():
        with open(spec_path, "r") as f:
            content = f.read()
        return Response(content=content, media_type="application/yaml")
    else:
        # Return auto-generated spec
        from fastapi.openapi.utils import get_openapi

        return get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
