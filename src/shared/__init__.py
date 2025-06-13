"""Shared components and utilities used across all services"""

from .base import TestableComponent

# Optional imports for future microservices
try:
    from .service_registry import ServiceRegistry
except ImportError:
    ServiceRegistry = None

__all__ = [
    'TestableComponent',
    'ServiceRegistry'
]
