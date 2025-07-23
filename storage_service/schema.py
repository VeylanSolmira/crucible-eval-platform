"""
Storage Service Schema Definition
Creates FastAPI app with routes for OpenAPI generation without runtime dependencies.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Import models
from models import (
    EvaluationCreate,
    EvaluationUpdate,
    EvaluationResponse,
    EvaluationListResponse,
    EventCreate,
    EventResponse,
    StatisticsResponse,
    StorageInfoResponse,
    HealthResponse,
    RunningEvaluationInfo,
    RunningEvaluationsResponse
)


def create_app_schema() -> FastAPI:
    """
    Create FastAPI app with all routes defined for schema generation.
    This contains no runtime dependencies - only the API contract.
    """
    
    app = FastAPI(
        title="Crucible Storage Service",
        description="Data storage and retrieval API for the Crucible evaluation platform",
        version="1.0.0",
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
    
    @app.get("/")
    async def root():
        """Root endpoint with service information"""
        pass
    
    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check endpoint"""
        pass
    
    @app.get("/info", response_model=StorageInfoResponse)
    async def get_storage_info():
        """Get storage backend information"""
        pass
    
    # Evaluation CRUD endpoints
    @app.post("/evaluations", response_model=EvaluationResponse, status_code=201)
    async def create_evaluation(evaluation: EvaluationCreate):
        """Create a new evaluation record"""
        pass
    
    @app.get("/evaluations/{eval_id}", response_model=EvaluationResponse)
    async def get_evaluation(eval_id: str):
        """Get evaluation by ID"""
        pass
    
    @app.put("/evaluations/{eval_id}", response_model=EvaluationResponse)
    async def update_evaluation(eval_id: str, update: EvaluationUpdate):
        """Update evaluation fields"""
        pass
    
    @app.delete("/evaluations/{eval_id}")
    async def delete_evaluation(eval_id: str):
        """Delete an evaluation"""
        pass
    
    @app.get("/evaluations", response_model=EvaluationListResponse)
    async def list_evaluations(
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
        offset: int = Query(0, ge=0, description="Number of results to skip"),
        status: Optional[str] = Query(None, description="Filter by status"),
        language: Optional[str] = Query(None, description="Filter by language"),
        sort_by: str = Query("created_at", description="Field to sort by"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
    ):
        """List evaluations with pagination and filtering"""
        pass
    
    # Running evaluations tracking
    @app.get("/evaluations/{eval_id}/running", response_model=RunningEvaluationInfo)
    async def get_running_info(eval_id: str):
        """Get running evaluation info from Redis cache"""
        pass
    
    @app.post("/evaluations/{eval_id}/running", status_code=204)
    async def set_running_info(
        eval_id: str,
        executor_id: Optional[str] = None,
        container_id: Optional[str] = None,
        job_name: Optional[str] = None
    ):
        """Mark evaluation as running with executor info"""
        pass
    
    @app.delete("/evaluations/{eval_id}/running", status_code=204)
    async def clear_running_info(eval_id: str):
        """Clear running status for evaluation"""
        pass
    
    @app.get("/evaluations/running", response_model=RunningEvaluationsResponse)
    async def get_all_running():
        """Get all currently running evaluations"""
        pass
    
    # Event tracking
    @app.post("/evaluations/{eval_id}/events", response_model=EventResponse, status_code=201)
    async def add_event(eval_id: str, event: EventCreate):
        """Add an event to evaluation history"""
        pass
    
    @app.get("/evaluations/{eval_id}/events", response_model=List[EventResponse])
    async def get_events(eval_id: str):
        """Get evaluation event history"""
        pass
    
    # Logs endpoint
    @app.get("/evaluations/{eval_id}/logs")
    async def get_evaluation_logs(eval_id: str):
        """Get execution logs for an evaluation"""
        pass
    
    # Statistics
    @app.get("/statistics", response_model=StatisticsResponse)
    async def get_statistics():
        """Get aggregate statistics across all evaluations"""
        pass
    
    # Search endpoint
    @app.get("/search")
    async def search_evaluations(
        q: str = Query(..., description="Search query"),
        limit: int = Query(20, ge=1, le=100)
    ):
        """Search evaluations by code content or metadata"""
        pass
    
    # Cleanup endpoint
    @app.post("/cleanup")
    async def cleanup_old_evaluations(
        older_than_days: int = Query(30, ge=1, description="Delete evaluations older than N days"),
        dry_run: bool = Query(True, description="If true, only return count without deleting")
    ):
        """Clean up old evaluation records"""
        pass
    
    return app