#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Queue + Testing for Concurrent Evaluations
Evolution: Handle multiple users without blocking + ensure it works!

Run with: python extreme_mvp_queue_testable.py [--unsafe]
Then open: http://localhost:8000

This version adds TestableComponent to the queue-based system.
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
from io import StringIO
import sys

# ============== TESTING AS FIRST-CLASS ABSTRACTION ==============

class TestableComponent(ABC):
    """
    Base class for all components that must be testable.
    Critical for concurrent systems - race conditions must be tested!
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

# ============== TESTABLE QUEUE ==============

class TaskQueue(TestableComponent):
    """
    Task queue for concurrent evaluations with testing support.
    """
    def __init__(self, max_workers: int = 3):
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = True
        self.active_tasks = {}
        self.completed_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        
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
        with self.lock:
            self.active_tasks[eval_id] = 'queued'
    
    def _worker(self, worker_name: str):
        """Worker thread that processes tasks"""
        while self.running:
            try:
                task = self.queue.get(timeout=1)
                eval_id = task['eval_id']
                
                # Update status
                with self.lock:
                    self.active_tasks[eval_id] = 'running'
                
                # Execute the task
                try:
                    task['func'](*task['args'], **task['kwargs'])
                    with self.lock:
                        self.active_tasks[eval_id] = 'completed'
                        self.completed_count += 1
                except Exception as e:
                    with self.lock:
                        self.active_tasks[eval_id] = f'failed: {str(e)}'
                        self.failed_count += 1
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                continue
    
    def get_status(self) -> dict:
        """Get queue status"""
        with self.lock:
            return {
                'queued': self.queue.qsize(),
                'active_tasks': dict(self.active_tasks),
                'workers': self.executor._max_workers,
                'completed': self.completed_count,
                'failed': self.failed_count
            }
    
    def shutdown(self):
        """Gracefully shutdown the queue"""
        self.running = False
        self.executor.shutdown(wait=True)
    
    def self_test(self) -> Dict[str, Any]:
        """Test queue functionality"""
        results = []
        test_results = {'completed': 0, 'failed': 0}
        
        # Test 1: Task submission and execution
        def test_task(result_dict, task_id):
            time.sleep(0.1)  # Simulate work
            result_dict[task_id] = 'done'
        
        test_dict = {}
        for i in range(5):
            self.submit(f"test_{i}", test_task, test_dict, f"test_{i}")
        
        # Wait for completion
        self.queue.join()
        time.sleep(0.2)  # Allow status updates
        
        results.append({
            'name': 'Task execution',
            'passed': len(test_dict) == 5 and all(v == 'done' for v in test_dict.values()),
            'error': None if len(test_dict) == 5 else f"Expected 5 tasks, completed {len(test_dict)}"
        })
        
        # Test 2: Concurrent execution
        start_times = {}
        end_times = {}
        
        def timed_task(task_id):
            start_times[task_id] = time.time()
            time.sleep(0.5)
            end_times[task_id] = time.time()
        
        # Submit tasks that would take 2.5s if sequential
        for i in range(5):
            self.submit(f"timed_{i}", timed_task, f"timed_{i}")
        
        start = time.time()
        self.queue.join()
        elapsed = time.time() - start
        
        # With 3 workers, should complete in ~1s, not 2.5s
        results.append({
            'name': 'Concurrent execution',
            'passed': elapsed < 1.5,  # Should be much less than 2.5s
            'error': None if elapsed < 1.5 else f"Took {elapsed:.2f}s, expected < 1.5s"
        })
        
        # Test 3: Error handling
        def failing_task():
            raise Exception("Test exception")
        
        self.submit("fail_test", failing_task)
        self.queue.join()
        time.sleep(0.1)
        
        status = self.get_status()
        failed_task = status['active_tasks'].get('fail_test', '')
        
        results.append({
            'name': 'Error handling',
            'passed': 'failed:' in failed_task,
            'error': None if 'failed:' in failed_task else f"Status: {failed_task}"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'Queue tests passed' if all_passed else 'Queue tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for queue"""
        class QueueTests(unittest.TestCase):
            def test_submission(self):
                q = TaskQueue(max_workers=2)
                try:
                    result = {'executed': False}
                    
                    def test_func():
                        result['executed'] = True
                    
                    q.submit('test1', test_func)
                    q.queue.join()
                    
                    self.assertTrue(result['executed'])
                finally:
                    q.shutdown()
            
            def test_concurrent_processing(self):
                q = TaskQueue(max_workers=3)
                try:
                    results = []
                    
                    def append_result(val):
                        results.append(val)
                        time.sleep(0.1)
                    
                    for i in range(10):
                        q.submit(f'test{i}', append_result, i)
                    
                    q.queue.join()
                    self.assertEqual(len(results), 10)
                finally:
                    q.shutdown()
        
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(QueueTests))
        return suite

# ============== MONITORING WITH TESTING ==============

class InMemoryMonitoring(TestableComponent):
    """Simple monitoring that tracks events with concurrency safety"""
    def __init__(self):
        self.events = {}
        self.lock = threading.Lock()
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        event = {
            'timestamp': timestamp,
            'type': event_type,
            'message': message
        }
        
        with self.lock:
            if eval_id not in self.events:
                self.events[eval_id] = []
            self.events[eval_id].append(event)
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        with self.lock:
            if eval_id not in self.events:
                return []
            return self.events[eval_id][start_idx:]
    
    def self_test(self) -> Dict[str, Any]:
        """Test thread-safe monitoring"""
        results = []
        
        # Test 1: Concurrent event emission
        test_id = "concurrent_test"
        threads = []
        
        def emit_many(thread_id):
            for i in range(10):
                self.emit_event(test_id, "info", f"Thread {thread_id} event {i}")
        
        for i in range(5):
            t = threading.Thread(target=emit_many, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        events = self.get_events(test_id)
        results.append({
            'name': 'Concurrent event handling',
            'passed': len(events) == 50,  # 5 threads * 10 events
            'error': None if len(events) == 50 else f"Expected 50 events, got {len(events)}"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'Monitoring tests passed' if all_passed else 'Monitoring tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite"""
        suite = unittest.TestSuite()
        # Add specific tests if needed
        return suite

# ============== EXECUTION ENGINE WITH TESTING ==============

class ExecutionEngine(TestableComponent):
    """Abstract execution engine"""
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        pass

class DockerEngine(ExecutionEngine):
    """Docker-based execution engine"""
    def __init__(self, monitoring_service):
        self.emit = lambda eval_id, event_type, msg: monitoring_service.emit_event(eval_id, event_type, msg)
    
    def execute(self, code: str, eval_id: str) -> dict:
        self.emit(eval_id, 'info', 'Creating code file...')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            self.emit(eval_id, 'info', 'Starting Docker container...')
            
            docker_cmd = [
                'docker', 'run',
                '--rm',
                '--network', 'none',
                '--memory', '100m',
                '--cpus', '0.5',
                '--read-only',
                '-v', f'{temp_file}:/code.py:ro',
                'python:3.11-slim',
                'python', '/code.py'
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            self.emit(eval_id, 'success' if result.returncode == 0 else 'error', 
                     f'Container exited with code {result.returncode}')
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout + result.stderr,
                'error': None if result.returncode == 0 else f'Exit code: {result.returncode}'
            }
            
        except subprocess.TimeoutExpired:
            self.emit(eval_id, 'error', 'Execution timed out after 5 seconds')
            return {
                'success': False,
                'output': '',
                'error': 'Timeout after 5 seconds'
            }
        except Exception as e:
            self.emit(eval_id, 'error', f'Execution failed: {str(e)}')
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
        finally:
            os.unlink(temp_file)
            self.emit(eval_id, 'info', 'Cleanup complete')
    
    def self_test(self) -> Dict[str, Any]:
        """Test Docker execution"""
        results = []
        monitoring = InMemoryMonitoring()
        self.emit = lambda eval_id, event_type, msg: monitoring.emit_event(eval_id, event_type, msg)
        
        # Test basic execution
        result = self.execute("print('test')", "test1")
        results.append({
            'name': 'Docker execution',
            'passed': result['success'] and 'test' in result['output'],
            'error': result.get('error')
        })
        
        # Test timeout
        result = self.execute("import time; time.sleep(10)", "test2")
        results.append({
            'name': 'Timeout handling',
            'passed': not result['success'] and 'Timeout' in result['error'],
            'error': None if 'Timeout' in str(result['error']) else "Timeout not detected"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'Engine tests passed' if all_passed else 'Engine tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite"""
        suite = unittest.TestSuite()
        return suite

class SubprocessEngine(ExecutionEngine):
    """Unsafe direct execution engine"""
    def __init__(self, monitoring_service):
        self.emit = lambda eval_id, event_type, msg: monitoring_service.emit_event(eval_id, event_type, msg)
    
    def execute(self, code: str, eval_id: str) -> dict:
        self.emit(eval_id, 'warning', '⚠️  UNSAFE: Direct Python execution!')
        
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout + result.stderr,
                'error': None if result.returncode == 0 else f'Exit code: {result.returncode}'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': 'Timeout after 5 seconds'
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
    
    def self_test(self) -> Dict[str, Any]:
        """Test subprocess execution"""
        results = []
        
        # Basic test only - don't test dangerous operations
        result = self.execute("print('test')", "test1")
        results.append({
            'name': 'Subprocess execution',
            'passed': result['success'] and 'test' in result['output'],
            'error': result.get('error')
        })
        
        return {
            'passed': all(r['passed'] for r in results),
            'tests': results,
            'message': 'Subprocess tests passed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite"""
        suite = unittest.TestSuite()
        return suite

# ============== PLATFORM WITH QUEUE ==============

class EvaluationPlatform(TestableComponent):
    """Main platform orchestrator with queue support"""
    
    def __init__(self, engine: ExecutionEngine, monitoring: Any, task_queue: TaskQueue):
        self.engine = engine
        self.monitoring = monitoring
        self.queue = task_queue
        self.evaluations = {}
        self.lock = threading.Lock()
    
    def submit_evaluation(self, code: str) -> str:
        """Submit code for evaluation"""
        eval_id = str(uuid.uuid4())[:8]
        
        with self.lock:
            self.evaluations[eval_id] = {
                'code': code,
                'status': 'queued',
                'created_at': datetime.now(),
                'result': None
            }
        
        # Submit to queue
        self.queue.submit(eval_id, self._run_evaluation, code, eval_id)
        
        return eval_id
    
    def _run_evaluation(self, code: str, eval_id: str):
        """Run evaluation (called by queue worker)"""
        with self.lock:
            self.evaluations[eval_id]['status'] = 'running'
        
        self.monitoring.emit_event(eval_id, 'info', 'Starting evaluation...')
        
        result = self.engine.execute(code, eval_id)
        
        with self.lock:
            self.evaluations[eval_id]['status'] = 'completed'
            self.evaluations[eval_id]['result'] = result
        
        self.monitoring.emit_event(eval_id, 'info', 'Evaluation complete')
    
    def get_evaluation(self, eval_id: str) -> Optional[dict]:
        """Get evaluation details"""
        with self.lock:
            return self.evaluations.get(eval_id)
    
    def get_all_evaluations(self) -> dict:
        """Get all evaluations"""
        with self.lock:
            return dict(self.evaluations)
    
    def self_test(self) -> Dict[str, Any]:
        """Test platform with queue"""
        results = []
        
        # Test 1: Multiple concurrent submissions
        eval_ids = []
        for i in range(5):
            eval_id = self.submit_evaluation(f"print('Test {i}')")
            eval_ids.append(eval_id)
        
        # All should be queued or running
        statuses = []
        for eval_id in eval_ids:
            eval = self.get_evaluation(eval_id)
            if eval:
                statuses.append(eval['status'])
        
        results.append({
            'name': 'Concurrent submissions',
            'passed': all(s in ['queued', 'running', 'completed'] for s in statuses),
            'error': f"Statuses: {statuses}" if len(statuses) != 5 else None
        })
        
        # Wait for completion
        self.queue.queue.join()
        time.sleep(0.5)
        
        # All should be completed
        completed = sum(1 for eid in eval_ids 
                       if self.get_evaluation(eid) and 
                       self.get_evaluation(eid)['status'] == 'completed')
        
        results.append({
            'name': 'Queue processing',
            'passed': completed == 5,
            'error': None if completed == 5 else f"Only {completed}/5 completed"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'Platform tests passed' if all_passed else 'Platform tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return platform test suite"""
        suite = unittest.TestSuite()
        return suite

# ============== HTTP HANDLER ==============

class EvalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path.startswith('/events/'):
            eval_id = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            # Send existing events
            events = platform.monitoring.get_events(eval_id)
            for event in events:
                self.wfile.write(f'data: {json.dumps(event)}\n\n'.encode())
                self.wfile.flush()
            
            # Keep connection open for new events
            start_idx = len(events)
            while True:
                new_events = platform.monitoring.get_events(eval_id, start_idx)
                for event in new_events:
                    self.wfile.write(f'data: {json.dumps(event)}\n\n'.encode())
                    self.wfile.flush()
                    start_idx += 1
                
                eval = platform.get_evaluation(eval_id)
                if eval and eval['status'] == 'completed':
                    # Send final result
                    self.wfile.write(f'data: {json.dumps({
                        "type": "complete",
                        "result": eval["result"]
                    })}\n\n'.encode())
                    self.wfile.flush()
                    break
                
                time.sleep(0.1)
                
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = {
                'queue': platform.queue.get_status(),
                'evaluations': platform.get_all_evaluations()
            }
            self.wfile.write(json.dumps(status, default=str).encode())
            
        elif self.path == '/test':
            # Run all component tests
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            test_results = {
                'queue': platform.queue.self_test(),
                'monitoring': platform.monitoring.self_test(),
                'engine': platform.engine.self_test(),
                'platform': platform.self_test()
            }
            
            self.wfile.write(json.dumps(test_results, indent=2).encode())
    
    def do_POST(self):
        if self.path == '/evaluate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            eval_id = platform.submit_evaluation(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'eval_id': eval_id}).encode())
            
        elif self.path == '/evaluate/batch':
            # Submit multiple evaluations
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            eval_ids = []
            for i in range(data.get('count', 5)):
                code = f"import time\nprint('Evaluation {i+1} starting...')\ntime.sleep(2)\nprint('Evaluation {i+1} complete!')"
                eval_id = platform.submit_evaluation(code)
                eval_ids.append(eval_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'eval_ids': eval_ids}).encode())
    
    def log_message(self, format, *args):
        pass

# HTML interface with queue status
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Concurrent Queue</title>
    <style>
        body { font-family: Arial; max-width: 900px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        button:disabled { background: #ccc; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .info { background: #17a2b8; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .queue-status { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .evaluation { background: white; border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .status-queued { color: #ffc107; }
        .status-running { color: #17a2b8; }
        .status-completed { color: #28a745; }
        .status-failed { color: #dc3545; }
        .test-results { background: #f8f9fa; padding: 15px; margin: 10px 0; }
        .test-passed { color: #28a745; }
        .test-failed { color: #dc3545; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Concurrent Evaluations!</h1>
    
    <div class="info">
        <h2>🚀 Queue-Based Processing + Testing</h2>
        <p><strong>New capabilities:</strong></p>
        <ul>
            <li>Multiple concurrent workers (3 by default)</li>
            <li>Non-blocking evaluation submission</li>
            <li>Real-time queue status monitoring</li>
            <li>TestableComponent for all components</li>
            <li>Comprehensive concurrency tests</li>
        </ul>
        <p><strong>This addresses Requirement #3:</strong> Scale to many concurrent evaluations</p>
    </div>
    
    <textarea id="code" placeholder="Enter Python code...">import time
print('Starting evaluation...')
time.sleep(2)
print('Processing...')
time.sleep(2)
print('Complete!')</textarea>
    <br>
    <button onclick="runEval()">Submit Evaluation</button>
    <button onclick="submitBatch()">Submit 5 Evaluations</button>
    <button onclick="refreshStatus()">Refresh Status</button>
    <button onclick="runTests()">🧪 Run Test Suite</button>
    
    <div class="queue-status">
        <h3>📊 Queue Status</h3>
        <div id="queueStatus">Loading...</div>
    </div>
    
    <div id="evaluations"></div>
    <div id="testResults"></div>
    
    <script>
        let activeConnections = {};
        
        async function runEval() {
            const code = document.getElementById('code').value;
            
            const response = await fetch('/evaluate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code: code})
            });
            
            const data = await response.json();
            startMonitoring(data.eval_id);
            refreshStatus();
        }
        
        async function submitBatch() {
            const response = await fetch('/evaluate/batch', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({count: 5})
            });
            
            const data = await response.json();
            data.eval_ids.forEach(id => startMonitoring(id));
            refreshStatus();
        }
        
        function startMonitoring(evalId) {
            if (activeConnections[evalId]) return;
            
            const eventSource = new EventSource('/events/' + evalId);
            activeConnections[evalId] = eventSource;
            
            eventSource.onmessage = function(e) {
                const event = JSON.parse(e.data);
                
                if (event.type === 'complete') {
                    eventSource.close();
                    delete activeConnections[evalId];
                    refreshStatus();
                }
            };
            
            eventSource.onerror = function() {
                eventSource.close();
                delete activeConnections[evalId];
            };
        }
        
        async function refreshStatus() {
            const response = await fetch('/status');
            const status = await response.json();
            
            // Update queue status
            const queueDiv = document.getElementById('queueStatus');
            queueDiv.innerHTML = `
                <strong>Workers:</strong> ${status.queue.workers}<br>
                <strong>Queued:</strong> ${status.queue.queued}<br>
                <strong>Completed:</strong> ${status.queue.completed}<br>
                <strong>Failed:</strong> ${status.queue.failed}
            `;
            
            // Update evaluations
            const evalsDiv = document.getElementById('evaluations');
            evalsDiv.innerHTML = '<h3>Recent Evaluations</h3>';
            
            const evalIds = Object.keys(status.evaluations).reverse().slice(0, 10);
            
            evalIds.forEach(id => {
                const eval = status.evaluations[id];
                const statusClass = 'status-' + eval.status;
                
                const evalDiv = document.createElement('div');
                evalDiv.className = 'evaluation';
                evalDiv.innerHTML = `
                    <strong>${id}</strong> - 
                    <span class="${statusClass}">${eval.status.toUpperCase()}</span> - 
                    ${new Date(eval.created_at).toLocaleTimeString()}
                    ${eval.result ? `<br><small>Output: ${eval.result.output || 'No output'}</small>` : ''}
                `;
                evalsDiv.appendChild(evalDiv);
            });
        }
        
        async function runTests() {
            const resultsDiv = document.getElementById('testResults');
            resultsDiv.innerHTML = '<h3>🧪 Running Test Suite...</h3>';
            
            try {
                const response = await fetch('/test');
                const results = await response.json();
                
                let html = '<div class="test-results"><h3>🧪 Test Results</h3>';
                
                for (const [component, result] of Object.entries(results)) {
                    html += `<h4>${component} (${result.passed ? '✅ PASSED' : '❌ FAILED'})</h4>`;
                    html += '<ul>';
                    for (const test of result.tests) {
                        const status = test.passed ? 
                            '<span class="test-passed">✓</span>' : 
                            '<span class="test-failed">✗</span>';
                        html += `<li>${status} ${test.name}`;
                        if (test.error) {
                            html += ` - <small>${test.error}</small>`;
                        }
                        html += '</li>';
                    }
                    html += '</ul>';
                }
                
                html += '</div>';
                resultsDiv.innerHTML = html;
                
            } catch (error) {
                resultsDiv.innerHTML = `<pre style="color: red;">Test Error: ${error.message}</pre>`;
            }
        }
        
        // Auto-refresh status
        setInterval(refreshStatus, 2000);
        refreshStatus();
    </script>
</body>
</html>
"""

def run_all_tests():
    """Run all tests and return results (for test runner)"""
    monitoring = InMemoryMonitoring()
    queue = TaskQueue(max_workers=2)
    engine = DockerEngine(monitoring)
    platform = EvaluationPlatform(engine, monitoring, queue)
    
    results = {
        'Queue': queue.self_test(),
        'Monitoring': monitoring.self_test(),
        'Engine': engine.self_test(),
        'Platform': platform.self_test()
    }
    
    # Cleanup
    queue.shutdown()
    
    return results

if __name__ == '__main__':
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--unsafe', action='store_true', help='Use unsafe subprocess execution')
    parser.add_argument('--test', action='store_true', help='Run tests only, do not start server')
    args = parser.parse_args()
    
    # Test-only mode
    if args.test:
        print("Running tests only...")
        results = run_all_tests()
        
        all_passed = True
        for component, result in results.items():
            status = "✅ PASSED" if result['passed'] else "❌ FAILED"
            print(f"\n{component}: {status}")
            
            if 'tests' in result:
                for test in result['tests']:
                    test_status = "✓" if test['passed'] else "✗"
                    print(f"  {test_status} {test['name']}")
                    if not test['passed'] and test.get('error'):
                        print(f"    → {test['error']}")
            
            if not result['passed']:
                all_passed = False
        
        sys.exit(0 if all_passed else 1)
    
    # Initialize components
    monitoring_service = InMemoryMonitoring()
    task_queue = TaskQueue(max_workers=3)
    
    if args.unsafe:
        print("⚠️  WARNING: Running in UNSAFE mode - direct Python execution!")
        execution_engine = SubprocessEngine(monitoring_service)
    else:
        execution_engine = DockerEngine(monitoring_service)
    
    platform = EvaluationPlatform(execution_engine, monitoring_service, task_queue)
    
    # Run startup tests
    print("Running startup tests...")
    startup_tests = {
        'Queue': task_queue.self_test(),
        'Monitoring': monitoring_service.self_test(),
        'Engine': execution_engine.self_test(),
        'Platform': platform.self_test()
    }
    
    all_passed = all(result['passed'] for result in startup_tests.values())
    
    if not all_passed:
        print("⚠️  STARTUP TESTS FAILED!")
        for component, result in startup_tests.items():
            if not result['passed']:
                print(f"  {component}: {result['message']}")
    else:
        print("✅ All startup tests passed!")
    
    # Start server
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print(f"\nCrucible Platform (Queue + Testing) running on http://localhost:8000")
    print("Features:")
    print("  - Concurrent evaluation processing")
    print("  - Real-time queue status")
    print("  - TestableComponent throughout")
    print("  - Comprehensive test suite")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        task_queue.shutdown()
        print("Goodbye!")