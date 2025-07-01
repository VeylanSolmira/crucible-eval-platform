"""
Storage Worker - Subscribes to events and updates database
This is a dedicated service that listens for evaluation events and persists them
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis.asyncio as redis
import httpx
import structlog
from shared.generated.python import EvaluationStatus

# Configure standard logging for libraries (redis, etc)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get structured logger for this module
logger = structlog.get_logger()

class StorageWorker:
    """
    Dedicated worker that subscribes to Redis events and updates storage.
    
    This follows the Kubernetes controller pattern:
    - Watches for specific events (like a controller watching resources)
    - Takes action based on events (updates database)
    - Loosely coupled from other services
    
    Benefits:
    - Storage logic isolated in one place
    - Can scale independently
    - Can add multiple storage backends
    - Resilient to failures (can replay events)
    """
    
    def __init__(self):
        # Redis connection for pub/sub
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.redis = redis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
        
        # HTTP client for storage service
        self.storage_url = os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8082")
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("storage_worker.initialized", 
                   backend="storage_service_api",
                   redis_url=redis_url,
                   storage_url=self.storage_url)
        
        self.running = True
        self.events_processed = 0
        
        # Log batching
        self.log_buffers: Dict[str, List[Dict]] = {}  # eval_id -> log entries
        self.log_buffer_timers: Dict[str, asyncio.Task] = {}  # eval_id -> flush timer
        self.log_batch_size = 100  # Flush after 100 log entries
        self.log_batch_timeout = 5.0  # Flush after 5 seconds
    
    async def start(self):
        """Start listening for events"""
        # Subscribe to relevant channels
        await self.pubsub.subscribe(
            "evaluation:queued",
            "evaluation:running",
            "evaluation:completed",
            "evaluation:failed"
        )
        
        # Subscribe to log channels using pattern
        await self.pubsub.psubscribe("evaluation:*:logs")
        
        logger.info("Storage worker started, listening for events...")
        
        # Process messages
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                await self.handle_message(message)
                
            if not self.running:
                break
    
    async def handle_message(self, message):
        """Process a single event message"""
        channel = message['channel'].decode('utf-8')
        try:
            data = json.loads(message['data'])
            
            # Check if this is a log event
            if ':logs' in channel:
                await self.handle_log_event(channel, data)
            else:
                logger.info(f"Received event on {channel}: {data.get('eval_id', 'unknown')}")
                
                if channel == "evaluation:queued":
                    await self.handle_evaluation_queued(data)
                elif channel == "evaluation:running":
                    await self.handle_evaluation_running(data)
                elif channel == "evaluation:completed":
                    await self.handle_evaluation_completed(data)
                elif channel == "evaluation:failed":
                    await self.handle_evaluation_failed(data)
                
            self.events_processed += 1
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
        except Exception as e:
            logger.error(f"Error handling message on {channel}: {e}")
    
    async def handle_log_event(self, channel: str, data: Dict[str, Any]):
        """Handle log events with batching"""
        eval_id = data.get('eval_id')
        if not eval_id:
            return
        
        # Add to buffer
        if eval_id not in self.log_buffers:
            self.log_buffers[eval_id] = []
        
        self.log_buffers[eval_id].append(data)
        
        # Check if we should flush
        should_flush = (
            len(self.log_buffers[eval_id]) >= self.log_batch_size or
            data.get('is_final', False)
        )
        
        if should_flush:
            # Cancel any existing timer
            if eval_id in self.log_buffer_timers:
                self.log_buffer_timers[eval_id].cancel()
                del self.log_buffer_timers[eval_id]
            
            # Flush immediately
            await self.flush_logs(eval_id)
        else:
            # Schedule a flush if not already scheduled
            if eval_id not in self.log_buffer_timers:
                timer = asyncio.create_task(self.delayed_flush(eval_id))
                self.log_buffer_timers[eval_id] = timer
    
    async def delayed_flush(self, eval_id: str):
        """Flush logs after timeout"""
        await asyncio.sleep(self.log_batch_timeout)
        await self.flush_logs(eval_id)
        if eval_id in self.log_buffer_timers:
            del self.log_buffer_timers[eval_id]
    
    async def flush_logs(self, eval_id: str):
        """Flush buffered logs to storage"""
        if eval_id not in self.log_buffers or not self.log_buffers[eval_id]:
            return
        
        logs = self.log_buffers[eval_id]
        self.log_buffers[eval_id] = []
        
        try:
            # Combine all log content
            combined_logs = "\n".join(log['content'] for log in logs)
            
            # Update storage service
            response = await self.client.post(
                f"{self.storage_url}/evaluations/{eval_id}/logs",
                json={
                    "content": combined_logs,
                    "append": True,  # Append to existing logs
                    "timestamp": logs[-1]['timestamp'],  # Use last timestamp
                    "last_update": logs[-1]['timestamp']  # Update last activity time
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Flushed {len(logs)} log entries for {eval_id}")
                
                # Also update Redis cache
                await self.redis.setex(
                    f"logs:{eval_id}:latest",
                    300,  # 5 minute TTL
                    combined_logs
                )
            else:
                logger.error(f"Failed to flush logs for {eval_id}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error flushing logs for {eval_id}: {e}")
    
    async def handle_evaluation_queued(self, data: Dict[str, Any]):
        """Handle evaluation queued event"""
        eval_id = data.get('eval_id')
        code = data.get('code')
        
        if not eval_id or not code:
            logger.error(f"Missing required fields in queued event: {data}")
            return
        
        try:
            # Call storage service API to create evaluation
            response = await self.client.post(
                f"{self.storage_url}/evaluations",
                json={
                    "id": eval_id,
                    "code": code,
                    "language": data.get('language', 'python'),
                    "status": EvaluationStatus.QUEUED.value,
                    "metadata": data.get('metadata', {})
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Stored queued evaluation {eval_id}")
                # Publish confirmation event (other services can listen)
                await self.redis.publish(
                    "storage:evaluation:created",
                    json.dumps({"eval_id": eval_id, "timestamp": datetime.now(timezone.utc).isoformat()})
                )
            else:
                logger.error(f"Failed to store queued evaluation {eval_id}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error storing queued evaluation {eval_id}: {e}")
    
    async def handle_evaluation_running(self, data: Dict[str, Any]):
        """Handle evaluation running event - store executor assignment in Redis"""
        eval_id = data.get('eval_id')
        executor_id = data.get('executor_id')
        container_id = data.get('container_id')
        
        if not eval_id or not executor_id:
            logger.error(f"Missing required fields in running event: {data}")
            return
        
        try:
            # Update PostgreSQL status to running
            response = await self.client.put(
                f"{self.storage_url}/evaluations/{eval_id}",
                json={"status": EvaluationStatus.RUNNING.value}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to update status to running for {eval_id}: {response.status_code}")
                return
                
            # Store transient executor info in Redis
            running_info = {
                "executor_id": executor_id,
                "container_id": container_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "timeout": data.get('timeout', 30)
            }
            
            # Set TTL to timeout + 60 second buffer
            ttl = data.get('timeout', 30) + 60
            await self.redis.setex(
                f"eval:{eval_id}:running",
                ttl,
                json.dumps(running_info)
            )
            
            # Add to running evaluations set
            await self.redis.sadd("running_evaluations", eval_id)
            
            logger.info(f"Stored running info for {eval_id} on {executor_id}")
            
            # Publish confirmation event
            await self.redis.publish(
                "storage:evaluation:running",
                json.dumps({
                    "eval_id": eval_id,
                    "executor_id": executor_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            )
            
        except Exception as e:
            logger.error(f"Error handling running evaluation {eval_id}: {e}")
    
    async def handle_evaluation_completed(self, data: Dict[str, Any]):
        """Handle evaluation completed event"""
        eval_id = data.get('eval_id')
        
        if not eval_id:
            logger.error(f"Missing eval_id in completed event: {data}")
            return
        
        try:
            # Call storage service API to update evaluation
            response = await self.client.put(
                f"{self.storage_url}/evaluations/{eval_id}",
                json={
                    "status": EvaluationStatus.COMPLETED.value,
                    "output": data.get('output', ''),
                    "error": data.get('error', ''),
                    "metadata": data.get('metadata', {})
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Updated completed evaluation {eval_id}")
                
                # Clean up Redis running info
                await self.redis.delete(f"eval:{eval_id}:running")
                await self.redis.srem("running_evaluations", eval_id)
                
                # Flush any remaining logs
                if eval_id in self.log_buffers:
                    await self.flush_logs(eval_id)
                    del self.log_buffers[eval_id]
                if eval_id in self.log_buffer_timers:
                    self.log_buffer_timers[eval_id].cancel()
                    del self.log_buffer_timers[eval_id]
                
                # Publish confirmation event
                await self.redis.publish(
                    "storage:evaluation:updated",
                    json.dumps({
                        "eval_id": eval_id,
                        "status": EvaluationStatus.COMPLETED.value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                )
            else:
                logger.error(f"Failed to update completed evaluation {eval_id}")
                
        except Exception as e:
            logger.error(f"Error updating completed evaluation {eval_id}: {e}")
    
    async def handle_evaluation_failed(self, data: Dict[str, Any]):
        """Handle evaluation failed event"""
        eval_id = data.get('eval_id')
        error = data.get('error', 'Unknown error')
        
        if not eval_id:
            logger.error(f"Missing eval_id in failed event: {data}")
            return
        
        try:
            # Call storage service API to update evaluation
            response = await self.client.put(
                f"{self.storage_url}/evaluations/{eval_id}",
                json={
                    "status": EvaluationStatus.FAILED.value,
                    "error": error
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Updated failed evaluation {eval_id}")
                
                # Clean up Redis running info
                await self.redis.delete(f"eval:{eval_id}:running")
                await self.redis.srem("running_evaluations", eval_id)
                
                # Publish confirmation event
                await self.redis.publish(
                    "storage:evaluation:updated",
                    json.dumps({
                        "eval_id": eval_id,
                        "status": EvaluationStatus.FAILED.value,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                )
            else:
                logger.error(f"Failed to update failed evaluation {eval_id}")
                
        except Exception as e:
            logger.error(f"Error updating failed evaluation {eval_id}: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check worker health"""
        try:
            # Check Redis connection
            await self.redis.ping()
            redis_healthy = True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            redis_healthy = False
        
        # Check storage service health
        storage_healthy = False
        try:
            response = await self.client.get(f"{self.storage_url}/health")
            storage_healthy = response.status_code == 200
        except Exception as e:
            logger.warning(f"Storage health check failed: {e}")
            storage_healthy = False
        
        return {
            "healthy": redis_healthy and storage_healthy,
            "redis": "healthy" if redis_healthy else "unhealthy",
            "storage": "healthy" if storage_healthy else "unhealthy",
            "events_processed": self.events_processed,
            "uptime": "TODO"  # Add uptime tracking
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Storage worker shutting down...")
        self.running = False
        await self.pubsub.unsubscribe()
        await self.redis.close()
        await self.client.aclose()

# Health endpoint using FastAPI
# NOTE: This adds ~20-30MB overhead for a single endpoint. Consider alternatives:
# 1. Kubernetes exec probes (no HTTP needed)
# 2. Docker HEALTHCHECK with exit codes
# 3. Simple asyncio HTTP server (~5MB)
# We use FastAPI for consistency and future extensibility (metrics, ready vs live)
from fastapi import FastAPI
import uvicorn
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Use structured logger
logger = structlog.get_logger()

def create_health_app(worker: StorageWorker) -> FastAPI:
    """Create health check app with worker dependency"""
    app = FastAPI(title="Storage Worker Health")
    
    @app.get("/health")
    async def health():
        """
        Health check endpoint for monitoring.
        
        Future enhancements:
        - Add /ready endpoint for readiness probes
        - Include detailed subsystem health
        - Add Prometheus metrics endpoint
        """
        status = await worker.health_check()
        # Log health check with structured data
        logger.info("health_check_requested", **status)
        return status
    
    return app

async def run_health_server_async(worker: StorageWorker):
    """Run health server using async uvicorn"""
    health_app = create_health_app(worker)
    
    config = uvicorn.Config(
        health_app, 
        host="0.0.0.0", 
        port=8085, 
        log_level="error"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Main entry point"""
    worker = StorageWorker()
    
    try:
        # Run both health server and worker concurrently
        await asyncio.gather(
            worker.start(),
            run_health_server_async(worker)
        )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await worker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())