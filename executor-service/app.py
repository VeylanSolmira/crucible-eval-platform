"""
Executor Service - Creates isolated containers for code execution
Uses Docker proxy for security-limited container creation
"""
import os
import sys
import json
import asyncio
from typing import Dict
from datetime import datetime
import logging

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn
import docker
from docker.errors import ContainerError, ImageNotFound, APIError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Executor Service")

# Docker client will use DOCKER_HOST env var (tcp://docker-proxy:2375)
docker_client = docker.from_env()
executor_id = os.getenv("HOSTNAME", "executor")

class ExecuteRequest(BaseModel):
    """Request to execute code"""
    eval_id: str
    code: str
    timeout: int = 30

class ExecuteResponse(BaseModel):
    """Response from execution"""
    eval_id: str
    status: str  # completed, failed, timeout
    output: str = ""
    error: str = ""
    exit_code: int = -1
    executor_id: str = executor_id

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
        "docker_status": docker_status
    }

def execute_in_container(eval_id: str, code: str, timeout: int) -> Dict:
    """Execute code in an isolated container"""
    container = None
    try:
        # Pull image if not present
        try:
            docker_client.images.get("python:3.11-slim")
        except ImageNotFound:
            logger.info("Pulling python:3.11-slim image...")
            docker_client.images.pull("python:3.11-slim")
        
        # Create and run container
        logger.info(f"Creating container for eval {eval_id}")
        container = docker_client.containers.run(
            image="python:3.11-slim",
            command=["python", "-c", code],
            detach=True,
            remove=False,  # We'll remove manually after getting logs
            # Security restrictions
            mem_limit="512m",
            nano_cpus=500000000,  # 0.5 CPU
            network_mode="none",  # No network
            read_only=True,
            security_opt=["no-new-privileges:true"],
            # Volumes - only tmp for writing
            tmpfs={'/tmp': 'size=100M'},
            environment={
                'PYTHONUNBUFFERED': '1',
                'EVAL_ID': eval_id
            },
            labels={
                'eval_id': eval_id,
                'executor': executor_id,
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        # Wait for completion with timeout
        try:
            result = container.wait(timeout=timeout)
            exit_code = result.get('StatusCode', -1)
            
            # Get logs
            logs = container.logs(stdout=True, stderr=True)
            output = logs.decode('utf-8', errors='replace')
            
            logger.info(f"Container {eval_id} exited with code {exit_code}")
            
            return {
                'eval_id': eval_id,
                'status': 'completed',
                'output': output,
                'error': '',
                'exit_code': exit_code,
                'executor_id': executor_id
            }
            
        except Exception as timeout_error:
            # Timeout or other error during wait
            logger.warning(f"Container {eval_id} timed out or errored: {timeout_error}")
            
            # Try to stop the container
            try:
                container.stop(timeout=5)
            except:
                container.kill()
            
            # Get any partial output
            try:
                logs = container.logs(stdout=True, stderr=True)
                output = logs.decode('utf-8', errors='replace')
            except:
                output = ""
            
            return {
                'eval_id': eval_id,
                'status': 'timeout',
                'output': output,
                'error': f'Execution exceeded {timeout}s timeout',
                'exit_code': -1,
                'executor_id': executor_id
            }
            
    except ContainerError as e:
        logger.error(f"Container error for {eval_id}: {e}")
        return {
            'eval_id': eval_id,
            'status': 'failed',
            'output': e.stderr.decode('utf-8', errors='replace') if e.stderr else '',
            'error': str(e),
            'exit_code': e.exit_status,
            'executor_id': executor_id
        }
        
    except Exception as e:
        logger.error(f"Unexpected error for {eval_id}: {e}")
        return {
            'eval_id': eval_id,
            'status': 'failed',
            'output': '',
            'error': f'Container creation failed: {str(e)}',
            'exit_code': -1,
            'executor_id': executor_id
        }
        
    finally:
        # Clean up container
        if container:
            try:
                container.remove(force=True)
                logger.info(f"Cleaned up container for {eval_id}")
            except Exception as e:
                logger.error(f"Failed to remove container for {eval_id}: {e}")

@app.post("/execute", response_model=ExecuteResponse)
async def execute(request: ExecuteRequest, background_tasks: BackgroundTasks):
    """
    Execute code in an isolated container.
    This is synchronous but wrapped in a background task for the API.
    """
    logger.info(f"Received execution request {request.eval_id}")
    
    # Run the execution synchronously (Docker operations are blocking)
    result = execute_in_container(
        request.eval_id,
        request.code,
        request.timeout
    )
    
    return ExecuteResponse(**result)

@app.get("/status")
async def status():
    """Get executor service status"""
    try:
        # List recent containers we created
        containers = docker_client.containers.list(
            all=True,
            filters={'label': f'executor={executor_id}'},
            limit=10
        )
        
        recent_executions = []
        for container in containers:
            recent_executions.append({
                'eval_id': container.labels.get('eval_id', 'unknown'),
                'status': container.status,
                'created': container.labels.get('created_at', 'unknown')
            })
        
        return {
            'executor_id': executor_id,
            'status': 'healthy',
            'recent_executions': recent_executions,
            'docker_host': os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
        }
        
    except Exception as e:
        return {
            'executor_id': executor_id,
            'status': 'error',
            'error': str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8083)