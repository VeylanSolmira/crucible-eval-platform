#!/usr/bin/env python3
"""
Test that verifies the evaluation status display bug where completed evaluations
still show as "running" in the evaluations list.

This test simulates the issue where:
1. Frontend fetches from /api/evaluations?status=running
2. Frontend hardcodes all results as status='running' 
3. Even if the actual evaluation is completed, UI shows it as running
"""
import asyncio
import httpx
import time
import json


async def test_evaluation_list_status_bug():
    """
    Test that demonstrates the status display bug in the evaluations list.
    """
    api_base = "http://localhost/api"  # Using nginx endpoint
    
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
        
        # 3. Check what /api/evaluations?status=running returns
        print("\n3. Checking running evaluations endpoint...")
        response = await client.get(f"{api_base}/evaluations?status=running")
        assert response.status_code == 200
        running_data = response.json()
        
        print(f"   Running evaluations count: {len(running_data.get('evaluations', []))}")
        
        # Check if our completed evaluation is in the "running" list
        running_eval_ids = [e["eval_id"] for e in running_data.get("evaluations", [])]
        
        if eval_id in running_eval_ids:
            print(f"\n❌ BUG CONFIRMED: Completed evaluation {eval_id} is in 'running' list!")
            
            # Get the evaluation from the running list
            running_eval = next(e for e in running_data["evaluations"] if e["eval_id"] == eval_id)
            print(f"   Data from running endpoint: status={running_eval.get('status')}")
            print(f"   But actual status is: {actual_status}")
            
            print("\n   Frontend will show this as 'running' because it hardcodes status!")
            return False
        else:
            print(f"\n✓ Completed evaluation {eval_id} is NOT in running list (correct)")
            
        # 4. Also check the general evaluations endpoint
        print("\n4. Checking general evaluations endpoint...")
        response = await client.get(f"{api_base}/evaluations")
        assert response.status_code == 200
        all_data = response.json()
        
        # Find our evaluation
        our_eval = next((e for e in all_data.get("evaluations", []) if e["eval_id"] == eval_id), None)
        if our_eval:
            print(f"   Status in general list: {our_eval.get('status')}")
            assert our_eval["status"] == "completed", "Status should be completed in general list"
        
        return True


async def test_frontend_status_logic():
    """
    Test that demonstrates how the frontend combines data sources incorrectly.
    """
    print("\n=== Testing Frontend Status Logic ===")
    
    # Simulate what the frontend does
    print("\n1. Frontend fetches from two sources:")
    print("   - useRunningEvaluations() -> /api/evaluations?status=running")
    print("   - useEvaluationHistory() -> /api/evaluations")
    
    print("\n2. For running evaluations, frontend does:")
    print("   status: 'running' as const  // HARDCODED!")
    
    print("\n3. This means:")
    print("   - Even if API returns a completed evaluation in the running list")
    print("   - Frontend will display it as 'running'")
    print("   - The ExecutionMonitor polls the specific eval and shows correct status")
    print("   - But the evaluations list stays wrong until page refresh")
    
    print("\n4. The fix would be:")
    print("   - Use the actual status from the API response")
    print("   - OR ensure the running endpoint only returns truly running evaluations")


if __name__ == "__main__":
    print("=== Evaluation Status Display Bug Test ===\n")
    
    # Run the main test
    bug_exists = asyncio.run(test_evaluation_list_status_bug())
    
    # Explain the issue
    asyncio.run(test_frontend_status_logic())
    
    if not bug_exists:
        print("\n⚠️  The bug exists in the frontend code that hardcodes status='running'")
        print("    even if the backend is working correctly!")