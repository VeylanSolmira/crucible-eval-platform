# Queue Service Integration Guide

## Quick Decision Summary

**For Crucible Platform:**
- Use **HTTP + JSON** initially (simplest, debuggable)
- **Shared base image** for all Python services
- **API key authentication** between services
- **Network isolation** with internal Docker networks
- Prepare interfaces for **easy Celery migration**

## Implementation Steps

### 1. Create Shared Base Image

```dockerfile
# base.Dockerfile
FROM python:3.11-slim AS python-base

# Common dependencies for all services
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    httpx==0.25.0 \
    python-dotenv==1.0.0

# Common setup
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Health check script
COPY scripts/healthcheck.py /healthcheck.py
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python /healthcheck.py || exit 1
```

### 2. Update docker-compose.yml

```yaml
version: '3.8'

services:
  # Public-facing reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    networks:
      - public
      - internal
    depends_on:
      - api
      - frontend

  # API Gateway - all external requests go through here
  api:
    build:
      context: .
      dockerfile: Dockerfile
    networks:
      - internal
      - db_network
    environment:
      - QUEUE_SERVICE_URL=http://queue:8081
      - QUEUE_API_KEY=${INTERNAL_QUEUE_API_KEY}
      - DATABASE_URL=postgresql://...
    depends_on:
      - postgres
      - queue

  # Queue Service - internal only
  queue:
    build:
      context: .
      dockerfile: queue-service/Dockerfile
    networks:
      - internal
      - worker_network
    environment:
      - API_KEY=${INTERNAL_QUEUE_API_KEY}
      - WORKER_API_KEY=${INTERNAL_WORKER_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s

  # Worker Service - pulls from queue, executes code
  worker:
    build:
      context: .
      dockerfile: worker-service/Dockerfile
    networks:
      - worker_network
      - execution_network
    environment:
      - QUEUE_SERVICE_URL=http://queue:8081
      - API_KEY=${INTERNAL_WORKER_API_KEY}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    depends_on:
      - queue

  # Frontend
  frontend:
    build:
      context: ./frontend
    networks:
      - internal
    environment:
      - API_URL=http://api:8080

  # Database
  postgres:
    image: postgres:15-alpine
    networks:
      - db_network
    volumes:
      - postgres_data:/var/lib/postgresql/data

networks:
  public:
    # External access
  internal:
    internal: true  # No external routing
  db_network:
    internal: true
  worker_network:
    internal: true
  execution_network:
    internal: true  # Most isolated

volumes:
  postgres_data:
```

### 3. Update API Service to Use Queue

```python
# src/api/services/queue_client.py
import httpx
from typing import Dict, Optional
import os

class QueueClient:
    def __init__(self):
        self.base_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
        self.api_key = os.getenv("QUEUE_API_KEY")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key},
            timeout=30.0
        )
    
    async def enqueue_task(self, eval_id: str, code: str, engine: str = "docker") -> Dict:
        """Add task to queue"""
        response = await self.client.post(
            "/tasks",
            json={
                "eval_id": eval_id,
                "code": code,
                "engine": engine,
                "priority": 1
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_queue_status(self) -> Dict:
        """Get queue statistics"""
        response = await self.client.get("/status")
        response.raise_for_status()
        return response.json()
    
    async def get_task_status(self, eval_id: str) -> Dict:
        """Get status of specific task"""
        response = await self.client.get(f"/tasks/{eval_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Clean up client"""
        await self.client.aclose()

# Update platform.py
from .services.queue_client import QueueClient

class EvaluationPlatform:
    def __init__(self):
        self.queue_client = QueueClient()
        # Remove internal queue
        # self.queue = Queue()
    
    async def submit_evaluation(self, eval_request: EvaluationRequest) -> EvaluationResponse:
        eval_id = str(uuid4())
        
        # Store in database
        await self.storage_manager.store(eval_id, eval_request, EvaluationResult(...))
        
        # Send to queue service
        await self.queue_client.enqueue_task(
            eval_id=eval_id,
            code=eval_request.code,
            engine=eval_request.get("engine", "docker")
        )
        
        return EvaluationResponse(
            eval_id=eval_id,
            status="queued",
            message="Evaluation queued for processing"
        )
    
    async def get_queue_status(self) -> dict:
        return await self.queue_client.get_queue_status()
```

### 4. Create Worker Service

```python
# worker-service/app.py
import asyncio
import httpx
import logging
from datetime import datetime
import os
import sys

# Add parent directory to path to import execution engines
sys.path.append('/app')
from src.execution_engine.execution import DockerEngine, GVisorEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Worker:
    def __init__(self):
        self.queue_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
        self.api_key = os.getenv("API_KEY")
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": self.api_key},
            timeout=30.0
        )
        
        # Initialize execution engines
        self.engines = {
            "docker": DockerEngine(),
            "gvisor": GVisorEngine()
        }
        
        self.running = True
    
    async def process_task(self, task: dict):
        """Execute a single task"""
        eval_id = task["eval_id"]
        code = task["code"]
        engine_name = task.get("engine", "docker")
        
        logger.info(f"Processing task {eval_id} with {engine_name}")
        
        try:
            # Get appropriate engine
            engine = self.engines.get(engine_name, self.engines["docker"])
            
            # Execute code
            result = engine.execute(code, eval_id)
            
            # Report success
            await self.client.post(
                f"{self.queue_url}/tasks/{eval_id}/complete",
                json={"output": result}
            )
            
            logger.info(f"Task {eval_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {eval_id} failed: {str(e)}")
            
            # Report failure
            await self.client.post(
                f"{self.queue_url}/tasks/{eval_id}/fail",
                json={"error": str(e)}
            )
    
    async def run(self):
        """Main worker loop"""
        logger.info("Worker started")
        
        while self.running:
            try:
                # Pull task from queue
                response = await self.client.get(f"{self.queue_url}/tasks/next")
                
                if response.status_code == 200:
                    task = response.json()
                    if task:
                        await self.process_task(task)
                    else:
                        # No tasks, wait a bit
                        await asyncio.sleep(1)
                else:
                    logger.error(f"Failed to get task: {response.status_code}")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Worker error: {str(e)}")
                await asyncio.sleep(5)
        
        await self.client.aclose()

async def main():
    worker = Worker()
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker shutting down")
        worker.running = False

if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Environment Configuration

```bash
# .env
# Internal API Keys (generate with: openssl rand -hex 32)
INTERNAL_QUEUE_API_KEY=a6f8d2b4e9c1f5a3d8b2e7c4f9a1d6b3e8c2f7a4d9b1e6c3f8a2d7b4e9c1f5a3
INTERNAL_WORKER_API_KEY=b7e9d3c5f1a2e6b4d8c3e7a5f9b2d7c4e8a3f6b1d9c2e5a3f7b2d6c4e9a1f4b3

# Service URLs (for local development)
QUEUE_SERVICE_URL=http://localhost:8081
API_SERVICE_URL=http://localhost:8080
```

### 6. Migration Path to Celery

```python
# Future: queue_service_celery.py
# Same API, different implementation
from celery import Celery

app = Celery('tasks', broker='redis://redis:6379')

@app.task
def process_evaluation(eval_id: str, code: str, engine: str):
    # Same logic, now distributed
    pass

# FastAPI wrapper remains the same
@app.post("/tasks")
async def enqueue_task(task: Task):
    # Instead of in-memory queue:
    process_evaluation.delay(task.eval_id, task.code, task.engine)
    return {"eval_id": task.eval_id, "status": "queued"}
```

## Security Considerations

1. **API Keys**: Different key for each service connection
2. **Network Isolation**: Services can only talk to what they need
3. **No Direct Execution Access**: API can't reach execution network
4. **Audit Logging**: Log all inter-service calls
5. **Rate Limiting**: Implement per-service limits

## Testing the Integration

```bash
# 1. Build base image
docker build -f base.Dockerfile -t crucible-base .

# 2. Start services
docker-compose up -d

# 3. Test queue service directly
curl http://localhost:8081/health

# 4. Submit evaluation through API
curl -X POST http://localhost:8080/api/eval \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello from modular queue!\")"}'

# 5. Watch logs
docker-compose logs -f queue worker
```

## Benefits Realized

1. **Independent Scaling**: Can run multiple workers
2. **Clear Interfaces**: Easy to swap implementations
3. **Better Monitoring**: Each service has clear metrics
4. **Fault Isolation**: Queue crash doesn't affect API
5. **Ready for Kubernetes**: Each component is containerized

This architecture sets you up perfectly for Day 3's Celery integration and Day 4's Kubernetes deployment!