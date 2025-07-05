"""
Integration test for evaluation lifecycle - ensures status updates correctly
from running to completed when executor finishes.
"""
import asyncio
import json
import time
import httpx
import pytest
from redis import Redis


@pytest.mark.asyncio
async def test_evaluation_completes_and_status_updates():
    """
    Test that when executor publishes completion event:
    1. Storage-worker updates the database
    2. Redis is cleaned up properly
    3. API returns correct status (not 404)
    4. Frontend sees status change from running to completed
    """
    redis_client = Redis(host='localhost', port=6379, decode_responses=True)
    api_base = "http://localhost:8000"
    
    # Submit an evaluation
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_base}/api/eval",
            json={
                "code": "print('Hello, World!')",
                "language": "python"
            }
        )
        assert response.status_code == 202
        eval_data = response.json()
        eval_id = eval_data["eval_id"]
        
        # Wait for it to start running
        await asyncio.sleep(2)
        
        # Check it's running
        response = await client.get(f"{api_base}/api/eval/{eval_id}")
        assert response.status_code in [200, 202]
        status_data = response.json()
        assert status_data["status"] == "running"
        
        # Wait for completion (simple print should be fast)
        max_wait = 30
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait:
            response = await client.get(f"{api_base}/api/eval/{eval_id}")
            assert response.status_code != 404, f"Got 404 for {eval_id} - evaluation disappeared!"
            
            status_data = response.json()
            final_status = status_data["status"]
            
            if final_status in ["completed", "failed", "timeout"]:
                break
                
            await asyncio.sleep(1)
        
        # Verify it completed
        assert final_status == "completed", f"Expected completed, got {final_status}"
        assert "Hello, World!" in status_data.get("output", "")
        
        # Verify Redis was cleaned up
        assert not redis_client.exists(f"eval:{eval_id}:running")
        assert eval_id not in redis_client.smembers("running_evaluations")
        
        # Verify we can still fetch it (no 404)
        response = await client.get(f"{api_base}/api/eval/{eval_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_executor_completion_event_flow():
    """
    Test the complete event flow when executor publishes completion.
    This simulates what happens internally.
    """
    redis_client = Redis(host='localhost', port=6379, decode_responses=True)
    
    # Create a test eval_id
    eval_id = f"test_eval_{int(time.time())}"
    
    # Simulate what storage-worker does
    # 1. Add to running evaluations (simulating evaluation start)
    redis_client.sadd("running_evaluations", eval_id)
    redis_client.hset(f"eval:{eval_id}:running", mapping={
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
    redis_client.publish("evaluation:completed", json.dumps(completion_event))
    
    # 3. Wait for storage-worker to process
    await asyncio.sleep(2)
    
    # 4. Verify Redis was cleaned up
    assert not redis_client.exists(f"eval:{eval_id}:running"), "Running key should be deleted"
    assert eval_id not in redis_client.smembers("running_evaluations"), "Should be removed from running set"
    
    # 5. Verify we can fetch from API without 404
    async with httpx.AsyncClient() as client:
        # Note: This assumes storage-worker created the DB entry
        # In real test, we'd need to ensure the evaluation exists in DB first
        pass


if __name__ == "__main__":
    # Run the main lifecycle test
    asyncio.run(test_evaluation_completes_and_status_updates())