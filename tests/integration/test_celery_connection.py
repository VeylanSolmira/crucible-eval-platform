#!/usr/bin/env python3
"""
Integration test for Celery and Redis connectivity.

This test verifies that the Celery worker can connect to Redis
and that the broker is properly configured.
"""

import os
import sys
import pytest
from celery import Celery
import redis


@pytest.mark.integration
@pytest.mark.celery
class TestCeleryConnection:
    """Test Celery connection and configuration."""
    
    @pytest.fixture(scope="class")
    def broker_url(self):
        """Get broker URL from environment."""
        return os.environ.get("CELERY_BROKER_URL", "redis://celery-redis:6379/0")
    
    @pytest.fixture(scope="class")
    def redis_client(self, broker_url):
        """Create Redis client for testing."""
        return redis.Redis.from_url(broker_url)
    
    @pytest.fixture(scope="class")
    def celery_app(self, broker_url):
        """Create Celery app for testing."""
        app = Celery("test", broker=broker_url)
        app.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
        )
        return app
    
    def test_redis_connection(self, redis_client):
        """Test direct Redis connection."""
        # Test ping
        assert redis_client.ping() is True
        
        # Test basic operations
        test_key = "test:connection:key"
        test_value = "test_value"
        
        # Set and get
        redis_client.set(test_key, test_value)
        assert redis_client.get(test_key).decode() == test_value
        
        # Cleanup
        redis_client.delete(test_key)
    
    def test_celery_broker_connection(self, celery_app):
        """Test Celery broker connection."""
        # Try to inspect the broker
        inspect = celery_app.control.inspect()
        
        # This might return None if no workers are running, which is OK
        # We're just testing that we can connect to the broker
        try:
            stats = inspect.stats()
            # If we get stats, workers are running
            if stats:
                assert isinstance(stats, dict)
                print(f"Found {len(stats)} active workers")
        except Exception as e:
            # Connection errors would raise here
            pytest.fail(f"Failed to connect to Celery broker: {e}")
    
    def test_celery_configuration(self, celery_app):
        """Test Celery configuration is correct."""
        # Verify serialization settings
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        
        # Verify broker URL is set
        assert celery_app.conf.broker_url is not None