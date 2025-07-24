"""
Example test demonstrating resource cleanup functionality.

This test shows how to use the resource cleanup features to ensure
tests run in a clean environment.
"""

import pytest
import time
import requests
from typing import List
from tests.utils.resource_manager import with_resource_cleanup, managed_test_resources


class TestResourceCleanupExample:
    """Example tests showing resource cleanup patterns."""
    
    def test_with_fixture(self, api_session, api_base_url, resource_manager):
        """Example using the resource_manager fixture."""
        # Submit multiple evaluations
        eval_ids = []
        for i in range(3):
            response = api_session.post(
                f"{api_base_url}/eval",
                json={
                    "code": f"print('Test evaluation {i}')",
                    "language": "python"
                }
            )
            assert response.status_code == 200
            eval_id = response.json()["eval_id"]
            eval_ids.append(eval_id)
            
            # Track the job for cleanup
            resource_manager.track_resource("jobs", f"evaluation-job-{eval_id}")
        
        # Wait for evaluations to complete
        for eval_id in eval_ids:
            self._wait_for_completion(api_session, api_base_url, eval_id)
        
        # Resources will be cleaned up automatically after test
        print(f"Submitted {len(eval_ids)} evaluations")
    
    @with_resource_cleanup(cleanup_level="pods", wait_after=5)
    def test_with_decorator(self, api_session, api_base_url):
        """Example using the decorator for automatic cleanup."""
        # Submit an evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={
                "code": "import time; time.sleep(2); print('Decorated test')",
                "language": "python"
            }
        )
        assert response.status_code == 200
        eval_id = response.json()["eval_id"]
        
        # Wait for completion
        self._wait_for_completion(api_session, api_base_url, eval_id)
        
        # Pods will be cleaned up after test, with 5 second wait
    
    def test_with_context_manager(self, api_session, api_base_url):
        """Example using context manager for fine-grained control."""
        with managed_test_resources("context_test", cleanup_level="all") as manager:
            # Submit evaluation
            response = api_session.post(
                f"{api_base_url}/eval",
                json={
                    "code": "print('Context manager test')",
                    "language": "python"
                }
            )
            assert response.status_code == 200
            eval_id = response.json()["eval_id"]
            
            # Track the resource
            manager.track_resource("jobs", f"evaluation-job-{eval_id}")
            
            # Wait for completion
            self._wait_for_completion(api_session, api_base_url, eval_id)
        
        # Both pods and jobs cleaned up when context exits
    
    @pytest.mark.slow
    @pytest.mark.skip(reason="Just an example test, haven't fully vetted cleanup logic yet")
    def test_heavy_resource_usage(self, api_session, api_base_url, resource_manager):
        """Example of a resource-intensive test that benefits from cleanup."""
        # Set cleanup level for heavy test
        resource_manager.cleanup_level = "all"
        
        # Submit many evaluations
        eval_ids = []
        for i in range(10):
            response = api_session.post(
                f"{api_base_url}/eval",
                json={
                    "code": f"import numpy as np; a = np.random.rand(1000, 1000); print(f'Matrix {i} created')",
                    "language": "python"
                }
            )
            assert response.status_code == 200
            eval_ids.append(response.json()["eval_id"])
        
        # Wait for all to complete
        for eval_id in eval_ids:
            self._wait_for_completion(api_session, api_base_url, eval_id, timeout=60)
        
        # Full cleanup happens after test
        print(f"Completed {len(eval_ids)} resource-intensive evaluations")
    
    def _wait_for_completion(self, api_session, api_base_url: str, eval_id: str, timeout: int = 30):
        """Helper to wait for evaluation completion."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = api_session.get(f"{api_base_url}/eval/{eval_id}")
            if response.status_code == 200:
                result = response.json()
                if result["status"] in ["completed", "failed", "timeout"]:
                    return result
            time.sleep(0.5)
        
        pytest.fail(f"Evaluation {eval_id} did not complete within {timeout} seconds")


@pytest.mark.parametrize("cleanup_level", ["none", "pods", "all"])
@pytest.mark.skip(reason="Just an example test, haven't fully vetted cleanup logic yet")
def test_cleanup_levels(api_session, api_base_url, cleanup_level):
    """Test different cleanup levels."""
    with managed_test_resources(f"cleanup_level_{cleanup_level}", cleanup_level=cleanup_level) as manager:
        # Submit a simple evaluation
        response = api_session.post(
            f"{api_base_url}/eval",
            json={
                "code": f"print('Testing cleanup level: {cleanup_level}')",
                "language": "python"
            }
        )
        assert response.status_code == 200
        
        # Log what will happen
        if cleanup_level == "none":
            print("No cleanup will occur")
        elif cleanup_level == "pods":
            print("Only pods will be cleaned up")
        else:
            print("Both pods and jobs will be cleaned up")