"""
Queue Service - Simple REST API wrapper around a Python queue
This provides a network API for task queueing, mimicking what Redis/Celery would provide
but using simple Python data structures.
"""
import os
from typing import Dict, Optional, Any
from datetime import datetime
import logging
from collections import deque
import json

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Queue Service", version="1.0.0")

# Simple in-memory queue (deque for FIFO behavior)
task_queue = deque()
task_registry: Dict[str, Dict[str, Any]] = {}

# Redis for event publishing (matching other services)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = None

class EnqueueRequest(BaseModel):
    """Request to enqueue a task"""
    eval_id: str
    code: str
    language: str = "python"
    engine: str = "docker"
    timeout: int = 30
    priority: int = 1

class TaskStatusResponse(BaseModel):
    """Status of a task"""
    eval_id: str
    status: str
    position: Optional[int] = None
    queued_at: Optional[datetime] = None
    message: Optional[str] = None

async def publish_event(channel: str, data: Dict[str, Any]):
    """Publish event to Redis (matching pattern from other services)"""
    if redis_client:
        try:
            message = json.dumps(data)
            await redis_client.publish(channel, message)
            logger.info(f"Published event to {channel}: {data.get('eval_id', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to publish event to {channel}: {e}")

@app.on_event("startup")
async def startup():
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(REDIS_URL)
    logger.info("Queue service started")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_healthy = False
    if redis_client:
        try:
            await redis_client.ping()
            redis_healthy = True
        except:
            pass
    
    return {
        "status": "healthy",
        "service": "queue",
        "queue_size": len(task_queue),
        "total_tasks": len(task_registry),
        "redis": "connected" if redis_healthy else "disconnected"
    }

@app.post("/tasks")
async def enqueue_task(
    request: EnqueueRequest,
    x_api_key: Optional[str] = Header(None)
) -> Dict:
    """Add a task to the queue"""
    # Simple API key check (if configured)
    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Add to queue and registry
    task_queue.append(request.eval_id)
    task_registry[request.eval_id] = {
        "status": "queued",
        "code": request.code,
        "language": request.language,
        "engine": request.engine,
        "timeout": request.timeout,
        "queued_at": datetime.utcnow(),
        "position": len(task_queue)  # Position in queue
    }
    
    logger.info(f"Enqueued task {request.eval_id}")
    
    return {
        "eval_id": request.eval_id,
        "status": "queued",
        "position": len(task_queue)
    }

@app.get("/tasks/next")
async def get_next_task() -> Optional[Dict]:
    """Get the next task for a worker to process"""
    if not task_queue:
        return None
    
    # Get next task from queue
    eval_id = task_queue.popleft()
    
    if eval_id in task_registry:
        task = task_registry[eval_id]
        task["status"] = "processing"
        
        # Update positions for remaining queued tasks
        for idx, queued_id in enumerate(task_queue):
            if queued_id in task_registry:
                task_registry[queued_id]["position"] = idx + 1
        
        return {
            "eval_id": eval_id,
            "code": task["code"],
            "language": task["language"],
            "engine": task["engine"],
            "timeout": task["timeout"]
        }
    
    return None

@app.post("/tasks/{eval_id}/complete")
async def mark_task_complete(eval_id: str, body: Dict) -> Dict:
    """Mark a task as completed"""
    if eval_id not in task_registry:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Remove from registry (it's done)
    task = task_registry.pop(eval_id)
    
    logger.info(f"Task {eval_id} completed")
    return {"status": "completed"}

@app.post("/tasks/{eval_id}/fail")
async def mark_task_failed(eval_id: str, body: Dict) -> Dict:
    """Mark a task as failed"""
    if eval_id not in task_registry:
        # Task might have already been removed
        logger.warning(f"Task {eval_id} not found, might already be processed")
        return {"status": "not_found"}
    
    # Remove from registry
    task = task_registry.pop(eval_id)
    
    logger.info(f"Task {eval_id} failed: {body.get('error', 'Unknown error')}")
    return {"status": "failed"}

@app.get("/tasks/{eval_id}")
async def get_task_status(eval_id: str) -> TaskStatusResponse:
    """Get the status of a specific task"""
    if eval_id not in task_registry:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = task_registry[eval_id]
    
    return TaskStatusResponse(
        eval_id=eval_id,
        status=task["status"],
        position=task.get("position"),
        queued_at=task.get("queued_at")
    )

@app.get("/status")
async def get_queue_status() -> Dict:
    """Get overall queue status"""
    queued = sum(1 for t in task_registry.values() if t["status"] == "queued")
    processing = sum(1 for t in task_registry.values() if t["status"] == "processing")
    
    return {
        "queued": queued,
        "processing": processing,
        "queue_length": len(task_queue),
        "total_tasks": len(task_registry)
    }

@app.delete("/tasks")
async def clear_queue() -> Dict:
    """Clear all tasks (admin endpoint)"""
    # This should be protected in production
    count = len(task_queue)
    task_queue.clear()
    task_registry.clear()
    
    logger.warning(f"Queue cleared, removed {count} tasks")
    
    return {
        "status": "cleared",
        "tasks_removed": count
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)