#!/usr/bin/env python3
"""
Diagnostic script to check why status isn't updating from running to completed.
Run this while an evaluation is running to see the state transitions.
"""
import asyncio
import httpx
import time
import json
from redis import Redis


async def diagnose_evaluation(eval_id: str):
    """Monitor an evaluation through its lifecycle"""
    redis_client = Redis(host='localhost', port=6379, decode_responses=True)
    api_base = "http://localhost:8000"
    
    print(f"\n=== Diagnosing evaluation: {eval_id} ===\n")
    
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < 60:  # Monitor for up to 60 seconds
            print(f"\n--- Check at {time.time() - start_time:.1f}s ---")
            
            # Check Redis state
            print("Redis state:")
            running_info = redis_client.hgetall(f"eval:{eval_id}:running")
            if running_info:
                print(f"  Running info: {running_info}")
            else:
                print("  No running info in Redis")
                
            is_in_running_set = eval_id in redis_client.smembers("running_evaluations")
            print(f"  In running_evaluations set: {is_in_running_set}")
            
            # Check API response
            try:
                response = await client.get(f"{api_base}/api/eval/{eval_id}")
                print(f"\nAPI response: {response.status_code}")
                
                if response.status_code == 200 or response.status_code == 202:
                    data = response.json()
                    current_status = data.get("status", "unknown")
                    print(f"  Status: {current_status}")
                    print(f"  Output: {data.get('output', '')[:100]}...")
                    
                    if current_status != last_status:
                        print(f"\n!!! STATUS CHANGED: {last_status} -> {current_status}")
                        last_status = current_status
                        
                    if current_status in ["completed", "failed", "timeout"]:
                        print("\n=== Evaluation finished ===")
                        print(f"Final status: {current_status}")
                        print(f"Full output: {data.get('output', '')}")
                        break
                elif response.status_code == 404:
                    print("  ERROR: Got 404 - evaluation not found!")
                    break
            except Exception as e:
                print(f"  API error: {e}")
            
            # Check for Redis pub/sub messages (can't easily do in sync code)
            # But we can check if storage-worker is running
            try:
                storage_worker_response = await client.get("http://localhost:8086/health")
                print(f"\nStorage-worker health: {storage_worker_response.status_code}")
            except:
                print("\nStorage-worker health: UNREACHABLE")
            
            await asyncio.sleep(2)


async def submit_and_diagnose():
    """Submit a new evaluation and diagnose it"""
    async with httpx.AsyncClient() as client:
        # Submit evaluation
        response = await client.post(
            "http://localhost:8000/api/eval",
            json={
                "code": "import time\nprint('Starting...')\ntime.sleep(5)\nprint('Done!')",
                "language": "python"
            }
        )
        
        if response.status_code in [200, 202]:
            eval_id = response.json()["eval_id"]
            print(f"Submitted evaluation: {eval_id}")
            await diagnose_evaluation(eval_id)
        else:
            print(f"Failed to submit evaluation: {response.status_code}")
            print(f"Response: {response.text}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Diagnose existing evaluation
        asyncio.run(diagnose_evaluation(sys.argv[1]))
    else:
        # Submit new evaluation and diagnose
        asyncio.run(submit_and_diagnose())