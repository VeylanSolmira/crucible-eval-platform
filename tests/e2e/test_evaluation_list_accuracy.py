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


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_evaluation_list_accuracy():
    """
    Test that evaluation lists accurately reflect evaluation status.
    """
    # Use the correct API base URL without double /api/
    api_host = os.getenv("API_HOST", "api-service.crucible.svc.cluster.local")
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
        
        # 2. Wait for it to complete
        print("\n2. Waiting for completion...")
        max_wait = 10
        start_time = time.time()
        actual_status = None
        
        while time.time() - start_time < max_wait:
            response = await client.get(f"{api_base}/eval/{eval_id}")
            assert response.status_code == 200
            data = response.json()
            actual_status = data["status"]
            
            if actual_status in ["completed", "failed"]:
                print(f"   Status: {actual_status}")
                break
                
            await asyncio.sleep(0.5)
        
        assert actual_status == "completed", f"Expected completed, got {actual_status}"
        
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
        
        # 3. Long-running evaluation
        response = await client.post(
            f"{api_base}/eval",
            json={"code": "import time; time.sleep(30)", "language": "python"}
        )
        assert response.status_code == 200
        eval_ids.append(response.json()["eval_id"])
        
        # Wait for first two to complete
        await asyncio.sleep(5)
        
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
        
        # Verify categorization
        assert eval_ids[0] in completed_ids or eval_ids[0] in failed_ids
        assert eval_ids[1] in completed_ids or eval_ids[1] in failed_ids
        assert eval_ids[2] in running_ids
        
        # Verify no overlap
        assert not (set(completed_ids) & set(running_ids))
        assert not (set(failed_ids) & set(running_ids))
        assert not (set(completed_ids) & set(failed_ids))