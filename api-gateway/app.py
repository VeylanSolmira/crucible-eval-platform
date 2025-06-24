"""
API Gateway Service - Routes requests to microservices
Pure gateway that forwards to queue, executor, and other services
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs from environment
QUEUE_SERVICE_URL = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage:8082")  # Future
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

app = FastAPI(
    title="Crucible API Gateway",
    description="API Gateway for Crucible Evaluation Platform",
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

# Health tracking
service_health = {
    "gateway": True,
    "queue": False,
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
        
        service_health["last_check"] = datetime.utcnow().isoformat()
        await asyncio.sleep(30)  # Check every 30 seconds

@app.on_event("startup")
async def startup():
    """Start background tasks"""
    asyncio.create_task(check_service_health())
    logger.info("API Gateway started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await client.aclose()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Crucible API Gateway",
        "version": "2.0.0",
        "endpoints": {
            "evaluate": "/api/eval",
            "status": "/api/eval-status/{eval_id}",
            "queue": "/api/queue-status",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    """Gateway health check"""
    all_healthy = all([
        service_health["gateway"],
        service_health["queue"]
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
        raise HTTPException(status_code=502, detail="Failed to queue evaluation")

@app.get("/api/eval-status/{eval_id}")
async def get_evaluation_status(eval_id: str):
    """Get evaluation status"""
    # In the future, this would query storage service for completed evaluations
    # For now, return a simple response
    return {
        "eval_id": eval_id,
        "status": "queued",
        "message": "Status tracking coming soon"
    }

@app.get("/api/queue-status")
async def get_queue_status():
    """Get queue status"""
    try:
        response = await client.get(f"{QUEUE_SERVICE_URL}/status")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return {
            "error": "Queue service unavailable",
            "queued": 0,
            "processing": 0,
            "completed": 0
        }

@app.get("/api/status")
async def platform_status():
    """Overall platform status"""
    queue_status = await get_queue_status()
    
    return {
        "platform": "healthy" if service_health["queue"] else "degraded",
        "services": {
            "gateway": "healthy",
            "queue": "healthy" if service_health["queue"] else "unhealthy",
            "storage": "not_implemented",
            "executor": "healthy"  # Assume healthy if queue is working
        },
        "queue": queue_status,
        "version": "2.0.0",
        "mode": "microservices"
    }

# WebSocket for real-time updates (future implementation)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time evaluation updates"""
    await websocket.accept()
    try:
        while True:
            # In future, stream evaluation events
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)