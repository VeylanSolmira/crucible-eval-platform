"""
Queue Worker - Pulls tasks from queue and assigns to executors
This is the "scheduler" that will evolve into Celery task routing
"""
import asyncio
import httpx
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import random
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
import uvicorn
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueueWorker:
    """
    Pulls tasks from queue service and assigns to executor workers.
    
    Future evolution:
    - Smart routing based on worker load
    - Priority-based scheduling
    - Worker health monitoring
    - Task retry logic
    - Dead letter queue handling
    """
    
    def __init__(self):
        self.queue_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
        self.api_key = os.getenv("QUEUE_API_KEY")
        
        # Redis for event publishing
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis_client = None  # Will be initialized in async context
        self._redis_url = redis_url
        
        # Executor workers pool
        self.executor_urls = self._discover_executors()
        logger.info(f"Queue worker managing {len(self.executor_urls)} executors")
        
        # HTTP client
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=30.0
        )
        
        self.running = True
        self.tasks_routed = 0
        self.worker_id = os.getenv("HOSTNAME", "queue-worker-1")
        
    def _discover_executors(self) -> List[str]:
        """Discover available executor workers"""
        # In docker-compose, we'll have executor-1, executor-2, executor-3
        # In Kubernetes, this would use service discovery
        executor_count = int(os.getenv("EXECUTOR_COUNT", "3"))
        base_url = os.getenv("EXECUTOR_BASE_URL", "http://executor")
        
        executors = []
        for i in range(1, executor_count + 1):
            # Docker compose creates services like executor-1, executor-2
            url = f"{base_url}-{i}:8083"
            executors.append(url)
        
        logger.info(f"Discovered {len(executors)} executor workers: {executors}")
        return executors
    
    async def check_executor_health(self, executor_url: str) -> bool:
        """Check if an executor is healthy"""
        try:
            response = await self.client.get(f"{executor_url}/health", timeout=2.0)
            return response.status_code == 200
        except:
            return False
    
    async def get_healthy_executor(self) -> Optional[str]:
        """Get a healthy executor using round-robin with health checks"""
        # Shuffle for basic load balancing
        executors = list(self.executor_urls)
        random.shuffle(executors)
        
        for executor_url in executors:
            if await self.check_executor_health(executor_url):
                return executor_url
        
        return None
    
    async def _publish_event(self, channel: str, data: Dict[str, Any]):
        """Publish event to Redis"""
        if self.redis_client:
            try:
                message = json.dumps(data)
                await self.redis_client.publish(channel, message)
                logger.info(f"Published event to {channel}: {data.get('eval_id', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to publish event to {channel}: {e}")
    
    async def route_task(self, task: Dict):
        """Route a task to an available executor and handle results"""
        eval_id = task["eval_id"]
        code = task["code"]
        
        logger.info(f"Processing task {eval_id}")
        
        # Get healthy executor
        executor_url = await self.get_healthy_executor()
        if not executor_url:
            logger.error("No healthy executors available")
            await self.client.post(
                f"{self.queue_url}/tasks/{eval_id}/fail",
                json={"error": "No healthy executors available"}
            )
            return
        
        logger.info(f"Executing task {eval_id} on {executor_url}")
        
        try:
            # Send code to executor for execution
            response = await self.client.post(
                f"{executor_url}/execute",
                json={
                    "eval_id": eval_id,
                    "code": code,
                    "timeout": 30
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                self.tasks_routed += 1
                
                # Report result back to queue
                if result["status"] == "completed":
                    await self.client.post(
                        f"{self.queue_url}/tasks/{eval_id}/complete",
                        json={"output": result}
                    )
                    # Publish completion event for storage worker
                    await self._publish_event("evaluation:completed", {
                        "eval_id": eval_id,
                        "result": result
                    })
                else:
                    await self.client.post(
                        f"{self.queue_url}/tasks/{eval_id}/fail",
                        json={"error": result.get("error", "Execution failed")}
                    )
                    # Publish failure event for storage worker
                    await self._publish_event("evaluation:failed", {
                        "eval_id": eval_id,
                        "error": result.get("error", "Execution failed")
                    })
                
                logger.info(f"Task {eval_id} completed with status: {result['status']}")
            else:
                logger.error(f"Executor rejected task: {response.status_code}")
                await self.client.post(
                    f"{self.queue_url}/tasks/{eval_id}/fail",
                    json={"error": f"Executor rejected task: {response.text}"}
                )
                
        except Exception as e:
            logger.error(f"Failed to execute task {eval_id}: {str(e)}")
            await self.client.post(
                f"{self.queue_url}/tasks/{eval_id}/fail",
                json={"error": str(e)}
            )
    
    async def run(self):
        """Main loop - pull tasks and route to executors"""
        # Initialize Redis client in async context
        self.redis_client = redis.from_url(self._redis_url)
        logger.info(f"Connected to Redis for event publishing")
        
        logger.info(f"Queue worker started: {self.worker_id}")
        logger.info(f"Managing {len(self.executor_urls)} executors")
        
        consecutive_errors = 0
        
        while self.running:
            try:
                # Pull next task from queue
                response = await self.client.get(f"{self.queue_url}/tasks/next")
                
                if response.status_code == 200:
                    task = response.json()
                    if task:
                        consecutive_errors = 0
                        await self.route_task(task)
                    else:
                        # No tasks available
                        await asyncio.sleep(1)
                else:
                    await asyncio.sleep(1)
                    
            except httpx.ConnectError:
                logger.error("Queue service connection failed")
                consecutive_errors += 1
                await asyncio.sleep(min(5 * consecutive_errors, 30))
                
            except Exception as e:
                logger.error(f"Queue worker error: {str(e)}")
                consecutive_errors += 1
                await asyncio.sleep(min(5 * consecutive_errors, 30))
        
        await self.client.aclose()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("Queue worker stopped")
    
    async def get_status(self) -> Dict:
        """Get worker status"""
        # Check executor health
        executor_health = {}
        for executor_url in self.executor_urls:
            executor_health[executor_url] = await self.check_executor_health(executor_url)
        
        healthy_count = sum(1 for healthy in executor_health.values() if healthy)
        
        return {
            "worker_id": self.worker_id,
            "status": "healthy" if healthy_count > 0 else "degraded",
            "tasks_routed": self.tasks_routed,
            "executors": {
                "total": len(self.executor_urls),
                "healthy": healthy_count,
                "health": executor_health
            }
        }

# FastAPI app for health/status
app = FastAPI(title="Queue Worker")

worker: Optional[QueueWorker] = None

@app.on_event("startup")
async def startup():
    global worker
    worker = QueueWorker()
    asyncio.create_task(worker.run())

@app.on_event("shutdown")
async def shutdown():
    if worker:
        worker.running = False

@app.get("/health")
async def health():
    if worker:
        status = await worker.get_status()
        return {
            "status": status["status"],
            "service": "queue-worker",
            "details": status
        }
    return {"status": "starting", "service": "queue-worker"}

@app.get("/status")
async def status():
    if worker:
        return await worker.get_status()
    return {"status": "not_initialized"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8084)