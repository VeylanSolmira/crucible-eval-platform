"""
Shared fixtures for integration tests.
"""

import pytest
import requests
import redis
import time
import logging
from typing import Generator, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default configuration
API_BASE_URL = "http://localhost:8000/api"
REDIS_URL = "redis://localhost:6379"


@pytest.fixture
def api_base_url() -> str:
    """Get API base URL from environment or use default"""
    import os
    return os.getenv("API_BASE_URL", API_BASE_URL)


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL from environment or use default"""
    import os
    return os.getenv("REDIS_URL", REDIS_URL)


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
        response = session.get(f"{api_base_url.replace('/api', '')}/health", timeout=5)
        response.raise_for_status()
        logger.info("API health check passed")
    except Exception as e:
        pytest.skip(f"API not accessible at {api_base_url}: {e}")
    
    yield session
    
    session.close()


@pytest.fixture
def redis_client(redis_url: str) -> Generator[redis.Redis, None, None]:
    """Create Redis client for testing"""
    client = redis.from_url(redis_url, decode_responses=True)
    
    # Verify Redis is accessible
    try:
        client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        pytest.skip(f"Redis not accessible at {redis_url}: {e}")
    
    yield client
    
    client.close()


@pytest.fixture(autouse=True)
def cleanup_test_data(redis_client: redis.Redis):
    """Automatically clean up test data after each test"""
    # Track test evaluation IDs
    test_eval_ids = []
    
    # Store original sismember method
    original_sadd = redis_client.sadd
    
    # Monkey patch to track test evaluations
    def track_sadd(key: str, *values):
        if key == "running_evaluations":
            test_eval_ids.extend(values)
        return original_sadd(key, *values)
    
    redis_client.sadd = track_sadd
    
    yield
    
    # Restore original method
    redis_client.sadd = original_sadd
    
    # Clean up any test data
    for eval_id in test_eval_ids:
        pattern = f"*{eval_id}*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.debug(f"Cleaned up {len(keys)} keys for {eval_id}")
    
    # Remove from running set
    if test_eval_ids:
        redis_client.srem("running_evaluations", *test_eval_ids)


@pytest.fixture
def wait_for_services():
    """Wait for all services to be ready before running tests"""
    max_wait = 30
    start_time = time.time()
    
    services_ready = False
    while time.time() - start_time < max_wait:
        try:
            # Check API health
            response = requests.get(f"{API_BASE_URL.replace('/api', '')}/health", timeout=2)
            if response.status_code == 200:
                health = response.json()
                if health.get("status") == "healthy":
                    services = health.get("services", {})
                    if all(services.values()):
                        services_ready = True
                        break
        except Exception:
            pass
        
        time.sleep(1)
    
    if not services_ready:
        pytest.skip("Services not ready after 30 seconds")
    
    logger.info("All services ready")


# Markers are now defined in pyproject.toml
# No need to define them here