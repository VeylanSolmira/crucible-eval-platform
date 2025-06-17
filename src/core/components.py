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

# Storage
from ..storage.storage import (
    StorageService,
    FileStorage,
    InMemoryStorage
)

# Event Bus
from ..event_bus.events import (
    EventBus,
    EventTypes
)

# Web Frontend
from ..web_frontend.web_frontend import (
    create_frontend,
    FrontendConfig,
    FrontendType,
    SimpleHTTPFrontend,
    AdvancedHTMLFrontend,
    FlaskFrontend,
    FastAPIFrontend,
    ReactFrontend
)

# Shared utilities
from ..shared.base import TestableComponent
from ..api.openapi_validator import OpenAPIValidatedAPI, create_openapi_validated_api

# API components (from future-services for now)
try:
    from ..api.api import (
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
    # Storage
    'StorageService',
    'FileStorage',
    'InMemoryStorage',
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
