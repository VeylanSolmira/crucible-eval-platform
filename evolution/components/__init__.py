"""
TRACE-AI Components Package

Each component can evolve independently into microservices or larger systems.
This modular architecture allows for:
- Independent testing
- Easy replacement/upgrading
- Distributed deployment
- Technology diversity
"""

from .base import TestableComponent
from .execution import ExecutionEngine, SubprocessEngine, DockerEngine, GVisorEngine
from .monitoring import MonitoringService, InMemoryMonitor, AdvancedMonitor
from .queue import TaskQueue
from .platform import TestableEvaluationPlatform, QueuedEvaluationPlatform
from .storage import StorageService, InMemoryStorage, FileStorage
from .api import APIService, RESTfulAPIHandler, create_api_service, create_api_handler, APIRequest, APIResponse, HTTPMethod
from .web_frontend import (
    WebFrontendService, FrontendConfig, FrontendType,
    create_frontend
)
from .events import EventBus, EventTypes

# Optional OpenAPI validation (requires openapi-core)
try:
    from .openapi_validator import OpenAPIValidatedAPI, create_openapi_validated_api
except ImportError:
    OpenAPIValidatedAPI = None
    create_openapi_validated_api = None

__all__ = [
    'TestableComponent',
    'ExecutionEngine',
    'SubprocessEngine', 
    'DockerEngine',
    'GVisorEngine',
    'MonitoringService',
    'InMemoryMonitor',
    'AdvancedMonitor',
    'TaskQueue',
    'TestableEvaluationPlatform',
    'QueuedEvaluationPlatform',
    'StorageService',
    'InMemoryStorage',
    'FileStorage',
    'APIService',
    'RESTfulAPIHandler',
    'create_api_service',
    'create_api_handler',
    'APIRequest',
    'APIResponse',
    'HTTPMethod',
    'WebFrontendService',
    'FrontendConfig',
    'FrontendType',
    'create_frontend',
    'OpenAPIValidatedAPI',
    'create_openapi_validated_api',
    'EventBus',
    'EventTypes'
]