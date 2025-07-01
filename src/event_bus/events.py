"""
Event Bus Component for Loose Coupling

This implements a simple pub/sub system that allows components to communicate
without knowing about each other. This is a foundational pattern for building
scalable, maintainable systems.
"""

from typing import Dict, Any, Callable, List
from collections import defaultdict
import asyncio
import threading
# Import from shared base module
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from shared.base import TestableComponent


class EventBus(TestableComponent):
    """
    Simple event bus for decoupling components.
    
    Features:
    - Synchronous and asynchronous event handling
    - Type-safe event registration
    - Thread-safe operation
    - Easy migration path to external message brokers
    """
    
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.async_subscribers = defaultdict(list)
        self.lock = threading.Lock()
        self.event_history = []  # For debugging/testing
        self.max_history = 1000
    
    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to an event type with a callback.
        
        Args:
            event_type: The event type to subscribe to (e.g., "evaluation.completed")
            callback: Function to call when event is published
        """
        with self.lock:
            self.subscribers[event_type].append(callback)
    
    def subscribe_async(self, event_type: str, callback: Callable[[Dict[str, Any]], Any]) -> None:
        """Subscribe with an async callback"""
        with self.lock:
            self.async_subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from an event"""
        with self.lock:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
            if callback in self.async_subscribers[event_type]:
                self.async_subscribers[event_type].remove(callback)
    
    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: The event type (e.g., "evaluation.completed")
            data: Event data/payload
        """
        # Add metadata
        event = {
            "type": event_type,
            "data": data,
            "timestamp": self._get_timestamp()
        }
        
        # Store in history
        with self.lock:
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
        
        # Get subscribers snapshot to avoid holding lock during callbacks
        with self.lock:
            sync_callbacks = self.subscribers[event_type].copy()
            async_callbacks = self.async_subscribers[event_type].copy()
        
        # Call synchronous subscribers
        for callback in sync_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event handler for {event_type}: {e}")
        
        # Handle async subscribers if any
        if async_callbacks:
            asyncio.create_task(self._publish_async(event_type, event, async_callbacks))
    
    async def _publish_async(self, event_type: str, event: Dict[str, Any], callbacks: List[Callable]) -> None:
        """Handle async subscribers"""
        for callback in callbacks:
            try:
                await callback(event)
            except Exception as e:
                print(f"Error in async event handler for {event_type}: {e}")
    
    def publish_async(self, event_type: str, data: Dict[str, Any]) -> asyncio.Task:
        """Async version of publish"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": self._get_timestamp()
        }
        
        # Store in history
        with self.lock:
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
        
        return asyncio.create_task(self._publish_to_all_async(event_type, event))
    
    async def _publish_to_all_async(self, event_type: str, event: Dict[str, Any]) -> None:
        """Publish to all subscribers asynchronously"""
        with self.lock:
            sync_callbacks = self.subscribers[event_type].copy()
            async_callbacks = self.async_subscribers[event_type].copy()
        
        # Call sync subscribers in thread pool
        loop = asyncio.get_event_loop()
        for callback in sync_callbacks:
            await loop.run_in_executor(None, callback, event)
        
        # Call async subscribers
        await self._publish_async(event_type, event, async_callbacks)
    
    def get_history(self, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get event history for debugging"""
        with self.lock:
            if event_type:
                filtered = [e for e in self.event_history if e["type"] == event_type]
                return filtered[-limit:]
            return self.event_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history"""
        with self.lock:
            self.event_history.clear()
    
    def _get_timestamp(self) -> float:
        """Get current timestamp"""
        import time
        return time.time()
    
    def self_test(self) -> Dict[str, Any]:
        """Test event bus functionality"""
        tests_passed = 0
        tests_total = 0
        
        # Test 1: Basic pub/sub
        tests_total += 1
        received_events = []
        
        def test_handler(event):
            received_events.append(event)
        
        self.subscribe("test.event", test_handler)
        self.publish("test.event", {"message": "test"})
        
        if len(received_events) == 1 and received_events[0]["data"]["message"] == "test":
            tests_passed += 1
        
        # Test 2: Multiple subscribers
        tests_total += 1
        counter = {"count": 0}
        
        def increment_handler(event):
            counter["count"] += 1
        
        self.subscribe("test.multi", increment_handler)
        self.subscribe("test.multi", increment_handler)
        self.publish("test.multi", {})
        
        if counter["count"] == 2:
            tests_passed += 1
        
        # Test 3: Unsubscribe
        tests_total += 1
        self.unsubscribe("test.event", test_handler)
        received_events.clear()
        self.publish("test.event", {"message": "should not receive"})
        
        if len(received_events) == 0:
            tests_passed += 1
        
        # Test 4: Event history
        tests_total += 1
        self.clear_history()
        self.publish("test.history", {"id": 1})
        self.publish("test.history", {"id": 2})
        history = self.get_history("test.history")
        
        if len(history) == 2:
            tests_passed += 1
        
        # Clean up
        self.subscribers.clear()
        self.async_subscribers.clear()
        self.clear_history()
        
        return {
            'passed': tests_passed == tests_total,
            'message': f"Event bus tests: {tests_passed}/{tests_total} passed"
        }
    
    def get_test_suite(self):
        """Get unittest suite for EventBus"""
        import unittest
        
        class EventBusTests(unittest.TestCase):
            def setUp(self):
                self.event_bus = EventBus()
                
            def tearDown(self):
                self.event_bus.subscribers.clear()
                self.event_bus.async_subscribers.clear()
                self.event_bus.clear_history()
            
            def test_publish_subscribe(self):
                """Test basic pub/sub"""
                received = []
                self.event_bus.subscribe("test", lambda e: received.append(e))
                self.event_bus.publish("test", {"data": "value"})
                
                self.assertEqual(len(received), 1)
                self.assertEqual(received[0]["data"]["data"], "value")
            
            def test_multiple_subscribers(self):
                """Test multiple subscribers get events"""
                count = [0]
                self.event_bus.subscribe("test", lambda e: count.__setitem__(0, count[0] + 1))
                self.event_bus.subscribe("test", lambda e: count.__setitem__(0, count[0] + 1))
                self.event_bus.publish("test", {})
                
                self.assertEqual(count[0], 2)
            
            def test_unsubscribe(self):
                """Test unsubscribe works"""
                received = []
                handler = lambda e: received.append(e)
                
                self.event_bus.subscribe("test", handler)
                self.event_bus.publish("test", {"first": True})
                self.assertEqual(len(received), 1)
                
                self.event_bus.unsubscribe("test", handler)
                self.event_bus.publish("test", {"second": True})
                self.assertEqual(len(received), 1)  # Still just 1
            
            def test_event_history(self):
                """Test event history tracking"""
                self.event_bus.publish("test1", {"id": 1})
                self.event_bus.publish("test2", {"id": 2})
                
                history = self.event_bus.get_history()
                self.assertEqual(len(history), 2)
                
                # Test filtering by type
                history_filtered = self.event_bus.get_history("test1")
                self.assertEqual(len(history_filtered), 1)
                self.assertEqual(history_filtered[0]["type"], "test1")
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(EventBusTests)
        return suite


# Predefined event types for type safety
class EventTypes:
    """Standard event types used across the platform"""
    
    # Evaluation lifecycle
    EVALUATION_QUEUED = "evaluation.queued"
    EVALUATION_STARTED = "evaluation.started"
    EVALUATION_PROGRESS = "evaluation.progress"
    EVALUATION_COMPLETED = "evaluation.completed"
    EVALUATION_FAILED = "evaluation.failed"
    
    # Platform events
    PLATFORM_READY = "platform.ready"
    PLATFORM_SHUTDOWN = "platform.shutdown"
    
    # Security events
    SECURITY_VIOLATION = "security.violation"
    RESOURCE_LIMIT_EXCEEDED = "resource.limit_exceeded"
    
    # Storage events
    STORAGE_SAVED = "storage.saved"
    STORAGE_RETRIEVED = "storage.retrieved"
    STORAGE_DELETED = "storage.deleted"
    
    # Queue events  
    QUEUE_TASK_ADDED = "queue.task_added"
    QUEUE_TASK_STARTED = "queue.task_started"
    QUEUE_TASK_COMPLETED = "queue.task_completed"
    QUEUE_WORKER_STARTED = "queue.worker_started"
    QUEUE_WORKER_STOPPED = "queue.worker_stopped"


# Example usage patterns
"""
# 1. Basic usage
event_bus = EventBus()

# Storage subscribes to evaluation events
def store_on_complete(event):
    if event["type"] == EventTypes.EVALUATION_COMPLETED:
        eval_id = event["data"]["eval_id"]
        result = event["data"]["result"]
        storage.store(eval_id, result)

event_bus.subscribe(EventTypes.EVALUATION_COMPLETED, store_on_complete)

# Platform publishes events
event_bus.publish(EventTypes.EVALUATION_COMPLETED, {
    "eval_id": "123",
    "result": {"output": "..."}
})

# 2. Async usage
async def async_handler(event):
    await send_notification(event["data"])

event_bus.subscribe_async(EventTypes.SECURITY_VIOLATION, async_handler)

# 3. Debugging
history = event_bus.get_history(EventTypes.EVALUATION_FAILED, limit=10)
for event in history:
    print(f"Failed at {event['timestamp']}: {event['data']}")
"""