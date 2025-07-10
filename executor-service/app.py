"""
Executor Service - Creates isolated containers for code execution
Uses Docker proxy for security-limited container creation
"""

import os
import json
import asyncio
from typing import Dict, Optional
from datetime import datetime, timezone
import logging
import threading
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
import uvicorn
import docker
from docker.errors import ImageNotFound
import redis.asyncio as redis

# Import shared event types
from shared.generated.python.events import EvaluationCompletedEvent, EventChannels

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables
redis_client: Optional[redis.Redis] = None
event_handler_task = None
docker_events_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global redis_client, event_handler_task, docker_events_thread, docker_client

    logger.info(f"Starting up executor service {executor_id}")

    # Initialize Docker client
    try:
        docker_client = docker.from_env()
        docker_client.ping()
        logger.info("Connected to Docker daemon successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Docker daemon: {e}")
        # Docker is critical for executor service
        raise

    # Connect to Redis
    try:
        logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")
        redis_client = await redis.from_url(
            f"redis://{redis_host}:{redis_port}", encoding="utf-8", decode_responses=True
        )
        await redis_client.ping()
        logger.info("Connected to Redis successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None

    # Start Docker events handler
    event_handler_task = asyncio.create_task(process_docker_events())

    yield

    # Shutdown
    logger.info("Shutting down executor service")

    # Cancel event handler
    if event_handler_task:
        event_handler_task.cancel()
        try:
            await event_handler_task
        except asyncio.CancelledError:
            pass

    # Close Redis connection
    if redis_client:
        await redis_client.close()


app = FastAPI(
    title="Crucible Executor Service",
    description="Creates isolated containers for secure code execution using Docker",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Docker client will be initialized on startup
docker_client = None
executor_id = os.getenv("HOSTNAME", "executor")

# Redis connection for publishing events
redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client: Optional[redis.Redis] = None

# Store running containers for monitoring and control
running_containers: Dict[str, docker.models.containers.Container] = {}
completed_containers = set()  # Track which containers we've already published completion for

# Track last log timestamp for incremental streaming
container_log_timestamps: Dict[str, datetime] = {}
# Track log sequence numbers for ordering
container_log_sequences: Dict[str, int] = {}


class ExecuteRequest(BaseModel):
    """Request to execute code"""

    eval_id: str
    code: str
    timeout: int = 30


class ExecuteResponse(BaseModel):
    """Response from execution"""

    eval_id: str
    status: str  # running, completed, failed, timeout, killed
    output: str = ""
    error: str = ""
    exit_code: int = -1
    executor_id: str = executor_id
    container_id: Optional[str] = None


class LogsResponse(BaseModel):
    """Response for container logs"""

    eval_id: str
    output: str
    error: str = ""
    is_running: bool
    exit_code: Optional[int] = None


class KillResponse(BaseModel):
    """Response for kill operation"""

    eval_id: str
    success: bool
    message: str


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check if we can reach Docker
        docker_client.ping()
        docker_status = "healthy"
    except Exception as e:
        docker_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if docker_status == "healthy" else "degraded",
        "service": "executor",
        "executor_id": executor_id,
        "docker_status": docker_status,
    }


@app.get("/capacity")
async def capacity():
    """Check if executor can accept new tasks - Kubernetes readiness probe pattern"""
    max_concurrent = int(os.getenv("MAX_CONCURRENT_EXECUTIONS", "1"))
    current_running = len(running_containers)
    
    can_accept = current_running < max_concurrent
    
    return {
        "executor_id": executor_id,
        "can_accept": can_accept,
        "running": current_running,
        "max_concurrent": max_concurrent,
        "available_slots": max(0, max_concurrent - current_running)
    }


def start_container(eval_id: str, code: str, timeout: int) -> Dict:
    """Start code execution in an isolated container"""
    try:
        # Get executor image from environment
        executor_image = os.getenv("EXECUTOR_IMAGE", "python:3.11-slim")
        
        # Pull image if not present
        try:
            docker_client.images.get(executor_image)
        except ImageNotFound:
            logger.info(f"Pulling {executor_image} image...")
            docker_client.images.pull(executor_image)

        # Create and run container
        logger.info(f"Creating container for eval {eval_id} using image {executor_image}")
        container = docker_client.containers.run(
            image=executor_image,
            command=["python", "-u", "-c", code],
            detach=True,
            remove=False,  # We'll remove manually after completion
            tty=True,  # Allocate a pseudo-TTY to force line buffering
            # Security restrictions
            mem_limit="512m",
            nano_cpus=500000000,  # 0.5 CPU
            network_mode="none",  # No network
            read_only=True,
            security_opt=["no-new-privileges:true"],
            # Volumes - only tmp for writing
            tmpfs={"/tmp": "size=100M"},
            environment={"PYTHONUNBUFFERED": "1", "EVAL_ID": eval_id},
            labels={
                "eval_id": eval_id,
                "executor": executor_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "timeout": str(timeout),
            },
        )

        # Store the container reference
        running_containers[eval_id] = container
        container_log_sequences[eval_id] = 0
        container_log_timestamps[eval_id] = datetime.now(timezone.utc)

        logger.info(f"Container {eval_id} started with ID {container.id[:12]}")

        # Schedule timeout cleanup
        asyncio.create_task(handle_timeout(eval_id, timeout))

        # Start log streaming
        asyncio.create_task(stream_container_logs(eval_id))

        # Start heartbeat monitoring
        asyncio.create_task(emit_heartbeat(eval_id))

        return {
            "eval_id": eval_id,
            "status": "running",
            "output": "",
            "error": "",
            "exit_code": -1,
            "executor_id": executor_id,
            "container_id": container.id[:12],
        }

    except Exception as e:
        logger.error(f"Failed to start container for {eval_id}: {e}")
        return {
            "eval_id": eval_id,
            "status": "failed",
            "output": "",
            "error": f"Container creation failed: {str(e)}",
            "exit_code": -1,
            "executor_id": executor_id,
            "container_id": None,
        }


async def emit_heartbeat(eval_id: str):
    """Emit periodic heartbeat messages to logs to indicate container is still alive"""
    try:
        while eval_id in running_containers:
            await asyncio.sleep(30)  # Every 30 seconds

            container = running_containers.get(eval_id)
            if not container:
                break

            try:
                container.reload()
                if container.status not in ["running", "restarting"]:
                    break

                # Emit heartbeat to logs
                if redis_client:
                    heartbeat_msg = (
                        f"[HEARTBEAT] Container still running (status: {container.status})"
                    )
                    seq = container_log_sequences.get(eval_id, 0) + 1
                    container_log_sequences[eval_id] = seq

                    log_event = {
                        "eval_id": eval_id,
                        "sequence": seq,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "content": heartbeat_msg,
                        "executor_id": executor_id,
                        "is_heartbeat": True,
                    }

                    await redis_client.publish(f"evaluation:{eval_id}:logs", json.dumps(log_event))

                    # Update last activity timestamp
                    await redis_client.setex(
                        f"logs:{eval_id}:last_heartbeat",
                        300,  # 5 minute TTL
                        datetime.now(timezone.utc).isoformat(),
                    )

                    logger.debug(f"Heartbeat sent for {eval_id}")

            except Exception as e:
                logger.error(f"Error sending heartbeat for {eval_id}: {e}")

    except Exception as e:
        logger.error(f"Fatal error in heartbeat for {eval_id}: {e}")
    finally:
        logger.info(f"Heartbeat monitoring ended for {eval_id}")


async def stream_container_logs(eval_id: str):
    """Stream container logs to Redis in real-time"""
    container = running_containers.get(eval_id)
    if not container:
        return

    logger.info(f"Starting log streaming for {eval_id}")
    last_timestamp = container_log_timestamps.get(eval_id, datetime.now(timezone.utc))

    try:
        while eval_id in running_containers:
            await asyncio.sleep(0.5)  # Check every 500ms

            try:
                container.reload()
                if container.status not in ["running", "created"]:
                    break

                # Get logs since last check
                # Docker expects naive datetimes, not timezone-aware
                current_time = datetime.now()
                last_timestamp_naive = last_timestamp.replace(tzinfo=None) if last_timestamp.tzinfo else last_timestamp
                logs = container.logs(
                    stdout=True, stderr=True, since=last_timestamp_naive, until=current_time
                )
                if logs:
                    log_text = logs.decode("utf-8", errors="replace")
                    if log_text.strip():
                        # Increment sequence number
                        seq = container_log_sequences.get(eval_id, 0) + 1
                        container_log_sequences[eval_id] = seq

                        # Publish to Redis
                        if redis_client:
                            log_event = {
                                "eval_id": eval_id,
                                "sequence": seq,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "content": log_text,
                                "executor_id": executor_id,
                            }

                            await redis_client.publish(
                                f"evaluation:{eval_id}:logs", json.dumps(log_event)
                            )

                            # Also cache in Redis for quick access
                            await redis_client.setex(
                                f"logs:{eval_id}:latest",
                                300,  # 5 minute TTL
                                log_text,
                            )

                            logger.debug(f"Published log chunk {seq} for {eval_id}")

                        # Update last timestamp (keep as aware for storage)
                        last_timestamp = datetime.now(timezone.utc)
                        container_log_timestamps[eval_id] = last_timestamp

            except Exception as e:
                logger.error(f"Error streaming logs for {eval_id}: {e}")

    except Exception as e:
        logger.error(f"Fatal error in log streaming for {eval_id}: {e}")
    finally:
        logger.info(f"Log streaming ended for {eval_id}")
        # Clean up tracking
        container_log_sequences.pop(eval_id, None)
        container_log_timestamps.pop(eval_id, None)


async def handle_timeout(eval_id: str, timeout: int):
    """Handle container timeout"""
    await asyncio.sleep(timeout)

    container = running_containers.get(eval_id)
    if container:
        try:
            container.reload()
            if container.status == "running":
                logger.info(f"Timeout reached for {eval_id}, stopping container")
                container.stop(timeout=5)
        except Exception as e:
            logger.error(f"Error handling timeout for {eval_id}: {e}")


async def get_container_logs(eval_id: str) -> Dict:
    """Get logs from a container"""
    container = running_containers.get(eval_id)
    if not container:
        return {
            "eval_id": eval_id,
            "output": "",
            "error": "Container not found",
            "is_running": False,
            "exit_code": None,
        }

    try:
        container.reload()

        # Get logs using stream for real-time output
        # Using stream=True returns a generator that yields log lines as they become available
        log_lines = []
        try:
            # Get logs as a stream (generator) instead of waiting for all output
            log_stream = container.logs(stdout=True, stderr=True, stream=True, follow=False)
            for line in log_stream:
                log_lines.append(line.decode("utf-8", errors="replace"))
        except Exception as e:
            logger.warning(f"Error streaming logs: {e}")
            # Fallback to non-streaming logs
            logs = container.logs(stdout=True, stderr=True)
            output = logs.decode("utf-8", errors="replace")
        else:
            output = "".join(log_lines)

        # Check if still running
        is_running = container.status in ["running", "created"]
        exit_code = None

        if container.status == "exited":
            exit_code = container.attrs["State"]["ExitCode"]

            # Note: Completion events are now published by the Docker events handler
            # This endpoint only returns logs for polling clients

            # Clean up if container is done and we've already published the event
            if eval_id in completed_containers:
                running_containers.pop(eval_id, None)
                try:
                    container.remove(force=True)
                except docker.errors.NotFound:
                    pass  # Container already removed
                except Exception as e:
                    logger.warning(f"Failed to remove container: {e}")

        return {
            "eval_id": eval_id,
            "output": output,
            "error": "",
            "is_running": is_running,
            "exit_code": exit_code,
        }

    except Exception as e:
        logger.error(f"Error getting logs for {eval_id}: {e}")
        return {
            "eval_id": eval_id,
            "output": "",
            "error": str(e),
            "is_running": False,
            "exit_code": None,
        }


def kill_container(eval_id: str) -> Dict:
    """Kill a running container"""
    container = running_containers.get(eval_id)
    if not container:
        return {"eval_id": eval_id, "success": False, "message": "Container not found"}

    try:
        container.kill()
        container.remove(force=True)
        running_containers.pop(eval_id, None)

        logger.info(f"Killed container for {eval_id}")
        return {"eval_id": eval_id, "success": True, "message": "Container killed successfully"}

    except Exception as e:
        logger.error(f"Error killing container {eval_id}: {e}")
        return {"eval_id": eval_id, "success": False, "message": str(e)}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """
    Start code execution in an isolated container.
    Returns immediately with running status.
    """
    logger.info(f"Received execution request {request.eval_id}")

    # Check if already running
    if request.eval_id in running_containers:
        return ExecuteResponse(
            eval_id=request.eval_id,
            status="failed",
            error="Evaluation already running",
            executor_id=executor_id,
        )

    # Start the container
    result = start_container(request.eval_id, request.code, request.timeout)

    return ExecuteResponse(**result)


@app.get("/logs/{eval_id}", response_model=LogsResponse)
async def get_logs(eval_id: str):
    """Get current logs from a running or completed container"""
    result = await get_container_logs(eval_id)
    return LogsResponse(**result)


@app.post("/kill/{eval_id}", response_model=KillResponse)
async def kill_execution(eval_id: str):
    """Kill a running container"""
    result = kill_container(eval_id)
    return KillResponse(**result)


@app.get("/status")
async def status():
    """Get executor service status"""
    try:
        # Get currently running containers
        running = []
        for eval_id, container in running_containers.items():
            try:
                container.reload()
                running.append(
                    {
                        "eval_id": eval_id,
                        "container_id": container.id[:12],
                        "status": container.status,
                        "created": container.labels.get("created_at", "unknown"),
                    }
                )
            except docker.errors.NotFound:
                # Container was removed
                running_containers.pop(eval_id, None)
            except Exception as e:
                logger.warning(f"Failed to reload container {eval_id}: {e}")

        # List recent containers we created
        containers = docker_client.containers.list(
            all=True, filters={"label": f"executor={executor_id}"}, limit=10
        )

        recent_executions = []
        for container in containers:
            recent_executions.append(
                {
                    "eval_id": container.labels.get("eval_id", "unknown"),
                    "status": container.status,
                    "created": container.labels.get("created_at", "unknown"),
                }
            )

        return {
            "executor_id": executor_id,
            "status": "healthy",
            "running_count": len(running),
            "running_executions": running,
            "recent_executions": recent_executions,
            "docker_host": os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock"),
        }

    except Exception as e:
        return {"executor_id": executor_id, "status": "error", "error": str(e)}


@app.get("/running")
async def list_running():
    """List all currently running executions"""
    running = []
    for eval_id, container in list(running_containers.items()):
        try:
            container.reload()
            running.append(
                {
                    "eval_id": eval_id,
                    "container_id": container.id[:12],
                    "status": container.status,
                    "created": container.labels.get("created_at", "unknown"),
                    "timeout": container.labels.get("timeout", "unknown"),
                }
            )
        except Exception:
            # Container might have been removed
            running_containers.pop(eval_id, None)

    return {"running_executions": running, "count": len(running)}


# OpenAPI endpoints
@app.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml():
    """Get OpenAPI specification in YAML format"""
    from fastapi.openapi.utils import get_openapi
    import yaml

    openapi_schema = get_openapi(
        title=app.title, version=app.version, description=app.description, routes=app.routes
    )

    yaml_content = yaml.dump(openapi_schema, sort_keys=False)
    return Response(content=yaml_content, media_type="application/yaml")


async def process_docker_events():
    """Process Docker events to detect container completion"""
    global redis_client

    logger.info("Docker events handler started")

    # Create a queue for events from the sync thread
    event_queue = asyncio.Queue()

    # Start the sync event processor in a thread
    loop = asyncio.get_event_loop()
    event_thread = threading.Thread(
        target=_process_events_sync, args=(event_queue, loop), daemon=True
    )
    event_thread.start()

    # Process events from the queue
    while True:
        try:
            # Wait for events from the sync thread
            eval_id, container = await event_queue.get()

            # Handle the completion in the async context
            await _handle_container_completion(eval_id, container)

        except Exception as e:
            logger.error(f"Error processing container completion: {e}")


def _process_events_sync(event_queue, loop):
    """Synchronous event processing (runs in thread)"""
    filters = {"type": "container", "label": f"executor={executor_id}"}

    logger.info(f"Docker events listener started with filters: {filters}")

    while True:
        try:
            for event in docker_client.events(decode=True, filters=filters):
                try:
                    action = event.get("Action", "")
                    actor = event.get("Actor", {})
                    attributes = actor.get("Attributes", {})

                    # Handle container death
                    if action in ["die", "stop"]:
                        eval_id = attributes.get("eval_id")
                        if eval_id:
                            logger.info(f"Container {eval_id} {action} event received")
                            
                            # Try to get container from our tracking
                            container = running_containers.get(eval_id)
                            
                            # If not in our dict, try Docker API
                            if not container:
                                try:
                                    # Use container ID from event
                                    container_id = event.get("id") or event.get("Actor", {}).get("ID")
                                    if container_id:
                                        container = docker_client.containers.get(container_id)
                                        logger.info(f"Retrieved container {eval_id} from Docker API")
                                except Exception as e:
                                    logger.warning(f"Could not retrieve container {eval_id}: {e}")
                                    # Still process the event with None container
                                    container = None
                            
                            # ALWAYS queue the event, even with None container
                            asyncio.run_coroutine_threadsafe(
                                event_queue.put((eval_id, container)), loop
                            )

                except Exception as e:
                    logger.error(f"Error processing Docker event: {e}")

        except Exception as e:
            logger.error(f"Docker events stream error: {e}")
            time.sleep(5)
            logger.info("Restarting Docker events stream...")


async def _handle_container_completion(eval_id: str, container):
    """Handle container completion - extract logs and publish event"""
    global redis_client

    try:
        logger.info(f"Processing completion for container {eval_id} (container={'exists' if container else 'None'})")
        
        # Initialize defaults
        output = ""
        error = ""
        exit_code = -1
        
        if container:
            try:
                # Normal path - we have the container
                container.reload()
                exit_code = container.attrs.get("State", {}).get("ExitCode", -1)
                # TODO: Consider using stream=True with logs() to properly separate stdout/stderr
                # Current approach mixes both streams together, making it impossible to distinguish
                # between normal output and error messages. Docker's stream API can provide this
                # but requires more complex parsing of the multiplexed stream format.
                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
                # Put all logs in error field if exit code != 0
                if exit_code == 0:
                    output = logs
                    error = ""
                else:
                    output = ""
                    error = logs
            except docker.errors.NotFound:
                logger.warning(f"Container {eval_id} was removed before we could get logs")
                error = "Container was removed before logs could be retrieved"
            except Exception as e:
                logger.error(f"Error retrieving logs for {eval_id}: {e}")
                error = f"Error retrieving logs: {str(e)}"
        else:
            # No container object - we missed it entirely
            logger.warning(f"Processing completion for {eval_id} without container object")
            error = "Container exited before logs could be captured"

        # Determine final status
        if exit_code == 0:
            status = "completed"
        else:
            # All non-zero exit codes are failures (including timeout 124/143, OOM 137, etc.)
            status = "failed"

        # Publish final logs before completion event
        if redis_client and (output or error):
            # Increment sequence for final logs
            seq = container_log_sequences.get(eval_id, 0) + 1
            log_event = {
                "eval_id": eval_id,
                "sequence": seq,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "content": output + ("\n" + error if error else ""),
                "executor_id": executor_id,
                "is_final": True,
            }

            await redis_client.publish(f"evaluation:{eval_id}:logs", json.dumps(log_event))

        # Publish completion event
        if redis_client:
            event = EvaluationCompletedEvent(
                eval_id=eval_id,
                status=status,
                output=output,
                error=error,
                exit_code=exit_code,
                executor_id=executor_id,
                completed_at=datetime.now(timezone.utc),
            )

            # Determine the channel based on status
            if status == "completed":
                channel = EventChannels.EVALUATION_COMPLETED
            else:
                channel = EventChannels.EVALUATION_FAILED

            await redis_client.publish(channel, event.model_dump_json())

            logger.info(f"Published {status} event for {eval_id} (exit code: {exit_code})")

        # Clean up
        running_containers.pop(eval_id, None)
        completed_containers.add(eval_id)

        # Only try to remove container if we have a reference
        if container:
            try:
                container.remove(force=True)
                logger.debug(f"Removed container for {eval_id}")
            except docker.errors.NotFound:
                logger.debug(f"Container {eval_id} already removed")
            except Exception as e:
                logger.error(f"Failed to remove container {eval_id}: {e}")

    except Exception as e:
        logger.error(f"Error handling container completion for {eval_id}: {e}")


# OpenAPI export is handled elsewhere, old startup/shutdown events removed
# Using lifespan context manager instead

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8083)
