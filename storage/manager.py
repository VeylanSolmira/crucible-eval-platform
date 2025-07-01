"""
Unified storage manager that coordinates between different storage backends.

This manager decides where to store different types of data based on:
- Size (large files go to S3/filesystem)
- Type (metadata goes to database, cache goes to Redis)
- Access patterns (hot data in Redis, cold in S3)
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

from .database import Evaluation, EvaluationEvent, EvaluationMetric


class StorageManager:
    """
    Coordinates storage across multiple backends.
    
    Storage strategy:
    - PostgreSQL: Evaluation metadata, searchable fields, relationships
    - Redis: Cache layer, active evaluation states (future)
    - S3: Large outputs, code artifacts (future)
    - Filesystem: Temporary files, local development
    """
    
    def __init__(self, db_session=None, filesystem_base: str = "/app/data"):
        self.db = db_session  # Will be injected by FastAPI
        self.filesystem_base = Path(filesystem_base)
        
        # TODO: Add Redis client
        # self.redis = RedisStorage()
        
        # TODO: Add S3 client
        # self.s3 = S3Storage()
        
        # Ensure filesystem directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary filesystem directories."""
        dirs = [
            self.filesystem_base / "tmp",  # Temporary execution files
            self.filesystem_base / "evaluations",  # Evaluation outputs
            self.filesystem_base / "artifacts",  # Code artifacts
        ]
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _compute_code_hash(self, code: str) -> str:
        """Compute SHA256 hash of code for deduplication."""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()
    
    async def create_evaluation(self, eval_id: str, code: str) -> Evaluation:
        """
        Create a new evaluation record.
        
        This is called when an evaluation is submitted.
        """
        code_hash = self._compute_code_hash(code)
        
        # Store code artifact on filesystem (later S3)
        code_path = self.filesystem_base / "artifacts" / f"{code_hash}.py"
        if not code_path.exists():
            code_path.write_text(code)
        
        # Create database record
        evaluation = Evaluation(
            id=eval_id,
            code_hash=code_hash,
            status='queued',
            created_at=datetime.now(timezone.utc),
            metadata={
                'code_lines': len(code.splitlines()),
                'code_size': len(code)
            }
        )
        
        # Add initial event
        event = EvaluationEvent(
            evaluation_id=eval_id,
            event_type='submitted',
            message='Evaluation submitted',
            metadata={'code_hash': code_hash}
        )
        evaluation.events.append(event)
        
        if self.db:
            self.db.add(evaluation)
            await self.db.commit()
            await self.db.refresh(evaluation)
        
        return evaluation
    
    async def update_evaluation_status(
        self, 
        eval_id: str, 
        status: str,
        **kwargs
    ) -> Optional[Evaluation]:
        """
        Update evaluation status and related fields.
        
        Called when evaluation transitions between states.
        """
        if not self.db:
            return None
            
        evaluation = await self.db.get(Evaluation, eval_id)
        if not evaluation:
            return None
        
        # Update status
        evaluation.status = status
        
        # Update timestamps based on status
        now = datetime.now(timezone.utc)
        if status == 'queued' and not evaluation.queued_at:
            evaluation.queued_at = now
        elif status == 'running' and not evaluation.started_at:
            evaluation.started_at = now
        elif status in ['completed', 'failed', 'timeout']:
            evaluation.completed_at = now
            
            # Calculate runtime
            if evaluation.started_at:
                runtime_delta = now - evaluation.started_at
                evaluation.runtime_ms = int(runtime_delta.total_seconds() * 1000)
        
        # Update other fields from kwargs
        for key, value in kwargs.items():
            if hasattr(evaluation, key):
                setattr(evaluation, key, value)
        
        # Add status change event
        event = EvaluationEvent(
            evaluation_id=eval_id,
            event_type='status_changed',
            message=f'Status changed to {status}',
            metadata=kwargs
        )
        evaluation.events.append(event)
        
        await self.db.commit()
        await self.db.refresh(evaluation)
        return evaluation
    
    async def store_evaluation_output(
        self,
        eval_id: str,
        output: str,
        error: Optional[str] = None,
        exit_code: Optional[int] = None
    ) -> Optional[Evaluation]:
        """
        Store evaluation output, deciding where based on size.
        
        Small outputs go inline in DB, large ones to filesystem/S3.
        """
        if not self.db:
            return None
            
        evaluation = await self.db.get(Evaluation, eval_id)
        if not evaluation:
            return None
        
        # Store based on size
        output_size = len(output.encode('utf-8'))
        evaluation.output_size_bytes = output_size
        
        # Threshold for inline storage (1MB)
        INLINE_THRESHOLD = 1024 * 1024
        
        if output_size <= INLINE_THRESHOLD:
            # Store inline
            evaluation.output_preview = output
        else:
            # Store to filesystem (later S3)
            output_path = self.filesystem_base / "evaluations" / f"{eval_id}_output.txt"
            output_path.write_text(output)
            evaluation.output_s3_key = str(output_path)  # Will be S3 key later
            
            # Store preview (first 1KB)
            evaluation.output_preview = output[:1024]
        
        # Handle error output
        if error:
            if len(error) <= INLINE_THRESHOLD:
                evaluation.error_preview = error
            else:
                error_path = self.filesystem_base / "evaluations" / f"{eval_id}_error.txt"
                error_path.write_text(error)
                evaluation.error_s3_key = str(error_path)
                evaluation.error_preview = error[:1024]
        
        evaluation.exit_code = exit_code
        
        await self.db.commit()
        await self.db.refresh(evaluation)
        return evaluation
    
    async def get_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete evaluation data.
        
        Combines data from database and filesystem/S3.
        """
        if not self.db:
            return None
            
        evaluation = await self.db.get(Evaluation, eval_id)
        if not evaluation:
            return None
        
        # Build response
        result = {
            'id': evaluation.id,
            'status': evaluation.status,
            'created_at': evaluation.created_at.isoformat() if evaluation.created_at else None,
            'started_at': evaluation.started_at.isoformat() if evaluation.started_at else None,
            'completed_at': evaluation.completed_at.isoformat() if evaluation.completed_at else None,
            'runtime_ms': evaluation.runtime_ms,
            'engine': evaluation.engine,
            'exit_code': evaluation.exit_code,
            'metadata': evaluation.metadata or {}
        }
        
        # Get full output if stored externally
        if evaluation.output_s3_key:
            # For now, read from filesystem
            output_path = Path(evaluation.output_s3_key)
            if output_path.exists():
                result['output'] = output_path.read_text()
        else:
            result['output'] = evaluation.output_preview
        
        # Get full error if stored externally
        if evaluation.error_s3_key:
            error_path = Path(evaluation.error_s3_key)
            if error_path.exists():
                result['error'] = error_path.read_text()
        else:
            result['error'] = evaluation.error_preview
        
        return result
    
    async def list_evaluations(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List evaluations with pagination and filtering.
        """
        if not self.db:
            return []
        
        from sqlalchemy import select
        
        query = select(Evaluation)
        if status:
            query = query.where(Evaluation.status == status)
        
        query = query.order_by(Evaluation.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        evaluations = result.scalars().all()
        
        return [
            {
                'id': e.id,
                'status': e.status,
                'created_at': e.created_at.isoformat() if e.created_at else None,
                'runtime_ms': e.runtime_ms,
                'engine': e.engine
            }
            for e in evaluations
        ]
    
    async def add_evaluation_event(
        self,
        eval_id: str,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[EvaluationEvent]:
        """Add an event to evaluation history."""
        if not self.db:
            return None
            
        event = EvaluationEvent(
            evaluation_id=eval_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {}
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
    
    async def add_evaluation_metric(
        self,
        eval_id: str,
        metric_name: str,
        metric_value: float,
        unit: Optional[str] = None
    ) -> Optional[EvaluationMetric]:
        """Add a metric for evaluation analytics."""
        if not self.db:
            return None
            
        metric = EvaluationMetric(
            evaluation_id=eval_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit
        )
        
        self.db.add(metric)
        await self.db.commit()
        await self.db.refresh(metric)
        return metric