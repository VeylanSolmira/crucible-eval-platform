"""
Configuration module that supports both development (semantic) and production (obfuscated) 
environment variable names.

In development: Uses semantic names like BIND_HOST
In production: Build process transforms to random names like A7X9K3M2P5Q8R1T4
"""

import os
import json
from pathlib import Path

class ConfigLoader:
    """
    Configuration loader that works with both semantic and obfuscated env vars.
    
    This allows the same code to work in development (readable names) and
    production (obfuscated names) without changes.
    """
    
    def __init__(self, mapping_file: str = None):
        self.mapping = {}
        
        # In production, a mapping file is injected by the build process
        if mapping_file and Path(mapping_file).exists():
            with open(mapping_file) as f:
                data = json.load(f)
                self.mapping = data.get('mapping', {})
        
        # Check for auto-generated mapping from build
        elif Path('/app/config/env_mapping.json').exists():
            with open('/app/config/env_mapping.json') as f:
                data = json.load(f)
                self.mapping = data.get('mapping', {})
    
    def get(self, semantic_name: str, default=None):
        """
        Get environment variable by semantic name.
        
        In development: Returns os.environ.get('BIND_HOST')
        In production: Returns os.environ.get('A7X9K3M2P5Q8R1T4')
        """
        # Check if we have a mapping (production mode)
        if self.mapping:
            obfuscated_name = self.mapping.get(semantic_name, semantic_name)
            value = os.environ.get(obfuscated_name)
            if value is not None:
                return value
        
        # Fall back to semantic name (development mode)
        return os.environ.get(semantic_name, default)


# Global config instance
_config = ConfigLoader()


class Config:
    """
    Application configuration with semantic property names.
    
    Usage:
        from config import config
        print(config.bind_host)  # Works in both dev and prod
    """
    
    # Server configuration
    @property
    def bind_host(self) -> str:
        """Host to bind server to (default: localhost)"""
        return _config.get('BIND_HOST', 'localhost')
    
    @property
    def port(self) -> int:
        """Port to bind server to (default: 8080)"""
        return int(_config.get('PORT', '8080'))
    
    # Service discovery
    @property
    def service_host(self) -> str:
        """Hostname for inter-service communication"""
        return _config.get('SERVICE_HOST', 'localhost')
    
    @property
    def platform_host(self) -> str:
        """API gateway hostname"""
        return _config.get('PLATFORM_HOST', 'localhost')
    
    # Security settings
    @property
    def max_execution_time(self) -> int:
        """Maximum execution time in seconds"""
        return int(_config.get('MAX_EXECUTION_TIME', '30'))
    
    @property
    def memory_limit(self) -> str:
        """Memory limit for containers (e.g., '100m')"""
        return _config.get('MEMORY_LIMIT', '100m')
    
    @property
    def cpu_limit(self) -> str:
        """CPU limit for containers (e.g., '0.5')"""
        return _config.get('CPU_LIMIT', '0.5')
    
    @property
    def enable_network(self) -> bool:
        """Whether to enable network access in containers"""
        return _config.get('ENABLE_NETWORK', 'false').lower() == 'true'
    
    # Logging
    @property
    def log_level(self) -> str:
        """Logging level (DEBUG, INFO, WARNING, ERROR)"""
        return _config.get('LOG_LEVEL', 'INFO')
    
    # Storage
    @property
    def storage_path(self) -> str:
        """Base path for storage"""
        return _config.get('STORAGE_PATH', '/app/storage')
    
    @property
    def temp_path(self) -> str:
        """Path for temporary files"""
        return _config.get('TEMP_PATH', f'{self.storage_path}/tmp')
    
    # Feature flags
    @property
    def enable_gvisor(self) -> bool:
        """Whether to enable gVisor runtime"""
        return _config.get('ENABLE_GVISOR', 'true').lower() == 'true'
    
    @property
    def enable_monitoring(self) -> bool:
        """Whether to enable monitoring"""
        return _config.get('ENABLE_MONITORING', 'true').lower() == 'true'
    
    # Development helpers
    def get_raw(self, key: str, default=None):
        """Get raw environment variable (for debugging)"""
        return _config.get(key, default)
    
    def is_production(self) -> bool:
        """Check if running in production (has obfuscated mapping)"""
        return bool(_config.mapping)
    
    def __repr__(self) -> str:
        """String representation (safe - doesn't leak values)"""
        mode = "production (obfuscated)" if self.is_production() else "development"
        return f"<Config mode={mode}>"


# Singleton instance
config = Config()


# For backwards compatibility
def get_env(key: str, default=None):
    """Legacy function for getting environment variables"""
    return config.get_raw(key, default)