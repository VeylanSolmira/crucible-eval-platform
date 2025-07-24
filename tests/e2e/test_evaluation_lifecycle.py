"""
Integration test for evaluation lifecycle - ensures status updates correctly
from running to completed when executor finishes.
"""
import asyncio
import json
import time
import httpx
import pytest
from shared.utils.resilient_connections import ResilientRedisClient
from tests.k8s_test_config import REDIS_URL, API_URL
from tests.utils.adaptive_timeouts import AdaptiveWaiter


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_completes_and_status_updates():
    """
    Test that when executor publishes completion event:
    1. Storage-worker updates the database
    2. Redis is cleaned up properly
    3. API returns correct status (not 404)
    4. Frontend sees status change from running to completed
    """
    redis_client = ResilientRedisClient(
        redis_url=REDIS_URL,
        service_name="test_evaluation_lifecycle",
        decode_responses=True
    )
    api_base = API_URL  # Already includes /api path
    
    # Submit an evaluation
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_base}/eval",  # api_base already includes /api
            json={
                "code": "print('Hello, World!')",
                "language": "python"
            }
        )
        assert response.status_code in [200, 202]  # API returns 200 OK
        eval_data = response.json()
        eval_id = eval_data["eval_id"]
        
        # Use adaptive waiter for better timing
        waiter = AdaptiveWaiter(initial_timeout=30)
        
        # Convert async client to sync for the waiter
        import requests
        sync_session = requests.Session()
        
        # Wait for evaluation to complete
        results = waiter.wait_for_evaluations(
            sync_session, 
            api_base,
            [eval_id],
            check_resources=True
        )
        
        assert len(results["completed"]) == 1, f"Evaluation did not complete: {results}"
        
        # Get final status
        response = await client.get(f"{api_base}/eval/{eval_id}")
        assert response.status_code in [200, 202]
        status_data = response.json()
        final_status = status_data["status"]
        
        # Already waited above with AdaptiveWaiter
        
        # Verify it completed
        assert final_status == "completed", f"Expected completed, got {final_status}"
        assert "Hello, World!" in status_data.get("output", "")
        
        # Verify Redis was cleaned up
        exists = await redis_client.exists(f"eval:{eval_id}:running")
        assert not exists
        running_evals = await redis_client.smembers("running_evaluations")
        assert eval_id not in running_evals
        
        # Verify we can still fetch it (no 404)
        response = await client.get(f"{api_base}/eval/{eval_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
    
    # Clean up
    await redis_client.close()


if __name__ == "__main__":
    # Run the main lifecycle test
    asyncio.run(test_evaluation_completes_and_status_updates())