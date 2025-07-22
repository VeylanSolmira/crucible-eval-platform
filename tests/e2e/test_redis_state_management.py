#!/usr/bin/env python3
"""
Test to verify Redis cleanup happens when evaluations complete.
This tests the full flow from evaluation completion to Redis cleanup.
"""
import asyncio
import httpx
import time
import json
import redis.asyncio as redis
import pytest
from k8s_test_config import API_URL, REDIS_URL


@pytest.mark.asyncio
async def test_redis_cleanup():
    """Test that Redis running set is cleaned up when evaluation completes."""
    api_base = API_URL
    redis_client = await redis.from_url(REDIS_URL)
    
    async with httpx.AsyncClient(verify=False) as client:
        # 1. Submit evaluation
        print("1. Submitting evaluation...")
        response = await client.post(
            f"{api_base}/eval",
            json={
                "code": "print('Redis cleanup test')",
                "language": "python"
            }
        )
        assert response.status_code == 200
        eval_id = response.json()["eval_id"]
        print(f"   Evaluation ID: {eval_id}")
        
        # 2. Wait for it to start running
        print("\n2. Waiting for evaluation to start...")
        start_time = time.time()
        is_running = False
        
        while time.time() - start_time < 10:
            # Check if in running set
            is_in_set = await redis_client.sismember("running_evaluations", eval_id)
            if is_in_set:
                print(f"   ✓ Found in running_evaluations set")
                is_running = True
                break
            await asyncio.sleep(0.5)
        
        assert is_running, "Evaluation never appeared in running set"
        
        # 3. Wait for completion
        print("\n3. Waiting for completion...")
        completed = False
        
        while time.time() - start_time < 30:
            response = await client.get(f"{api_base}/eval/{eval_id}")
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                print(f"   Status: {status}")
                
                if status in ["completed", "failed"]:
                    completed = True
                    break
            
            await asyncio.sleep(1)
        
        assert completed, "Evaluation did not complete in time"
        
        # 4. Check Redis cleanup
        print("\n4. Checking Redis cleanup...")
        
        # Give storage-worker time to process the event
        await asyncio.sleep(2)
        
        # Check if removed from running set
        is_in_set = await redis_client.sismember("running_evaluations", eval_id)
        running_info_exists = await redis_client.exists(f"eval:{eval_id}:running")
        
        print(f"   In running_evaluations set: {is_in_set}")
        print(f"   Running info exists: {bool(running_info_exists)}")
        
        # 5. Check what the running endpoint returns
        print("\n5. Checking running endpoint...")
        response = await client.get(f"{api_base}/evaluations?status=running")
        if response.status_code == 200:
            data = response.json()
            running_ids = [e["eval_id"] for e in data.get("evaluations", [])]
            print(f"   Running evaluations: {running_ids}")
            
            if eval_id in running_ids:
                print(f"   ❌ ERROR: Completed evaluation {eval_id} still in running list!")
                return False
            else:
                print(f"   ✓ Completed evaluation {eval_id} NOT in running list")
        
        # Summary
        print("\n=== SUMMARY ===")
        if is_in_set or running_info_exists:
            print("❌ FAILED: Redis cleanup did not happen properly")
            print(f"   - In running set: {is_in_set}")
            print(f"   - Running info exists: {running_info_exists}")
            return False
        else:
            print("✓ PASSED: Redis was cleaned up correctly")
            return True
    
    await redis_client.close()


async def monitor_redis_pubsub():
    """Monitor Redis pub/sub channels to see what events are published."""
    redis_client = await redis.from_url(REDIS_URL)
    pubsub = redis_client.pubsub()
    
    # Subscribe to all evaluation channels
    await pubsub.subscribe(
        "evaluation:queued",
        "evaluation:running", 
        "evaluation:completed",
        "evaluation:failed",
        "storage:evaluation:*"
    )
    
    print("Monitoring Redis pub/sub events...")
    print("Press Ctrl+C to stop\n")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"].decode()
                try:
                    data = json.loads(message["data"])
                    print(f"[{channel}] {data}")
                except:
                    print(f"[{channel}] {message['data']}")
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    
    await pubsub.unsubscribe()
    await redis_client.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Run pub/sub monitor
        asyncio.run(monitor_redis_pubsub())
    else:
        # Run cleanup test
        asyncio.run(test_redis_cleanup())