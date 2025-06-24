"""
API Service - Routes requests and handles storage
This replaces the monolithic app.py when running in microservices mode
"""
import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, Response
from pydantic import BaseModel
import uvicorn

# Import Redis for event publishing
import redis.asyncio as redis

# Import storage for reading evaluations (read-only)
from storage import FlexibleStorageManager
from storage.config import StorageConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs from environment
QUEUE_SERVICE_URL = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "dev-internal-api-key")

app = FastAPI(
    title="Crucible API Service (Microservices Mode)",
    description="API service for distributed Crucible platform",
    version="2.0.0"
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
    headers={"X-API-Key": INTERNAL_API_KEY} if INTERNAL_API_KEY else {},
    timeout=30.0
)

# Initialize Redis for event publishing
redis_client = redis.from_url(REDIS_URL)
logger.info(f"Connected to Redis for event publishing")

# Initialize storage for reading only (storage worker handles writes)
storage_config = StorageConfig.from_environment()
storage = FlexibleStorageManager.from_config(storage_config)
logger.info(f"Storage initialized for reading")

# Request models
class EvaluationRequest(BaseModel):
    code: str
    language: str = "python"
    engine: str = "docker"
    timeout: int = 30

class EvaluationResponse(BaseModel):
    eval_id: str
    status: str = "queued"
    message: str = "Evaluation queued for processing"
    queue_position: Optional[int] = None

class EvaluationStatusResponse(BaseModel):
    eval_id: str
    status: str
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
    "storage": True,  # Storage is read-only, so we just check if initialized
    "last_check": None
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
        
        # Check Redis
        try:
            await redis_client.ping()
            service_health["redis"] = True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            service_health["redis"] = False
        
        service_health["last_check"] = datetime.utcnow().isoformat()
        await asyncio.sleep(30)  # Check every 30 seconds

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
    asyncio.create_task(check_service_health())
    asyncio.create_task(poll_completed_evaluations())
    
    # Auto-export OpenAPI specification on startup
    try:
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, skipping OpenAPI YAML export")
            yaml = None
            
        openapi_schema = app.openapi()
        
        # Write both YAML and JSON versions
        spec_dir = Path(__file__).parent
        
        # Write YAML version if yaml is available
        if yaml:
            with open(spec_dir / "openapi.yaml", "w") as f:
                yaml.dump(openapi_schema, f, default_flow_style=False, sort_keys=False)
                logger.info(f"Exported OpenAPI YAML to: {spec_dir / 'openapi.yaml'}")
        
        # Write JSON version
        with open(spec_dir / "openapi.json", "w") as f:
            json.dump(openapi_schema, f, indent=2)
            logger.info(f"Exported OpenAPI JSON to: {spec_dir / 'openapi.json'}")
            
    except Exception as e:
        logger.error(f"Failed to export OpenAPI spec: {e}")
        # Don't fail startup if export fails
    
    logger.info("API Service started in microservices mode")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await client.aclose()
    await redis_client.close()
    storage.close()

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
            "status": "/api/eval-status/{eval_id}",
            "evaluations": "/api/evaluations",
            "queue": "/api/queue-status",
            "platform": "/api/status",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    """Gateway health check"""
    all_healthy = all([
        service_health["gateway"],
        service_health["queue"],
        service_health["storage"]
    ])
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": service_health,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/eval", response_model=EvaluationResponse)
async def evaluate(request: EvaluationRequest):
    """Submit code for evaluation"""
    if not service_health["queue"]:
        raise HTTPException(status_code=503, detail="Queue service unavailable")
    
    # Generate eval ID
    eval_id = f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
    
    try:
        # Publish event for storage worker to handle
        await publish_evaluation_event("evaluation:queued", {
            "eval_id": eval_id,
            "code": request.code,
            "language": request.language,
            "engine": request.engine,
            "metadata": {
                "submitted_at": datetime.utcnow().isoformat(),
                "timeout": request.timeout
            }
        })
        
        # Forward to queue service
        response = await client.post(
            f"{QUEUE_SERVICE_URL}/tasks",
            json={
                "eval_id": eval_id,
                "code": request.code,
                "language": request.language,
                "engine": request.engine,
                "timeout": request.timeout,
                "priority": 1
            }
        )
        response.raise_for_status()
        
        # Get queue status for position
        queue_status = await client.get(f"{QUEUE_SERVICE_URL}/status")
        queue_data = queue_status.json() if queue_status.status_code == 200 else {}
        
        return EvaluationResponse(
            eval_id=eval_id,
            status="queued",
            message="Evaluation queued successfully",
            queue_position=queue_data.get("queued", 0)
        )
        
    except httpx.HTTPError as e:
        logger.error(f"Queue service error: {e}")
        # Publish failure event
        await publish_evaluation_event("evaluation:failed", {
            "eval_id": eval_id,
            "error": str(e)
        })
        raise HTTPException(status_code=502, detail="Failed to queue evaluation")

@app.get("/api/eval-status/{eval_id}", response_model=EvaluationStatusResponse)
async def get_evaluation_status(eval_id: str):
    """Get evaluation status from storage"""
    try:
        evaluation = storage.get_evaluation(eval_id)
        if evaluation:
            # Return typed response
            return EvaluationStatusResponse(
                eval_id=evaluation.get('id', eval_id),
                status=evaluation.get('status', 'unknown'),
                created_at=evaluation.get('created_at'),
                completed_at=evaluation.get('completed_at'),
                output=evaluation.get('output', ''),
                error=evaluation.get('error', ''),
                success=evaluation.get('status') == 'completed'
            )
        else:
            raise HTTPException(status_code=404, detail="Evaluation not found")
    except Exception as e:
        logger.error(f"Error retrieving evaluation {eval_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve evaluation")

@app.get("/api/evaluations")
async def get_evaluations(limit: int = 100, offset: int = 0):
    """Get evaluation history"""
    try:
        evaluations = storage.list_evaluations(limit=limit, offset=offset)
        return {
            "evaluations": [
                {
                    "eval_id": e.get('id', 'unknown'),
                    "status": e.get('status', 'unknown'),
                    "created_at": e.get('created_at'),
                    "code_preview": e.get('code', '')[:100] + "..." if len(e.get('code', '')) > 100 else e.get('code', ''),
                    "success": e.get('status') == 'completed'
                }
                for e in evaluations
            ],
            "count": len(evaluations),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error listing evaluations: {e}")
        return {
            "evaluations": [],
            "count": 0,
            "error": str(e)
        }

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
            error="Queue service unavailable",
            queued=0,
            processing=0,
            queue_length=0,
            total_tasks=0
        )

@app.get("/api/status", response_model=StatusResponse)
async def platform_status():
    """Overall platform status"""
    queue_status = await get_queue_status()
    
    # Get storage stats
    storage_stats = storage.get_statistics() if hasattr(storage, 'get_statistics') else {}
    
    services = ServiceHealthInfo(
        gateway="healthy",
        queue="healthy" if service_health["queue"] else "unhealthy",
        storage="healthy" if service_health["storage"] else "unhealthy",
        executor="healthy"  # Assume healthy if queue is working
    )
    
    return StatusResponse(
        platform="healthy" if all([service_health["queue"], service_health["storage"]]) else "degraded",
        mode="microservices",
        services=services,
        queue=queue_status,
        storage=storage_stats,
        version="2.0.0"
    )

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = ServiceHealthInfo(
        gateway="healthy",
        queue="healthy" if service_health["queue"] else "unhealthy",
        storage="healthy" if service_health["storage"] else "unhealthy",
        executor="healthy"
    )
    
    return HealthResponse(
        status="ok" if all([service_health["queue"], service_health["storage"]]) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        services=services
    )

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
                "timestamp": datetime.utcnow().isoformat(),
                "services": service_health
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
        with open(spec_path, 'r') as f:
            content = f.read()
        return Response(content=content, media_type="application/yaml")
    else:
        # Return auto-generated spec
        from fastapi.openapi.utils import get_openapi
        return get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)