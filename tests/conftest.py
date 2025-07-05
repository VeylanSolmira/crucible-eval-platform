"""
Shared test configuration and fixtures for all tests.
"""

import urllib3

# Disable SSL warnings for self-signed certificates in test environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Configuration
API_BASE_URL = "https://localhost/api"
API_DEV_URL = "http://localhost:8000/api"

# SSL Configuration
VERIFY_SSL = False  # Set to True for production with valid certs

# Default request configuration
DEFAULT_REQUEST_CONFIG = {
    "verify": VERIFY_SSL,
    "timeout": 5
}

# Test environment detection
import os
USE_DEV_API = os.environ.get("USE_DEV_API", "false").lower() == "true"

def get_api_url():
    """Get the appropriate API URL based on environment"""
    return API_DEV_URL if USE_DEV_API else API_BASE_URL

def get_request_config(**overrides):
    """Get request configuration with optional overrides"""
    config = DEFAULT_REQUEST_CONFIG.copy()
    config.update(overrides)
    return config