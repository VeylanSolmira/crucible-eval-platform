"""
Core storage functionality including base classes and managers.
"""

from .base import StorageService
from .config import StorageConfig
from .flexible_manager import FlexibleStorageManager

__all__ = ["StorageService", "StorageConfig", "FlexibleStorageManager"]