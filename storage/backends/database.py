"""
Database storage implementation using SQLAlchemy.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import os
import sys
from pathlib import Path

# Add parent directory to path to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..core.base import StorageService
from ..models.models import Evaluation, EvaluationEvent

# Import resilient connection utilities if available
try:
    from shared.utils.resilient_connections import get_sqlalchemy_engine
    RESILIENT_CONNECTIONS_AVAILABLE = True
except ImportError:
    RESILIENT_CONNECTIONS_AVAILABLE = False


class DatabaseStorage(StorageService):
    """
    PostgreSQL storage backend using SQLAlchemy.

    Features:
    - ACID transactions
    - Concurrent access support
    - Efficient querying with indexes
    - Support for large data via S3 pointers
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        
        # Use resilient connection if available
        if RESILIENT_CONNECTIONS_AVAILABLE and not database_url.startswith("sqlite"):
            # Use resilient connection for PostgreSQL
            self.engine = get_sqlalchemy_engine(
                self.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False,
            )
        else:
            # Fallback to regular connection for SQLite or if resilient connections not available
            if database_url.startswith("sqlite"):
                # SQLite doesn't support these pool settings
                self.engine = create_engine(
                    self.database_url,
                    pool_pre_ping=True,  # Verify connections before use
                    echo=False,  # Set to True for SQL debugging
                )
            else:
                # PostgreSQL with full pool settings
                self.engine = create_engine(
                    self.database_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,  # Verify connections before use
                    echo=False,  # Set to True for SQL debugging
                )
        self.SessionLocal = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        """Store evaluation in database."""
        try:
            with self.get_session() as session:
                # Check if evaluation exists
                existing = session.get(Evaluation, eval_id)

                # Field mapping for database columns
                field_mapping = {
                    "status": "status",
                    "code_hash": "code_hash",
                    "output": "output",
                    "output_truncated": "output_truncated",
                    "output_size": "output_size",
                    "output_location": "output_location",
                    "error": "error",
                    "error_truncated": "error_truncated",
                    "error_size": "error_size",
                    "error_location": "error_location",
                    "exit_code": "exit_code",
                    "runtime_ms": "runtime_ms",
                    "memory_used_mb": "memory_used_mb",
                    "engine": "engine",
                    "worker_id": "worker_id",
                    "code_location": "code_location",
                }

                if existing:
                    # Update existing using field mapping
                    for data_key, model_key in field_mapping.items():
                        if data_key in data:
                            setattr(existing, model_key, data[data_key])

                    # Update metadata for extra fields
                    extra_keys = set(data.keys()) - set(field_mapping.keys()) - {"id"}
                    if extra_keys:
                        current_metadata = existing.eval_metadata or {}
                        current_metadata.update({k: data[k] for k in extra_keys})
                        existing.eval_metadata = current_metadata
                else:
                    # Create new evaluation
                    eval_record = Evaluation(id=eval_id)

                    for data_key, model_key in field_mapping.items():
                        if data_key in data:
                            setattr(eval_record, model_key, data[data_key])

                    # Store any extra data in metadata JSON field
                    extra_keys = set(data.keys()) - set(field_mapping.keys()) - {"id"}
                    if extra_keys:
                        eval_record.eval_metadata = {k: data[k] for k in extra_keys}

                    # Set timestamps
                    if "timestamp" in data:
                        eval_record.created_at = datetime.fromisoformat(data["timestamp"])

                    session.add(eval_record)

                return True

        except SQLAlchemyError as e:
            # Log error (in production, use proper logging)
            print(f"Database error storing evaluation {eval_id}: {e}")
            return False

    def retrieve_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evaluation from database."""
        try:
            with self.get_session() as session:
                eval_record = session.get(Evaluation, eval_id)

                if not eval_record:
                    return None

                # Build response dict
                result = {
                    "id": eval_record.id,
                    "status": eval_record.status,
                    "code_hash": eval_record.code_hash,
                }

                # Add optional fields if present
                if eval_record.output:
                    result["output"] = eval_record.output
                if eval_record.error:
                    result["error"] = eval_record.error
                if eval_record.exit_code is not None:
                    result["exit_code"] = eval_record.exit_code
                if eval_record.runtime_ms is not None:
                    result["runtime_ms"] = eval_record.runtime_ms
                if eval_record.memory_used_mb is not None:
                    result["memory_used_mb"] = eval_record.memory_used_mb
                if eval_record.engine:
                    result["engine"] = eval_record.engine
                if eval_record.worker_id:
                    result["worker_id"] = eval_record.worker_id

                # Add metadata fields
                if eval_record.eval_metadata:
                    result.update(eval_record.eval_metadata)

                # Add timestamps
                if eval_record.created_at:
                    result["timestamp"] = eval_record.created_at.isoformat()

                return result

        except SQLAlchemyError as e:
            print(f"Database error retrieving evaluation {eval_id}: {e}")
            return None

    def store_events(self, eval_id: str, events: List[Dict[str, Any]]) -> bool:
        """Store events in database."""
        try:
            with self.get_session() as session:
                # Delete existing events for this evaluation
                session.execute(
                    delete(EvaluationEvent).where(EvaluationEvent.evaluation_id == eval_id)
                )

                # Add new events
                for event in events:
                    event_record = EvaluationEvent(
                        evaluation_id=eval_id,
                        event_type=event.get("type", "unknown"),
                        message=event.get("message", ""),
                    )

                    # Set timestamp if provided
                    if "timestamp" in event:
                        event_record.timestamp = datetime.fromisoformat(event["timestamp"])

                    # Store extra fields in metadata
                    extra_keys = set(event.keys()) - {"type", "message", "timestamp"}
                    if extra_keys:
                        event_record.event_metadata = {k: event[k] for k in extra_keys}

                    session.add(event_record)

                return True

        except SQLAlchemyError as e:
            print(f"Database error storing events for {eval_id}: {e}")
            return False

    def retrieve_events(self, eval_id: str) -> List[Dict[str, Any]]:
        """Retrieve events from database."""
        try:
            with self.get_session() as session:
                # Query events ordered by timestamp
                stmt = (
                    select(EvaluationEvent)
                    .where(EvaluationEvent.evaluation_id == eval_id)
                    .order_by(EvaluationEvent.timestamp)
                )

                events = session.execute(stmt).scalars().all()

                result = []
                for event in events:
                    event_dict = {
                        "type": event.event_type,
                        "message": event.message,
                        "timestamp": event.timestamp.isoformat(),
                    }

                    # Add metadata fields
                    if event.event_metadata:
                        event_dict.update(event.event_metadata)

                    result.append(event_dict)

                return result

        except SQLAlchemyError as e:
            print(f"Database error retrieving events for {eval_id}: {e}")
            return []

    def store_metadata(self, eval_id: str, metadata: Dict[str, Any]) -> bool:
        """Store metadata by updating evaluation record."""
        try:
            with self.get_session() as session:
                eval_record = session.get(Evaluation, eval_id)

                if not eval_record:
                    # Create evaluation if it doesn't exist
                    eval_record = Evaluation(id=eval_id, code_hash="metadata_only_hash", status="unknown")
                    session.add(eval_record)

                # Update metadata
                eval_record.eval_metadata = metadata

                return True

        except SQLAlchemyError as e:
            print(f"Database error storing metadata for {eval_id}: {e}")
            return False

    def retrieve_metadata(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata from evaluation record."""
        try:
            with self.get_session() as session:
                eval_record = session.get(Evaluation, eval_id)

                if not eval_record:
                    return None

                return eval_record.eval_metadata or {}

        except SQLAlchemyError as e:
            print(f"Database error retrieving metadata for {eval_id}: {e}")
            return None

    def list_evaluations(self, limit: int = 100, offset: int = 0) -> List[str]:
        """List evaluation IDs with pagination."""
        try:
            with self.get_session() as session:
                # Query evaluations ordered by creation time (newest first)
                stmt = (
                    select(Evaluation.id)
                    .order_by(Evaluation.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )

                result = session.execute(stmt).scalars().all()
                return list(result)

        except SQLAlchemyError as e:
            print(f"Database error listing evaluations: {e}")
            return []

    def count_evaluations(self, status: Optional[str] = None) -> int:
        """Count total evaluations, optionally filtered by status."""
        try:
            with self.get_session() as session:
                from sqlalchemy import func

                # Build query
                stmt = select(func.count(Evaluation.id))

                # Add status filter if provided
                if status:
                    stmt = stmt.where(Evaluation.status == status)

                # Execute and return count
                result = session.execute(stmt).scalar()
                return result or 0

        except SQLAlchemyError as e:
            print(f"Database error counting evaluations: {e}")
            return 0

    def delete_evaluation(self, eval_id: str) -> bool:
        """Delete evaluation and all related data (cascades to events/metrics)."""
        try:
            with self.get_session() as session:
                eval_record = session.get(Evaluation, eval_id)

                if not eval_record:
                    return False

                session.delete(eval_record)
                return True

        except SQLAlchemyError as e:
            print(f"Database error deleting evaluation {eval_id}: {e}")
            return False
