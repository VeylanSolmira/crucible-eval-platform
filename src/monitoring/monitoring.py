"""
Monitoring services for evaluation tracking.
These can evolve into full observability platforms.

NOTE: Currently monolithic by design. See docs/architecture/when-to-modularize.md

Future modularization structure:
- collectors/     # Metric collection (CPU, memory, GPU, custom)
- exporters/      # Export to monitoring systems (Prometheus, CloudWatch)
- aggregators/    # Metric aggregation and processing
- storage/        # Time-series data storage

TODO: Consider modularizing when:
- Adding Prometheus/Grafana integration
- Need specialized metric collectors
- Supporting multiple export formats
"""

import threading
import queue
from datetime import datetime, timezone
from typing import Dict, List, Any
from queue import Queue
import unittest

from ..shared.base import TestableComponent


class MonitoringService(TestableComponent):
    """
    Abstract monitoring service that must be testable.
    
    Future evolution:
    - OpenTelemetry integration
    - Distributed tracing
    - Metrics aggregation
    - Anomaly detection
    - Real-time streaming
    """
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        """Emit an event for an evaluation"""
        raise NotImplementedError
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        """Retrieve events for an evaluation"""
        raise NotImplementedError
    
    def self_test(self) -> Dict[str, Any]:
        """Test monitoring capabilities"""
        test_id = "test-monitor"
        tests_passed = []
        tests_failed = []
        
        # Test event emission and retrieval
        try:
            self.emit_event(test_id, "test", "message1")
            self.emit_event(test_id, "test", "message2")
            events = self.get_events(test_id)
            
            if len(events) == 2:
                tests_passed.append("Event storage")
            else:
                tests_failed.append(f"Event storage: expected 2, got {len(events)}")
                
            if events[0]['message'] == 'message1':
                tests_passed.append("Event ordering")
            else:
                tests_failed.append("Event ordering: wrong order")
                
        except Exception as e:
            tests_failed.append(f"Monitoring test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }


class InMemoryMonitor(MonitoringService):
    """
    Simple in-memory event store.
    
    Future evolution:
    - Redis backend
    - PostgreSQL with TimescaleDB
    - Kafka streaming
    - S3 archival
    """
    
    def __init__(self):
        self.events = {}
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        if eval_id not in self.events:
            self.events[eval_id] = []
        self.events[eval_id].append({
            'type': event_type,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        return self.events.get(eval_id, [])[start_idx:]
    
    def get_test_suite(self) -> unittest.TestSuite:
        class MonitorTests(unittest.TestCase):
            def setUp(self):
                self.monitor = InMemoryMonitor()
            
            def test_event_persistence(self):
                self.monitor.emit_event("test-1", "info", "test message")
                events = self.monitor.get_events("test-1")
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]['message'], "test message")
            
            def test_multiple_evaluations(self):
                self.monitor.emit_event("eval-1", "start", "Starting eval 1")
                self.monitor.emit_event("eval-2", "start", "Starting eval 2")
                self.monitor.emit_event("eval-1", "end", "Ending eval 1")
                
                eval1_events = self.monitor.get_events("eval-1")
                eval2_events = self.monitor.get_events("eval-2")
                
                self.assertEqual(len(eval1_events), 2)
                self.assertEqual(len(eval2_events), 1)
            
            def test_event_ordering(self):
                for i in range(5):
                    self.monitor.emit_event("test", "info", f"Message {i}")
                
                events = self.monitor.get_events("test")
                for i, event in enumerate(events):
                    self.assertEqual(event['message'], f"Message {i}")
        
        return unittest.TestLoader().loadTestsFromTestCase(MonitorTests)


class AdvancedMonitor(MonitoringService):
    """
    Advanced monitoring with real-time event streaming via subscribers.
    
    Features:
    - Thread-safe event storage
    - Real-time event streaming to subscribers
    - Queue-based subscription pattern
    
    Future evolution:
    - WebSocket streaming
    - Server-Sent Events (SSE)
    - gRPC streaming
    - Apache Kafka integration
    """
    
    def __init__(self):
        self.events = {}  # eval_id -> list of events
        self.subscribers = {}  # eval_id -> list of queues
        self.lock = threading.Lock()
    
    def subscribe(self, eval_id: str) -> Queue:
        """Subscribe to real-time events for an evaluation"""
        subscriber_queue = queue.Queue()
        
        with self.lock:
            if eval_id not in self.subscribers:
                self.subscribers[eval_id] = []
            self.subscribers[eval_id].append(subscriber_queue)
            
            # Send existing events to new subscriber
            existing_events = self.events.get(eval_id, [])
            for event in existing_events:
                subscriber_queue.put(event)
        
        return subscriber_queue
    
    def unsubscribe(self, eval_id: str, subscriber_queue: Queue) -> None:
        """Unsubscribe from events"""
        with self.lock:
            if eval_id in self.subscribers:
                try:
                    self.subscribers[eval_id].remove(subscriber_queue)
                    if not self.subscribers[eval_id]:
                        del self.subscribers[eval_id]
                except ValueError:
                    pass  # Queue not in list
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        """Emit an event and notify all subscribers"""
        timestamp = datetime.now(timezone.utc).isoformat()
        event = {
            'timestamp': timestamp,
            'type': event_type,
            'message': message,
            'eval_id': eval_id
        }
        
        with self.lock:
            # Store event
            if eval_id not in self.events:
                self.events[eval_id] = []
            self.events[eval_id].append(event)
            
            # Notify subscribers
            if eval_id in self.subscribers:
                dead_queues = []
                for subscriber_queue in self.subscribers[eval_id]:
                    try:
                        subscriber_queue.put_nowait(event)
                    except queue.Full:
                        # Queue is full, mark for removal
                        dead_queues.append(subscriber_queue)
                
                # Remove dead queues
                for dead_queue in dead_queues:
                    self.subscribers[eval_id].remove(dead_queue)
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        """Get stored events for an evaluation"""
        with self.lock:
            if eval_id not in self.events:
                return []
            return self.events[eval_id][start_idx:]
    
    def get_all_evaluations(self) -> List[str]:
        """Get list of all evaluation IDs"""
        with self.lock:
            return list(self.events.keys())
    
    def clear_evaluation(self, eval_id: str) -> None:
        """Clear events and subscribers for an evaluation"""
        with self.lock:
            if eval_id in self.events:
                del self.events[eval_id]
            if eval_id in self.subscribers:
                # Notify subscribers that stream is ending
                for subscriber_queue in self.subscribers[eval_id]:
                    try:
                        subscriber_queue.put_nowait({'type': 'stream_end', 'eval_id': eval_id})
                    except queue.Full:
                        pass
                del self.subscribers[eval_id]
    
    def self_test(self) -> Dict[str, Any]:
        """Test advanced monitoring functionality"""
        tests_passed = []
        tests_failed = []
        
        # Run base tests first
        base_result = super().self_test()
        if base_result['passed']:
            tests_passed.extend(base_result.get('tests_passed', ['Base monitoring']))
        else:
            tests_failed.extend(base_result.get('tests_failed', ['Base monitoring failed']))
        
        # Test subscription
        try:
            test_id = "test-subscribe"
            subscriber = self.subscribe(test_id)
            
            # Emit event
            self.emit_event(test_id, "test", "subscription test")
            
            # Check subscriber received it
            try:
                event = subscriber.get(timeout=1)
                if event['message'] == 'subscription test':
                    tests_passed.append("Subscription delivery")
                else:
                    tests_failed.append("Subscription delivery: wrong message")
            except queue.Empty:
                tests_failed.append("Subscription delivery: no event received")
                
            self.unsubscribe(test_id, subscriber)
            
        except Exception as e:
            tests_failed.append(f"Subscription test: {str(e)}")
        
        # Test multiple subscribers
        try:
            test_id = "test-multi-sub"
            subs = [self.subscribe(test_id) for _ in range(3)]
            
            self.emit_event(test_id, "broadcast", "test broadcast")
            
            received_count = 0
            for sub in subs:
                try:
                    event = sub.get(timeout=0.5)
                    if event['message'] == 'test broadcast':
                        received_count += 1
                except queue.Empty:
                    pass
            
            if received_count == 3:
                tests_passed.append("Multi-subscriber broadcast")
            else:
                tests_failed.append(f"Multi-subscriber broadcast: {received_count}/3 received")
            
            # Cleanup
            for sub in subs:
                self.unsubscribe(test_id, sub)
                
        except Exception as e:
            tests_failed.append(f"Multi-subscriber test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        monitor = self
        
        class AdvancedMonitorTests(unittest.TestCase):
            def setUp(self):
                self.monitor = monitor
            
            def test_subscription_receives_events(self):
                """Test that subscribers receive events"""
                eval_id = "test-sub-1"
                subscriber = self.monitor.subscribe(eval_id)
                
                try:
                    self.monitor.emit_event(eval_id, "info", "Test message")
                    
                    event = subscriber.get(timeout=1)
                    self.assertEqual(event['message'], "Test message")
                    self.assertEqual(event['type'], "info")
                finally:
                    self.monitor.unsubscribe(eval_id, subscriber)
            
            def test_existing_events_on_subscribe(self):
                """Test that new subscribers receive existing events"""
                eval_id = "test-sub-2"
                
                # Emit events before subscription
                self.monitor.emit_event(eval_id, "info", "Event 1")
                self.monitor.emit_event(eval_id, "info", "Event 2")
                
                # Subscribe
                subscriber = self.monitor.subscribe(eval_id)
                
                try:
                    # Should receive existing events
                    event1 = subscriber.get(timeout=1)
                    event2 = subscriber.get(timeout=1)
                    
                    self.assertEqual(event1['message'], "Event 1")
                    self.assertEqual(event2['message'], "Event 2")
                finally:
                    self.monitor.unsubscribe(eval_id, subscriber)
            
            def test_thread_safety(self):
                """Test concurrent access to monitoring"""
                eval_id = "test-concurrent"
                subscriber = self.monitor.subscribe(eval_id)
                
                try:
                    def emit_events(thread_id):
                        for i in range(10):
                            self.monitor.emit_event(eval_id, "info", f"Thread {thread_id} Event {i}")
                    
                    # Start multiple threads
                    threads = []
                    for i in range(5):
                        t = threading.Thread(target=emit_events, args=(i,))
                        threads.append(t)
                        t.start()
                    
                    # Wait for completion
                    for t in threads:
                        t.join()
                    
                    # Check we received all events
                    received_count = 0
                    while True:
                        try:
                            subscriber.get(timeout=0.1)
                            received_count += 1
                        except queue.Empty:
                            break
                    
                    self.assertEqual(received_count, 50)  # 5 threads * 10 events
                    
                finally:
                    self.monitor.unsubscribe(eval_id, subscriber)
        
        return unittest.TestLoader().loadTestsFromTestCase(AdvancedMonitorTests)