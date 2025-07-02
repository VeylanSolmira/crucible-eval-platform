"""
Example of integrating the flexible storage system with the API.
"""

import os
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .flexible_manager import FlexibleStorageManager
from .backends.database import DatabaseStorage
from .backends.file import FileStorage
from .backends.memory import InMemoryStorage


def create_storage_manager(db_session: Optional[AsyncSession] = None) -> FlexibleStorageManager:
    """
    Create a storage manager based on environment configuration.

    This shows how to set up different storage strategies:
    - Production: Database primary, File fallback, Redis cache
    - Development: File primary, Memory cache
    - Testing: All in-memory
    """

    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        # Production setup
        primary = DatabaseStorage()
        fallback = FileStorage("/data/storage")
        cache = None  # Would be RedisStorage() when implemented

    elif env == "testing":
        # Testing setup - all in memory
        primary = InMemoryStorage()
        fallback = None
        cache = InMemoryStorage()

    else:
        # Development setup
        primary = FileStorage("./data/storage")
        fallback = InMemoryStorage()
        cache = InMemoryStorage()

    return FlexibleStorageManager(
        primary_storage=primary, fallback_storage=fallback, cache_storage=cache
    )


# Example of how to update the API routes to use flexible storage
"""
# In src/api/routes.py, you could update the dependency:

def get_storage_manager() -> FlexibleStorageManager:
    '''Dependency to get storage manager.'''
    return create_storage_manager()


@router.post("/evaluations", response_model=EvaluationCreateResponse)
async def create_evaluation(
    request: EvaluationCreate,
    storage: FlexibleStorageManager = Depends(get_storage_manager)
):
    '''Submit code for evaluation.'''
    # Generate eval ID
    eval_id = f"eval_{uuid.uuid4().hex[:8]}"
    
    # Create evaluation
    success = await storage.create_evaluation(
        eval_id, 
        request.code,
        language=request.language,
        timeout=request.timeout
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create evaluation")
    
    # Submit to execution queue
    # ...
    
    return EvaluationCreateResponse(
        eval_id=eval_id,
        status="queued",
        message="Evaluation queued for processing"
    )
"""
