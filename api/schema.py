"""
API Schema Definition
Creates FastAPI app with routes for OpenAPI generation without runtime dependencies.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, Query, Request
from fastapi.middleware.cors import CORSMiddleware

# Import models
from .models import (
    EvaluationRequest,
    EvaluationSubmitResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    EvaluationStatusResponse,
    QueueStatusResponse,
    StatusResponse,
    HealthResponse,
    ServiceHealthInfo
)
from shared.generated.python import EvaluationStatus, EvaluationResponse


def create_app_schema() -> FastAPI:
    """
    Create FastAPI app with all routes defined for schema generation.
    This contains no runtime dependencies - only the API contract.
    """
    
    app = FastAPI(
        title="Crucible API Gateway",
        description="Main API gateway for Crucible evaluation platform (microservices mode)",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint - returns basic API information."""
        pass
    
    # Health endpoints
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        pass
    
    @app.get("/health/ready")
    async def readiness_check():
        """Readiness check that verifies all services are available."""
        pass
    
    # Status endpoint
    @app.get("/status", response_model=StatusResponse)
    async def get_platform_status():
        """Get comprehensive platform status including all services."""
        pass
    
    # Queue endpoints
    @app.get("/queue/status", response_model=QueueStatusResponse)
    async def get_queue_status():
        """Get current queue status and metrics."""
        pass
    
    # Evaluation endpoints
    @app.post("/eval", response_model=EvaluationResponse, deprecated=True)
    async def submit_evaluation(request: EvaluationRequest):
        """
        Submit code for evaluation (single evaluation).
        
        This endpoint submits to Celery for processing.
        Use WebSocket endpoint for real-time updates.
        
        DEPRECATED: Use /api/eval endpoint instead.
        """
        pass
    
    @app.get("/eval/{eval_id}", response_model=EvaluationStatusResponse)
    async def get_evaluation_status(eval_id: str):
        """Get the status of a specific evaluation."""
        pass
    
    @app.get("/eval/{eval_id}/logs", response_model=Dict[str, Any])
    async def get_evaluation_logs(eval_id: str):
        """Get execution logs for a specific evaluation."""
        pass
    
    @app.post("/eval/{eval_id}/cancel", response_model=Dict[str, str])
    async def cancel_evaluation(eval_id: str):
        """Cancel a running evaluation."""
        pass
    
    # Batch endpoint
    @app.post("/batch", response_model=BatchEvaluationResponse)
    async def submit_batch_evaluation(request: BatchEvaluationRequest):
        """Submit multiple evaluations in a single request."""
        pass
    
    # List evaluations
    @app.get("/evaluations", response_model=List[EvaluationStatusResponse])
    async def list_evaluations(
        status: Optional[EvaluationStatus] = Query(None, description="Filter by status"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
        offset: int = Query(0, ge=0, description="Number of results to skip")
    ):
        """List all evaluations with optional status filter."""
        pass
    
    @app.get("/evaluations/running", response_model=List[Dict[str, Any]])
    async def get_running_evaluations():
        """Get all currently running evaluations from storage service."""
        pass
    
    # Statistics endpoint
    @app.get("/statistics", response_model=Dict[str, Any])
    async def get_statistics():
        """Get evaluation statistics from storage service."""
        pass
    
    # DLQ endpoints
    @app.get("/dlq/messages", response_model=List[Dict[str, Any]])
    async def get_dlq_messages(
        queue: Optional[str] = Query(None, description="Specific queue to fetch from"),
        limit: int = Query(10, ge=1, le=100, description="Number of messages to return")
    ):
        """Get messages from the dead letter queue."""
        pass
    
    @app.post("/dlq/messages/{message_id}/retry", response_model=Dict[str, str])
    async def retry_dlq_message(message_id: str, queue: Optional[str] = None):
        """Retry a specific message from the DLQ."""
        pass
    
    @app.delete("/dlq/messages/{message_id}", response_model=Dict[str, str])
    async def delete_dlq_message(message_id: str, queue: Optional[str] = None):
        """Delete a specific message from the DLQ."""
        pass
    
    @app.delete("/dlq/messages", response_model=Dict[str, Any])
    async def clear_dlq(
        queue: Optional[str] = Query(None, description="Specific queue to clear"),
        older_than_hours: Optional[int] = Query(None, ge=1, description="Clear messages older than N hours")
    ):
        """Clear messages from the DLQ."""
        pass
    
    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint for real-time evaluation updates.
        
        After connection, send evaluation IDs to subscribe:
        {"action": "subscribe", "eval_id": "your-eval-id"}
        """
        pass
    
    # API endpoints (forwarding to this service)
    @app.post("/api/eval", response_model=EvaluationResponse)
    async def api_submit_evaluation(request: EvaluationRequest):
        """
        Submit code for evaluation through the API gateway.
        
        This is the main evaluation endpoint that handles both
        Celery submission and status tracking.
        """
        pass
    
    @app.get("/api/eval/{eval_id}", response_model=EvaluationStatusResponse)
    async def api_get_evaluation_status(eval_id: str):
        """Get evaluation status through the API gateway."""
        pass
    
    return app