#!/usr/bin/env python3
"""
Test Redis state management for evaluation lifecycle using pytest.
"""
import pytest
import time
import json

# The redis_client and api_session fixtures are imported from conftest.py


@pytest.fixture
def wait_for():
    """Fixture for polling with timeout."""
    def _wait(condition_func, timeout=10, interval=0.5):
        """Wait for condition to be true, return True if met, False if timeout."""
        end_time = time.time() + timeout
        while time.time() < end_time:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    return _wait


class TestRedisStateManagement:
    """Test Redis state management during evaluation lifecycle."""
    
    def test_basic_evaluation_lifecycle(self, redis_client, api_session, api_base_url, wait_for):
        """Test that Redis state is properly managed throughout evaluation lifecycle."""
        # Submit evaluation
        payload = {
            "code": "print('Testing Redis state'); import time; time.sleep(2); print('Done')",
            "language": "python"
        }
        
        response = api_session.post(f"{api_base_url}/eval", json=payload)
        assert response.status_code == 200, f"Failed to submit: {response.status_code}"
        
        eval_id = response.json()["eval_id"]
        print(f"\nSubmitted evaluation: {eval_id}")
        
        # Define keys we're checking
        running_key = f"eval:{eval_id}:running"
        running_set = "running_evaluations"
        
        # Wait for evaluation to enter running state
        def is_running():
            return redis_client.exists(running_key) and redis_client.sismember(running_set, eval_id)
        
        assert wait_for(is_running, timeout=10), f"Evaluation {eval_id} did not enter running state"
        print("✓ Evaluation entered running state")
        
        # Verify running info has required fields
        running_info = redis_client.get(running_key)
        assert running_info, "Running key exists but has no value"
        
        info_dict = json.loads(running_info)
        required_fields = ["executor_id", "container_id", "started_at", "timeout"]
        for field in required_fields:
            assert field in info_dict, f"Missing required field '{field}' in running info"
        print(f"✓ Running info valid: executor={info_dict['executor_id']}")
        
        # Wait for evaluation to complete
        def is_complete():
            resp = api_session.get(f"{api_base_url}/eval/{eval_id}")
            if resp.status_code == 200:
                return resp.json()["status"] in ["completed", "failed"]
            return False
        
        assert wait_for(is_complete, timeout=30), f"Evaluation {eval_id} did not complete"
        print("✓ Evaluation completed")
        
        # Wait for Redis state to be cleaned up
        def is_cleaned_up():
            return (not redis_client.exists(running_key) and 
                    not redis_client.sismember(running_set, eval_id))
        
        assert wait_for(is_cleaned_up, timeout=5), "Redis state not cleaned up after completion"
        print("✓ Redis state cleaned up")
        
    def test_failed_evaluation_cleanup(self, redis_client, api_session, api_base_url, wait_for):
        """Test that Redis state is cleaned up even when evaluation fails."""
        # Submit evaluation that will fail
        payload = {
            "code": "import sys; sys.exit(1)",
            "language": "python"
        }
        
        response = api_session.post(f"{api_base_url}/eval", json=payload)
        assert response.status_code == 200
        
        eval_id = response.json()["eval_id"]
        print(f"\nSubmitted failing evaluation: {eval_id}")
        
        # Wait for completion (should fail quickly)
        def is_done():
            resp = api_session.get(f"{api_base_url}/eval/{eval_id}")
            if resp.status_code == 200:
                return resp.json()["status"] in ["completed", "failed"]
            return False
        
        assert wait_for(is_done, timeout=15), "Evaluation did not complete"
        
        # Verify it failed
        resp = api_session.get(f"{api_base_url}/eval/{eval_id}")
        assert resp.json()["status"] == "failed", "Expected failed status"
        print("✓ Evaluation failed as expected")
        
        # Wait for Redis cleanup
        running_key = f"eval:{eval_id}:running"
        def is_cleaned_up():
            return (not redis_client.exists(running_key) and 
                    not redis_client.sismember("running_evaluations", eval_id))
        
        assert wait_for(is_cleaned_up, timeout=5), "Redis state not cleaned up after failure"
        print("✓ Redis cleaned up after failure")
        
        # Print success summary
        print("\n✅ Redis state management test completed successfully!")
        print("   - Evaluation lifecycle tracking works correctly")
        print("   - State cleanup happens after both success and failure")