"""
Storage abstraction layer for Crucible Platform.

This module provides a unified interface for different storage backends:
- Database (PostgreSQL) - Structured metadata and queries
- Redis - Caching and queue state
- S3 - Large file storage (future)
- Filesystem - Local temporary files
- In-memory - Testing and development
"""

from .manager import StorageManager
from .flexible_manager import FlexibleStorageManager
from .base import StorageService

# Import backends
from .backends.memory import InMemoryStorage
from .backends.file import FileStorage

# Optional import for database
try:
    from .backends.database import DatabaseStorage
except ImportError:
    DatabaseStorage = None

__all__ = [
    "StorageManager",
    "FlexibleStorageManager",
    "StorageService",
    "InMemoryStorage",
    "FileStorage",
    "DatabaseStorage",
]
