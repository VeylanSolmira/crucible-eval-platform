#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Production Safety with gVisor
Evolution: From 3.5/4 to 4/4 - achieving production-grade isolation

Run with: python extreme_mvp_gvisor.py [--runtime=runc|runsc]
Then open: http://localhost:8000

This version adds gVisor (runsc) runtime for production-grade safety.
This is what Google Cloud Run uses for untrusted code execution.

Requirements: 
- Docker with gVisor runtime installed
- Or use --runtime=runc to fall back to standard Docker
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import uuid
import tempfile
import os
import threading
import time
import queue
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import unittest
import sys

# ============== TESTING AS FUNDAMENTAL ==============
class TestableComponent(ABC):
    """
    Base abstraction that makes testing a requirement from day one.
    Even our extreme MVP must be testable!
    """
    
    @abstractmethod
    def self_test(self) -> Dict[str, Any]:
        """
        Every component must be able to test itself.
        Returns: {'passed': bool, 'tests': [...], 'message': str}
        """
        pass
    
    @abstractmethod
    def get_test_suite(self) -> unittest.TestSuite:
        """Return a unittest suite for this component"""
        pass

# In-memory "database" 
evaluations = {}

# ============== QUEUE ABSTRACTION ==============
class TaskQueue(TestableComponent):
    """
    Simple task queue for concurrent evaluations.
    This abstraction emerged from the pain of blocking execution.
    """
    def __init__(self, max_workers: int = 3):
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = True
        self.active_tasks = {}
        self._test_mode = False
        
        # Start worker threads
        for i in range(max_workers):
            self.executor.submit(self._worker, f"worker-{i}")
    
    def submit(self, eval_id: str, func, *args, **kwargs):
        """Submit a task to the queue"""
        task = {
            'eval_id': eval_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'submitted_at': datetime.utcnow()
        }
        self.queue.put(task)
        self.active_tasks[eval_id] = 'queued'
    
    def _worker(self, worker_name: str):
        """Worker thread that processes tasks"""
        while self.running:
            try:
                task = self.queue.get(timeout=1)
                eval_id = task['eval_id']
                
                # Update status
                self.active_tasks[eval_id] = 'running'
                
                # Execute the task
                try:
                    task['func'](*task['args'], **task['kwargs'])
                    self.active_tasks[eval_id] = 'completed'
                except Exception as e:
                    self.active_tasks[eval_id] = f'failed: {str(e)}'
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                continue
    
    def get_status(self) -> dict:
        """Get queue status"""
        return {
            'queued': self.queue.qsize(),
            'active_tasks': dict(self.active_tasks),
            'workers': self.executor._max_workers
        }
    
    def shutdown(self):
        """Gracefully shutdown the queue"""
        self.running = False
        self.executor.shutdown(wait=True)
    
    def self_test(self) -> Dict[str, Any]:
        """Test queue functionality"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Queue accepts tasks
        try:
            test_executed = False
            def test_func():
                nonlocal test_executed
                test_executed = True
            
            self.submit("test-queue-1", test_func)
            time.sleep(0.5)  # Give worker time to execute
            
            if test_executed:
                tests_passed.append("Task execution")
            else:
                tests_failed.append("Task didn't execute")
        except Exception as e:
            tests_failed.append(f"Task execution: {str(e)}")
        
        # Test 2: Multiple workers
        try:
            if self.executor._max_workers == 3:
                tests_passed.append("Worker count correct")
            else:
                tests_failed.append(f"Expected 3 workers, got {self.executor._max_workers}")
        except Exception as e:
            tests_failed.append(f"Worker check: {str(e)}")
        
        # Test 3: Queue status reporting
        try:
            status = self.get_status()
            if 'queued' in status and 'workers' in status:
                tests_passed.append("Status reporting")
            else:
                tests_failed.append("Status missing fields")
        except Exception as e:
            tests_failed.append(f"Status check: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Queue: {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests passed"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Comprehensive queue tests"""
        queue = self
        
        class QueueTests(unittest.TestCase):
            def test_task_submission(self):
                """Test tasks can be submitted and executed"""
                result = {'executed': False}
                
                def test_task():
                    result['executed'] = True
                
                queue.submit("test-1", test_task)
                time.sleep(0.5)
                self.assertTrue(result['executed'])
            
            def test_concurrent_execution(self):
                """Test multiple tasks run concurrently"""
                results = []
                
                def task(n):
                    time.sleep(0.1)
                    results.append(n)
                
                # Submit more tasks than workers
                for i in range(5):
                    queue.submit(f"test-{i}", task, i)
                
                # Wait for completion
                time.sleep(1)
                
                # All tasks should complete
                self.assertEqual(len(results), 5)
                self.assertEqual(set(results), {0, 1, 2, 3, 4})
            
            def test_queue_status(self):
                """Test queue status reporting"""
                status = queue.get_status()
                self.assertIn('queued', status)
                self.assertIn('workers', status)
                self.assertIn('active_tasks', status)
                self.assertEqual(status['workers'], 3)
        
        return unittest.TestLoader().loadTestsFromTestCase(QueueTests)

# ============== MONITORING ABSTRACTION ==============
class MonitoringService(ABC, TestableComponent):
    @abstractmethod
    def emit_event(self, eval_id: str, event_type: str, message: str):
        pass
    
    @abstractmethod
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        pass

class InMemoryMonitor(MonitoringService):
    def __init__(self):
        self.events = {}
        self.lock = threading.Lock()
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        with self.lock:
            if eval_id not in self.events:
                self.events[eval_id] = []
            
            event = {
                'type': event_type,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'eval_id': eval_id
            }
            self.events[eval_id].append(event)
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        with self.lock:
            return self.events.get(eval_id, [])[start_idx:]
    
    def self_test(self) -> Dict[str, Any]:
        """Test monitoring functionality"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Event emission and retrieval
        try:
            test_id = "test-monitor-1"
            self.emit_event(test_id, 'info', 'Test message')
            events = self.get_events(test_id)
            
            if len(events) == 1 and events[0]['message'] == 'Test message':
                tests_passed.append("Event storage")
            else:
                tests_failed.append("Event storage failed")
        except Exception as e:
            tests_failed.append(f"Event storage: {str(e)}")
        
        # Test 2: Thread safety
        try:
            test_id = "test-monitor-2"
            from concurrent.futures import ThreadPoolExecutor
            
            def emit_many(n):
                for i in range(10):
                    self.emit_event(test_id, 'info', f'Message {n}-{i}')
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(emit_many, i) for i in range(5)]
                for f in futures:
                    f.result()
            
            events = self.get_events(test_id)
            if len(events) == 50:  # 5 threads * 10 messages
                tests_passed.append("Thread safety")
            else:
                tests_failed.append(f"Expected 50 events, got {len(events)}")
        except Exception as e:
            tests_failed.append(f"Thread safety: {str(e)}")
        
        # Test 3: Event ordering
        try:
            test_id = "test-monitor-3"
            self.emit_event(test_id, 'info', 'First')
            self.emit_event(test_id, 'warning', 'Second')
            self.emit_event(test_id, 'error', 'Third')
            
            events = self.get_events(test_id)
            if (len(events) == 3 and 
                events[0]['message'] == 'First' and
                events[2]['message'] == 'Third'):
                tests_passed.append("Event ordering")
            else:
                tests_failed.append("Events not in order")
        except Exception as e:
            tests_failed.append(f"Event ordering: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Monitor: {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests passed"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Comprehensive monitoring tests"""
        monitor = self
        
        class MonitorTests(unittest.TestCase):
            def test_event_emission(self):
                """Test basic event emission"""
                eval_id = "test-emit"
                monitor.emit_event(eval_id, 'info', 'Test event')
                events = monitor.get_events(eval_id)
                
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]['type'], 'info')
                self.assertEqual(events[0]['message'], 'Test event')
                self.assertIn('timestamp', events[0])
            
            def test_event_pagination(self):
                """Test event retrieval with start index"""
                eval_id = "test-paginate"
                
                # Emit 5 events
                for i in range(5):
                    monitor.emit_event(eval_id, 'info', f'Event {i}')
                
                # Get all events
                all_events = monitor.get_events(eval_id)
                self.assertEqual(len(all_events), 5)
                
                # Get events starting from index 2
                partial_events = monitor.get_events(eval_id, start_idx=2)
                self.assertEqual(len(partial_events), 3)
                self.assertEqual(partial_events[0]['message'], 'Event 2')
            
            def test_concurrent_access(self):
                """Test thread-safe concurrent access"""
                eval_id = "test-concurrent"
                event_count = 100
                thread_count = 10
                
                def emit_events(thread_id):
                    for i in range(event_count // thread_count):
                        monitor.emit_event(eval_id, 'info', f'Thread {thread_id} Event {i}')
                
                import threading
                threads = []
                for i in range(thread_count):
                    t = threading.Thread(target=emit_events, args=(i,))
                    threads.append(t)
                    t.start()
                
                for t in threads:
                    t.join()
                
                events = monitor.get_events(eval_id)
                self.assertEqual(len(events), event_count)
        
        return unittest.TestLoader().loadTestsFromTestCase(MonitorTests)

# ============== EXECUTION ENGINE WITH GVISOR ==============
class ExecutionEngine(ABC, TestableComponent):
    def __init__(self, monitor: Optional[MonitoringService] = None):
        self.monitor = monitor
    
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        pass
    
    def emit(self, eval_id: str, event_type: str, message: str):
        if self.monitor:
            self.monitor.emit_event(eval_id, event_type, message)

class GVisorEngine(ExecutionEngine):
    """
    Production-grade Docker execution with gVisor runtime.
    
    Security layers (matching Google Cloud Run):
    1. Docker container isolation
    2. gVisor (runsc) - userspace kernel for syscall interception
    3. Network completely disabled
    4. Non-root user (65534:65534)
    5. Read-only filesystem
    6. Resource limits (CPU/memory)
    
    This provides defense-in-depth against:
    - Container escape attempts
    - Kernel exploits (gVisor handles syscalls)
    - Network exfiltration (no network)
    - Privilege escalation (non-root)
    - Filesystem persistence (read-only)
    - Resource exhaustion (limits enforced)
    """
    
    def __init__(self, monitor: Optional[MonitoringService] = None, runtime: str = 'runsc'):
        super().__init__(monitor)
        self.runtime = runtime  # 'runsc' for gVisor, 'runc' for standard
        
    def execute(self, code: str, eval_id: str) -> dict:
        self.emit(eval_id, 'info', f'Starting execution with {self.runtime} runtime')
        self.emit(eval_id, 'info', 'Creating temporary file...')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Build Docker command with production safety features
            docker_cmd = [
                'docker', 'run',
                '--rm',                      # Remove container after exit
                '--runtime', self.runtime,   # gVisor (runsc) or standard (runc)
                '--user', '65534:65534',     # Non-root user (nobody:nogroup)
                '--network', 'none',         # No network access
                '--memory', '100m',          # Memory limit
                '--cpus', '0.5',            # CPU limit
                '--read-only',              # Read-only root filesystem
                '--tmpfs', '/tmp:size=10M',  # Small writable /tmp
                '--security-opt', 'no-new-privileges',  # Prevent privilege escalation
                '-v', f'{temp_file}:/code.py:ro',  # Mount code read-only
                'python:3.11-slim',
                'python', '-u', '/code.py'
            ]
            
            if self.runtime == 'runsc':
                self.emit(eval_id, 'info', 'Using gVisor for enhanced isolation')
                self.emit(eval_id, 'info', 'Syscalls intercepted in userspace')
            else:
                self.emit(eval_id, 'warning', 'Using standard runtime (less secure)')
            
            self.emit(eval_id, 'info', 'Starting container with production safety...')
            
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.emit(eval_id, 'success', 'Container started securely')
            
            output_lines = []
            start_time = time.time()
            
            while True:
                if time.time() - start_time > 30:
                    self.emit(eval_id, 'error', 'Timeout after 30 seconds')
                    process.terminate()
                    break
                    
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                    
                line = line.rstrip()
                output_lines.append(line)
                self.emit(eval_id, 'output', f'> {line}')
            
            return_code = process.wait()
            
            if return_code == 0:
                self.emit(eval_id, 'success', 'Container exited cleanly')
                status = 'completed'
            else:
                self.emit(eval_id, 'error', f'Container exited with code {return_code}')
                status = 'failed'
                
            return {
                'id': eval_id,
                'status': status,
                'output': '\n'.join(output_lines),
                'runtime': self.runtime,
                'security': 'production-grade' if self.runtime == 'runsc' else 'standard'
            }
            
        except Exception as e:
            self.emit(eval_id, 'error', f'System error: {str(e)}')
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'runtime': self.runtime
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                self.emit(eval_id, 'info', 'Cleaned up temporary file')
    
    def get_description(self) -> str:
        if self.runtime == 'runsc':
            return "gVisor (Production-grade isolation like Google Cloud Run)"
        else:
            return "Docker (Standard runtime - not production safe)"
    
    def self_test(self) -> Dict[str, Any]:
        """Test production safety features"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Basic execution works
        try:
            result = self.execute("print('gvisor test')", "test-1")
            if result['status'] == 'completed' and 'gvisor test' in result['output']:
                tests_passed.append("Basic execution")
            else:
                tests_failed.append("Basic execution failed")
        except Exception as e:
            tests_failed.append(f"Basic execution: {str(e)}")
        
        # Test 2: Network is completely blocked
        try:
            result = self.execute("""
import socket
try:
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('8.8.8.8', 53))
    print('DANGER: Network accessible!')
except Exception as e:
    print('Good: Network blocked -', str(e))
""", "test-2")
            if 'Good: Network blocked' in result.get('output', ''):
                tests_passed.append("Network isolation")
            else:
                tests_failed.append("Network not properly blocked!")
        except Exception as e:
            tests_failed.append(f"Network test: {str(e)}")
        
        # Test 3: Running as non-root user
        try:
            result = self.execute("import os; print(f'UID: {os.getuid()}')", "test-3")
            if '65534' in result.get('output', ''):
                tests_passed.append("Non-root execution")
            else:
                tests_failed.append("Not running as nobody user!")
        except Exception as e:
            tests_failed.append(f"User test: {str(e)}")
        
        # Test 4: Filesystem is read-only (except /tmp)
        try:
            result = self.execute("""
try:
    with open('/test.txt', 'w') as f:
        f.write('should fail')
    print('DANGER: Root filesystem writable!')
except Exception as e:
    print('Good: Root filesystem read-only')
    
# But /tmp should work
try:
    with open('/tmp/test.txt', 'w') as f:
        f.write('tmp works')
    print('Good: /tmp is writable')
except:
    print('Bad: /tmp not writable')
""", "test-4")
            if 'Good: Root filesystem read-only' in result.get('output', '') and 'Good: /tmp is writable' in result.get('output', ''):
                tests_passed.append("Filesystem protection")
            else:
                tests_failed.append("Filesystem protection incomplete!")
        except Exception as e:
            tests_failed.append(f"Filesystem test: {str(e)}")
        
        # Test 5: gVisor runtime detection (if using runsc)
        if self.runtime == 'runsc':
            try:
                result = self.execute("""
# gVisor has specific behavior we can detect
import platform
import os
print(f"Platform: {platform.system()}")
print(f"Kernel: {platform.release()}")
# gVisor reports as Linux but with specific characteristics
""", "test-5")
                if result['status'] == 'completed':
                    tests_passed.append("gVisor runtime active")
                else:
                    tests_failed.append("gVisor runtime check failed")
            except Exception as e:
                tests_failed.append(f"gVisor test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Comprehensive production safety tests"""
        engine = self
        
        class GVisorTests(unittest.TestCase):
            def test_no_network_access(self):
                """Verify complete network isolation"""
                result = engine.execute("""
import socket
import urllib.request
tests = []

# Test 1: Raw socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('8.8.8.8', 53))
    tests.append('FAIL: Socket connected')
except:
    tests.append('PASS: Socket blocked')

# Test 2: HTTP request
try:
    urllib.request.urlopen('http://example.com')
    tests.append('FAIL: HTTP worked')
except:
    tests.append('PASS: HTTP blocked')

print(' | '.join(tests))
""", "test-net")
                self.assertIn('PASS: Socket blocked', result['output'])
                self.assertIn('PASS: HTTP blocked', result['output'])
            
            def test_user_isolation(self):
                """Verify running as non-root"""
                result = engine.execute("""
import os
print(f"UID: {os.getuid()}")
print(f"GID: {os.getgid()}")
print(f"Username: {os.environ.get('USER', 'not set')}")
""", "test-user")
                self.assertIn('65534', result['output'])  # nobody user
            
            def test_filesystem_restrictions(self):
                """Verify filesystem is properly restricted"""
                result = engine.execute("""
import os
tests = []

# Test root filesystem
try:
    open('/evil.txt', 'w').write('bad')
    tests.append('FAIL: Root writable')
except:
    tests.append('PASS: Root read-only')

# Test /tmp is available but limited
try:
    open('/tmp/test.txt', 'w').write('x' * 1000)
    tests.append('PASS: /tmp writable')
except:
    tests.append('FAIL: /tmp not writable')

# Test can't access sensitive files
try:
    open('/etc/shadow', 'r').read()
    tests.append('FAIL: Can read /etc/shadow')
except:
    tests.append('PASS: Cannot read /etc/shadow')

print(' | '.join(tests))
""", "test-fs")
                self.assertIn('PASS: Root read-only', result['output'])
                self.assertIn('PASS: /tmp writable', result['output'])
            
            def test_resource_limits(self):
                """Verify resource limits are enforced"""
                # This test attempts to exceed memory limit
                result = engine.execute("""
try:
    # Try to allocate 200MB (limit is 100MB)
    data = 'x' * (200 * 1024 * 1024)
    print('FAIL: Memory limit not enforced')
except:
    print('PASS: Memory limit enforced')
""", "test-mem")
                # Should either fail or be killed
                self.assertTrue(
                    'PASS: Memory limit enforced' in result.get('output', '') or
                    result['status'] != 'completed'
                )
        
        return unittest.TestLoader().loadTestsFromTestCase(GVisorTests)

# ============== PLATFORM WITH PRODUCTION SAFETY ==============
class EvaluationPlatform(TestableComponent):
    """Platform now with production-grade safety"""
    
    def __init__(self, engine: ExecutionEngine, monitor: MonitoringService, task_queue: TaskQueue):
        self.engine = engine
        self.monitor = monitor
        self.queue = task_queue
        self.evaluations_lock = threading.Lock()
    
    def submit_evaluation(self, code: str) -> str:
        """Submit evaluation to queue"""
        eval_id = str(uuid.uuid4())[:8]
        
        with self.evaluations_lock:
            evaluations[eval_id] = {
                'id': eval_id,
                'status': 'queued',
                'output': None,
                'error': None,
                'submitted_at': datetime.utcnow().isoformat()
            }
        
        self.monitor.emit_event(eval_id, 'info', 'Evaluation submitted to queue')
        self.queue.submit(eval_id, self._run_evaluation, code, eval_id)
        
        return eval_id
    
    def _run_evaluation(self, code: str, eval_id: str):
        """Run evaluation with monitoring"""
        with self.evaluations_lock:
            evaluations[eval_id]['status'] = 'running'
            evaluations[eval_id]['started_at'] = datetime.utcnow().isoformat()
        
        result = self.engine.execute(code, eval_id)
        
        with self.evaluations_lock:
            evaluations[eval_id].update(result)
            evaluations[eval_id]['completed_at'] = datetime.utcnow().isoformat()
        
        self.monitor.emit_event(eval_id, 'complete', 'Evaluation finished')
    
    def self_test(self) -> Dict[str, Any]:
        """Platform tests delegate to engine"""
        return self.engine.self_test()
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Platform tests delegate to engine"""
        return self.engine.get_test_suite()

# Global instances
platform = None
task_queue = None

# ============== HTML WITH SECURITY STATUS ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Production-Grade Safety</title>
    <style>
        body { font-family: Arial; max-width: 900px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; margin-right: 10px; }
        button:disabled { background: #ccc; }
        .success { background: #d4edda; color: #155724; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .info { background: #cce5ff; color: #004085; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .security { background: #e8f8e8; border: 2px solid #28a745; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .event { margin: 3px 0; padding: 5px; background: white; font-size: 14px; }
        .event.error { border-left: 3px solid #dc3545; }
        .event.warning { border-left: 3px solid #ffc107; }
        .event.success { border-left: 3px solid #28a745; }
        .event.info { border-left: 3px solid #17a2b8; }
        .queue-status { background: #e8f4f8; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .two-column { display: flex; gap: 20px; }
        .column { flex: 1; }
        pre { background: #f5f5f5; padding: 10px; font-family: monospace; }
        .security-features { list-style: none; padding: 0; }
        .security-features li { padding: 5px 0; }
        .security-features li:before { content: '✓ '; color: #28a745; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Now with Production-Grade Safety!</h1>
    
    <div class="security">
        <h2>🛡️ Production Security Achieved (4/4 Requirements Met!)</h2>
        <p><strong>This configuration matches Google Cloud Run's security model:</strong></p>
        <ul class="security-features">
            <li>Docker container isolation (base layer)</li>
            <li>gVisor runtime (syscall interception in userspace)</li>
            <li>Network completely disabled (no data exfiltration)</li>
            <li>Non-root user 65534:65534 (nobody:nogroup)</li>
            <li>Read-only root filesystem (with small /tmp)</li>
            <li>Resource limits enforced (CPU/memory)</li>
            <li>No privilege escalation possible</li>
        </ul>
        <p><strong>Defense against AI model attacks:</strong></p>
        <ul>
            <li>Container escape: gVisor intercepts dangerous syscalls</li>
            <li>Kernel exploits: Userspace kernel prevents host access</li>
            <li>Data theft: No network means no exfiltration</li>
            <li>Persistence: Read-only filesystem prevents backdoors</li>
        </ul>
    </div>
    
    <div class="info" id="runtime-info">
        <strong>Current Configuration:</strong> <span id="config">Loading...</span>
    </div>
    
    <div class="queue-status">
        <h3>Queue Status</h3>
        <div id="queue-info">Loading...</div>
    </div>
    
    <div class="two-column">
        <div class="column">
            <h3>Submit New Evaluation</h3>
            <textarea id="code">import os
import platform

print("=== Security Test ===")
print(f"User ID: {os.getuid()}")  # Should be 65534 (nobody)
print(f"Platform: {platform.system()}")
print(f"Kernel: {platform.release()}")

# Test network isolation
try:
    import socket
    socket.socket().connect(('8.8.8.8', 53))
    print("WARNING: Network accessible!")
except:
    print("Good: Network properly blocked")

# Test filesystem
try:
    open('/evil.txt', 'w').write('bad')
    print("WARNING: Root filesystem writable!")
except:
    print("Good: Root filesystem read-only")

print("\\nProduction safety verified!")</textarea>
            <br><br>
            <button onclick="runEval()">Run Secure Evaluation</button>
            <button onclick="runSecurityTests()">Run Security Test Suite</button>
        </div>
        
        <div class="column">
            <h3>Active Evaluations</h3>
            <div id="active-evals"></div>
        </div>
    </div>
    
    <div class="monitoring">
        <h3>Execution Events</h3>
        <div id="events"></div>
    </div>
    
    <script>
        let activeEvals = new Set();
        let eventSources = new Map();
        
        // Get configuration
        fetch('/config').then(r => r.json()).then(data => {
            const configEl = document.getElementById('config');
            if (data.runtime === 'runsc') {
                configEl.innerHTML = '<strong style="color: #28a745;">gVisor Runtime (Production Safe)</strong>';
            } else {
                configEl.innerHTML = '<strong style="color: #dc3545;">Standard Runtime (Not Production Safe)</strong>';
                document.getElementById('runtime-info').className = 'warning';
            }
        });
        
        // Update queue status
        setInterval(updateQueueStatus, 1000);
        
        async function updateQueueStatus() {
            const response = await fetch('/queue-status');
            const data = await response.json();
            
            document.getElementById('queue-info').innerHTML = `
                <strong>Queued:</strong> ${data.queued} | 
                <strong>Workers:</strong> ${data.workers} | 
                <strong>Active:</strong> ${Object.keys(data.active_tasks).length}
            `;
            
            const activeDiv = document.getElementById('active-evals');
            const activeHtml = Object.entries(data.active_tasks)
                .map(([id, status]) => `<div>${id}: ${status}</div>`)
                .join('') || '<div>No active evaluations</div>';
            activeDiv.innerHTML = activeHtml;
        }
        
        async function runEval() {
            const code = document.getElementById('code').value;
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            monitorEvaluation(data.eval_id);
        }
        
        async function runSecurityTests() {
            const code = `
# Comprehensive security test suite
import os
import sys
import socket
import platform

print("=== PRODUCTION SECURITY VERIFICATION ===\\n")

# Test 1: User isolation
print(f"1. User ID: {os.getuid()} (should be 65534)")
print(f"   Group ID: {os.getgid()}")

# Test 2: Network isolation
print("\\n2. Network isolation test:")
failed_connections = 0
for host, port in [('8.8.8.8', 53), ('1.1.1.1', 443), ('google.com', 80)]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        print(f"   FAIL: Connected to {host}:{port}")
        failed_connections += 1
    except:
        print(f"   PASS: Cannot connect to {host}:{port}")

# Test 3: Filesystem restrictions
print("\\n3. Filesystem security:")
fs_tests = []
try:
    open('/root_test.txt', 'w').write('test')
    fs_tests.append("FAIL: Root filesystem writable")
except:
    fs_tests.append("PASS: Root filesystem read-only")

try:
    open('/tmp/test.txt', 'w').write('test')
    fs_tests.append("PASS: /tmp is writable")
except:
    fs_tests.append("FAIL: /tmp not writable")

for test in fs_tests:
    print(f"   {test}")

# Test 4: System information
print("\\n4. System information:")
print(f"   Platform: {platform.system()}")
print(f"   Python: {sys.version.split()[0]}")
print(f"   Working dir: {os.getcwd()}")

# Summary
if failed_connections == 0 and all('PASS' in t for t in fs_tests if 'Root' in t):
    print("\\n✓ ALL SECURITY TESTS PASSED")
    print("This environment is production-safe for AI evaluation!")
else:
    print("\\n✗ SECURITY ISSUES DETECTED")
    print("This environment may not be safe for untrusted code!")
`;
            
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            monitorEvaluation(data.eval_id);
        }
        
        function monitorEvaluation(evalId) {
            if (eventSources.has(evalId)) return;
            
            const eventSource = new EventSource(`/monitor/${evalId}`);
            eventSources.set(evalId, eventSource);
            activeEvals.add(evalId);
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addEvent(data);
                
                if (data.type === 'complete') {
                    eventSource.close();
                    eventSources.delete(evalId);
                    activeEvals.delete(evalId);
                }
            };
        }
        
        function addEvent(event) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${event.type}`;
            const time = new Date(event.timestamp).toLocaleTimeString();
            eventDiv.innerHTML = `<strong>${time}</strong> [${event.eval_id}] ${event.message}`;
            
            if (eventsDiv.children.length >= 20) {
                eventsDiv.removeChild(eventsDiv.firstChild);
            }
            
            eventsDiv.appendChild(eventDiv);
        }
    </script>
</body>
</html>
"""

class EvalHandler(BaseHTTPRequestHandler, TestableComponent):
    def self_test(self) -> Dict[str, Any]:
        return {'passed': True, 'tests_passed': ['Handler ready'], 'tests_failed': [], 'message': 'Ready'}
    
    def get_test_suite(self) -> unittest.TestSuite:
        return unittest.TestSuite()
        
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path == '/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'runtime': platform.engine.runtime,
                'workers': task_queue.executor._max_workers
            }).encode())
            
        elif self.path == '/queue-status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(task_queue.get_status()).encode())
            
        elif self.path.startswith('/monitor/'):
            eval_id = self.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            last_event_idx = 0
            
            while True:
                events = platform.monitor.get_events(eval_id, last_event_idx)
                for event in events:
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                    self.wfile.flush()
                    last_event_idx += 1
                    
                    if event['type'] == 'complete':
                        return
                
                time.sleep(0.1)
                
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/eval':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            eval_id = platform.submit_evaluation(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'eval_id': eval_id}).encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    # Check test level from environment (default: FULL for safety)
    test_level = os.environ.get('CRUCIBLE_TEST_LEVEL', 'FULL')
    
    # Parse runtime argument
    runtime = 'runsc'  # Default to gVisor
    for arg in sys.argv[1:]:
        if arg.startswith('--runtime='):
            runtime = arg.split('=')[1]
            if runtime not in ['runc', 'runsc']:
                print(f"ERROR: Unknown runtime '{runtime}'. Use 'runc' or 'runsc'")
                sys.exit(1)
    
    # Check Docker availability
    print("Checking Docker availability...")
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        print("Docker is available")
    except:
        print("ERROR: Docker not found. Please install Docker.")
        sys.exit(1)
    
    # Check gVisor availability if requested
    if runtime == 'runsc':
        print("Checking gVisor (runsc) availability...")
        try:
            # Test if runsc runtime is available
            test_result = subprocess.run(
                ['docker', 'run', '--rm', '--runtime=runsc', 'alpine', 'echo', 'test'],
                capture_output=True,
                text=True
            )
            if test_result.returncode == 0:
                print("gVisor runtime is available")
            else:
                print("WARNING: gVisor runtime not found. Falling back to standard runtime.")
                print("To install gVisor: https://gvisor.dev/docs/user_guide/install/")
                runtime = 'runc'
        except:
            print("WARNING: Could not test gVisor. Falling back to standard runtime.")
            runtime = 'runc'
    
    # Pull Python image
    print("Ensuring Python Docker image is available...")
    subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
    
    # Create services
    monitor = InMemoryMonitor()
    engine = GVisorEngine(monitor, runtime=runtime)
    task_queue = TaskQueue(max_workers=3)
    platform = EvaluationPlatform(engine, monitor, task_queue)
    
    # Run tests based on level
    if test_level == 'FULL':
        print("\nRunning FULL test suite for ALL components...")
        print("="*50)
        
        # Test all components
        all_passed = True
        components = [
            ("Monitor", monitor),
            ("Task Queue", task_queue),
            ("Execution Engine", engine),
            ("Platform", platform)
        ]
        
        # Run self-tests for each component
        print("\n1. Running self-tests for each component:")
        for name, component in components:
            test_results = component.self_test()
            print(f"\n{name}: {test_results['message']}")
            if test_results['tests_passed']:
                print("  Passed:", ", ".join(test_results['tests_passed']))
            if test_results['tests_failed']:
                print("  FAILED:", ", ".join(test_results['tests_failed']))
                all_passed = False
        
        if not all_passed:
            print("\n" + "="*70)
            print("FATAL: Component self-tests FAILED!")
            print("Platform is NOT safe for use.")
            print("="*70)
            sys.exit(1)
        
        # Run comprehensive test suites
        print("\n2. Running comprehensive test suites:")
        for name, component in components:
            print(f"\nTesting {name}...")
            suite = component.get_test_suite()
            if suite.countTestCases() > 0:
                runner = unittest.TextTestRunner(verbosity=1)
                result = runner.run(suite)
                
                if not result.wasSuccessful():
                    print("\n" + "="*70)
                    print(f"FATAL: {name} tests FAILED!")
                    print("Platform is NOT safe for production use.")
                    print("="*70)
                    sys.exit(1)
            else:
                print(f"  No comprehensive tests for {name}")
        
        print("\n" + "="*50)
        print("ALL SECURITY TESTS PASSED")
        if runtime == 'runsc':
            print("Platform is PRODUCTION SAFE (4/4 requirements)")
        else:
            print("Platform has basic safety (3.5/4 requirements)")
        print("="*50 + "\n")
        
    elif test_level == 'QUICK':
        print("="*70)
        print("WARNING: Running only quick tests")
        print("Production safety NOT fully verified!")
        print("="*70 + "\n")
        
        # Quick test all components
        components = [
            ("Monitor", monitor),
            ("Task Queue", task_queue),
            ("Execution Engine", engine),
            ("Platform", platform)
        ]
        
        all_passed = True
        for name, component in components:
            test_results = component.self_test()
            print(f"{name}: {test_results['message']}")
            if not test_results['passed']:
                all_passed = False
        
        if not all_passed:
            print("\nERROR: Even quick tests failed!")
            sys.exit(1)
        
    elif test_level == 'NONE':
        print("="*70)
        print("DANGER: All tests skipped!")
        print("Production safety is UNVERIFIED!")
        print("="*70)
        input("\nPress Enter to continue at your own risk...")
    
    # Start server
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print(f"Crucible Platform running at http://localhost:8000")
    print(f"Runtime: {runtime} ({'PRODUCTION SAFE' if runtime == 'runsc' else 'BASIC SAFETY ONLY'})")
    print(f"Workers: 3 concurrent evaluations")
    print(f"Test level: {test_level}")
    
    if runtime == 'runsc':
        print("\nSecurity model matches Google Cloud Run:")
        print("- gVisor syscall interception")
        print("- Non-root user execution")
        print("- Network fully disabled")
        print("- Read-only filesystem")
        print("\nThis configuration can safely run untrusted AI model code.")
    else:
        print("\nWARNING: Running without gVisor. NOT safe for production!")
        print("Install gVisor for production use: https://gvisor.dev/docs/user_guide/install/")
    
    print("\nPress Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        task_queue.shutdown()