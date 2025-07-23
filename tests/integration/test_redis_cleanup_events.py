"""
Integration tests for Redis cleanup via pub/sub events.

Tests that storage-worker properly cleans up Redis state when receiving
completion/failure/cancellation events through Redis pub/sub.
"""

import asyncio
import json
import time
import pytest
import httpx
from shared.utils.resilient_connections import ResilientRedisClient
from tests.k8s_test_config import REDIS_URL, STORAGE_SERVICE_URL as STORAGE_URL


@pytest.mark.integration
@pytest.mark.asyncio
async def test_executor_completion_event_flow():
    """
    Test the complete event flow when executor publishes completion.
    This simulates what happens internally.
    """
    redis_client = ResilientRedisClient(
        redis_url=REDIS_URL,
        service_name="test_executor_completion",
        decode_responses=True
    )
    
    # Create a test eval_id
    eval_id = f"test_eval_{int(time.time())}"
    
    # First, create the evaluation in the database so storage-worker can update it
    async with httpx.AsyncClient() as client:
        # Create evaluation in submitted state
        response = await client.post(
            f"{STORAGE_URL}/evaluations",
            json={
                "id": eval_id,
                "code": "print('test')",
                "language": "python",
                "status": "submitted"
            }
        )
        assert response.status_code == 200, f"Failed to create evaluation: {response.text}"
        
        # Update to running state using PUT endpoint
        response = await client.put(
            f"{STORAGE_URL}/evaluations/{eval_id}",
            json={"status": "running"}
        )
        assert response.status_code == 200, f"Failed to update to running: {response.text}"
    
    # Simulate what happens when evaluation starts running
    # Add to running evaluations (this is what dispatcher does)
    await redis_client.sadd("running_evaluations", eval_id)
    await redis_client.hset(f"eval:{eval_id}:running", mapping={
        "eval_id": eval_id,
        "status": "running",
        "started_at": time.time()
    })
    
    # 2. Simulate executor publishing completion event
    completion_event = {
        "eval_id": eval_id,
        "status": "completed",
        "output": "Test output",
        "error": "",
        "exit_code": 0,
        "executor_id": "test-executor"
    }
    
    # Publish to the channel storage-worker listens to
    await redis_client.publish("evaluation:completed", json.dumps(completion_event))
    
    # 3. Wait for storage-worker to process
    # Note: Storage worker might need time to receive and process the event
    # TODO: Replace sleep with proper event verification - could:
    #   - Poll Redis keys until cleaned up (with timeout)
    #   - Subscribe to storage:evaluation:updated event
    #   - Check storage worker metrics/logs
    await asyncio.sleep(3)
    
    # 4. Verify Redis was cleaned up
    exists = await redis_client.exists(f"eval:{eval_id}:running")
    assert not exists, "Running key should be deleted"
    running_evals = await redis_client.smembers("running_evaluations")
    assert eval_id not in running_evals, "Should be removed from running set"
    
    # 5. Verify evaluation was updated in database
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{STORAGE_URL}/evaluations/{eval_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed", f"Expected completed status, got {data['status']}"
        assert data["output"] == "Test output"
    
    # Clean up
    await redis_client.close()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_executor_completion_event_flow())