"""
Kubernetes test configuration.

This module handles service discovery for tests running against Kubernetes.
"""

import os
from typing import Dict


def get_k8s_service_url(service_name: str, namespace: str = None, port: int = None) -> str:
    """
    Get the appropriate service URL based on test environment.
    
    Args:
        service_name: Name of the Kubernetes service
        namespace: Kubernetes namespace (default: from K8S_NAMESPACE env var or crucible)
        port: Service port (if different from default)
    
    Returns:
        Service URL appropriate for the test environment
    """
    # Use namespace from environment if not specified
    if namespace is None:
        namespace = os.environ.get("K8S_NAMESPACE", "crucible")
    
    # Check if we're running inside Kubernetes
    in_cluster = os.environ.get("KUBERNETES_SERVICE_HOST") is not None
    in_cluster_tests = os.environ.get("IN_CLUSTER_TESTS", "false").lower() == "true"
    
    if in_cluster or in_cluster_tests:
        # Inside cluster: use Kubernetes DNS
        return f"{service_name}.{namespace}.svc.cluster.local"
    else:
        # Outside cluster: must use environment variables
        raise ValueError(
            f"Not running in cluster and no explicit service URL provided. "
            f"Please set appropriate environment variables for {service_name} service. "
            f"For example: {service_name.upper()}_HOST=localhost (if using port-forward)"
        )


def get_service_config() -> Dict[str, str]:
    """
    Get service configuration for all platform services.
    
    Returns:
        Dictionary of service URLs based on environment
    """
    base_config = {
        "celery_redis_host": get_k8s_service_url("celery-redis"),
        "redis_host": get_k8s_service_url("redis"),
        "postgres_host": get_k8s_service_url("postgres"),
        "api_host": get_k8s_service_url("api-service"),
        "storage_host": get_k8s_service_url("storage-service"),
    }
    
    # Build full URLs
    config = {
        "CELERY_BROKER_URL": os.environ.get(
            "CELERY_BROKER_URL", 
            f"redis://{base_config['celery_redis_host']}:6379/0"
        ),
        "REDIS_URL": os.environ.get(
            "REDIS_URL",
            f"redis://{base_config['redis_host']}:6379/0"
        ),
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL",
            f"postgresql://crucible:changeme@{base_config['postgres_host']}:5432/crucible"
        ),
        "API_URL": os.environ.get(
            "API_URL",
            f"http://{base_config['api_host']}:8080/api"
        ),
        "STORAGE_SERVICE_URL": os.environ.get(
            "STORAGE_SERVICE_URL",
            f"http://{base_config['storage_host']}:8082"
        ),
    }
    
    return config


# Export commonly used configurations
SERVICE_CONFIG = get_service_config()
CELERY_BROKER_URL = SERVICE_CONFIG["CELERY_BROKER_URL"]
REDIS_URL = SERVICE_CONFIG["REDIS_URL"]
DATABASE_URL = SERVICE_CONFIG["DATABASE_URL"]
API_URL = SERVICE_CONFIG["API_URL"]
STORAGE_SERVICE_URL = SERVICE_CONFIG["STORAGE_SERVICE_URL"]

# Celery result backend (uses database 1 on celery-redis)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    f"redis://{SERVICE_CONFIG['CELERY_BROKER_URL'].split('://')[1].split('/')[0]}/1"
)

# SSL Configuration
# In production/cluster: verify SSL
# In local development: skip SSL verification
in_cluster = os.environ.get("KUBERNETES_SERVICE_HOST") is not None
in_cluster_tests = os.environ.get("IN_CLUSTER_TESTS", "false").lower() == "true"
VERIFY_SSL = os.environ.get("VERIFY_SSL", str(in_cluster or in_cluster_tests)).lower() == "true"

# Default timeout for requests
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "5"))