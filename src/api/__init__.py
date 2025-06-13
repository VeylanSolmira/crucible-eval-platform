"""API module - handles evaluation requests and responses"""

from .api import (
    APIService,
    RESTfulAPIHandler,
    APIRequest,
    APIResponse,
    HTTPMethod,
    create_api_service,
    create_api_handler
)

# OpenAPI validation is optional
try:
    from .openapi_validator import OpenAPIValidator
except ImportError:
    OpenAPIValidator = None

__all__ = [
    'APIService',
    'RESTfulAPIHandler',
    'APIRequest',
    'APIResponse',
    'HTTPMethod',
    'create_api_service',
    'create_api_handler',
    'OpenAPIValidator'
]
