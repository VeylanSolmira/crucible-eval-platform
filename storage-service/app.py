"""
Storage Service - RESTful API for data access
Provides read/write access to evaluation data through a clean API
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
import uvicorn
import yaml

from storage import FlexibleStorageManager
from storage.config import StorageConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crucible Storage Service",
    description="RESTful API for accessing evaluation data across multiple storage backends (database, file, S3, Redis)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage with multiple backends
storage_config = StorageConfig.from_environment()
storage = FlexibleStorageManager.from_config(storage_config)

# Determine which backend is primary based on config
primary_backend = "memory"  # default
if storage_config.database_url and storage_config.prefer_database:
    primary_backend = "database"
elif storage_config.file_storage_path:
    primary_backend = "file"

# Log storage configuration
logger.info(f"Storage service initialized:")
logger.info(f"  Primary backend: {primary_backend}")
logger.info(f"  Database URL: {'configured' if storage_config.database_url else 'not configured'}")
logger.info(f"  File storage: {storage_config.file_storage_path or 'not configured'}")
logger.info(f"  Cache enabled: {storage_config.enable_caching}")
logger.info(f"  Large file threshold: {storage_config.large_file_threshold} bytes")

# The FlexibleStorageManager handles:
# - Database for structured data and queries
# - File system for large outputs (>100KB)
# - S3 for long-term storage (if configured)
# - Redis/Memory for caching frequently accessed data
# - Automatic fallback if primary storage fails

# Request/Response models
class EvaluationCreate(BaseModel):
    id: str = Field(..., description="Evaluation ID")
    code: str = Field(..., description="Code to be evaluated")
    language: str = Field(default="python", description="Programming language")
    status: str = Field(default="queued", description="Initial status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class EvaluationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="New status")
    output: Optional[str] = Field(None, description="Execution output")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata to merge")

class EvaluationResponse(BaseModel):
    id: str
    code: Optional[str] = None
    language: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    output_truncated: bool = False
    error_truncated: bool = False
    runtime_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Storage info (only included when requested)
    storage_info: Optional[Dict[str, Any]] = Field(None, exclude=True)

class EvaluationListResponse(BaseModel):
    evaluations: List[EvaluationResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

class EventCreate(BaseModel):
    type: str = Field(..., description="Event type")
    message: str = Field(..., description="Event message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")

class EventResponse(BaseModel):
    type: str
    timestamp: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class StatisticsResponse(BaseModel):
    total_evaluations: int
    by_status: Dict[str, int]
    by_language: Dict[str, int]
    average_runtime_ms: Optional[float] = None
    success_rate: float
    last_24h_count: int
    peak_hour: Optional[str] = None
    storage_info: Dict[str, Any] = Field(default_factory=dict)

class StorageInfoResponse(BaseModel):
    primary_backend: str
    fallback_backend: Optional[str] = None
    cache_enabled: bool
    large_output_storage: str = Field(description="Where outputs >100KB are stored")
    storage_thresholds: Dict[str, int]
    backends_available: List[str]

# Health check
@app.get("/health")
async def health():
    """Health check endpoint"""
    # Test storage connectivity
    storage_healthy = True
    try:
        # Try to list a few evaluations to test storage
        storage.list_evaluations(limit=1)
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        storage_healthy = False
    
    return {
        "status": "healthy" if storage_healthy else "unhealthy",
        "service": "storage",
        "storage_backend": primary_backend,
        "timestamp": datetime.utcnow().isoformat()
    }

# Storage info endpoint
@app.get("/storage-info", response_model=StorageInfoResponse)
async def get_storage_info():
    """Get information about storage configuration"""
    backends = ["memory"]
    if storage_config.database_url:
        backends.append("database")
    if storage_config.file_storage_path:
        backends.append("file")
    if storage_config.enable_caching:
        backends.append("cache")
    
    return StorageInfoResponse(
        primary_backend=primary_backend,
        fallback_backend="file" if storage_config.file_storage_path and primary_backend != "file" else None,
        cache_enabled=storage_config.enable_caching,
        large_output_storage="file" if storage_config.file_storage_path else "database",
        storage_thresholds={
            "inline_threshold": storage.INLINE_THRESHOLD,
            "preview_size": storage.PREVIEW_SIZE
        },
        backends_available=backends
    )

# Evaluation endpoints
@app.post("/evaluations", response_model=EvaluationResponse)
async def create_evaluation(evaluation: EvaluationCreate):
    """Create a new evaluation record"""
    try:
        success = storage.create_evaluation(
            evaluation.id,
            evaluation.code,
            language=evaluation.language,
            **evaluation.metadata
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store evaluation")
        
        # Retrieve and return the created evaluation
        result = storage.get_evaluation(evaluation.id)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored evaluation")
        
        return EvaluationResponse(**result)
    except Exception as e:
        logger.error(f"Error creating evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluations/{eval_id}", response_model=EvaluationResponse)
async def get_evaluation(eval_id: str, include_storage_info: bool = Query(False)):
    """Get evaluation by ID
    
    The storage service automatically retrieves from:
    1. Cache (if enabled and available)
    2. Primary backend (database/file/memory)
    3. Fallback backend (if primary fails)
    
    Large outputs (>100KB) are automatically fetched from S3/filesystem.
    """
    result = storage.get_evaluation(eval_id)
    if not result:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Add storage location info if requested
    if include_storage_info:
        result['_storage_info'] = {
            'output_location': result.get('output_location', 'inline'),
            'error_location': result.get('error_location', 'inline'),
            'output_truncated': result.get('output_truncated', False),
            'error_truncated': result.get('error_truncated', False),
            'output_size': result.get('output_size', len(result.get('output', ''))),
            'error_size': result.get('error_size', len(result.get('error', '')))
        }
    
    return EvaluationResponse(**result)

@app.put("/evaluations/{eval_id}", response_model=EvaluationResponse)
async def update_evaluation(eval_id: str, update: EvaluationUpdate):
    """Update an existing evaluation"""
    # Check if evaluation exists
    existing = storage.get_evaluation(eval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Update evaluation
    update_data = update.dict(exclude_unset=True)
    success = storage.update_evaluation(eval_id, **update_data)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update evaluation")
    
    # Return updated evaluation
    result = storage.get_evaluation(eval_id)
    return EvaluationResponse(**result)

@app.get("/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    status: Optional[str] = Query(None, description="Filter by status"),
    language: Optional[str] = Query(None, description="Filter by language"),
    since: Optional[str] = Query(None, description="Filter by creation time (ISO format)")
):
    """List evaluations with pagination and filtering"""
    try:
        # Get evaluations from storage
        evaluations = storage.list_evaluations(limit=limit + 1, offset=offset, status=status)
        
        # Check if there are more results
        has_more = len(evaluations) > limit
        if has_more:
            evaluations = evaluations[:limit]
        
        # Apply additional filters
        if language:
            evaluations = [e for e in evaluations if e.get('language') == language]
        
        if since:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            evaluations = [
                e for e in evaluations 
                if e.get('created_at') and 
                datetime.fromisoformat(e['created_at']) >= since_dt
            ]
        
        # Convert to response models
        evaluation_responses = [EvaluationResponse(**e) for e in evaluations]
        
        return EvaluationListResponse(
            evaluations=evaluation_responses,
            total=len(evaluation_responses),
            limit=limit,
            offset=offset,
            has_more=has_more
        )
    except Exception as e:
        logger.error(f"Error listing evaluations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/evaluations/{eval_id}")
async def delete_evaluation(eval_id: str):
    """Delete an evaluation (soft delete)"""
    # Check if evaluation exists
    existing = storage.get_evaluation(eval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Mark as deleted instead of hard delete
    success = storage.update_evaluation(
        eval_id,
        status="deleted",
        deleted_at=datetime.utcnow().isoformat()
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete evaluation")
    
    return {"message": "Evaluation deleted successfully"}

# Event endpoints
@app.post("/evaluations/{eval_id}/events", response_model=EventResponse)
async def add_event(eval_id: str, event: EventCreate):
    """Add an event to evaluation history"""
    # Check if evaluation exists
    existing = storage.get_evaluation(eval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Add event
    success = storage.add_event(
        eval_id,
        event.type,
        event.message,
        **event.metadata
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add event")
    
    # Return the event with timestamp
    return EventResponse(
        type=event.type,
        timestamp=datetime.utcnow().isoformat(),
        message=event.message,
        metadata=event.metadata
    )

@app.get("/evaluations/{eval_id}/events", response_model=List[EventResponse])
async def get_events(eval_id: str):
    """Get evaluation event history"""
    # Check if evaluation exists
    existing = storage.get_evaluation(eval_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Get events
    events = storage.get_events(eval_id)
    
    # Convert to response models
    return [EventResponse(**event) for event in events]

# Statistics endpoint
@app.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    since: Optional[str] = Query(None, description="Calculate stats since this time (ISO format)")
):
    """Get aggregated statistics"""
    try:
        # Get all evaluations (this is inefficient for large datasets - should use DB aggregation)
        all_evaluations = storage.list_evaluations(limit=10000)
        
        # Filter by time if requested
        if since:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            evaluations = [
                e for e in all_evaluations 
                if e.get('created_at') and 
                datetime.fromisoformat(e['created_at']) >= since_dt
            ]
        else:
            evaluations = all_evaluations
        
        # Calculate statistics
        total = len(evaluations)
        
        # Count by status
        by_status = {}
        for e in evaluations:
            status = e.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1
        
        # Count by language
        by_language = {}
        for e in evaluations:
            lang = e.get('language', 'unknown')
            by_language[lang] = by_language.get(lang, 0) + 1
        
        # Calculate average runtime
        runtimes = [e.get('runtime_ms', 0) for e in evaluations if e.get('runtime_ms')]
        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else None
        
        # Success rate
        completed = by_status.get('completed', 0)
        failed = by_status.get('failed', 0)
        success_rate = completed / (completed + failed) if (completed + failed) > 0 else 0.0
        
        # Last 24h count
        now = datetime.utcnow()
        last_24h = [
            e for e in evaluations
            if e.get('created_at') and
            (now - datetime.fromisoformat(e['created_at'].replace('Z', '+00:00'))).total_seconds() < 86400
        ]
        
        return StatisticsResponse(
            total_evaluations=total,
            by_status=by_status,
            by_language=by_language,
            average_runtime_ms=avg_runtime,
            success_rate=success_rate,
            last_24h_count=len(last_24h),
            peak_hour=None,  # TODO: Implement peak hour calculation
            storage_info={
                "primary_backend": primary_backend,
                "cache_hits": getattr(storage, 'cache_hits', 0),
                "cache_misses": getattr(storage, 'cache_misses', 0),
                "large_outputs_externalized": len([e for e in evaluations if e.get('output_truncated', False)])
            }
        )
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bulk operations
@app.post("/evaluations/bulk")
async def bulk_create_evaluations(evaluations: List[EvaluationCreate]):
    """Create multiple evaluations in one request"""
    results = []
    errors = []
    
    for eval_data in evaluations:
        try:
            success = storage.create_evaluation(
                eval_data.id,
                eval_data.code,
                language=eval_data.language,
                **eval_data.metadata
            )
            if success:
                results.append({"id": eval_data.id, "status": "created"})
            else:
                errors.append({"id": eval_data.id, "error": "Failed to store"})
        except Exception as e:
            errors.append({"id": eval_data.id, "error": str(e)})
    
    return {
        "created": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }

# Storage Explorer endpoints
@app.get("/storage/overview")
async def get_storage_overview():
    """Get overview of all storage backends with metrics"""
    overview = {
        "backends": {},
        "summary": {
            "total_evaluations": 0,
            "total_storage_bytes": 0,
            "active_backends": 0
        }
    }
    
    # Database metrics
    if storage_config.database_url:
        try:
            # Get basic database stats
            all_evals = storage.list_evaluations(limit=10000)
            db_metrics = {
                "type": "postgresql",
                "status": "healthy",
                "metrics": {
                    "evaluations": len(all_evals),
                    "events": 0,  # TODO: Count events
                    "size_bytes": 0,  # TODO: Calculate size
                    "oldest_record": None
                }
            }
            
            # Find oldest record
            if all_evals:
                oldest = min(all_evals, key=lambda e: e.get('created_at', '9999'))
                db_metrics["metrics"]["oldest_record"] = oldest.get('created_at')
            
            overview["backends"]["database"] = db_metrics
            overview["summary"]["total_evaluations"] = len(all_evals)
            overview["summary"]["active_backends"] += 1
        except Exception as e:
            logger.error(f"Failed to get database metrics: {e}")
            overview["backends"]["database"] = {
                "type": "postgresql",
                "status": "error",
                "error": str(e)
            }
    
    # Redis metrics
    if storage_config.enable_caching:
        try:
            # For now, we'll add basic Redis info
            # In production, would query Redis INFO command
            overview["backends"]["redis"] = {
                "type": "redis",
                "status": "healthy",
                "metrics": {
                    "keys": 0,  # TODO: Count keys
                    "memory_used_bytes": 0,
                    "hit_rate": 0.0,
                    "ttl_stats": {}
                }
            }
            overview["summary"]["active_backends"] += 1
        except Exception as e:
            logger.error(f"Failed to get Redis metrics: {e}")
    
    # File system metrics
    if storage_config.file_storage_path:
        try:
            import os
            from pathlib import Path
            
            storage_path = Path(storage_config.file_storage_path)
            if storage_path.exists():
                # Count files and calculate size
                file_count = 0
                total_size = 0
                largest_file = None
                largest_size = 0
                
                for root, dirs, files in os.walk(storage_path):
                    for file in files:
                        file_path = Path(root) / file
                        file_count += 1
                        size = file_path.stat().st_size
                        total_size += size
                        if size > largest_size:
                            largest_size = size
                            largest_file = file
                
                overview["backends"]["file"] = {
                    "type": "filesystem",
                    "status": "healthy",
                    "metrics": {
                        "files": file_count,
                        "total_size_bytes": total_size,
                        "directories": len(list(storage_path.rglob("*/"))) ,
                        "largest_file": largest_file
                    }
                }
                overview["summary"]["total_storage_bytes"] += total_size
                overview["summary"]["active_backends"] += 1
        except Exception as e:
            logger.error(f"Failed to get file system metrics: {e}")
    
    # Memory metrics (if using memory backend)
    if hasattr(storage, 'cache_hits'):
        overview["backends"]["memory"] = {
            "type": "in-memory",
            "status": "healthy",
            "metrics": {
                "cached_evaluations": 0,  # TODO: Count cached items
                "cache_size_bytes": 0,
                "eviction_count": 0,
                "cache_hits": getattr(storage, 'cache_hits', 0),
                "cache_misses": getattr(storage, 'cache_misses', 0)
            }
        }
        overview["summary"]["active_backends"] += 1
    
    return overview

@app.get("/storage/{backend}/details")
async def get_storage_backend_details(backend: str):
    """Get detailed information about a specific storage backend"""
    if backend == "database":
        if not storage_config.database_url:
            raise HTTPException(status_code=404, detail="Database backend not configured")
        
        try:
            # Get evaluations with more detail
            evaluations = storage.list_evaluations(limit=100)
            
            # Group by status
            by_status = {}
            for eval in evaluations:
                status = eval.get('status', 'unknown')
                by_status[status] = by_status.get(status, 0) + 1
            
            return {
                "backend": "database",
                "connection": "postgresql",
                "tables": {
                    "evaluations": {
                        "count": len(evaluations),
                        "by_status": by_status,
                        "columns": ["id", "code", "status", "output", "error", "created_at", "completed_at"]
                    },
                    "evaluation_events": {
                        "count": 0,  # TODO: Implement event counting
                        "columns": ["id", "evaluation_id", "event_type", "timestamp", "message"]
                    }
                },
                "recent_evaluations": evaluations[:10]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    elif backend == "redis":
        if not storage_config.enable_caching:
            raise HTTPException(status_code=404, detail="Redis backend not configured")
        
        # TODO: Connect to Redis and get actual stats
        return {
            "backend": "redis",
            "status": "healthy",
            "info": {
                "keys": [],
                "memory": {},
                "stats": {}
            }
        }
    
    elif backend == "file":
        if not storage_config.file_storage_path:
            raise HTTPException(status_code=404, detail="File backend not configured")
        
        from pathlib import Path
        storage_path = Path(storage_config.file_storage_path)
        
        # List files
        files = []
        for file_path in storage_path.rglob("*"):
            if file_path.is_file():
                files.append({
                    "path": str(file_path.relative_to(storage_path)),
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })
        
        # Sort by size
        files.sort(key=lambda x: x['size'], reverse=True)
        
        return {
            "backend": "file",
            "path": str(storage_path),
            "files": files[:50],  # Top 50 largest files
            "total_files": len(files)
        }
    
    else:
        raise HTTPException(status_code=404, detail=f"Unknown backend: {backend}")

@app.get("/evaluations/{eval_id}/complete")
async def get_evaluation_complete(eval_id: str):
    """Get complete evaluation data including all artifacts and events"""
    # Get base evaluation
    evaluation = storage.get_evaluation(eval_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    # Get events
    events = storage.get_events(eval_id)
    
    # Determine storage locations
    storage_locations = {
        "metadata": "database",
        "events": "database"
    }
    
    # Check if output is in file storage
    if evaluation.get('output_location'):
        storage_locations["output"] = evaluation['output_location']
    elif evaluation.get('output'):
        storage_locations["output"] = "database" if len(evaluation['output']) < 100 else "unknown"
    
    # Build complete response
    return {
        "evaluation": evaluation,
        "events": events,
        "storage_locations": storage_locations,
        "timeline": [
            {
                "timestamp": evaluation.get('created_at'),
                "event": "created",
                "details": "Evaluation created"
            }
        ] + [
            {
                "timestamp": event.get('timestamp'),
                "event": event.get('type'),
                "details": event.get('message')
            }
            for event in events
        ] + ([
            {
                "timestamp": evaluation.get('completed_at'),
                "event": "completed",
                "details": f"Status: {evaluation.get('status')}"
            }
        ] if evaluation.get('completed_at') else []),
        "metadata": {
            "total_events": len(events),
            "execution_time_ms": evaluation.get('runtime_ms'),
            "output_size": evaluation.get('output_size', len(evaluation.get('output', ''))),
            "error_size": evaluation.get('error_size', len(evaluation.get('error', '')))
        }
    }

# OpenAPI endpoints
@app.get("/openapi.yaml", include_in_schema=False)
async def get_openapi_yaml():
    """Get OpenAPI specification in YAML format"""
    from fastapi.openapi.utils import get_openapi
    import yaml
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )
    
    yaml_content = yaml.dump(openapi_schema, sort_keys=False)
    return Response(content=yaml_content, media_type="application/yaml")

@app.on_event("startup")
async def export_openapi_spec():
    """Export OpenAPI spec on startup for documentation"""
    try:
        from fastapi.openapi.utils import get_openapi
        import yaml
        import json
        from pathlib import Path
        
        # Get OpenAPI schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes
        )
        
        # Create directory if it doesn't exist
        Path("/app/storage-service").mkdir(exist_ok=True)
        
        # Export as JSON
        with open("/app/storage-service/openapi.json", "w") as f:
            json.dump(openapi_schema, f, indent=2)
        
        # Export as YAML
        with open("/app/storage-service/openapi.yaml", "w") as f:
            yaml.dump(openapi_schema, f, sort_keys=False)
        
        logger.info("OpenAPI spec exported to /app/storage-service/openapi.json and openapi.yaml")
    except Exception as e:
        logger.error(f"Failed to export OpenAPI spec: {e}")
        # Don't fail startup if export fails

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8082)