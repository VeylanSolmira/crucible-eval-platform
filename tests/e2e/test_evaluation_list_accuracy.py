#!/usr/bin/env python3
"""
End-to-end test that verifies evaluation list accuracy.

This test ensures that:
1. Completed evaluations are removed from the running list
2. Evaluation status is accurately reflected in both specific and list endpoints
3. The API correctly filters evaluations by status
"""
import asyncio
import httpx
import time
import os
import pytest
from tests.utils.adaptive_timeouts import wait_with_progress
import requests


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_list_accuracy():
    """
    Test that evaluation lists accurately reflect evaluation status.
    """
    # Use the correct API base URL without double /api/
    namespace = os.getenv("K8S_NAMESPACE", "crucible")
    api_host = os.getenv("API_HOST", f"api-service.{namespace}.svc.cluster.local")
    api_port = os.getenv("API_PORT", "8080")
    api_base = f"http://{api_host}:{api_port}/api"
    
    async with httpx.AsyncClient(verify=False) as client:
        # 1. Submit a simple evaluation that completes quickly
        print("1. Submitting evaluation...")
        response = await client.post(
            f"{api_base}/eval",
            json={
                "code": "print('Quick test')",
                "language": "python"
            }
        )
        assert response.status_code == 200
        eval_id = response.json()["eval_id"]
        print(f"   Evaluation ID: {eval_id}")
        
        # 2. Wait for it to complete using adaptive waiter
        print("\n2. Waiting for completion...")
        sync_session = requests.Session()
        results = wait_with_progress(sync_session, api_base, [eval_id], timeout=30)
        
        assert len(results["completed"]) == 1, f"Evaluation did not complete: {results}"
        
        # Verify it's actually completed
        response = await client.get(f"{api_base}/eval/{eval_id}")
        assert response.status_code == 200
        data = response.json()
        actual_status = data["status"]
        assert actual_status == "completed", f"Expected completed, got {actual_status}"
        print(f"   Status: {actual_status}")
        
        # 3. Verify completed evaluation is NOT in running list
        print("\n3. Checking running evaluations endpoint...")
        response = await client.get(f"{api_base}/evaluations?status=running")
        assert response.status_code == 200
        running_data = response.json()
        
        running_eval_ids = [e["eval_id"] for e in running_data.get("evaluations", [])]
        assert eval_id not in running_eval_ids, \
            f"Completed evaluation {eval_id} should not be in running list"
        print(f"   ✓ Completed evaluation not in running list (correct)")
        
        # 4. Verify evaluation appears with correct status in general list
        print("\n4. Checking general evaluations endpoint...")
        response = await client.get(f"{api_base}/evaluations")
        assert response.status_code == 200
        all_data = response.json()
        
        our_eval = next((e for e in all_data.get("evaluations", []) if e["eval_id"] == eval_id), None)
        assert our_eval is not None, f"Evaluation {eval_id} not found in general list"
        assert our_eval["status"] == "completed", \
            f"Expected status 'completed', got '{our_eval['status']}' in general list"
        print(f"   ✓ Status correctly shown as 'completed' in general list")
        
        # 5. Test status filtering for completed evaluations
        print("\n5. Checking completed evaluations endpoint...")
        response = await client.get(f"{api_base}/evaluations?status=completed")
        assert response.status_code == 200
        completed_data = response.json()
        
        completed_eval_ids = [e["eval_id"] for e in completed_data.get("evaluations", [])]
        assert eval_id in completed_eval_ids, \
            f"Completed evaluation {eval_id} should be in completed list"
        print(f"   ✓ Evaluation found in completed list (correct)")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_evaluation_statuses():
    """
    Test that multiple evaluations with different statuses are correctly categorized.
    """
    api_host = os.getenv("API_HOST", "api-service.crucible.svc.cluster.local")
    api_port = os.getenv("API_PORT", "8080")
    api_base = f"http://{api_host}:{api_port}/api"
    
    async with httpx.AsyncClient(verify=False) as client:
        # Submit multiple evaluations
        eval_ids = []
        
        # 1. Quick completion
        response = await client.post(
            f"{api_base}/eval",
            json={"code": "print('test1')", "language": "python"}
        )
        assert response.status_code == 200
        eval_ids.append(response.json()["eval_id"])
        
        # 2. Evaluation that will fail
        response = await client.post(
            f"{api_base}/eval",
            json={"code": "raise Exception('test error')", "language": "python"}
        )
        assert response.status_code == 200
        eval_ids.append(response.json()["eval_id"])
        
        # Wait for both to complete using adaptive waiter
        sync_session = requests.Session()
        results = wait_with_progress(sync_session, api_base, eval_ids, timeout=30)
        
        # Should have 2 evaluations in terminal state (completed or failed)
        total_done = len(results["completed"]) + len(results["failed"])
        assert total_done == 2, f"Expected 2 evaluations done, got {total_done}: {results}"
        
        # Give a bit more time for status to propagate to list endpoints
        await asyncio.sleep(2)
        
        # Check status endpoints
        response = await client.get(f"{api_base}/evaluations?status=completed")
        assert response.status_code == 200
        completed_ids = [e["eval_id"] for e in response.json().get("evaluations", [])]
        
        response = await client.get(f"{api_base}/evaluations?status=failed")
        assert response.status_code == 200
        failed_ids = [e["eval_id"] for e in response.json().get("evaluations", [])]
        
        response = await client.get(f"{api_base}/evaluations?status=running")
        assert response.status_code == 200
        running_ids = [e["eval_id"] for e in response.json().get("evaluations", [])]
        
        # Verify categorization - both evaluations should be in terminal states
        assert eval_ids[0] in completed_ids or eval_ids[0] in failed_ids
        assert eval_ids[1] in completed_ids or eval_ids[1] in failed_ids
        
        # Verify no overlap
        assert not (set(completed_ids) & set(running_ids))
        assert not (set(failed_ids) & set(running_ids))
        assert not (set(completed_ids) & set(failed_ids))