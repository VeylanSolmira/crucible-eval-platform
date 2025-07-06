"""
Storage backend implementations.
"""

from .memory import InMemoryStorage
from .file import FileStorage

# Optional database backend
try:
    from .database import DatabaseStorage
except ImportError:
    DatabaseStorage = None

__all__ = ["InMemoryStorage", "FileStorage", "DatabaseStorage"]