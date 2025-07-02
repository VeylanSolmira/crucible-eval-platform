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
from shared.generated.python import EvaluationStatus

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Import Redis for event publishing
import redis.asyncio as redis

# Import Celery client for dual-write
from api.app.celery_client import submit_evaluation_to_celery

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

# HTTP client for service communication
client = httpx.AsyncClient(
    headers={"X-API-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {}, timeout=30.0
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
        try:
            # Check queue service
            response = await client.get(f"{QUEUE_SERVICE_URL}/health")
            service_health["queue"] = response.status_code == 200
        except Exception as e:
            logger.error(f"Queue health check failed: {e}")
            service_health["queue"] = False

        try:
            # Check storage service
            response = await client.get(f"{STORAGE_SERVICE_URL}/health")
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
    try:
        # Check queue service
        response = await client.get(f"{QUEUE_SERVICE_URL}/health")
        service_health["queue"] = response.status_code == 200
    except Exception as e:
        logger.error(f"Queue health check failed: {e}")
        service_health["queue"] = False

    try:
        # Check storage service
        response = await client.get(f"{STORAGE_SERVICE_URL}/health")
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
    await client.aclose()
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
            "status": "/api/eval-status/{eval_id}",
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


@app.post("/api/eval", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest):
    """Submit code for evaluation"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")

    # Generate eval ID
    eval_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

    try:
        # Publish event for storage worker to handle
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

        # TODO: Remove traffic split after Celery migration is complete (Day 7)
        # Traffic split: 50% to Celery, 50% to legacy queue
        import random

        use_celery = os.getenv(
            "CELERY_ENABLED", "false"
        ).lower() == "true" and random.random() < float(os.getenv("CELERY_PERCENTAGE", "0.5"))

        if use_celery:
            # Submit to Celery
            celery_task_id = submit_evaluation_to_celery(
                eval_id=eval_id,
                code=request.code,
                language=request.language,
                priority=request.priority,
            )
            if celery_task_id:
                logger.info(f"Submitted evaluation {eval_id} to Celery: {celery_task_id}")
            else:
                # Fallback to legacy queue if Celery submission fails
                logger.warning(
                    f"Celery submission failed for {eval_id}, falling back to legacy queue"
                )
                response = await client.post(
                    f"{QUEUE_SERVICE_URL}/tasks",
                    json={
                        "eval_id": eval_id,
                        "code": request.code,
                        "language": request.language,
                        "engine": request.engine,
                        "timeout": request.timeout,
                        "priority": 10 if request.priority else 1,
                    },
                )
                response.raise_for_status()
        else:
            # Submit to legacy queue
            response = await client.post(
                f"{QUEUE_SERVICE_URL}/tasks",
                json={
                    "eval_id": eval_id,
                    "code": request.code,
                    "language": request.language,
                    "engine": request.engine,
                    "timeout": request.timeout,
                    "priority": 10 if request.priority else 1,
                },
            )
            response.raise_for_status()
            logger.info(f"Submitted evaluation {eval_id} to legacy queue")

        # Set a pending key in Redis with 60s TTL
        try:
            await redis_client.setex(f"pending:{eval_id}", 60, "queued")
            logger.info(f"Set pending key for {eval_id}")
        except Exception as e:
            logger.error(f"Failed to set pending key for {eval_id}: {e}")

        # Get queue status for position
        queue_status = await client.get(f"{QUEUE_SERVICE_URL}/status")
        queue_data = queue_status.json() if queue_status.status_code == 200 else {}

        return EvaluationResponse(
            eval_id=eval_id,
            status=EvaluationStatus.QUEUED,
            message="Evaluation queued successfully",
            queue_position=queue_data.get("queued", 0),
        )

    except httpx.HTTPError as e:
        logger.error(f"Queue service error: {e}")
        # Publish failure event
        await publish_evaluation_event("evaluation:failed", {"eval_id": eval_id, "error": str(e)})
        raise HTTPException(status_code=502, detail="Failed to queue evaluation")


@app.post("/api/eval-batch", response_model=BatchEvaluationResponse)
async def evaluate_batch(request: BatchEvaluationRequest):
    """Submit multiple evaluations as a batch"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")

    results = []
    queued_count = 0
    failed_count = 0

    # Get current queue status for position calculation
    try:
        queue_status = await client.get(f"{QUEUE_SERVICE_URL}/status")
        queue_data = queue_status.json() if queue_status.status_code == 200 else {}
        current_queue_size = queue_data.get("queued", 0)
    except Exception as e:
        logger.warning(f"Failed to get queue status: {e}")
        current_queue_size = 0

    # Process each evaluation
    for idx, eval_request in enumerate(request.evaluations):
        eval_id = (
            f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        )

        try:
            # Publish event for storage worker
            await publish_evaluation_event(
                "evaluation:queued",
                {
                    "eval_id": eval_id,
                    "code": eval_request.code,
                    "language": eval_request.language,
                    "engine": eval_request.engine,
                    "metadata": {
                        "submitted_at": datetime.now(timezone.utc).isoformat(),
                        "timeout": eval_request.timeout,
                        "batch": True,
                        "batch_index": idx,
                    },
                },
            )

            # Forward to queue service
            response = await client.post(
                f"{QUEUE_SERVICE_URL}/tasks",
                json={
                    "eval_id": eval_id,
                    "code": eval_request.code,
                    "language": eval_request.language,
                    "engine": eval_request.engine,
                    "timeout": eval_request.timeout,
                    "priority": 1,
                },
            )
            response.raise_for_status()

            # Set a pending key in Redis with 60s TTL
            await redis_client.setex(f"pending:{eval_id}", 60, "queued")

            results.append(
                EvaluationResponse(
                    eval_id=eval_id,
                    status=EvaluationStatus.QUEUED,
                    message="Evaluation queued successfully",
                    queue_position=current_queue_size + queued_count + 1,
                )
            )
            queued_count += 1

        except Exception as e:
            logger.error(f"Failed to queue evaluation {idx}: {e}")
            results.append(
                EvaluationResponse(
                    eval_id=eval_id,
                    status=EvaluationStatus.FAILED,
                    message=f"Failed to queue: {str(e)}",
                    queue_position=None,
                )
            )
            failed_count += 1

            # Publish failure event
            await publish_evaluation_event(
                "evaluation:failed",
                {"eval_id": eval_id, "error": str(e), "batch": True, "batch_index": idx},
            )

    return BatchEvaluationResponse(
        evaluations=results,
        total=len(request.evaluations),
        queued=queued_count,
        failed=failed_count,
    )


@app.get(
    "/api/eval-status/{eval_id}",
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
    """Get evaluation status from storage service"""
    # During startup, retry once if storage appears unavailable
    if not service_health["storage"]:
        # Check if we're in startup period (first 2 minutes)
        if hasattr(check_service_health, "start_time"):
            elapsed = (datetime.now(timezone.utc) - check_service_health.start_time).total_seconds()
            if elapsed < 120:
                # Do a quick health check and retry
                logger.info("Storage appears unavailable during startup, doing quick health check")
                await check_service_health_once()
                if not service_health["storage"]:
                    raise HTTPException(status_code=503, detail="Storage service unavailable")
        else:
            raise HTTPException(status_code=503, detail="Storage service unavailable")

    try:
        # Proxy to storage service
        storage_response = await client.get(f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}")

        if storage_response.status_code == 404:
            # Check Redis to see if this evaluation is pending
            try:
                pending_status = await redis_client.get(f"pending:{eval_id}")
                logger.info(f"Redis check for {eval_id}: {pending_status}")
                if pending_status:
                    # Return 202 Accepted for pending evaluations
                    response.status_code = 202
                    logger.info(f"Setting status code to 202 for {eval_id}")
                    return EvaluationStatusResponse(
                        eval_id=eval_id,
                        status=EvaluationStatus.QUEUED,
                        created_at=None,
                        completed_at=None,
                        output="",
                        error="",
                        success=False,
                    )
            except Exception as e:
                logger.error(f"Failed to check Redis for {eval_id}: {e}")

            # Otherwise, it truly doesn't exist
            raise HTTPException(status_code=404, detail="Evaluation not found")
        elif not storage_response.status_code == 200:
            raise HTTPException(
                status_code=storage_response.status_code, detail="Storage service error"
            )

        evaluation = storage_response.json()

        # Return typed response, ensuring None values are converted to empty strings
        return EvaluationStatusResponse(
            eval_id=evaluation.get("id", eval_id),
            status=evaluation.get("status", "unknown"),
            created_at=evaluation.get("created_at"),
            completed_at=evaluation.get("completed_at"),
            output=evaluation.get("output") or "",
            error=evaluation.get("error") or "",
            success=evaluation.get("status") == EvaluationStatus.COMPLETED.value,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving evaluation {eval_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evaluation")


@app.get("/api/eval/{eval_id}")
async def get_evaluation_status(eval_id: str):
    """
    Get evaluation status - checks Redis first for real-time status, falls back to DB.
    This provides instant status updates for running evaluations.
    """
    try:
        # First, try to get running info from Redis (real-time)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}/running"
                )
                if response.status_code == 200:
                    running_info = response.json()
                    # If it's in Redis, it's running
                    return JSONResponse({
                        "eval_id": eval_id,
                        "status": "running",
                        "is_running": True,
                        "executor_id": running_info.get("executor_id"),
                        "started_at": running_info.get("started_at"),
                        **running_info
                    })
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                logger.warning(f"Error checking Redis for {eval_id}: {e}")
            # If 404, evaluation is not in Redis (not running), continue to DB
        
        # Fall back to database for completed/failed evaluations
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{STORAGE_SERVICE_URL}/evaluations/{eval_id}"
            )
            response.raise_for_status()
            
            eval_data = response.json()
            # Add is_running field for consistency
            eval_data["is_running"] = eval_data.get("status") == "running"
            return eval_data
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        logger.error(f"Error fetching evaluation {eval_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch evaluation")
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
        response = await client.put(
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
    async with httpx.AsyncClient() as client:
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
    async with httpx.AsyncClient() as client:
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

    async with httpx.AsyncClient() as client:
        try:
            kill_response = await client.post(f"{executor_url}/kill/{eval_id}")
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
    from app.celery_client import CELERY_ENABLED, cancel_celery_task

    if not CELERY_ENABLED:
        return JSONResponse(
            content={"error": "Celery not enabled - using legacy queue system"}, status_code=503
        )

    # Cancel the Celery task
    result = cancel_celery_task(eval_id, terminate=terminate)

    if result.get("cancelled"):
        # Update storage to reflect cancellation
        async with httpx.AsyncClient() as client:
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
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{STORAGE_SERVICE_URL}/evaluations/running")
                if response.status_code == 200:
                    data = response.json()
                    # Transform to match expected format
                    evaluations = []
                    for eval_info in data.get("running_evaluations", []):
                        # Get additional details from DB if needed
                        try:
                            db_response = await client.get(
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
        response = await client.get(f"{STORAGE_SERVICE_URL}/evaluations", params=params)

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
    """Get queue status"""
    try:
        response = await client.get(f"{QUEUE_SERVICE_URL}/status")
        response.raise_for_status()
        data = response.json()
        return QueueStatusResponse(**data)
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return QueueStatusResponse(
            error="Queue service unavailable", queued=0, processing=0, queue_length=0, total_tasks=0
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
            response = await client.get(f"{STORAGE_SERVICE_URL}/statistics")
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
        response = await client.get(f"{STORAGE_SERVICE_URL}/statistics")
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
