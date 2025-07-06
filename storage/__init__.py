"""
Storage abstraction layer for Crucible Platform.

This module provides a unified interface for different storage backends:
- Database (PostgreSQL) - Structured metadata and queries
- Redis - Caching and queue state
- S3 - Large file storage (future)
- Filesystem - Local temporary files
- In-memory - Testing and development
"""

from .core.flexible_manager import FlexibleStorageManager
from .core.base import StorageService

# Import backends
from .backends import InMemoryStorage, FileStorage, DatabaseStorage

__all__ = [
    "FlexibleStorageManager",
    "StorageService",
    "InMemoryStorage",
    "FileStorage",
    "DatabaseStorage",
]
