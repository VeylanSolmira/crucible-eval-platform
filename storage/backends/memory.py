"""
In-memory storage implementation.
"""

import threading
from typing import Dict, List, Any, Optional

from ..core.base import StorageService


class InMemoryStorage(StorageService):
    """
    Simple in-memory storage for testing and development.
    Thread-safe implementation using locks.

    Future evolution:
    - Add TTL support
    - Add size limits
    - Add LRU eviction
    - Add persistence snapshots
    """

    def __init__(self):
        self.evaluations = {}
        self.events = {}
        self.metadata = {}
        self.lock = threading.Lock()

    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        with self.lock:
            self.evaluations[eval_id] = data.copy()
            return True

    def retrieve_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.evaluations.get(eval_id, {}).copy() if eval_id in self.evaluations else None

    def store_events(self, eval_id: str, events: List[Dict[str, Any]]) -> bool:
        with self.lock:
            self.events[eval_id] = [event.copy() for event in events]
            return True

    def retrieve_events(self, eval_id: str) -> List[Dict[str, Any]]:
        with self.lock:
            return [event.copy() for event in self.events.get(eval_id, [])]

    def store_metadata(self, eval_id: str, metadata: Dict[str, Any]) -> bool:
        with self.lock:
            self.metadata[eval_id] = metadata.copy()
            return True

    def retrieve_metadata(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.metadata.get(eval_id, {}).copy() if eval_id in self.metadata else None

    def list_evaluations(self, limit: int = 100, offset: int = 0) -> List[str]:
        with self.lock:
            eval_ids = list(self.evaluations.keys())
            return eval_ids[offset : offset + limit]

    def delete_evaluation(self, eval_id: str) -> bool:
        with self.lock:
            deleted = False
            if eval_id in self.evaluations:
                del self.evaluations[eval_id]
                deleted = True
            if eval_id in self.events:
                del self.events[eval_id]
                deleted = True
            if eval_id in self.metadata:
                del self.metadata[eval_id]
                deleted = True
            return deleted
