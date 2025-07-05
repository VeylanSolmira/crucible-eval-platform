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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import shared types
from shared.generated.python import EvaluationStatus, EvaluationResponse as EvaluationDetailResponse

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Import Redis for event publishing
import redis.asyncio as redis

# Import Celery client for dual-write
from api.app.celery_client import submit_evaluation_to_celery, CELERY_ENABLED, cancel_celery_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs from environment
QUEUE_SERVICE_URL = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8082")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-api-key")

app = FastAPI(
    title="Crucible API Service (Microservices Mode)",
    description="API service for distributed Crucible platform",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create HTTP client factory function instead of global client
def create_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Create an HTTP client with proper headers and timeout"""
    return httpx.AsyncClient(
        headers={"X-API-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {},
        timeout=timeout
    )

# Initialize Redis for event publishing
redis_client = redis.from_url(REDIS_URL)
logger.info("Connected to Redis for event publishing")
logger.info(f"Storage service URL: {STORAGE_SERVICE_URL}")

# Status enum now imported from shared contracts
# See: shared/types/evaluation-status.yaml


# Request models
class EvaluationRequest(BaseModel):
    code: str
    language: str = "python"
    engine: str = "docker"
    timeout: int = 30
    priority: bool = False  # High priority flag for queue jumping


class EvaluationResponse(BaseModel):
    eval_id: str
    status: EvaluationStatus = EvaluationStatus.QUEUED
    message: str = "Evaluation queued for processing"
    queue_position: Optional[int] = None


class BatchEvaluationRequest(BaseModel):
    evaluations: List[EvaluationRequest]


class BatchEvaluationResponse(BaseModel):
    evaluations: List[EvaluationResponse]
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
                response = await health_client.get(f"{STORAGE_SERVICE_URL}/health")
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
            response = await health_client.get(f"{STORAGE_SERVICE_URL}/health")
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
            "queue": "/api/queue-status",
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

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": service_health,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _submit_evaluation(request: EvaluationRequest, eval_id: Optional[str] = None) -> EvaluationResponse:
    """Core evaluation submission logic - shared between single and batch endpoints"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")

    # Generate eval ID if not provided
    if not eval_id:
        eval_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

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
        celery_task_id = submit_evaluation_to_celery(
            eval_id=eval_id,
            code=request.code,
            language=request.language,
            priority=request.priority,
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

        return EvaluationResponse(
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


@app.post("/api/eval", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest):
    """Submit code for evaluation"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")

    # Generate eval ID and immediately acknowledge with "submitted" status
    eval_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
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
        eval_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
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
                    "batch": True,
                },
            },
        )
        
        # Add to results with submitted status
        results.append(
            EvaluationResponse(
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
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}/running"
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
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}"
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
    response_model=EvaluationDetailResponse,
    responses={
        200: {
            "model": EvaluationDetailResponse,
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
            response = await client.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}")
            response.raise_for_status()
            
            eval_data = response.json()
            
            # Map storage service response to our detail response
            return EvaluationDetailResponse(
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
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
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
            response = await client.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}/logs")

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
    """Kill a running evaluation"""
    # Step 1: Get executor assignment from storage service
    async with create_http_client() as client:
        try:
            response = await client.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}/running")
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

    # Step 2: Kill container on assigned executor
    executor_id = running_info.get("executor_id")
    if not executor_id:
        return JSONResponse(content={"error": "Invalid running information"}, status_code=500)

    executor_url = f"http://{executor_id}:8083"

    async with create_http_client() as executor_client:
        try:
            kill_response = await executor_client.post(f"{executor_url}/kill/{eval_id}")
            return kill_response.json()
        except Exception as e:
            logger.error(f"Failed to kill container on {executor_id}: {e}")
            return JSONResponse(
                content={"error": f"Failed to kill evaluation: {str(e)}"}, status_code=500
            )


@app.post("/api/eval/{eval_id}/cancel")
async def cancel_evaluation(eval_id: str, terminate: bool = False):
    """
    Cancel a queued or running evaluation task.

    This cancels the Celery task, preventing it from running if queued,
    or optionally terminating it if already running.

    Different from /kill which stops the Docker container execution.
    """
    # First check if Celery is enabled
    if not CELERY_ENABLED:
        return JSONResponse(
            content={"error": "Celery not enabled - using legacy queue system"}, status_code=503
        )

    # Cancel the Celery task
    result = cancel_celery_task(eval_id, terminate=terminate)

    if result.get("cancelled"):
        # Update storage to reflect cancellation
        async with create_http_client() as client:
            try:
                await client.put(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}",
                    json={"status": "cancelled", "error": "Task cancelled by user"},
                )
            except Exception as e:
                logger.error(f"Failed to update storage after cancellation: {e}")

        return {
            "eval_id": eval_id,
            "status": "cancelled",
            "message": result.get("message", "Task cancelled successfully"),
        }
    else:
        # Cancellation failed or not applicable
        status_code = 400 if "already" in result.get("message", "") else 500
        return JSONResponse(
            content={"error": result.get("message", "Failed to cancel task"), "details": result},
            status_code=status_code,
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
                response = await running_client.get(f"{STORAGE_SERVICE_URL}/evaluations/running")
                if response.status_code == 200:
                    data = response.json()
                    # Transform to match expected format
                    evaluations = []
                    for eval_info in data.get("running_evaluations", []):
                        # Get additional details from DB if needed
                        try:
                            async with create_http_client() as db_client:
                                db_response = await db_client.get(
                                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_info['eval_id']}"
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
            response = await storage_client.get(f"{STORAGE_SERVICE_URL}/evaluations", params=params)

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


@app.get("/api/queue-status", response_model=QueueStatusResponse)
async def get_queue_status():
    """Get queue status - now returns Celery status since legacy queue is deactivated"""
    # Legacy queue deactivated - return empty status
    # TODO: Replace with Celery queue metrics
    return QueueStatusResponse(
        queued=0,
        processing=0,
        queue_length=0,
        total_tasks=0,
        error=None
    )


@app.get("/api/celery-status")
async def get_celery_status_endpoint():
    """Get Celery cluster status including workers, queues, and tasks."""
    from app.celery_client import get_celery_status, CELERY_ENABLED, celery_app

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
                response = await stats_client.get(f"{STORAGE_SERVICE_URL}/statistics")
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
        from app.celery_client import get_celery_status, CELERY_ENABLED

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
            response = await stats_client.get(f"{STORAGE_SERVICE_URL}/statistics")
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
