"""
Worker Service - Uses existing execution engines to process tasks
This worker pulls tasks from the queue service and executes them.
"""
import asyncio
import httpx
import logging
import os
import sys
from pathlib import Path
from typing import Dict
import structlog

# Add src to path so we can import existing components
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import execution engines
from src.execution_engine.execution import DockerEngine, GVisorEngine
from src.shared.events import EventBus, EventTypes

# Configure structured logging
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class Worker:
    def __init__(self):
        self.queue_url = os.getenv("QUEUE_SERVICE_URL", "http://queue:8081")
        self.api_key = os.getenv("API_KEY")
        self.api_url = os.getenv("API_SERVICE_URL", "http://api:8080")
        
        # HTTP client for queue communication
        self.client = httpx.AsyncClient(
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=30.0
        )
        
        # Initialize execution engines
        self._init_engines()
        
        # Event bus for notifications
        self.event_bus = EventBus()
        
        self.running = True
        self.worker_id = os.getenv("HOSTNAME", "worker-1")
        
    def _init_engines(self):
        """Initialize available execution engines"""
        self.engines = {}
        
        # Try Docker first (most common)
        try:
            self.engines["docker"] = DockerEngine()
            logger.info("docker_engine_initialized")
        except Exception as e:
            logger.warning("docker_engine_unavailable", error=str(e))
        
        # Try gVisor if on Linux
        import platform
        if platform.system() == "Linux":
            try:
                self.engines["gvisor"] = GVisorEngine()
                logger.info("gvisor_engine_initialized")
            except Exception as e:
                logger.warning("gvisor_engine_unavailable", error=str(e))
        
        if not self.engines:
            logger.error("no_execution_engines_available")
            raise RuntimeError("No execution engines available")
    
    async def process_task(self, task: Dict):
        """Execute a single task using the appropriate engine"""
        eval_id = task["eval_id"]
        code = task["code"]
        engine_name = task.get("engine", "docker")
        
        log = logger.bind(eval_id=eval_id, engine=engine_name, worker=self.worker_id)
        log.info("processing_task_started")
        
        try:
            # Get appropriate engine
            engine = self.engines.get(engine_name)
            if not engine:
                # Fallback to docker if requested engine not available
                engine = self.engines.get("docker")
                if not engine:
                    raise RuntimeError(f"No execution engine available for {engine_name}")
                log.warning("engine_fallback", requested=engine_name, using="docker")
            
            # Execute code (this is sync, matching existing interface)
            result = engine.execute(code, eval_id)
            
            # Report success back to queue
            await self.client.post(
                f"{self.queue_url}/tasks/{eval_id}/complete",
                json={"output": result}
            )
            
            # Emit completion event
            self.event_bus.emit(EventTypes.EVALUATION_COMPLETED, {
                "eval_id": eval_id,
                "result": result,
                "worker_id": self.worker_id
            })
            
            log.info("task_completed_successfully", 
                    status=result.get("status"),
                    output_length=len(result.get("output", "")))
            
        except Exception as e:
            log.error("task_failed", error=str(e), exc_info=True)
            
            # Report failure
            await self.client.post(
                f"{self.queue_url}/tasks/{eval_id}/fail",
                json={"error": str(e)}
            )
            
            # Emit failure event
            self.event_bus.emit(EventTypes.EVALUATION_FAILED, {
                "eval_id": eval_id,
                "error": str(e),
                "worker_id": self.worker_id
            })
    
    async def run(self):
        """Main worker loop"""
        logger.info("worker_started", 
                   worker_id=self.worker_id,
                   engines=list(self.engines.keys()))
        
        consecutive_errors = 0
        
        while self.running:
            try:
                # Pull next task from queue
                response = await self.client.get(f"{self.queue_url}/tasks/next")
                
                if response.status_code == 200:
                    task = response.json()
                    if task:
                        consecutive_errors = 0  # Reset on success
                        await self.process_task(task)
                    else:
                        # No tasks available, wait a bit
                        await asyncio.sleep(1)
                elif response.status_code == 404:
                    # No tasks, this is normal
                    await asyncio.sleep(1)
                else:
                    logger.error("failed_to_get_task", 
                               status_code=response.status_code,
                               response=response.text)
                    consecutive_errors += 1
                    await asyncio.sleep(min(5 * consecutive_errors, 30))
                    
            except httpx.ConnectError:
                logger.error("queue_connection_failed", queue_url=self.queue_url)
                consecutive_errors += 1
                await asyncio.sleep(min(5 * consecutive_errors, 30))
                
            except Exception as e:
                logger.error("worker_error", error=str(e), exc_info=True)
                consecutive_errors += 1
                await asyncio.sleep(min(5 * consecutive_errors, 30))
        
        await self.client.aclose()
        logger.info("worker_stopped", worker_id=self.worker_id)

    async def health_check(self):
        """Health check endpoint data"""
        return {
            "status": "healthy",
            "worker_id": self.worker_id,
            "engines": list(self.engines.keys()),
            "queue_url": self.queue_url
        }

async def main():
    """Main entry point with health check server"""
    worker = Worker()
    
    # Also run a simple health check server
    from fastapi import FastAPI
    import uvicorn
    
    health_app = FastAPI()
    
    @health_app.get("/health")
    async def health():
        return await worker.health_check()
    
    # Run worker and health server concurrently
    async def run_health_server():
        config = uvicorn.Config(
            health_app, 
            host="0.0.0.0", 
            port=8082, 
            log_level="error"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    try:
        # Run both worker loop and health server
        await asyncio.gather(
            worker.run(),
            run_health_server()
        )
    except KeyboardInterrupt:
        logger.info("worker_shutting_down")
        worker.running = False

if __name__ == "__main__":
    asyncio.run(main())