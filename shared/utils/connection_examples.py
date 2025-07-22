"""
Examples of how to use resilient_connections in services.

This file shows how to migrate from direct connections to resilient ones.
"""

# Example 1: Storage Worker (Async Redis)
# Before:
import redis.asyncio as redis
redis_client = redis.from_url("redis://redis:6379")

# After:
from shared.utils.resilient_connections import get_async_redis_client
redis_client = await get_async_redis_client("redis://redis:6379")


# Example 2: API Service (Sync Redis)
# Before:
import redis
redis_client = redis.from_url(REDIS_URL)

# After:
from shared.utils.resilient_connections import get_redis_client
redis_client = get_redis_client(REDIS_URL)


# Example 3: Storage Service (SQLAlchemy)
# Before:
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL)

# After:
from shared.utils.resilient_connections import get_sqlalchemy_engine
engine = get_sqlalchemy_engine(DATABASE_URL)


# Example 4: Celery Worker (Multiple connections)
# Before:
redis_broker = redis.from_url(CELERY_BROKER_URL)
redis_main = redis.from_url(REDIS_URL)

# After:
from shared.utils.resilient_connections import get_redis_client
redis_broker = get_redis_client(CELERY_BROKER_URL)
redis_main = get_redis_client(REDIS_URL)


# Example 5: Custom retry configuration
from shared.utils.resilient_connections import create_retry_decorator

# Create custom retry for HTTP services
http_retry = create_retry_decorator(
    max_attempts=3,
    min_wait=2,
    max_wait=10,
    exception_types=(ConnectionError, TimeoutError)
)

@http_retry
def connect_to_executor_service():
    response = requests.get("http://executor-service/health")
    response.raise_for_status()
    return response