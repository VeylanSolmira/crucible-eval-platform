"""
File-based storage implementation.
"""

import json
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..core.base import StorageService


class FileStorage(StorageService):
    """
    File-based storage with JSON serialization.
    Thread-safe implementation with atomic writes.

    Directory structure:
    base_path/
    ├── evaluations/
    │   └── {eval_id}.json
    ├── events/
    │   └── {eval_id}.json
    └── metadata/
        └── {eval_id}.json
    """

    def __init__(self, base_path: str = "data/storage"):
        self.base_path = Path(base_path)
        self.lock = threading.Lock()

        # Create directory structure
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure storage directories exist"""
        directories = [
            self.base_path,
            self.base_path / "evaluations",
            self.base_path / "events",
            self.base_path / "metadata",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_eval_path(self, eval_id: str) -> Path:
        """Get evaluation file path"""
        return self.base_path / "evaluations" / f"{eval_id}.json"

    def _get_events_path(self, eval_id: str) -> Path:
        """Get events file path"""
        return self.base_path / "events" / f"{eval_id}.json"

    def _get_metadata_path(self, eval_id: str) -> Path:
        """Get metadata file path"""
        return self.base_path / "metadata" / f"{eval_id}.json"

    def _write_json(self, path: Path, data: Any) -> bool:
        """Write JSON data to file atomically"""
        try:
            # Write to temporary file first for atomicity
            temp_path = path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic rename
            temp_path.replace(path)
            return True

        except Exception as e:
            # Clean up temp file if exists
            if "temp_path" in locals() and temp_path.exists():
                temp_path.unlink()
            print(f"Error writing to {path}: {e}")
            return False

    def _read_json(self, path: Path) -> Optional[Any]:
        """Read JSON data from file"""
        if not path.exists():
            return None

        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading JSON from {path}: {e}")
            return None

    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        with self.lock:
            path = self._get_eval_path(eval_id)
            return self._write_json(path, data)

    def retrieve_evaluation(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            path = self._get_eval_path(eval_id)
            return self._read_json(path)

    def store_events(self, eval_id: str, events: List[Dict[str, Any]]) -> bool:
        with self.lock:
            path = self._get_events_path(eval_id)
            return self._write_json(path, events)

    def retrieve_events(self, eval_id: str) -> List[Dict[str, Any]]:
        with self.lock:
            path = self._get_events_path(eval_id)
            result = self._read_json(path)
            return result if result is not None else []

    def store_metadata(self, eval_id: str, metadata: Dict[str, Any]) -> bool:
        with self.lock:
            path = self._get_metadata_path(eval_id)
            return self._write_json(path, metadata)

    def retrieve_metadata(self, eval_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            path = self._get_metadata_path(eval_id)
            return self._read_json(path)

    def list_evaluations(self, limit: int = 100, offset: int = 0) -> List[str]:
        with self.lock:
            eval_dir = self.base_path / "evaluations"
            if not eval_dir.exists():
                return []

            # Get all evaluation files sorted by modification time (newest first)
            eval_files = sorted(
                eval_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
            )

            # Extract IDs and apply pagination
            eval_ids = [f.stem for f in eval_files]
            return eval_ids[offset : offset + limit]

    def delete_evaluation(self, eval_id: str) -> bool:
        with self.lock:
            deleted = False

            # Delete all associated files
            for path_func in [self._get_eval_path, self._get_events_path, self._get_metadata_path]:
                path = path_func(eval_id)
                if path.exists():
                    path.unlink()
                    deleted = True

            return deleted
