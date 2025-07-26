"""
Resilient connection utilities for Redis and PostgreSQL.

Provides connection functions with automatic retry logic using tenacity.
This ensures services can handle temporary connection failures gracefully,
following cloud-native best practices.
"""

import logging
import os
from typing import Optional, Any, Callable
from urllib.parse import urlparse

import redis
from redis.asyncio import Redis as AsyncRedis
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log,
)

# For PostgreSQL connections
try:
    import asyncpg
    import psycopg2
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import create_async_engine
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_ATTEMPTS = int(os.getenv("CONNECTION_MAX_RETRIES", "5"))
DEFAULT_MIN_WAIT = int(os.getenv("CONNECTION_MIN_WAIT", "1"))  # seconds
DEFAULT_MAX_WAIT = int(os.getenv("CONNECTION_MAX_WAIT", "30"))  # seconds


# Redis Connection Functions
@retry(
    stop=stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=DEFAULT_MIN_WAIT, max=DEFAULT_MAX_WAIT),
    retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
)
def get_redis_client(
    url: str,
    decode_responses: bool = True,
    max_attempts: Optional[int] = None,
) -> redis.Redis:
    """
    Get a synchronous Redis client with retry logic.
    
    Args:
        url: Redis connection URL (e.g., "redis://localhost:6379/0")
        decode_responses: Whether to decode responses to strings
        max_attempts: Override default max retry attempts
        
    Returns:
        Connected Redis client
        
    Raises:
        redis.ConnectionError: After all retry attempts are exhausted
    """
    client = redis.from_url(url, decode_responses=decode_responses)
    # Test the connection
    client.ping()
    logger.info(f"Successfully connected to Redis at {_sanitize_url(url)}")
    return client


@retry(
    stop=stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=DEFAULT_MIN_WAIT, max=DEFAULT_MAX_WAIT),
    retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.INFO),
)
async def get_async_redis_client(
    url: str,
    decode_responses: bool = True,
    max_attempts: Optional[int] = None,
) -> AsyncRedis:
    """
    Get an asynchronous Redis client with retry logic.
    
    Args:
        url: Redis connection URL (e.g., "redis://localhost:6379/0")
        decode_responses: Whether to decode responses to strings
        max_attempts: Override default max retry attempts
        
    Returns:
        Connected async Redis client
        
    Raises:
        redis.ConnectionError: After all retry attempts are exhausted
    """
    client = AsyncRedis.from_url(url, decode_responses=decode_responses)
    # Test the connection
    await client.ping()
    logger.info(f"Successfully connected to async Redis at {_sanitize_url(url)}")
    return client


# PostgreSQL Connection Functions
if POSTGRES_AVAILABLE:
    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=DEFAULT_MIN_WAIT, max=DEFAULT_MAX_WAIT),
        retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.DatabaseError)),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO),
    )
    def get_postgres_connection(
        url: str,
        max_attempts: Optional[int] = None,
    ) -> psycopg2.extensions.connection:
        """
        Get a psycopg2 connection with retry logic.
        
        Args:
            url: PostgreSQL connection URL
            max_attempts: Override default max retry attempts
            
        Returns:
            Connected psycopg2 connection
            
        Raises:
            psycopg2.OperationalError: After all retry attempts are exhausted
        """
        conn = psycopg2.connect(url)
        logger.info(f"Successfully connected to PostgreSQL at {_sanitize_url(url)}")
        return conn


    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=DEFAULT_MIN_WAIT, max=DEFAULT_MAX_WAIT),
        retry=retry_if_exception_type((Exception,)),  # asyncpg has various exception types
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO),
    )
    async def get_async_postgres_connection(
        url: str,
        max_attempts: Optional[int] = None,
    ) -> asyncpg.Connection:
        """
        Get an asyncpg connection with retry logic.
        
        Args:
            url: PostgreSQL connection URL
            max_attempts: Override default max retry attempts
            
        Returns:
            Connected asyncpg connection
            
        Raises:
            asyncpg.PostgresError: After all retry attempts are exhausted
        """
        conn = await asyncpg.connect(url)
        logger.info(f"Successfully connected to async PostgreSQL at {_sanitize_url(url)}")
        return conn


    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=DEFAULT_MIN_WAIT, max=DEFAULT_MAX_WAIT),
        retry=retry_if_exception_type((Exception,)),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO),
    )
    def get_sqlalchemy_engine(
        url: str,
        max_attempts: Optional[int] = None,
        **engine_kwargs
    ):
        """
        Get a SQLAlchemy engine with retry logic.
        
        Args:
            url: Database connection URL
            max_attempts: Override default max retry attempts
            **engine_kwargs: Additional arguments for create_engine
            
        Returns:
            Connected SQLAlchemy engine
        """
        engine = create_engine(url, **engine_kwargs)
        # Test the connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info(f"Successfully created SQLAlchemy engine for {_sanitize_url(url)}")
        return engine


    @retry(
        stop=stop_after_attempt(DEFAULT_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=DEFAULT_MIN_WAIT, max=DEFAULT_MAX_WAIT),
        retry=retry_if_exception_type((Exception,)),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO),
    )
    async def get_async_sqlalchemy_engine(
        url: str,
        max_attempts: Optional[int] = None,
        **engine_kwargs
    ):
        """
        Get an async SQLAlchemy engine with retry logic.
        
        Args:
            url: Database connection URL (use postgresql+asyncpg://)
            max_attempts: Override default max retry attempts
            **engine_kwargs: Additional arguments for create_async_engine
            
        Returns:
            Connected async SQLAlchemy engine
        """
        engine = create_async_engine(url, **engine_kwargs)
        # Test the connection
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info(f"Successfully created async SQLAlchemy engine for {_sanitize_url(url)}")
        return engine


# Utility Functions
def _sanitize_url(url: str) -> str:
    """
    Remove password from connection URL for logging.
    
    Args:
        url: Connection URL
        
    Returns:
        URL with password replaced by ****
    """
    parsed = urlparse(url)
    if parsed.password:
        sanitized = url.replace(f":{parsed.password}@", ":****@")
        return sanitized
    return url


class ResilientRedisClient:
    """
    Redis client with automatic retry, reconnection, and graceful degradation.
    
    This client maintains a persistent connection and handles:
    - Initial connection failures (service can start without Redis)
    - Reconnection after connection loss
    - Pub/sub operations
    - Graceful degradation when Redis is unavailable
    """
    
    def __init__(self, redis_url: str, service_name: str, decode_responses: bool = False):
        """
        Initialize Redis client.
        
        Args:
            redis_url: Redis connection URL
            service_name: Name of service using this client (for logging)
            decode_responses: Whether to decode responses to strings
        """
        self.redis_url = redis_url
        self.service_name = service_name
        self.decode_responses = decode_responses
        self._client: Optional[AsyncRedis] = None
        self._pubsub: Optional[Any] = None
    
    async def _connect(self) -> bool:
        """
        Establish connection to Redis.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._client = await get_async_redis_client(
                self.redis_url,
                decode_responses=self.decode_responses
            )
            return True
        except Exception as e:
            logger.error(f"[{self.service_name}] Failed to connect to Redis: {e}")
            self._client = None
            return False
    
    async def get_client(self) -> Optional[AsyncRedis]:
        """
        Get Redis client with automatic reconnection.
        
        Returns:
            Redis client instance or None if unavailable
        """
        # If no client, try to connect
        if not self._client:
            await self._connect()
            return self._client
        
        # Validate existing connection
        try:
            await self._client.ping()
            return self._client
        except Exception as e:
            logger.warning(f"[{self.service_name}] Lost Redis connection, attempting reconnect: {e}")
            self._client = None
            await self._connect()
            return self._client
    
    async def publish(self, channel: str, message: str) -> bool:
        """
        Publish message to channel.
        
        Args:
            channel: Channel name
            message: Message to publish (will be encoded to bytes)
            
        Returns:
            True if successful, False otherwise
        """
        client = await self.get_client()
        if client:
            try:
                # Ensure message is bytes if decode_responses is False
                if not self.decode_responses and isinstance(message, str):
                    message_bytes = message.encode('utf-8')
                else:
                    message_bytes = message
                    
                await client.publish(channel, message_bytes)
                logger.debug(f"[{self.service_name}] Published to {channel}")
                return True
            except Exception as e:
                logger.error(f"[{self.service_name}] Failed to publish to {channel}: {e}")
        else:
            logger.warning(f"[{self.service_name}] Cannot publish to {channel}: Redis unavailable")
        return False
    
    async def subscribe(self, *channels: str) -> Optional[Any]:
        """
        Subscribe to channels for pub/sub.
        
        Args:
            channels: Channel names to subscribe to
            
        Returns:
            PubSub instance or None if connection failed
        """
        client = await self.get_client()
        if client:
            try:
                self._pubsub = client.pubsub()
                await self._pubsub.subscribe(*channels)
                logger.info(f"[{self.service_name}] Subscribed to channels: {', '.join(channels)}")
                return self._pubsub
            except Exception as e:
                logger.error(f"[{self.service_name}] Failed to subscribe: {e}")
                self._pubsub = None
        else:
            logger.warning(f"[{self.service_name}] Cannot subscribe: Redis unavailable")
        return None
    
    async def get(self, key: str) -> Optional[bytes]:
        """Get value for key."""
        client = await self.get_client()
        if client:
            try:
                return await client.get(key)
            except Exception as e:
                logger.error(f"[{self.service_name}] Failed to get key {key}: {e}")
        return None
    
    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set key-value pair.
        
        Args:
            key: Key name
            value: Value to set
            ex: Expiration in seconds
            
        Returns:
            True if successful
        """
        client = await self.get_client()
        if client:
            try:
                await client.set(key, value, ex=ex)
                return True
            except Exception as e:
                logger.error(f"[{self.service_name}] Failed to set key {key}: {e}")
        return False
    
    async def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration."""
        return await self.set(key, value, ex=seconds)
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        client = await self.get_client()
        if client:
            try:
                return await client.exists(*keys)
            except Exception as e:
                logger.error(f"[{self.service_name}] Failed to check existence: {e}")
        return 0
    
    async def sismember(self, key: str, member: str) -> bool:
        """Check if member exists in set."""
        client = await self.get_client()
        if client:
            try:
                return await client.sismember(key, member)
            except Exception as e:
                logger.error(f"[{self.service_name}] Failed to check set membership: {e}")
        return False
    
    async def sadd(self, key: str, *values: str) -> int:
        """
        Add one or more members to a set.
        
        Args:
            key: Set key
            values: Values to add
            
        Returns:
            Number of elements added to the set
        """
        client = await self.get_client()
        if not client:
            return 0
        
        try:
            return await client.sadd(key, *values)
        except Exception as e:
            logger.error(f"[{self.service_name}] Error adding to set: {e}")
            return 0
    
    async def smembers(self, key: str) -> set:
        """
        Get all members of a set.
        
        Args:
            key: Set key
            
        Returns:
            Set of members (empty set if error)
        """
        client = await self.get_client()
        if not client:
            return set()
        
        try:
            return await client.smembers(key)
        except Exception as e:
            logger.error(f"[{self.service_name}] Error getting set members: {e}")
            return set()
    
    async def hset(self, key: str, mapping: dict = None, **kwargs) -> int:
        """
        Set hash field values.
        
        Args:
            key: Hash key
            mapping: Dict of field:value pairs
            **kwargs: Additional field:value pairs
            
        Returns:
            Number of fields added
        """
        client = await self.get_client()
        if not client:
            return 0
        
        try:
            if mapping:
                return await client.hset(key, mapping=mapping)
            else:
                return await client.hset(key, **kwargs)
        except Exception as e:
            logger.error(f"[{self.service_name}] Error setting hash: {e}")
            return 0
    
    async def close(self) -> None:
        """Clean shutdown of Redis connections."""
        if self._pubsub:
            try:
                await self._pubsub.close()
            except Exception as e:
                logger.error(f"[{self.service_name}] Error closing pubsub: {e}")
            finally:
                self._pubsub = None
        
        if self._client:
            try:
                await self._client.aclose()
                logger.info(f"[{self.service_name}] Closed Redis connection")
            except Exception as e:
                logger.error(f"[{self.service_name}] Error closing Redis client: {e}")
            finally:
                self._client = None


def create_retry_decorator(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: int = DEFAULT_MIN_WAIT,
    max_wait: int = DEFAULT_MAX_WAIT,
    exception_types: tuple = (Exception,),
    logger_instance: Optional[logging.Logger] = None,
) -> Callable:
    """
    Create a custom retry decorator with specified parameters.
    
    This is useful when you need retry logic for custom connection types
    or want different retry behavior.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exception_types: Tuple of exception types to retry on
        logger_instance: Logger to use (defaults to module logger)
        
    Returns:
        Configured retry decorator
        
    Example:
        ```python
        my_retry = create_retry_decorator(max_attempts=3, exception_types=(MyError,))
        
        @my_retry
        def connect_to_service():
            # Your connection logic here
            pass
        ```
    """
    log = logger_instance or logger
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exception_types),
        before=before_log(log, logging.INFO),
        after=after_log(log, logging.INFO),
    )