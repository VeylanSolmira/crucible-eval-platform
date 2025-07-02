"""
Flexible storage manager that can work with any storage backend.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from .base import StorageService
from .backends.memory import InMemoryStorage
from .backends.file import FileStorage
from .config import StorageConfig

# Conditional import for database
try:
    from .backends.database import DatabaseStorage

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    DatabaseStorage = None


class FlexibleStorageManager:
    """
    Storage manager that works with pluggable storage backends.

    This manager provides a high-level API for the platform while
    delegating actual storage to configurable backends.
    """

    def __init__(
        self,
        primary_storage: Optional[StorageService] = None,
        fallback_storage: Optional[StorageService] = None,
        cache_storage: Optional[StorageService] = None,
    ):
        """
        Initialize storage manager with configurable backends.

        Args:
            primary_storage: Main storage backend (e.g., DatabaseStorage)
            fallback_storage: Backup storage if primary fails (e.g., FileStorage)
            cache_storage: Fast cache layer (e.g., InMemoryStorage or Redis)
        """
        self.primary = primary_storage or self._create_default_storage()
        self.fallback = fallback_storage
        self.cache = cache_storage

        # Thresholds
        self.INLINE_THRESHOLD = 1024 * 1024  # 1MB
        self.PREVIEW_SIZE = 1024  # 1KB

    @classmethod
    def from_config(cls, config: StorageConfig) -> "FlexibleStorageManager":
        """Create storage manager from configuration."""
        primary_storage = None
        fallback_storage = None
        cache_storage = None

        # Set up primary storage based on config
        if config.database_url and SQLALCHEMY_AVAILABLE and config.prefer_database:
            try:
                primary_storage = DatabaseStorage(config.database_url)
                print("Using database as primary storage")
            except Exception as e:
                print(f"Failed to initialize database storage: {e}")

        # Set up file storage as primary or fallback
        if config.file_storage_path:
            file_storage = FileStorage(config.file_storage_path)
            if primary_storage is None:
                primary_storage = file_storage
                print("Using file storage as primary")
            else:
                fallback_storage = file_storage
                print("Using file storage as fallback")

        # Set up cache if enabled
        if config.enable_caching:
            cache_storage = InMemoryStorage()
            print("Caching enabled")

        # Use in-memory as last resort
        if primary_storage is None:
            primary_storage = InMemoryStorage()
            print("Using in-memory storage")

        return cls(
            primary_storage=primary_storage,
            fallback_storage=fallback_storage,
            cache_storage=cache_storage,
        )

    def _create_default_storage(self) -> StorageService:
        """Create default storage based on environment."""
        # Try database first
        try:
            from .database.connection import get_database_url  # noqa: F401

            return DatabaseStorage()
        except ImportError:
            pass

        # Fall back to file storage
        return FileStorage()

    def _compute_code_hash(self, code: str) -> str:
        """Compute SHA256 hash of code."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _prepare_evaluation_data(
        self, eval_id: str, code: str, status: str = "queued", **kwargs
    ) -> Dict[str, Any]:
        """Prepare evaluation data for storage."""
        now = datetime.now(timezone.utc)

        data = {
            "id": eval_id,
            "code_hash": self._compute_code_hash(code),
            "status": status,
            "timestamp": now.isoformat(),
            "created_at": now.isoformat(),
            "code_lines": len(code.splitlines()),
            "code_size": len(code),
        }

        # Add any additional fields
        data.update(kwargs)

        return data

    def create_evaluation(self, eval_id: str, code: str, **kwargs) -> bool:
        """Create a new evaluation."""
        data = self._prepare_evaluation_data(eval_id, code, **kwargs)

        # Store in cache if available
        if self.cache:
            self.cache.store_evaluation(eval_id, data)

        # Try primary storage
        try:
            result = self.primary.store_evaluation(eval_id, data)
            if result:
                # Store initial event
                events = [
                    {
                        "type": "submitted",
                        "timestamp": data["timestamp"],
                        "message": "Evaluation submitted",
                        "code_hash": data["code_hash"],
                    }
                ]
                self.primary.store_events(eval_id, events)
                return True
        except Exception as e:
            print(f"Primary storage failed: {e}")

            # Try fallback
            if self.fallback:
                try:
                    return self.fallback.store_evaluation(eval_id, data)
                except Exception as e2:
                    print(f"Fallback storage also failed: {e2}")

        return False

    def update_evaluation(
        self,
        eval_id: str,
        status: Optional[str] = None,
        output: Optional[str] = None,
        error: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Update an existing evaluation."""
        # Get current data
        current = self.get_evaluation(eval_id)
        if not current:
            return False

        # Update fields
        if status:
            current["status"] = status

            # Update timestamps
            now = datetime.now(timezone.utc).isoformat()
            if status == "running" and "started_at" not in current:
                current["started_at"] = now
            elif status in ["completed", "failed", "timeout"]:
                current["completed_at"] = now

                # Calculate runtime
                if "started_at" in current:
                    started = datetime.fromisoformat(current["started_at"])
                    completed = datetime.fromisoformat(now)
                    runtime_ms = int((completed - started).total_seconds() * 1000)
                    current["runtime_ms"] = runtime_ms

        # Handle output/error with clear truncation tracking
        if output is not None:
            current["output_size"] = len(output)
            if len(output) <= self.INLINE_THRESHOLD:
                current["output"] = output
                current["output_truncated"] = False
            else:
                current["output"] = output[: self.PREVIEW_SIZE]
                current["output_truncated"] = True
                # TODO: Store full output to S3/filesystem and set output_location

        if error is not None:
            current["error_size"] = len(error)
            if len(error) <= self.INLINE_THRESHOLD:
                current["error"] = error
                current["error_truncated"] = False
            else:
                current["error"] = error[: self.PREVIEW_SIZE]
                current["error_truncated"] = True
                # TODO: Store full error to S3/filesystem and set error_location

        # Update any additional fields
        # Special handling for metadata - merge instead of replace
        if "metadata" in kwargs:
            existing_metadata = current.get("metadata", {})
            new_metadata = kwargs.pop("metadata")
            current["metadata"] = {**existing_metadata, **new_metadata}

        # Update other fields normally
        current.update(kwargs)

        # Update cache
        if self.cache:
            self.cache.store_evaluation(eval_id, current)

        # Update primary storage
        try:
            result = self.primary.store_evaluation(eval_id, current)

            # Add status change event
            if result and status:
                event = {
                    "type": "status_changed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": f"Status changed to {status}",
                    "old_status": current.get("previous_status"),
                    "new_status": status,
                }

                # Get existing events and append
                events = self.primary.retrieve_events(eval_id)
                events.append(event)
                self.primary.store_events(eval_id, events)

            return result

        except Exception as e:
            print(f"Update failed: {e}")
            if self.fallback:
                return self.fallback.store_evaluation(eval_id, current)

        return False

    def get_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        """Get evaluation data."""
        # Check cache first
        if self.cache:
            cached = self.cache.retrieve_evaluation(eval_id)
            if cached:
                return cached

        # Try primary storage
        try:
            result = self.primary.retrieve_evaluation(eval_id)
            if result:
                # Update cache
                if self.cache:
                    self.cache.store_evaluation(eval_id, result)
                return result
        except Exception as e:
            print(f"Primary retrieval failed: {e}")

        # Try fallback
        if self.fallback:
            try:
                return self.fallback.retrieve_evaluation(eval_id)
            except Exception as e:
                print(f"Fallback retrieval failed: {e}")

        return None

    def add_event(self, eval_id: str, event_type: str, message: str, **metadata) -> bool:
        """Add an event to evaluation history."""
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            **metadata,
        }

        try:
            # Get existing events
            events = self.primary.retrieve_events(eval_id)
            events.append(event)

            # Store updated events
            return self.primary.store_events(eval_id, events)
        except Exception as e:
            print(f"Failed to add event: {e}")
            return False

    def get_events(self, eval_id: str) -> List[Dict[str, Any]]:
        """Get evaluation events."""
        try:
            return self.primary.retrieve_events(eval_id)
        except Exception as e:
            print(f"Failed to get events: {e}")
            if self.fallback:
                return self.fallback.retrieve_events(eval_id)
        return []

    def list_evaluations(
        self, limit: int = 100, offset: int = 0, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List evaluations with metadata."""
        try:
            # Get evaluation IDs from primary storage
            eval_ids = self.primary.list_evaluations(limit=limit, offset=offset)

            # Retrieve full evaluation data for each ID
            evaluations = []
            for eval_id in eval_ids:
                eval_data = self.get_evaluation(eval_id)
                if eval_data:
                    # Filter by status if specified
                    if status is None or eval_data.get("status") == status:
                        evaluations.append(eval_data)

            return evaluations

        except Exception as e:
            print(f"Failed to list evaluations: {e}")
            if self.fallback:
                try:
                    eval_ids = self.fallback.list_evaluations(limit, offset)
                    evaluations = []
                    for eval_id in eval_ids:
                        eval_data = self.get_evaluation(eval_id)
                        if eval_data:
                            if status is None or eval_data.get("status") == status:
                                evaluations.append(eval_data)
                    return evaluations
                except Exception:
                    pass
        return []

    def count_evaluations(self, status: Optional[str] = None) -> int:
        """Count total evaluations, optionally filtered by status."""
        # Try to get count from primary backend
        if hasattr(self.primary, "count_evaluations"):
            try:
                return self.primary.count_evaluations(status)
            except Exception as e:
                print(f"Failed to count evaluations: {e}")

        # Fallback to counting via list (inefficient but works)
        try:
            all_items = self.primary.list_evaluations(limit=100000, offset=0)
            if status:
                # Need to fetch each evaluation to check status
                count = 0
                for eval_id in all_items:
                    eval_data = self.get_evaluation(eval_id)
                    if eval_data and eval_data.get("status") == status:
                        count += 1
                return count
            else:
                return len(all_items)
        except Exception as e:
            print(f"Failed to count evaluations via list: {e}")
            return 0

    def delete_evaluation(self, eval_id: str) -> bool:
        """Delete an evaluation and all associated data."""
        # Remove from cache
        if self.cache:
            self.cache.delete_evaluation(eval_id)

        # Delete from primary
        try:
            result = self.primary.delete_evaluation(eval_id)

            # Also delete from fallback if it exists
            if self.fallback:
                self.fallback.delete_evaluation(eval_id)

            return result

        except Exception as e:
            print(f"Failed to delete evaluation: {e}")
            if self.fallback:
                return self.fallback.delete_evaluation(eval_id)

        return False
