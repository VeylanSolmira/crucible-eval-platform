"""
Shared test configuration and fixtures for all tests.
"""

import pytest
import urllib3

# Disable SSL warnings for self-signed certificates in test environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import resource manager functionality if available
try:
    from tests.utils.resource_manager import pytest_addoption as resource_manager_addoption
    from tests.utils.resource_manager import resource_manager
    _resource_manager_available = True
except ImportError:
    # Resource manager not available (may be running outside cluster)
    resource_manager_addoption = None
    resource_manager = None
    _resource_manager_available = False

def pytest_addoption(parser):
    """Add custom command-line options."""
    # Call resource manager's addoption if available
    if resource_manager_addoption:
        resource_manager_addoption(parser)

# Register custom markers
def pytest_configure(config):
    """Register custom markers for test classification."""
    config.addinivalue_line(
        "markers", 
        "blackbox: Test that only uses external APIs and should work regardless of implementation"
    )
    config.addinivalue_line(
        "markers", 
        "whitebox: Test that depends on internal implementation details (Docker, file paths, etc.)"
    )
    config.addinivalue_line(
        "markers", 
        "graybox: Test that uses some internal knowledge but mostly tests behavior"
    )
    
    # Location-based markers for Kubernetes testing
    config.addinivalue_line(
        "markers",
        "requires_cluster_admin: Test requires cluster admin access (must run outside cluster)"
    )
    config.addinivalue_line(
        "markers",
        "requires_kubectl: Test requires kubectl access to verify Kubernetes resources"
    )
    config.addinivalue_line(
        "markers",
        "in_cluster_only: Test must run inside Kubernetes cluster for service access"
    )
    config.addinivalue_line(
        "markers",
        "location_agnostic: Test can run anywhere (default if no location marker)"
    )
    
    # Production requirement markers
    config.addinivalue_line(
        "markers",
        "production: Test that validates production-critical requirements (must pass in prod)"
    )

# Test environment detection
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This is optional - in containers, env vars should be set directly
try:
    load_dotenv()
except Exception:
    # Ignore errors - .env file is optional
    pass

# Lazy load configuration
_config_cache = None

def _load_config():
    """Lazy load configuration only when needed"""
    global _config_cache
    if _config_cache is None:
        from k8s_test_config import API_URL, VERIFY_SSL, REQUEST_TIMEOUT
        _config_cache = {
            "api_url": API_URL,
            "verify_ssl": VERIFY_SSL,
            "request_timeout": REQUEST_TIMEOUT
        }
    return _config_cache

# Default request configuration (will be loaded lazily)
def get_default_request_config():
    """Get default request configuration"""
    config = _load_config()
    return {
        "verify": config["verify_ssl"],
        "timeout": config["request_timeout"]
    }

def get_api_url():
    """Get the appropriate API URL based on environment"""
    config = _load_config()
    return config["api_url"]

def get_request_config(**overrides):
    """Get request configuration with optional overrides"""
    config = get_default_request_config().copy()
    config.update(overrides)
    return config

# Custom hook to print test results in a parseable format
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print test results in a simple JSON format after all tests complete."""
    import json
    
    # Get the test results from the terminal reporter stats
    stats = terminalreporter.stats
    passed = len(stats.get('passed', []))
    failed = len(stats.get('failed', []))
    skipped = len(stats.get('skipped', []))
    
    # Print in a specific format that's easy to find
    results = {"passed": passed, "failed": failed, "skipped": skipped}
    print(f"\nTEST_RESULTS_JSON:{json.dumps(results)}")
    print()  # Extra newline for clarity

# Re-export resource_manager fixture if available
if _resource_manager_available and resource_manager:
    globals()['resource_manager'] = resource_manager