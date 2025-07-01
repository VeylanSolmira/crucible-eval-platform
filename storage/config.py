"""
Storage configuration for Crucible Platform.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class StorageConfig:
    """Configuration for storage system."""
    
    # Database configuration
    database_url: Optional[str] = None
    
    # File storage configuration
    file_storage_path: Optional[str] = None
    
    # Redis configuration (future)
    redis_url: Optional[str] = None
    
    # Storage preferences
    prefer_database: bool = True
    enable_caching: bool = True
    
    # Large file threshold (bytes) - files larger than this go to file storage
    large_file_threshold: int = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def from_environment(cls) -> "StorageConfig":
        """Create configuration from environment variables."""
        return cls(
            database_url=os.environ.get("DATABASE_URL"),
            file_storage_path=os.environ.get("FILE_STORAGE_PATH", "./data"),
            redis_url=os.environ.get("REDIS_URL"),
            prefer_database=os.environ.get("PREFER_DATABASE", "true").lower() == "true",
            enable_caching=os.environ.get("ENABLE_CACHING", "true").lower() == "true",
            large_file_threshold=int(os.environ.get("LARGE_FILE_THRESHOLD", str(10 * 1024 * 1024)))
        )
    
    @classmethod
    def for_testing(cls, use_memory: bool = True) -> "StorageConfig":
        """Create configuration for testing."""
        if use_memory:
            return cls(
                database_url=None,
                file_storage_path=None,
                prefer_database=False,
                enable_caching=False
            )
        else:
            # Use temporary directory for tests
            return cls(
                database_url=None,
                file_storage_path="/tmp/crucible-test-storage",
                prefer_database=False,
                enable_caching=False
            )