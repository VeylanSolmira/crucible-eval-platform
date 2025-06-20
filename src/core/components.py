"""
Components import helper for the platform

This module provides a clean import interface for all platform components,
handling the path setup and providing a single place to manage imports.
This is a common pattern in Python projects (similar to Django's shortcuts).
"""

# Core platform classes removed to break circular import
# Import these directly from core.py in your application code

# Execution engines
from ..execution_engine.execution import (
    ExecutionEngine,
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    DisabledEngine
)

# Monitoring
from ..monitoring.monitoring import (
    MonitoringService,
    AdvancedMonitor
)

# Queue
from ..queue.queue import (
    TaskQueue
)

# Storage - Now use 'from storage import ...' at the root level
# The storage module has been moved to /storage/ with improved architecture

# Event Bus
from ..event_bus.events import (
    EventBus,
    EventTypes
)

# Shared utilities
from ..shared.base import TestableComponent
from api.openapi_validator import OpenAPIValidatedAPI, create_openapi_validated_api

# API components (from future-services for now)
try:
    from api.api import (
        create_api_service,
        create_api_handler
    )
except ImportError:
    # Fallback for API components
    def create_api_service(*args, **kwargs):
        raise NotImplementedError("API Gateway not available")
    
    def create_api_handler(*args, **kwargs):
        raise NotImplementedError("API Gateway not available")

# Re-export everything
__all__ = [
    # Base
    'TestableComponent',
    # Execution
    'ExecutionEngine',
    'SubprocessEngine',
    'DockerEngine',
    'GVisorEngine',
    # Monitoring
    'MonitoringService',
    'AdvancedMonitor',
    # Queue
    'TaskQueue',
    # Storage - removed, use 'from storage import ...' instead
    # Events
    'EventBus',
    'EventTypes',
    # Frontend
    'create_frontend',
    'FrontendConfig',
    'FrontendType',
    'SimpleHTTPFrontend',
    'AdvancedHTMLFrontend',
    'FlaskFrontend',
    'FastAPIFrontend',
    'ReactFrontend',
    # API
    'create_api_service',
    'create_api_handler',
    # Utilities
    'OpenAPIValidatedAPI',
    'create_openapi_validated_api',
]
# Storage imports removed - use 'from storage import ...' instead
