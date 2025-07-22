"""
Unit test for storage worker Redis cleanup functionality.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from storage_worker import StorageWorker


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_cleanup_on_completion():
    """
    Test that storage worker cleans up Redis keys when processing completion event.
    """
    # Create storage worker instance
    worker = StorageWorker()
    
    # Mock Redis client
    worker.redis = AsyncMock()
    worker.redis.delete = AsyncMock()
    worker.redis.srem = AsyncMock()
    worker.redis.publish = AsyncMock()
    
    # Create a completion event message
    eval_id = "test-eval-123"
    
    # Mock HTTP client - make it return success
    worker.client = AsyncMock()
    
    # Create proper mock response objects
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json = MagicMock(return_value={
        "eval_id": eval_id,
        "status": "running"  # Current status before completion
    })
    
    mock_put_response = MagicMock()
    mock_put_response.status_code = 200
    
    # Configure the async methods to return these mock objects
    worker.client.get = AsyncMock(return_value=mock_get_response)
    worker.client.put = AsyncMock(return_value=mock_put_response)
    message = {
        "channel": b"evaluation:completed",
        "data": json.dumps({
            "eval_id": eval_id,
            "status": "completed",
            "output": "Test output",
            "exit_code": 0,
            "metadata": {
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        }).encode()
    }
    
    # Process the message
    await worker.handle_message(message)
    
    # Verify Redis cleanup was called
    worker.redis.delete.assert_called_once_with(f"eval:{eval_id}:running")
    worker.redis.srem.assert_called_once_with("running_evaluations", eval_id)
    
    # Verify storage service was updated  
    worker.client.put.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_cleanup_on_failed():
    """
    Test that storage worker cleans up Redis keys when processing failed event.
    """
    # Create storage worker instance
    worker = StorageWorker()
    
    # Mock Redis client
    worker.redis = AsyncMock()
    worker.redis.delete = AsyncMock()
    worker.redis.srem = AsyncMock()
    worker.redis.publish = AsyncMock()
    
    # Create a failed event message
    eval_id = "test-eval-456"
    
    # Mock HTTP client
    worker.client = AsyncMock()
    
    # Create proper mock response objects
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json = MagicMock(return_value={
        "eval_id": eval_id,
        "status": "running"  # Current status before failure
    })
    
    mock_put_response = MagicMock()
    mock_put_response.status_code = 200
    
    # Configure the async methods to return these mock objects
    worker.client.get = AsyncMock(return_value=mock_get_response)
    worker.client.put = AsyncMock(return_value=mock_put_response)
    message = {
        "channel": b"evaluation:failed",
        "data": json.dumps({
            "eval_id": eval_id,
            "error": "Test error",
            "exit_code": 1,
            "metadata": {
                "failed_at": datetime.now(timezone.utc).isoformat()
            }
        }).encode()
    }
    
    # Process the message
    await worker.handle_message(message)
    
    # Verify Redis cleanup was called
    worker.redis.delete.assert_called_once_with(f"eval:{eval_id}:running")
    worker.redis.srem.assert_called_once_with("running_evaluations", eval_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_cleanup_on_timeout():
    """
    Test that storage worker cleans up Redis keys when processing timeout event.
    """
    # Create storage worker instance
    worker = StorageWorker()
    
    # Mock Redis client
    worker.redis = AsyncMock()
    worker.redis.delete = AsyncMock()
    worker.redis.srem = AsyncMock()
    worker.redis.publish = AsyncMock()
    
    # Create a timeout event message
    eval_id = "test-eval-789"
    
    # Mock HTTP client
    worker.client = AsyncMock()
    
    # Create proper mock response objects
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json = MagicMock(return_value={
        "eval_id": eval_id,
        "status": "running"  # Current status before timeout
    })
    
    mock_put_response = MagicMock()
    mock_put_response.status_code = 200
    
    # Configure the async methods to return these mock objects
    worker.client.get = AsyncMock(return_value=mock_get_response)
    worker.client.put = AsyncMock(return_value=mock_put_response)
    message = {
        "channel": b"evaluation:failed",
        "data": json.dumps({
            "eval_id": eval_id,
            "error": "Execution time exceeded",
            "exit_code": -1,
            "metadata": {
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "reason": "timeout"
            }
        }).encode()
    }
    
    # Process the message
    await worker.handle_message(message)
    
    # Verify Redis cleanup was called
    worker.redis.delete.assert_called_once_with(f"eval:{eval_id}:running")
    worker.redis.srem.assert_called_once_with("running_evaluations", eval_id)