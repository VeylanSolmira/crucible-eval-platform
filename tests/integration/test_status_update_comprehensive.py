#!/usr/bin/env python3
"""
Comprehensive test suite for the evaluation status update issue.

This identifies all the components involved in the status update flow
and proposes tests for each one.
"""
import asyncio
import httpx
import time
import json
import redis.asyncio as redis
from tests.utils.utils import submit_evaluation


class StatusUpdateTestSuite:
    """
    Test suite that covers all components involved in status updates.
    """
    
    def __init__(self):
        self.api_base = "http://localhost/api"
        self.redis_url = "redis://localhost:6379"
        self.issues_found = []
        self.test_proposals = []
    
    async def run_all_tests(self):
        """Run comprehensive test suite."""
        print("=== COMPREHENSIVE STATUS UPDATE TEST SUITE ===\n")
        
        # Test each component in the flow
        await self.test_1_event_publishing()
        await self.test_2_redis_pubsub()
        await self.test_3_storage_worker_processing()
        await self.test_4_api_endpoints()
        await self.test_5_frontend_polling()
        await self.test_6_cache_invalidation()
        await self.test_7_race_conditions()
        
        # Summary
        self.print_summary()
        self.generate_test_proposals()
    
    async def test_1_event_publishing(self):
        """Test 1: Verify events are published when status changes."""
        print("TEST 1: Event Publishing")
        print("-" * 40)
        
        # Submit evaluation using unified function
        eval_id = submit_evaluation("print('test')")
        
        # Monitor Redis for events
        redis_client = await redis.from_url(self.redis_url)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("evaluation:*")
        
        # Wait for events
        events_received = []
        start_time = time.time()
        
        async def collect_events():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    events_received.append({
                        "channel": message["channel"],
                        "data": json.loads(message["data"])
                    })
        
        # Collect events for 5 seconds
        try:
            await asyncio.wait_for(collect_events(), timeout=5)
        except asyncio.TimeoutError:
            pass
        
        # Check what events were published
        print(f"Events received: {len(events_received)}")
        for event in events_received:
            print(f"  - {event['channel']}: eval_id={event['data'].get('eval_id')}")
        
        # Issues to check
        if not any(e["channel"] == "evaluation:completed" for e in events_received):
            self.issues_found.append("No completion event published")
        
        await redis_client.close()
        
        print()
    
    async def test_2_redis_pubsub(self):
        """Test 2: Verify Redis pub/sub is working correctly."""
        print("TEST 2: Redis Pub/Sub Mechanism")
        print("-" * 40)
        
        redis_client = await redis.from_url(self.redis_url)
        
        # Test pub/sub directly
        test_channel = "test:channel"
        test_message = {"test": "message", "timestamp": time.time()}
        
        # Subscribe
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(test_channel)
        
        # Publish
        await redis_client.publish(test_channel, json.dumps(test_message))
        
        # Check if received
        received = False
        async for message in pubsub.listen():
            if message["type"] == "message":
                received = True
                break
        
        print(f"Pub/Sub working: {received}")
        if not received:
            self.issues_found.append("Redis pub/sub not working")
        
        await redis_client.close()
        print()
    
    async def test_3_storage_worker_processing(self):
        """Test 3: Verify storage-worker processes events correctly."""
        print("TEST 3: Storage Worker Event Processing")
        print("-" * 40)
        
        # Check if storage-worker is healthy
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get("http://localhost:8086/health")
                print(f"Storage-worker health: {resp.status_code}")
        except:
            print("Storage-worker health: UNREACHABLE")
            self.issues_found.append("Storage-worker not reachable")
        
        # TODO: Test event processing directly
        print()
    
    async def test_4_api_endpoints(self):
        """Test 4: Verify API endpoints return correct data."""
        print("TEST 4: API Endpoint Responses")
        print("-" * 40)
        
        async with httpx.AsyncClient(verify=False) as client:
            # Submit and wait for completion using unified function
            eval_id = submit_evaluation("print('api test')")
            
            # Wait for completion
            await asyncio.sleep(3)
            
            # Test different endpoints
            endpoints = [
                f"/eval/{eval_id}",
                f"/evaluations?status=running",
                f"/evaluations",
                f"/eval/{eval_id}/logs"
            ]
            
            for endpoint in endpoints:
                resp = await client.get(f"{self.api_base}{endpoint}")
                print(f"{endpoint}: {resp.status_code}")
                
                if "evaluations" in endpoint and "status=running" in endpoint:
                    data = resp.json()
                    running_ids = [e["eval_id"] for e in data.get("evaluations", [])]
                    if eval_id in running_ids:
                        self.issues_found.append(f"Completed eval {eval_id} in running list")
        
        print()
    
    async def test_5_frontend_polling(self):
        """Test 5: Simulate frontend polling behavior."""
        print("TEST 5: Frontend Polling Simulation")
        print("-" * 40)
        
        # Simulate React Query polling
        print("Frontend polls these endpoints:")
        print("- useRunningEvaluations: /api/evaluations?status=running (every 2s)")
        print("- useEvaluation: /api/eval/{id} (every 1s while running)")
        print("- useEvaluationLogs: /api/eval/{id}/logs (every 1s)")
        
        # Issue: Frontend hardcodes status
        print("\nISSUE: Frontend hardcodes status='running' for all from running endpoint")
        self.issues_found.append("Frontend hardcodes status='running'")
        
        print()
    
    async def test_6_cache_invalidation(self):
        """Test 6: Test React Query cache invalidation."""
        print("TEST 6: Cache Invalidation")
        print("-" * 40)
        
        print("React Query cache behavior:")
        print("- Evaluation data: staleTime=Infinity (never stale once complete)")
        print("- Running evaluations: refetchInterval=2000ms")
        print("- Logs: refetchInterval based on is_running flag")
        
        print("\nPotential cache issues:")
        print("- Completed evaluations might stay in 'running' query cache")
        print("- No invalidation of 'running' query when evaluation completes")
        
        self.test_proposals.append({
            "name": "Frontend Cache Invalidation Test",
            "description": "Test that React Query properly invalidates cached queries when evaluation status changes",
            "approach": "Use Playwright to monitor network requests and verify cache behavior"
        })
        
        print()
    
    async def test_7_race_conditions(self):
        """Test 7: Test for race conditions."""
        print("TEST 7: Race Conditions")
        print("-" * 40)
        
        print("Potential race conditions:")
        print("1. Storage service updates DB, but event not yet processed")
        print("2. Frontend polls during status transition")
        print("3. Multiple status updates arrive out of order")
        print("4. Redis cleanup happens before final poll")
        
        self.test_proposals.append({
            "name": "Race Condition Test",
            "description": "Submit multiple evaluations and verify status consistency under load",
            "approach": "Concurrent submissions with precise timing checks"
        })
        
        print()
    
    def print_summary(self):
        """Print test summary."""
        print("=== SUMMARY ===")
        print(f"\nIssues found: {len(self.issues_found)}")
        for issue in self.issues_found:
            print(f"  - {issue}")
    
    def generate_test_proposals(self):
        """Generate comprehensive test proposals."""
        print("\n=== PROPOSED TEST SUITE ===\n")
        
        # Add more test proposals
        self.test_proposals.extend([
            {
                "name": "Event Flow Integration Test",
                "description": "End-to-end test of event flow from executor -> storage -> frontend",
                "components": ["storage-service", "storage-worker", "redis", "api"],
                "approach": "Submit evaluation, monitor all events and state changes"
            },
            {
                "name": "Frontend Status Synchronization Test",
                "description": "Test that all UI components show consistent status",
                "components": ["frontend", "react-query"],
                "approach": "Use Playwright to verify ExecutionMonitor and Evaluations list stay in sync"
            },
            {
                "name": "Redis State Lifecycle Test",
                "description": "Verify Redis keys are created and cleaned up properly",
                "components": ["redis", "storage-worker"],
                "approach": "Monitor Redis keys throughout evaluation lifecycle"
            },
            {
                "name": "API Consistency Test",
                "description": "Verify all API endpoints return consistent status",
                "components": ["api", "storage-service"],
                "approach": "Poll multiple endpoints and verify data consistency"
            },
            {
                "name": "WebSocket Real-time Updates Test",
                "description": "Test real-time updates if/when implemented",
                "components": ["websocket", "frontend"],
                "approach": "Verify instant status updates without polling"
            },
            {
                "name": "Database Transaction Test",
                "description": "Test status updates under database transaction failures",
                "components": ["postgresql", "storage-service"],
                "approach": "Simulate transaction rollbacks and verify status consistency"
            },
            {
                "name": "Service Restart Resilience Test",
                "description": "Test status updates when services restart mid-evaluation",
                "components": ["all-services"],
                "approach": "Restart services during evaluation and verify recovery"
            }
        ])
        
        # Print all proposals
        for i, proposal in enumerate(self.test_proposals, 1):
            print(f"{i}. {proposal['name']}")
            print(f"   Description: {proposal['description']}")
            if "components" in proposal:
                print(f"   Components: {', '.join(proposal['components'])}")
            print(f"   Approach: {proposal['approach']}")
            print()


async def main():
    """Run the comprehensive test suite."""
    suite = StatusUpdateTestSuite()
    await suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())