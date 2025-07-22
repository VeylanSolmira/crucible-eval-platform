"""
Dispatcher Service - Stateless service that creates Kubernetes Jobs for code evaluation.
Provides a simple HTTP interface for queue workers to request code execution.

File sync test: Adding this comment to test Skaffold file syncing
"""

import os
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone
import uuid
import json
import asyncio
from contextlib import asynccontextmanager
import yaml

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import uvicorn

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
EXECUTOR_IMAGE = os.getenv("EXECUTOR_IMAGE", None)
MAX_JOB_TTL = int(os.getenv("MAX_JOB_TTL", "3600"))  # 1 hour
JOB_CLEANUP_TTL = int(os.getenv("JOB_CLEANUP_TTL", "300"))  # 5 minutes
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Security configuration
REQUIRE_GVISOR = os.getenv("REQUIRE_GVISOR", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
HOST_OS = os.getenv("HOST_OS", "linux").lower()  # linux, macos, windows


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
    
    yield
    
    # Shutdown
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

def get_latest_executor_image(executor_type: str) -> Optional[str]:
    """Find the most recent executor image from node image store"""
    try:
        # List all nodes
        nodes = core_v1.list_node()
        if not nodes.items:
            return None
            
        # Get images from first node (in Kind there's usually just one)
        node_images = nodes.items[0].status.images
        
        # Find images matching the executor type
        matching_images = []
        for image in node_images:
            if image and image.names:  # Check that image and names exist
                for name in image.names:
                    # Match executor images with SHA tags (e.g., executor-ml:6fffbe9ad576...)
                    if f"executor-{executor_type}" in name and len(name.split(":")[-1]) >= 12:
                        # Check if tag looks like a SHA (at least 12 hex chars)
                        tag = name.split(":")[-1]
                        if all(c in "0123456789abcdef" for c in tag[:12]):
                            matching_images.append(name)
        
        # Return the first match (most recent)
        if matching_images:
            logger.info(f"Found executor image: {matching_images[0]}")
            return matching_images[0]
            
        return None
    except ApiException as e:
        logger.error(f"Failed to query node images: {e}")
        return None

def check_gvisor_availability():
    """Check if gVisor RuntimeClass is available in the cluster"""
    global gvisor_runtime_available
    
    # Use cached value if available
    if gvisor_runtime_available is not None:
        return gvisor_runtime_available
    
    try:
        # Check if gvisor RuntimeClass exists
        node_v1.read_runtime_class("gvisor")
        gvisor_runtime_available = True
        logger.info("gVisor RuntimeClass found - will use for evaluations")
        return True
    except ApiException as e:
        if e.status == 404:
            gvisor_runtime_available = False
            if ENVIRONMENT == "production":
                logger.error(
                    "gVisor RuntimeClass not found in production! "
                    "Production deployments MUST have gVisor installed."
                )
            elif HOST_OS == "macos":
                logger.debug(
                    "gVisor RuntimeClass not found on macOS host - this is expected."
                )
            else:
                logger.warning(
                    "gVisor RuntimeClass not found - running without enhanced isolation. "
                    "Consider installing gVisor for better security."
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
        "require_gvisor": REQUIRE_GVISOR,
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


@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest):
    """
    Create a Kubernetes Job to execute the provided code.
    """
    logger.info(f"Creating job for evaluation {request.eval_id}, code length: {len(request.code)} chars, timeout: {request.timeout}s")
    
    # Check gVisor availability and requirements
    use_gvisor = check_gvisor_availability()
    
    # In production, gVisor is mandatory for security
    if ENVIRONMENT == "production" and not use_gvisor:
        raise HTTPException(
            status_code=503,
            detail="gVisor runtime is required in production but not available. "
                   "Cannot execute evaluations without proper isolation."
        )
    
    # If explicitly required via env var, enforce it
    if REQUIRE_GVISOR and not use_gvisor:
        raise HTTPException(
            status_code=503,
            detail="gVisor runtime is required (REQUIRE_GVISOR=true) but not available. "
                   "Note: gVisor cannot run on macOS hosts, even with Kind/Docker."
        )
    
    # Log warning in development without gVisor
    if ENVIRONMENT == "development" and not use_gvisor:
        if HOST_OS == "macos":
            logger.info(
                "Running on macOS host - gVisor not available. "
                "Network isolation relies on NetworkPolicies only. "
                "This is expected for macOS development."
            )
        else:
            logger.warning(
                "Running without gVisor in development. "
                "Network isolation relies on NetworkPolicies only. "
                "Consider installing gVisor for enhanced isolation."
            )
    
    # Generate job name using shared utility
    job_name = generate_job_name(request.eval_id)
    
    logger.info(f"Creating job {job_name} for evaluation {request.eval_id}")
    
    # Determine which executor image to use
    executor_image = EXECUTOR_IMAGE  # Default fallback
    
    # In development, try to find the latest image from node
    if ENVIRONMENT == "development":
        latest_image = get_latest_executor_image("ml")
        if latest_image:
            executor_image = latest_image
            logger.info(f"Using latest executor-ml image from node: {executor_image}")
        else:
            logger.warning("Could not find executor-ml in node images, using default")
    
    if request.executor_image:
        # Load available images
        available_images = load_executor_images()
        
        # Check if it's a known image name
        if request.executor_image in available_images:
            executor_image = available_images[request.executor_image]
            logger.info(f"Using named executor image: {executor_image}")
        # Check if it's a full image path (contains / or :)
        elif "/" in request.executor_image or ":" in request.executor_image:
            executor_image = request.executor_image
            logger.info(f"Using custom executor image: {executor_image}")
        else:
            logger.warning(f"Unknown executor image '{request.executor_image}', using default")
            executor_image = available_images.get("default", EXECUTOR_IMAGE)
    
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
            active_deadline_seconds=request.timeout,
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
                            command=["python", "-u", "-c", request.code],
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
                                    "memory": "128Mi",
                                    "cpu": "100m"
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
                        logs_result = await get_job_logs(job_name)
                        
                        # Publish evaluation completed event
                        event_data = {
                            "eval_id": eval_id,
                            "output": logs_result.get("logs", ""),
                            "exit_code": logs_result.get("exit_code", 0),
                            "metadata": {
                                "job_name": job_name,
                                "completed_at": job.status.completion_time.isoformat() if job.status.completion_time else datetime.now(timezone.utc).isoformat()
                            }
                        }
                        success = await redis_client.publish(
                            "evaluation:completed",
                            json.dumps(event_data)
                        )
                        if success:
                            logger.info(f"Published evaluation:completed event for {eval_id}")
                    
                    elif status == "failed":
                        # Get job logs for the failed evaluation
                        logs_result = await get_job_logs(job_name)
                        
                        # Publish evaluation failed event
                        event_data = {
                            "eval_id": eval_id,
                            "error": logs_result.get("logs", "Job failed"),
                            "exit_code": logs_result.get("exit_code", 1),
                            "metadata": {
                                "job_name": job_name,
                                "failed_at": job.status.completion_time.isoformat() if job.status.completion_time else datetime.now(timezone.utc).isoformat()
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


@app.get("/logs/{job_name}")
async def get_job_logs(job_name: str, tail_lines: int = 100):
    """
    Get logs from a job's pod.
    """
    try:
        # Find pods for this job
        pods = core_v1.list_namespaced_pod(
            namespace=KUBERNETES_NAMESPACE,
            label_selector=f"job-name={job_name}"
        )
        
        if not pods.items:
            return {"logs": "", "message": "No pods found for job"}
        
        # Get logs from the first pod
        pod_name = pods.items[0].metadata.name
        
        # Get logs
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=KUBERNETES_NAMESPACE,
            tail_lines=tail_lines
        )
        
        return {
            "job_name": job_name,
            "pod_name": pod_name,
            "logs": logs
        }
        
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail="Pod not found")
        raise HTTPException(
            status_code=e.status,
            detail=f"Kubernetes API error: {e.reason}"
        )


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