"""
Dispatcher Service - Stateless service that creates Kubernetes Jobs for code evaluation.
Provides a simple HTTP interface for queue workers to request code execution.
"""

import os
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
import uuid
import json
import asyncio
from contextlib import asynccontextmanager
import yaml

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
import uvicorn
import httpx

# Import shared resilient Redis client
from shared.utils.resilient_connections import ResilientRedisClient
from shared.utils.kubernetes_utils import generate_job_name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
KUBERNETES_NAMESPACE = os.getenv("KUBERNETES_NAMESPACE", "crucible")
EXECUTOR_IMAGE = os.getenv("EXECUTOR_IMAGE", "executor-ml")
REGISTRY_PREFIX = os.getenv("REGISTRY_PREFIX", "")  # e.g. "localhost:5000" or "123456.dkr.ecr.region.amazonaws.com"
DEFAULT_IMAGE_TAG = os.getenv("DEFAULT_IMAGE_TAG", "latest")  # Default tag when none specified
MAX_JOB_TTL = int(os.getenv("MAX_JOB_TTL", "3600"))  # 1 hour
JOB_CLEANUP_TTL = int(os.getenv("JOB_CLEANUP_TTL", "300"))  # 5 minutes
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Security configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HOST_OS = os.getenv("HOST_OS", "linux")  # Default to linux, can be set to "darwin" for macOS

# Feature flags
ENABLE_EVENT_MONITORING = os.getenv("ENABLE_EVENT_MONITORING", "true").lower() == "true"


def watch_job_events_sync(event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """
    Synchronous function to watch Kubernetes job events.
    This runs in a thread pool executor and puts events in a queue.
    """
    w = watch.Watch()
    
    try:
        # Watch for job events in our namespace
        for event in w.stream(
            batch_v1.list_namespaced_job,
            namespace=KUBERNETES_NAMESPACE,
            label_selector="app=evaluation",
            _request_timeout=300  # 5 minute timeout, then reconnect
        ):
            # Put event in queue to be processed in main async context
            asyncio.run_coroutine_threadsafe(
                event_queue.put(event),
                loop
            )
    except Exception as e:
        logger.error(f"Watch stream error: {e}")
        raise
    finally:
        w.stop()


async def monitor_job_events(app: FastAPI):
    """
    Background task that watches Kubernetes job events and publishes status updates.
    This replaces the polling-based approach with event-driven updates.
    """
    redis_client = app.state.redis_client
    event_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    
    # Start the watcher in a thread
    watcher_task = loop.run_in_executor(
        None,
        watch_job_events_sync,
        event_queue,
        loop
    )
    
    try:
        while True:
            try:
                # Get event from queue with timeout to check for cancellation
                event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                
                # Process the event in the main async context
                await process_job_event(event, redis_client)
                
            except asyncio.TimeoutError:
                # Check if watcher thread is still running
                if watcher_task.done():
                    # Watcher died, restart it
                    logger.warning("Job watcher thread died, restarting...")
                    watcher_task = loop.run_in_executor(
                        None,
                        watch_job_events_sync,
                        event_queue,
                        loop
                    )
            except Exception as e:
                logger.error(f"Error processing job event: {e}")
                
    except asyncio.CancelledError:
        # Graceful shutdown
        logger.info("Job monitor shutting down")
        raise


async def process_job_event(event: Dict, redis_client: ResilientRedisClient):
    """Process a single job event and publish appropriate Redis events."""
    try:
        event_type = event['type']
        job = event['object']  # This is always a V1Job from the Kubernetes watch stream
        
        # The watch stream always returns V1Job objects from the Kubernetes Python client
        job_name = job.metadata.name
        eval_id = job.metadata.labels.get('eval-id') if job.metadata.labels else None
        
        if not eval_id:
            return  # Not an evaluation job or missing label
        
        # Get status from V1Job object - handle None values safely
        active = job.status.active if job.status and job.status.active else 0
        succeeded = job.status.succeeded if job.status and job.status.succeeded else 0
        failed = job.status.failed if job.status and job.status.failed else 0
        
        # Determine job status
        status = None
        if active > 0:
            status = "running"
        elif succeeded > 0:
            status = "succeeded"
        elif failed > 0:
            status = "failed"
        else:
            status = "pending"
        
        # Check if this is a state change
        state_key = f"job:{job_name}:last_state"
        last_state_bytes = await redis_client.get(state_key)
        last_state = last_state_bytes.decode('utf-8') if last_state_bytes else None
        
        # If state changed or this is a new job, publish event
        if status != last_state:
            await redis_client.setex(state_key, 300, status)  # Cache for 5 minutes
            
            logger.info(f"Job {job_name} state change: {last_state} -> {status}")
            
            if status == "running":
                # Publish running event
                # Get start time and timeout from V1Job object
                start_time = job.status.start_time.isoformat() if job.status and job.status.start_time else None
                timeout = job.spec.active_deadline_seconds if job.spec and job.spec.active_deadline_seconds else 300
                
                event_data = {
                    "eval_id": eval_id,
                    "executor_id": job_name,
                    "container_id": job_name,
                    "timeout": timeout,
                    "started_at": start_time if start_time else datetime.now(timezone.utc).isoformat()
                }
                await redis_client.publish("evaluation:running", json.dumps(event_data))
                logger.info(f"Published evaluation:running event for {eval_id}")
                
            elif status == "succeeded":
                # Get job logs
                logs_result = await get_job_logs_internal(job_name)
                
                # Check exit code to determine if it's truly successful
                exit_code = logs_result.get("exit_code", 0)
                completion_time = job.status.completion_time.isoformat() if job.status and job.status.completion_time else None
                
                if exit_code == 0:
                    # Publish completed event
                    event_data = {
                        "eval_id": eval_id,
                        "output": logs_result.get("logs", ""),
                        "exit_code": exit_code,
                        "metadata": {
                            "job_name": job_name,
                            "completed_at": completion_time if completion_time else datetime.now(timezone.utc).isoformat(),
                            "log_source": logs_result.get("source", "unknown")
                        }
                    }
                    await redis_client.publish("evaluation:completed", json.dumps(event_data))
                    logger.info(f"Published evaluation:completed event for {eval_id} (logs from {logs_result.get('source', 'unknown')})")
                else:
                    # Non-zero exit code means failure
                    event_data = {
                        "eval_id": eval_id,
                        "error": logs_result.get("logs", "Process exited with non-zero code"),
                        "exit_code": exit_code,
                        "metadata": {
                            "job_name": job_name,
                            "failed_at": completion_time if completion_time else datetime.now(timezone.utc).isoformat(),
                            "log_source": logs_result.get("source", "unknown")
                        }
                    }
                    await redis_client.publish("evaluation:failed", json.dumps(event_data))
                    logger.info(f"Published evaluation:failed event for {eval_id} (exit code {exit_code})")
                
            elif status == "failed":
                # Get job logs
                logs_result = await get_job_logs_internal(job_name)
                
                # Publish failed event
                completion_time = job.status.completion_time.isoformat() if job.status and job.status.completion_time else None
                event_data = {
                    "eval_id": eval_id,
                    "error": logs_result.get("logs", "Job failed"),
                    "exit_code": logs_result.get("exit_code", 1),
                    "metadata": {
                        "job_name": job_name,
                        "failed_at": completion_time if completion_time else datetime.now(timezone.utc).isoformat(),
                        "log_source": logs_result.get("source", "unknown")
                    }
                }
                await redis_client.publish("evaluation:failed", json.dumps(event_data))
                logger.info(f"Published evaluation:failed event for {eval_id} (logs from {logs_result.get('source', 'unknown')})")
                
        # Handle job deletion events
        if event_type == "DELETED" and eval_id:
            # Publish cancellation event if job was deleted before completion
            if last_state in ["pending", "running"]:
                await redis_client.publish(
                    "evaluation:cancelled",
                    json.dumps({
                        "eval_id": eval_id,
                        "job_name": job_name,
                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "Job deleted"
                    })
                )
                logger.info(f"Published evaluation:cancelled event for deleted job {job_name}")
                
    except Exception as e:
        logger.error(f"Error processing job event: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    # Startup
    # Initialize Redis client (no need to wait for connection)
    app.state.redis_client = ResilientRedisClient(
        redis_url=REDIS_URL,
        service_name="dispatcher",
        decode_responses=False
    )
    logger.info("Dispatcher service started - Redis will connect when needed")
    
    # Start background job monitoring task if enabled
    monitor_task = None
    if ENABLE_EVENT_MONITORING:
        monitor_task = asyncio.create_task(monitor_job_events(app))
        logger.info("Started Kubernetes job event monitoring")
    else:
        logger.info("Event monitoring disabled - using polling approach")
    
    yield
    
    # Shutdown
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
    
    if hasattr(app.state, 'redis_client'):
        await app.state.redis_client.close()
        logger.info("Dispatcher service shutdown complete")


# Initialize FastAPI with lifespan
app = FastAPI(
    title="Evaluation Dispatcher",
    description="Creates Kubernetes Jobs for code evaluation",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize Kubernetes client
try:
    # Try in-cluster config first (when running in K8s)
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config")
except:
    # Fall back to kubeconfig (for local development)
    try:
        config.load_kube_config()
        logger.info("Loaded local Kubernetes config")
    except Exception as e:
        logger.error(f"Failed to load Kubernetes config: {e}")
        raise

# Create API clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()
node_v1 = client.NodeV1Api()

# Cache for gVisor availability check
gvisor_runtime_available = None
# Cache for available executor images
available_images_cache = None
cache_timestamp = None


# Dependency injection for Redis client
def get_redis_client() -> ResilientRedisClient:
    """Get Redis client from app state."""
    return app.state.redis_client

def load_executor_images() -> Dict[str, str]:
    """Load available executor images from ConfigMap"""
    global available_images_cache, cache_timestamp
    
    # Cache for 30 seconds
    if available_images_cache and cache_timestamp and (datetime.now(timezone.utc) - cache_timestamp).seconds < 30:
        return available_images_cache
    
    try:
        # Read ConfigMap
        config_map = core_v1.read_namespaced_config_map(
            name="executor-images",
            namespace=KUBERNETES_NAMESPACE
        )
        
        # Parse YAML data
        images_yaml = config_map.data.get("images.yaml", "")
        images_data = yaml.safe_load(images_yaml)
        
        # Build image mapping
        image_map = {}
        default_image = None
        
        for img in images_data.get("images", []):
            if img.get("available", True):  # Default to available if not specified
                name = img["name"]
                full_image = img["image"]
                
                image_map[name] = full_image
                
                if img.get("default", False):
                    default_image = full_image
        
        # Set default if none specified
        if not default_image and image_map:
            default_image = list(image_map.values())[0]
        
        if default_image:
            image_map["default"] = default_image
            
        available_images_cache = image_map
        cache_timestamp = datetime.now(timezone.utc)
        
        logger.info(f"Loaded {len(image_map)} executor images from ConfigMap")
        return image_map
        
    except ApiException as e:
        logger.warning(f"Failed to load executor images from ConfigMap: {e}")
        # Fallback to environment variable
        return {"default": EXECUTOR_IMAGE}

# Commented out - no longer needed with registry approach
# def get_latest_executor_image(executor_type: str) -> Optional[str]:
#     """Find the most recent executor image from node image store"""
#     try:
#         # List all nodes
#         nodes = core_v1.list_node()
#         if not nodes.items:
#             return None
#             
#         # Get images from first node (in Kind there's usually just one)
#         node_images = nodes.items[0].status.images
#         
#         # Find images matching the executor type
#         matching_images = []
#         for image in node_images:
#             if image and image.names:  # Check that image and names exist
#                 for name in image.names:
#                     # Handle both "base" and "executor-base" formats
#                     search_pattern = executor_type if executor_type.startswith("executor-") else f"executor-{executor_type}"
#                     
#                     # Match executor images with SHA tags (e.g., executor-ml:6fffbe9ad576...)
#                     # Also handle docker.io/ prefix that kind adds
#                     if (f"crucible-platform/{search_pattern}" in name or f"docker.io/crucible-platform/{search_pattern}" in name) and len(name.split(":")[-1]) >= 12:
#                         # Check if tag looks like a SHA (at least 12 hex chars)
#                         tag = name.split(":")[-1]
#                         if all(c in "0123456789abcdef" for c in tag[:12]):
#                             matching_images.append(name)
#         
#         # Return the first match (most recent)
#         if matching_images:
#             logger.info(f"Found executor image: {matching_images[0]}")
#             return matching_images[0]
#             
#         return None
#     except ApiException as e:
#         logger.error(f"Failed to query node images: {e}")
#         return None

def resolve_executor_image(requested_image: str, available_images: Dict[str, str]) -> str:
    """
    Resolve an executor image name to a full registry path with :latest tag.
    
    Args:
        requested_image: The image name requested (e.g., "executor-base", "base", full path)
        available_images: Dict of known images from configmap
        
    Returns:
        Full image path with registry prefix and tag
    """
    # Check if it's a known image name from configmap
    if requested_image in available_images:
        image = available_images[requested_image]
    # Check if it's already a full image path
    elif "/" in requested_image or ":" in requested_image:
        image = requested_image
    else:
        # Unknown image, use default
        logger.warning(f"Unknown executor image '{requested_image}', using default")
        image = available_images.get("default", EXECUTOR_IMAGE)
    
    # Add registry prefix if configured
    if REGISTRY_PREFIX and not image.startswith(REGISTRY_PREFIX):
        image = f"{REGISTRY_PREFIX}/{image}"
    
    # Add default tag if no tag specified
    if ":" not in image.split("/")[-1]:  # Check last part for tag
        image = f"{image}:{DEFAULT_IMAGE_TAG}"
    
    logger.info(f"Resolved executor image '{requested_image}' to: {image}")
    return image


def check_gvisor_availability():
    """Check if gVisor RuntimeClass is available in the cluster"""
    global gvisor_runtime_available
    
    # Use cached value if available
    if gvisor_runtime_available is not None:
        return gvisor_runtime_available
    
    # Only allow bypassing gVisor check for local development on macOS
    if ENVIRONMENT == "local" and HOST_OS == "darwin":
        gvisor_runtime_available = False
        logger.info("gVisor disabled for local development on macOS")
        return gvisor_runtime_available
    
    # For all other environments (including dev on EKS), check if RuntimeClass exists
    try:
        # Check if gvisor RuntimeClass exists
        node_v1.read_runtime_class("gvisor")
        gvisor_runtime_available = True
        logger.info("gVisor RuntimeClass found - will use for evaluations")
        return True
    except ApiException as e:
        if e.status == 404:
            gvisor_runtime_available = False
            logger.error(
                f"gVisor RuntimeClass not found in {ENVIRONMENT} environment! "
                "All non-local deployments MUST have gVisor installed for security."
            )
            return False
        else:
            # Unexpected error - don't cache
            logger.error(f"Error checking gVisor availability: {e}")
            return False




@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Crucible Dispatcher Service",
        "version": "1.0.0",
        "gvisor_available": gvisor_runtime_available,
        "environment": ENVIRONMENT,
        "description": "Creates and manages Kubernetes Jobs for code evaluation",
        "endpoints": {
            "execute": "/execute",
            "status": "/status/{job_name}",
            "logs": "/logs/{job_name}",
            "images": "/images",
            "health": "/health",
            "ready": "/ready"
        }
    }


@app.get("/images")
async def list_executor_images():
    """List available executor images"""
    images = load_executor_images()
    
    # Transform to list format for API response
    image_list = []
    for name, full_image in images.items():
        if name != "default":
            image_list.append({
                "name": name,
                "image": full_image,
                "default": full_image == images.get("default", "")
            })
    
    return {
        "images": image_list,
        "default": images.get("default", EXECUTOR_IMAGE)
    }


# Request/Response models
class ExecuteRequest(BaseModel):
    eval_id: str = Field(..., description="Unique evaluation ID")
    code: str = Field(..., description="Python code to execute")
    language: str = Field(default="python", description="Programming language")
    timeout: int = Field(default=300, ge=1, le=MAX_JOB_TTL, description="Execution timeout in seconds")
    memory_limit: str = Field(default="512Mi", description="Memory limit (e.g., 512Mi, 1Gi)")
    cpu_limit: str = Field(default="500m", description="CPU limit (e.g., 500m, 1)")
    priority: int = Field(default=0, description="Priority level: 1=high, 0=normal, -1=low")
    executor_image: Optional[str] = Field(default=None, description="Executor image name (e.g., 'python-ml') or full image path")
    
class ExecuteResponse(BaseModel):
    eval_id: str
    job_name: str
    status: str
    message: Optional[str] = None


# Capacity check models
class CapacityRequest(BaseModel):
    memory_limit: str = Field(default="512Mi", description="Memory limit (e.g., 512Mi, 1Gi)")
    cpu_limit: str = Field(default="500m", description="CPU limit (e.g., 500m, 1)")


class CapacityResponse(BaseModel):
    has_capacity: bool
    available_memory_mb: int
    available_cpu_millicores: int
    total_memory_mb: int
    total_cpu_millicores: int
    reason: Optional[str] = None


# Import resource parsing utilities from shared location
from shared.utils.resource_parsing import parse_memory, parse_cpu


def min_resource(limit: str, default: str, resource_type: str) -> str:
    """Return the minimum of limit and default for resource requests.
    
    This ensures that resource requests never exceed limits (Kubernetes requirement).
    """
    if resource_type == "memory":
        limit_mb = parse_memory(limit)
        default_mb = parse_memory(default)
        if limit_mb < default_mb:
            return limit
        return default
    elif resource_type == "cpu":
        limit_mc = parse_cpu(limit)
        default_mc = parse_cpu(default)
        if limit_mc < default_mc:
            return limit
        return default
    return default


@app.post("/capacity/check", response_model=CapacityResponse)
async def check_capacity(request: CapacityRequest):
    """
    Check if the cluster has capacity for a new evaluation with specified resources.
    """
    try:
        # Get ResourceQuota for evaluations
        quota = core_v1.read_namespaced_resource_quota(
            name="evaluation-quota",
            namespace=KUBERNETES_NAMESPACE
        )
        
        # Parse current usage and limits
        memory_limit = quota.status.hard.get("limits.memory", "0")
        memory_used = quota.status.used.get("limits.memory", "0")
        cpu_limit = quota.status.hard.get("limits.cpu", "0")
        cpu_used = quota.status.used.get("limits.cpu", "0")
        
        # Convert to standard units
        total_memory_mb = parse_memory(memory_limit)
        used_memory_mb = parse_memory(memory_used)
        total_cpu_millicores = parse_cpu(cpu_limit)
        used_cpu_millicores = parse_cpu(cpu_used)
        
        available_memory_mb = total_memory_mb - used_memory_mb
        available_cpu_millicores = total_cpu_millicores - used_cpu_millicores
        
        # Check requested resources
        requested_memory_mb = parse_memory(request.memory_limit)
        requested_cpu_millicores = parse_cpu(request.cpu_limit)
        
        # Determine if we have capacity
        has_capacity = (
            available_memory_mb >= requested_memory_mb and
            available_cpu_millicores >= requested_cpu_millicores
        )
        
        reason = None
        if not has_capacity:
            if available_memory_mb < requested_memory_mb:
                reason = f"Insufficient memory: {available_memory_mb}MB available, {requested_memory_mb}MB requested"
            else:
                reason = f"Insufficient CPU: {available_cpu_millicores}m available, {requested_cpu_millicores}m requested"
        
        return CapacityResponse(
            has_capacity=has_capacity,
            available_memory_mb=available_memory_mb,
            available_cpu_millicores=available_cpu_millicores,
            total_memory_mb=total_memory_mb,
            total_cpu_millicores=total_cpu_millicores,
            reason=reason
        )
        
    except ApiException as e:
        if e.status == 404:
            # No resource quota found, assume capacity is available
            logger.warning("No ResourceQuota found, assuming capacity is available")
            return CapacityResponse(
                has_capacity=True,
                available_memory_mb=99999,
                available_cpu_millicores=99999,
                total_memory_mb=99999,
                total_cpu_millicores=99999,
                reason="No resource quota configured"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Failed to check capacity: {str(e)}")


@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    """
    Create a Kubernetes Job to execute the provided code.
    """
    logger.info(f"Creating job for evaluation {request.eval_id}, code length: {len(request.code)} chars, timeout: {request.timeout}s")
    
    # Check gVisor availability and requirements
    use_gvisor = check_gvisor_availability()
    
    # gVisor is mandatory except for local macOS development
    if not use_gvisor and not (ENVIRONMENT == "local" and HOST_OS == "darwin"):
        raise HTTPException(
            status_code=503,
            detail=f"gVisor runtime is required but not available in {ENVIRONMENT} environment. "
                   "Cannot execute evaluations without proper isolation."
        )
    
    # Log info for local macOS development
    if ENVIRONMENT == "local" and HOST_OS == "darwin" and not use_gvisor:
        logger.info(
            "Running without gVisor on local macOS. "
            "This is only acceptable for local development."
        )
    
    # Generate job name using shared utility
    job_name = generate_job_name(request.eval_id)
    
    logger.info(f"Creating job {job_name} for evaluation {request.eval_id}")
    
    # Validate resource limits against cluster capacity
    try:
        # Get ResourceQuota to check total limits
        quota = core_v1.read_namespaced_resource_quota(
            name="evaluation-quota",
            namespace=KUBERNETES_NAMESPACE
        )
        
        # Parse total limits
        total_memory_mb = parse_memory(quota.status.hard.get("limits.memory", "0"))
        total_cpu_millicores = parse_cpu(quota.status.hard.get("limits.cpu", "0"))
        
        # Parse requested resources
        requested_memory_mb = parse_memory(request.memory_limit)
        requested_cpu_millicores = parse_cpu(request.cpu_limit)
        
        # Check if request exceeds total cluster limits
        if requested_memory_mb > total_memory_mb:
            raise HTTPException(
                status_code=400,
                detail=f"Requested memory ({request.memory_limit}) exceeds total cluster limit ({quota.status.hard.get('limits.memory')})"
            )
        
        if requested_cpu_millicores > total_cpu_millicores:
            raise HTTPException(
                status_code=400,
                detail=f"Requested CPU ({request.cpu_limit}) exceeds total cluster limit ({quota.status.hard.get('limits.cpu')})"
            )
            
        logger.info(f"Resource validation passed: {request.memory_limit} memory, {request.cpu_limit} CPU")
        
    except ApiException as e:
        if e.status == 404:
            # No quota configured, allow the request
            logger.warning("No ResourceQuota found, skipping resource validation")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to validate resources: {str(e)}")
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse resource limits: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid resource format: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during resource validation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resource validation error: {str(e)}")
    
    # Determine which executor image to use
    if request.executor_image:
        # Load available images and resolve
        available_images = load_executor_images()
        executor_image = resolve_executor_image(request.executor_image, available_images)
    else:
        # Use default and resolve it too
        available_images = load_executor_images()
        executor_image = resolve_executor_image(EXECUTOR_IMAGE, available_images)
        logger.info(f"No executor specified, using default: {executor_image}")
    
    # Create job manifest
    job = client.V1Job(
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels={
                "app": "evaluation",
                "eval-id": request.eval_id,
                "created-by": "dispatcher"
            },
            annotations={
                "eval-id": request.eval_id,
                "created-at": datetime.now(timezone.utc).isoformat()
            }
        ),
        spec=client.V1JobSpec(
            # Clean up job after completion
            ttl_seconds_after_finished=JOB_CLEANUP_TTL,
            # Maximum runtime
            active_deadline_seconds=request.timeout + 300,  # 5 minute buffer
            # Don't retry on failure (evaluations shouldn't be retried)
            backoff_limit=0,
            # Pod template
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": "evaluation",
                        "eval-id": request.eval_id
                    }
                ),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    # Use gVisor runtime for strong isolation when available
                    runtime_class_name="gvisor" if use_gvisor else None,
                    # Set priority class based on priority level
                    priority_class_name=(
                        "high-priority-evaluation" if request.priority > 0
                        else "low-priority-evaluation" if request.priority < 0
                        else "normal-priority-evaluation"
                    ),
                    # Reduce grace period so timeouts are enforced quickly
                    termination_grace_period_seconds=1,
                    # EKS nodes have ECR permissions via IAM role, no pull secret needed
                    image_pull_secrets=None,
                    # Security context for pod
                    security_context=client.V1PodSecurityContext(
                        run_as_non_root=True,
                        run_as_user=1000,
                        fs_group=1000,
                        seccomp_profile=client.V1SeccompProfile(
                            type="RuntimeDefault"
                        )
                    ),
                    containers=[
                        client.V1Container(
                            name="evaluation",
                            image=executor_image,
                            image_pull_policy="IfNotPresent",  # Don't try to pull if image exists locally
                            command=["timeout_wrapper.sh", str(request.timeout), "python", "-u", "-c", request.code],
                            # Environment variables
                            env=[
                                client.V1EnvVar(name="EVAL_ID", value=request.eval_id),
                                client.V1EnvVar(name="PYTHONUNBUFFERED", value="1")
                            ],
                            # Resource limits
                            resources=client.V1ResourceRequirements(
                                limits={
                                    "memory": request.memory_limit,
                                    "cpu": request.cpu_limit
                                },
                                requests={
                                    # Set requests to be min of limit or reasonable defaults
                                    # This ensures requests <= limits (Kubernetes requirement)
                                    "memory": min_resource(request.memory_limit, "128Mi", "memory"),
                                    "cpu": min_resource(request.cpu_limit, "100m", "cpu")
                                }
                            ),
                            # Security context for container
                            security_context=client.V1SecurityContext(
                                allow_privilege_escalation=False,
                                read_only_root_filesystem=True,
                                run_as_non_root=True,
                                capabilities=client.V1Capabilities(
                                    drop=["ALL"]
                                )
                            ),
                            # Mount temp directory for writing
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="tmp",
                                    mount_path="/tmp"
                                )
                            ]
                        )
                    ],
                    # Volumes
                    volumes=[
                        client.V1Volume(
                            name="tmp",
                            empty_dir=client.V1EmptyDirVolumeSource(
                                size_limit="100Mi"
                            )
                        )
                    ]
                )
            )
        )
    )
    
    try:
        # Create the job
        batch_v1.create_namespaced_job(
            namespace=KUBERNETES_NAMESPACE,
            body=job
        )
        
        logger.info(
            f"Successfully created job {job_name} "
            f"(runtime: {'gVisor' if use_gvisor else 'standard'})"
        )
        
        return ExecuteResponse(
            eval_id=request.eval_id,
            job_name=job_name,
            status="created",
            message=f"Job created successfully"
        )
        
    except ApiException as e:
        logger.error(f"Failed to create job {job_name}: {e}")
        
        # Check if this is a ResourceQuota error
        if e.status == 403 and "exceeded quota" in str(e.body):
            # Return 429 (Too Many Requests) for quota errors so Celery will retry
            raise HTTPException(
                status_code=429,
                detail=f"Resource quota exceeded - too many jobs. Please wait and retry."
            )
        
        raise HTTPException(
            status_code=e.status,
            detail=f"Kubernetes API error: {e.reason}"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating job {job_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@app.get("/status/{job_name}")
async def get_job_status(job_name: str, redis_client: ResilientRedisClient = Depends(get_redis_client)):
    """
    Get the status of a Kubernetes Job.
    """
    try:
        job = batch_v1.read_namespaced_job_status(
            name=job_name,
            namespace=KUBERNETES_NAMESPACE
        )
        
        # Determine status
        previous_status = None
        if job.status.succeeded:
            status = "succeeded"
        elif job.status.failed:
            status = "failed"
        elif job.status.active:
            status = "running"
        else:
            status = "pending"
        
        # Get evaluation ID from job labels
        eval_id = job.metadata.labels.get("eval-id")
        
        # Check if this is a state transition and publish event
        if eval_id:
            try:
                # Check if we've seen this state before
                state_key = f"job:{job_name}:last_state"
                last_state = await redis_client.get(state_key)
                if last_state:
                    last_state = last_state.decode('utf-8')
                
                # If state changed, publish event
                if status != last_state:
                    await redis_client.setex(state_key, 300, status)  # Cache state for 5 minutes
                    
                    if status == "running":
                        # Publish running event with all required fields
                        event_data = {
                            "eval_id": eval_id,
                            "executor_id": job_name,  # Use job name as executor ID
                            "container_id": job_name,  # In K8s, pod name is similar to job name
                            "timeout": job.spec.active_deadline_seconds or 300,
                            "started_at": job.status.start_time.isoformat() if job.status.start_time else datetime.now(timezone.utc).isoformat()
                        }
                        success = await redis_client.publish(
                            "evaluation:running",
                            json.dumps(event_data)
                        )
                        if success:
                            logger.info(f"Published evaluation:running event for {eval_id}")
                    
                    elif status == "succeeded":
                        # Get job logs for the completed evaluation
                        logs_result = await get_job_logs_internal(job_name)
                        
                        # Check exit code to determine if it's truly successful
                        exit_code = logs_result.get("exit_code", 0)
                        
                        if exit_code == 0:
                            # Publish evaluation completed event
                            event_data = {
                                "eval_id": eval_id,
                                "output": logs_result.get("logs", ""),
                                "exit_code": exit_code,
                                "metadata": {
                                    "job_name": job_name,
                                    "completed_at": job.status.completion_time.isoformat() if job.status.completion_time else datetime.now(timezone.utc).isoformat(),
                                    "log_source": logs_result.get("source", "unknown")
                                }
                            }
                            success = await redis_client.publish(
                                "evaluation:completed",
                                json.dumps(event_data)
                            )
                            if success:
                                logger.info(f"Published evaluation:completed event for {eval_id} (logs from {logs_result.get('source', 'unknown')})")
                        else:
                            # Non-zero exit code means failure
                            event_data = {
                                "eval_id": eval_id,
                                "error": logs_result.get("logs", "Process exited with non-zero code"),
                                "exit_code": exit_code,
                                "metadata": {
                                    "job_name": job_name,
                                    "failed_at": job.status.completion_time.isoformat() if job.status.completion_time else datetime.now(timezone.utc).isoformat(),
                                    "log_source": logs_result.get("source", "unknown")
                                }
                            }
                            success = await redis_client.publish(
                                "evaluation:failed",
                                json.dumps(event_data)
                            )
                            if success:
                                logger.info(f"Published evaluation:failed event for {eval_id} (exit code {exit_code})")
                    
                    elif status == "failed":
                        # Get job logs for the failed evaluation
                        logs_result = await get_job_logs_internal(job_name)
                        
                        # Publish evaluation failed event
                        event_data = {
                            "eval_id": eval_id,
                            "error": logs_result.get("logs", "Job failed"),
                            "exit_code": logs_result.get("exit_code", 1),
                            "metadata": {
                                "job_name": job_name,
                                "failed_at": job.status.completion_time.isoformat() if job.status.completion_time else datetime.now(timezone.utc).isoformat(),
                                "log_source": logs_result.get("source", "unknown")
                            }
                        }
                        success = await redis_client.publish(
                            "evaluation:failed",
                            json.dumps(event_data)
                        )
                        if success:
                            logger.info(f"Published evaluation:failed event for {eval_id}")
                        
            except Exception as e:
                logger.error(f"Failed to publish event for job {job_name}: {e}")
                # Continue - don't fail the status check due to event publishing issues
        
        return {
            "job_name": job_name,
            "status": status,
            "start_time": job.status.start_time,
            "completion_time": job.status.completion_time,
            "active": job.status.active,
            "succeeded": job.status.succeeded,
            "failed": job.status.failed,
            "eval_id": eval_id  # Include eval_id in response
        }
        
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(
            status_code=e.status,
            detail=f"Kubernetes API error: {e.reason}"
        )


async def get_logs_from_loki(job_name: str) -> Optional[str]:
    """
    Query Loki for logs from a specific job/pod.
    Returns the log content or None if not found.
    """
    loki_url = os.getenv("LOKI_URL", "http://loki:3100")
    
    try:
        # Query for logs from pods with this job name
        # Using LogQL to search for logs from pods matching the job
        query = f'{{job="fluentbit",kubernetes_namespace_name="{KUBERNETES_NAMESPACE}",kubernetes_pod_name=~"{job_name}.*"}}'
        
        # Time range - last hour should be enough for recent evaluations
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)
        
        params = {
            "query": query,
            "start": int(start_time.timestamp() * 1e9),  # Nanoseconds
            "end": int(end_time.timestamp() * 1e9),
            "limit": 5000,  # Limit number of log lines
            "direction": "forward"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{loki_url}/loki/api/v1/query_range",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data["status"] == "success":
                    if not data["data"]["result"]:
                        logger.info(f"Loki query succeeded but found no streams for {job_name}")
                        return None  # No logs found in Loki
                    
                    # Log the number of streams found for debugging
                    logger.info(f"Loki found {len(data['data']['result'])} log streams for {job_name}")
                    
                    # Combine all log lines from all streams
                    all_logs = []
                    for stream in data["data"]["result"]:
                        for timestamp, line in stream["values"]:
                            # Fluent Bit sends logs as JSON with a "log" field
                            try:
                                import json as json_module
                                log_data = json_module.loads(line)
                                if "log" in log_data:
                                    # Extract the actual log message from the JSON
                                    log_line = log_data["log"]
                                    # Remove the timestamp and stream indicator if present
                                    # Format: "2025-07-24T10:38:29.007631626Z stderr F Error stream test"
                                    parts = log_line.split(" ", 3)
                                    if len(parts) >= 4 and parts[2] in ["F", "P"]:
                                        # Extract just the message part
                                        all_logs.append(parts[3].rstrip("\n"))
                                    else:
                                        # Use the whole line if format doesn't match
                                        all_logs.append(log_line.rstrip("\n"))
                                else:
                                    # If not JSON or no "log" field, use as-is
                                    all_logs.append(line)
                            except json_module.JSONDecodeError:
                                # If not valid JSON, try the old format
                                if " F " in line or " P " in line:
                                    parts = line.split(" F " if " F " in line else " P ", 1)
                                    if len(parts) > 1:
                                        all_logs.append(parts[1])
                                else:
                                    all_logs.append(line)
                    
                    logger.info(f"Collected {len(all_logs)} log lines for {job_name}")
                    # Return None if no logs found, otherwise return the logs (even if empty string)
                    return "\n".join(all_logs) if all_logs else ""
            else:
                logger.warning(f"Loki query failed with status {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.error(f"Error querying Loki for job {job_name}: {e}")
    
    return None


@app.get("/logs/{job_name}")
async def get_job_logs_internal(job_name: str, tail_lines: int = 100):
    """
    Internal function to get logs from a job's pod.
    Returns a dict with logs and exit code.
    """
    try:
        # Find pods for this job
        pods = core_v1.list_namespaced_pod(
            namespace=KUBERNETES_NAMESPACE,
            label_selector=f"job-name={job_name}"
        )
        
        if not pods.items:
            # No pods found - try Loki as fallback
            logger.info(f"No pods found for job {job_name}, checking Loki for logs")
            loki_logs = await get_logs_from_loki(job_name)
            if loki_logs is not None:
                return {
                    "job_name": job_name,
                    "pod_name": "deleted",
                    "logs": loki_logs,
                    "exit_code": 0,  # Default to 0 since we can't determine from Loki
                    "source": "loki"
                }
            return {"logs": "", "exit_code": 1, "message": "No pods found for job and no logs in Loki"}
        
        # Get logs from the first pod
        pod = pods.items[0]
        pod_name = pod.metadata.name
        
        # Get logs
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=KUBERNETES_NAMESPACE,
            tail_lines=tail_lines
        )
        
        # Try to get exit code from container status
        exit_code = 0
        if pod.status.container_statuses:
            container_status = pod.status.container_statuses[0]
            if container_status.state.terminated:
                exit_code = container_status.state.terminated.exit_code or 0
        
        return {
            "job_name": job_name,
            "pod_name": pod_name,
            "logs": logs,
            "exit_code": exit_code,
            "source": "kubernetes"
        }
        
    except ApiException as e:
        if e.status == 404:
            # Pod not found - try Loki
            logger.info(f"Pod not found for job {job_name}, checking Loki for logs")
            loki_logs = await get_logs_from_loki(job_name)
            if loki_logs is not None:
                return {
                    "job_name": job_name,
                    "pod_name": "deleted",
                    "logs": loki_logs,
                    "exit_code": 0,
                    "source": "loki"
                }
        logger.error(f"Failed to get logs for job {job_name}: {e}")
        return {"logs": f"Failed to get logs: {str(e)}", "exit_code": 1}


@app.get("/logs/{job_name}")
async def get_job_logs(job_name: str, tail_lines: int = 100):
    """
    Get logs from a job's pod.
    """
    result = await get_job_logs_internal(job_name, tail_lines)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@app.delete("/job/{job_name}")
async def delete_job(job_name: str, redis_client: ResilientRedisClient = Depends(get_redis_client)):
    """
    Delete a Kubernetes Job and its pods.
    """
    try:
        # First, get the job to extract eval_id from labels
        job = batch_v1.read_namespaced_job(
            name=job_name,
            namespace=KUBERNETES_NAMESPACE
        )
        
        eval_id = job.metadata.labels.get("eval-id")
        
        # Delete the job (this also deletes pods)
        batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=KUBERNETES_NAMESPACE,
            propagation_policy="Foreground"
        )
        
        # Emit cancellation event if we have an eval_id
        if eval_id:
            try:
                await redis_client.publish(
                    "evaluation:cancelled",
                    json.dumps({
                        "eval_id": eval_id,
                        "job_name": job_name,
                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "Job deleted via API"
                    })
                )
                logger.info(f"Published cancellation event for evaluation {eval_id}")
            except Exception as e:
                logger.error(f"Failed to publish cancellation event: {e}")
        
        return {
            "job_name": job_name,
            "eval_id": eval_id,
            "status": "deleted"
        }
        
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(
            status_code=e.status,
            detail=f"Kubernetes API error: {e.reason}"
        )


@app.get("/health")
async def health():
    """
    Health check endpoint.
    """
    try:
        # Try to list namespaces to verify K8s connection
        core_v1.read_namespace(name=KUBERNETES_NAMESPACE)
        return {"status": "healthy", "namespace": KUBERNETES_NAMESPACE}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/ready")
async def ready():
    """
    Readiness check endpoint.
    """
    # For now, ready when healthy
    # Could add additional checks here
    return await health()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)