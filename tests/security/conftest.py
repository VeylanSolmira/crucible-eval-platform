"""
Shared fixtures for security tests.
"""

import pytest
import requests
import time
import logging
from typing import Generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration from k8s_test_config (parent directory)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from k8s_test_config import API_URL, REQUEST_TIMEOUT, VERIFY_SSL


@pytest.fixture
def api_base_url() -> str:
    """Get API base URL from environment or use default"""
    return os.getenv("API_URL", API_URL)


def get_api_url():
    """Get the appropriate API URL based on environment"""
    return os.getenv("API_URL", API_URL)


def get_request_config(**overrides):
    """Get request configuration with optional overrides"""
    config = {
        "timeout": REQUEST_TIMEOUT,
        "verify": VERIFY_SSL
    }
    config.update(overrides)
    return config


@pytest.fixture
def api_session(api_base_url: str) -> Generator[requests.Session, None, None]:
    """Create a requests session for API calls"""
    session = requests.Session()
    # Add any common headers
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    
    # Verify API is accessible
    try:
        # API_URL already includes /api, so just append /health
        response = session.get(f"{api_base_url}/health", timeout=5)
        response.raise_for_status()
        logger.info("API health check passed")
    except Exception as e:
        pytest.skip(f"API not accessible at {api_base_url}: {e}")
    
    yield session
    
    session.close()