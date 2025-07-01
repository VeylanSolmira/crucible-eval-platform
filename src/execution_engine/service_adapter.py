"""
Adapter to use either local or remote execution engines based on configuration.

⚠️ STATUS: PREPARED BUT NOT INTEGRATED
This adapter is ready for when we need to support remote execution.
Currently, the main app.py creates execution engines directly.

To activate:
1. Set EXECUTION_MODE=remote in environment
2. Update app.py to use create_execution_engine() from this module
3. Start the execution service (src/execution_service/server.py)

This allows the platform to run in both monolith and microservices modes
without changing the core application logic.
"""

import os
import logging

from .execution import DockerEngine, GVisorEngine, DisabledEngine
from .remote_engine import RemoteExecutionEngine

logger = logging.getLogger(__name__)


def create_execution_engine():
    """
    Factory function to create the appropriate execution engine based on environment.
    
    Environment variables:
    - EXECUTION_MODE: 'local' (default) or 'remote'
    - EXECUTION_SERVICE_URL: URL of remote execution service (if mode=remote)
    
    Returns:
        ExecutionEngine instance (local or remote)
    """
    mode = os.environ.get('EXECUTION_MODE', 'local').lower()
    
    if mode == 'remote':
        # Use remote execution service
        service_url = os.environ.get('EXECUTION_SERVICE_URL')
        if not service_url:
            logger.error("EXECUTION_MODE=remote but EXECUTION_SERVICE_URL not set")
            return DisabledEngine("Remote execution service URL not configured")
        
        try:
            logger.info(f"Connecting to remote execution service at {service_url}")
            return RemoteExecutionEngine(service_url)
        except Exception as e:
            logger.error(f"Failed to connect to remote execution service: {e}")
            return DisabledEngine(f"Cannot connect to execution service: {e}")
    
    else:
        # Local execution (current behavior)
        logger.info("Using local execution engine")
        
        # Try to initialize local engine (same logic as before)
        import platform
        
        if platform.system() == 'Linux':
            try:
                return GVisorEngine()
            except Exception as e:
                logger.info(f"gVisor not available: {e}, trying Docker")
        
        try:
            return DockerEngine()
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            return DisabledEngine(f"No local execution engine available: {e}")


# For backward compatibility
def get_default_engine():
    """Get the default execution engine based on environment."""
    return create_execution_engine()