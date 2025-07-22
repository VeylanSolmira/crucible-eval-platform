"""
Shared logging configuration for all services.

This module provides consistent logging setup across all microservices,
including filtering of noisy health check logs.
"""

import logging
import os
from typing import Dict, Any


class HealthCheckFilter(logging.Filter):
    """Filter to exclude health check endpoints from logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to exclude health check logs"""
        # Check if this is a uvicorn access log
        if record.name == "uvicorn.access":
            message = record.getMessage()
            # Filter out common health check endpoints
            health_endpoints = [
                "/health",
                "/ready", 
                "/readiness",
                "/liveness",
                "/healthz",
                "/_health",
                "/api/health"
            ]
            for endpoint in health_endpoints:
                if f'"{endpoint} HTTP' in message:
                    return False
        return True


def configure_logging(
    service_name: str,
    level: str = None,
    exclude_health_checks: bool = True
) -> Dict[str, Any]:
    """
    Configure logging for a service with consistent format.
    
    Args:
        service_name: Name of the service for log identification
        level: Logging level (default from LOG_LEVEL env var or INFO)
        exclude_health_checks: Whether to filter out health check logs
        
    Returns:
        Logging configuration dict for use with logging.config.dictConfig
    """
    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {},
        "formatters": {
            "default": {
                "format": f"[%(asctime)s] %(levelname)s [{service_name}] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": f"[%(asctime)s] %(levelname)s [{service_name}] %(name)s:%(funcName)s:%(lineno)d: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
                "filters": []
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        },
        "loggers": {
            # Reduce verbosity of some common libraries
            "urllib3": {"level": "WARNING"},
            "kubernetes": {"level": "WARNING"},
            "werkzeug": {"level": "WARNING"}
        }
    }
    
    # Add health check filter if requested
    if exclude_health_checks:
        config["filters"]["health_check"] = {
            "()": HealthCheckFilter
        }
        config["handlers"]["console"]["filters"].append("health_check")
        
        # For uvicorn specifically
        config["loggers"]["uvicorn.access"] = {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False
        }
    
    return config


# Environment-specific settings
def should_exclude_health_checks() -> bool:
    """Determine if health checks should be excluded based on environment"""
    env = os.getenv("ENVIRONMENT", "development")
    # Always exclude in development, configurable in production
    if env == "development":
        return True
    return os.getenv("EXCLUDE_HEALTH_CHECK_LOGS", "true").lower() == "true"