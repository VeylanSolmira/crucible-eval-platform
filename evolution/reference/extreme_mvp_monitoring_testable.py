#!/usr/bin/env python3
"""
Crucible Evaluation Platform - With Real-time Monitoring AND Testing
Evolution 2: Add Server-Sent Events for execution progress + TestableComponent

Run with: python extreme_mvp_monitoring_testable.py
Then open: http://localhost:8000

Requirements: Docker must be installed and running
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import uuid
import tempfile
import os
import threading
import time
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import unittest
from io import StringIO

# ============== TESTING AS FIRST-CLASS ABSTRACTION ==============

class TestableComponent(ABC):
    """
    Base class for all components that must be testable.
    This ensures safety features are verifiable!
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

# ============== MONITORING SERVICE WITH TESTING ==============

class MonitoringService(TestableComponent):
    """Service for tracking evaluation events"""
    
    def __init__(self):
        self.events = {}  # eval_id -> list of events
        self.subscribers = {}  # eval_id -> list of queues
        self.lock = threading.Lock()
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        """Emit an event for an evaluation"""
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
            
            # Notify subscribers
            if eval_id in self.subscribers:
                for queue in self.subscribers[eval_id]:
                    queue.put(event)
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        """Get events for an evaluation starting from index"""
        with self.lock:
            if eval_id not in self.events:
                return []
            return self.events[eval_id][start_idx:]
    
    def self_test(self) -> Dict[str, Any]:
        """Test monitoring functionality"""
        results = []
        
        # Test 1: Event emission and retrieval
        test_id = "test_" + str(uuid.uuid4())[:8]
        self.emit_event(test_id, "info", "Test event")
        events = self.get_events(test_id)
        
        results.append({
            'name': 'Event emission',
            'passed': len(events) == 1 and events[0]['message'] == "Test event",
            'error': None if len(events) == 1 else f"Expected 1 event, got {len(events)}"
        })
        
        # Test 2: Multiple events
        self.emit_event(test_id, "warning", "Another event")
        events = self.get_events(test_id)
        
        results.append({
            'name': 'Multiple events',
            'passed': len(events) == 2,
            'error': None if len(events) == 2 else f"Expected 2 events, got {len(events)}"
        })
        
        # Test 3: Event ordering
        ordered = events[0]['message'] == "Test event" and events[1]['message'] == "Another event"
        results.append({
            'name': 'Event ordering',
            'passed': ordered,
            'error': None if ordered else "Events out of order"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'All monitoring tests passed' if all_passed else 'Some monitoring tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for monitoring"""
        class MonitoringTests(unittest.TestCase):
            def setUp(self):
                self.service = MonitoringService()
            
            def test_event_emission(self):
                eval_id = "test_eval"
                self.service.emit_event(eval_id, "info", "Test")
                events = self.service.get_events(eval_id)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]['message'], "Test")
            
            def test_concurrent_access(self):
                eval_id = "concurrent_test"
                
                def emit_events():
                    for i in range(10):
                        self.service.emit_event(eval_id, "info", f"Event {i}")
                
                threads = [threading.Thread(target=emit_events) for _ in range(5)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                
                events = self.service.get_events(eval_id)
                self.assertEqual(len(events), 50)  # 5 threads * 10 events
        
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(MonitoringTests))
        return suite

# ============== EXECUTION ENGINE WITH MONITORING ==============

class DockerExecutionEngine(TestableComponent):
    """Docker-based execution with monitoring support"""
    
    def __init__(self, monitoring_service: MonitoringService):
        self.monitoring = monitoring_service
    
    def execute(self, code: str, eval_id: str) -> dict:
        """Execute code in Docker container with monitoring"""
        self.monitoring.emit_event(eval_id, 'info', 'Creating code file...')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            self.monitoring.emit_event(eval_id, 'info', 'Building Docker command...')
            
            # Docker command
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
            
            self.monitoring.emit_event(eval_id, 'info', 'Starting container...')
            
            # Execute with real-time output
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            output_lines = []
            self.monitoring.emit_event(eval_id, 'info', 'Container running')
            
            # Stream output
            for line in iter(process.stdout.readline, ''):
                if line:
                    line = line.rstrip()
                    output_lines.append(line)
                    self.monitoring.emit_event(eval_id, 'output', f"Output: {line}")
            
            process.wait()
            
            if process.returncode == 0:
                self.monitoring.emit_event(eval_id, 'success', 'Container exited successfully')
            else:
                self.monitoring.emit_event(eval_id, 'error', f'Container exited with code {process.returncode}')
            
            return {
                'success': process.returncode == 0,
                'output': '\n'.join(output_lines),
                'error': None if process.returncode == 0 else f'Exit code: {process.returncode}'
            }
            
        except Exception as e:
            self.monitoring.emit_event(eval_id, 'error', f'Execution failed: {str(e)}')
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
        finally:
            os.unlink(temp_file)
            self.monitoring.emit_event(eval_id, 'info', 'Evaluation complete')
    
    def self_test(self) -> Dict[str, Any]:
        """Test Docker execution with monitoring"""
        results = []
        test_id = "test_" + str(uuid.uuid4())[:8]
        
        # Test 1: Basic execution with monitoring
        result = self.execute("print('Hello from Docker!')", test_id)
        results.append({
            'name': 'Docker execution with monitoring',
            'passed': result['success'] and 'Hello from Docker!' in result['output'],
            'error': result.get('error')
        })
        
        # Test 2: Check monitoring events were recorded
        events = self.monitoring.get_events(test_id)
        has_start = any(e['message'].startswith('Starting container') for e in events)
        has_output = any('Hello from Docker!' in e['message'] for e in events)
        has_complete = any('complete' in e['message'].lower() for e in events)
        
        results.append({
            'name': 'Monitoring events recorded',
            'passed': has_start and has_output and has_complete,
            'error': f"Missing events: start={has_start}, output={has_output}, complete={has_complete}"
        })
        
        # Test 3: Network isolation
        result = self.execute("import urllib.request; urllib.request.urlopen('http://google.com')", test_id)
        results.append({
            'name': 'Network isolation',
            'passed': not result['success'] and 'Network is unreachable' in str(result['output'] + str(result['error'])),
            'error': None if not result['success'] else "Network access should be blocked"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'All execution tests passed' if all_passed else 'Some execution tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite"""
        class ExecutionTests(unittest.TestCase):
            def setUp(self):
                self.monitoring = MonitoringService()
                self.engine = DockerExecutionEngine(self.monitoring)
            
            def test_basic_execution(self):
                result = self.engine.execute("print('test')", "test1")
                self.assertTrue(result['success'])
                self.assertIn('test', result['output'])
            
            def test_monitoring_integration(self):
                eval_id = "test2"
                self.engine.execute("print('monitored')", eval_id)
                events = self.monitoring.get_events(eval_id)
                
                # Should have multiple events
                self.assertGreater(len(events), 3)
                
                # Should have lifecycle events
                event_messages = [e['message'] for e in events]
                self.assertTrue(any('Starting' in m for m in event_messages))
                self.assertTrue(any('complete' in m for m in event_messages))
        
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(ExecutionTests))
        return suite

# ============== PLATFORM WITH MONITORING AND TESTING ==============

class EvaluationPlatform(TestableComponent):
    """Main platform orchestrator"""
    
    def __init__(self, engine: DockerExecutionEngine, monitoring: MonitoringService):
        self.engine = engine
        self.monitoring = monitoring
        self.evaluations = {}
    
    def submit_evaluation(self, code: str) -> str:
        """Submit code for evaluation"""
        eval_id = str(uuid.uuid4())[:8]
        
        # Store evaluation
        self.evaluations[eval_id] = {
            'code': code,
            'status': 'pending',
            'created_at': datetime.now(),
            'result': None
        }
        
        # Start evaluation in background
        thread = threading.Thread(target=self._run_evaluation, args=(code, eval_id))
        thread.start()
        
        return eval_id
    
    def _run_evaluation(self, code: str, eval_id: str):
        """Run evaluation with monitoring"""
        self.evaluations[eval_id]['status'] = 'running'
        self.monitoring.emit_event(eval_id, 'info', 'Starting evaluation...')
        
        result = self.engine.execute(code, eval_id)
        
        self.evaluations[eval_id]['status'] = 'completed'
        self.evaluations[eval_id]['result'] = result
    
    def get_evaluation(self, eval_id: str) -> Optional[dict]:
        """Get evaluation details"""
        return self.evaluations.get(eval_id)
    
    def self_test(self) -> Dict[str, Any]:
        """Test the platform"""
        results = []
        
        # Test 1: Submission creates evaluation
        eval_id = self.submit_evaluation("print('test')")
        eval = self.get_evaluation(eval_id)
        
        results.append({
            'name': 'Evaluation submission',
            'passed': eval is not None and eval['status'] in ['pending', 'running'],
            'error': None if eval else "Evaluation not created"
        })
        
        # Test 2: Wait for completion
        time.sleep(3)  # Give it time to complete
        eval = self.get_evaluation(eval_id)
        
        results.append({
            'name': 'Evaluation completion',
            'passed': eval is not None and eval['status'] == 'completed',
            'error': f"Status: {eval['status'] if eval else 'None'}"
        })
        
        all_passed = all(r['passed'] for r in results)
        return {
            'passed': all_passed,
            'tests': results,
            'message': 'Platform tests passed' if all_passed else 'Platform tests failed'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return platform test suite"""
        class PlatformTests(unittest.TestCase):
            def setUp(self):
                monitoring = MonitoringService()
                engine = DockerExecutionEngine(monitoring)
                self.platform = EvaluationPlatform(engine, monitoring)
            
            def test_evaluation_lifecycle(self):
                eval_id = self.platform.submit_evaluation("print('lifecycle test')")
                self.assertIsNotNone(eval_id)
                
                # Should start as pending
                eval = self.platform.get_evaluation(eval_id)
                self.assertIn(eval['status'], ['pending', 'running'])
                
                # Wait for completion
                time.sleep(3)
                eval = self.platform.get_evaluation(eval_id)
                self.assertEqual(eval['status'], 'completed')
                self.assertIsNotNone(eval['result'])
        
        suite = unittest.TestSuite()
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(PlatformTests))
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
            # Server-Sent Events endpoint
            eval_id = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            # Send existing events
            events = platform.monitoring.get_events(eval_id)
            for i, event in enumerate(events):
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
                
                # Check if evaluation is complete
                eval = platform.get_evaluation(eval_id)
                if eval and eval['status'] == 'completed':
                    self.wfile.write(f'data: {json.dumps({"type": "complete", "message": "Evaluation finished"})}\n\n'.encode())
                    self.wfile.flush()
                    break
                
                time.sleep(0.1)
                
        elif self.path == '/test':
            # Run all tests
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            test_results = {
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
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

# HTML interface with SSE support and testing
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Real-time Monitoring with Testing</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        textarea { width: 100%; height: 150px; font-family: monospace; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        button:disabled { background: #ccc; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .info { background: #17a2b8; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .event { margin: 5px 0; padding: 5px; background: white; border-left: 3px solid #28a745; }
        .event.error { border-left-color: #dc3545; }
        .event.warning { border-left-color: #ffc107; }
        .test-results { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .test-passed { color: #28a745; }
        .test-failed { color: #dc3545; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Monitoring + Testing!</h1>
    
    <div class="info">
        <h2>🧪 Testing as First-Class Citizen</h2>
        <p><strong>Every component is testable:</strong></p>
        <ul>
            <li>MonitoringService - Verifies event tracking</li>
            <li>ExecutionEngine - Tests Docker isolation</li>
            <li>Platform - Validates lifecycle management</li>
        </ul>
        <p><strong>Safety through verification!</strong></p>
    </div>
    
    <p>Submit Python code for evaluation:</p>
    
    <textarea id="code" placeholder="import time
print('Starting evaluation...')
time.sleep(2)
print('Processing step 1...')
time.sleep(2)
print('Processing step 2...')
time.sleep(2)
print('Complete!')">import time
print('Starting evaluation...')
time.sleep(2)
print('Processing step 1...')
time.sleep(2)
print('Processing step 2...')
time.sleep(2)
print('Complete!')</textarea>
    <br><br>
    <button id="runBtn" onclick="runEval()">Run with Monitoring</button>
    <button onclick="runTests()">🧪 Run Test Suite</button>
    
    <div class="monitoring">
        <h3>📊 Real-time Monitoring</h3>
        <div id="events">
            <div class="event">Waiting for evaluation...</div>
        </div>
    </div>
    
    <div id="result"></div>
    <div id="testResults"></div>
    
    <script>
        let eventSource = null;
        
        async function runEval() {
            const code = document.getElementById('code').value;
            const eventsDiv = document.getElementById('events');
            const resultDiv = document.getElementById('result');
            const runBtn = document.getElementById('runBtn');
            
            // Clear previous
            eventsDiv.innerHTML = '';
            resultDiv.innerHTML = '';
            runBtn.disabled = true;
            
            try {
                // Submit evaluation
                const response = await fetch('/evaluate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code: code})
                });
                
                const data = await response.json();
                
                // Start monitoring
                eventSource = new EventSource('/events/' + data.eval_id);
                
                eventSource.onmessage = function(e) {
                    const event = JSON.parse(e.data);
                    const eventDiv = document.createElement('div');
                    eventDiv.className = 'event';
                    
                    if (event.type === 'error') eventDiv.className += ' error';
                    if (event.type === 'warning') eventDiv.className += ' warning';
                    
                    eventDiv.innerHTML = `<strong>${event.timestamp}</strong> - ${event.message}`;
                    eventsDiv.appendChild(eventDiv);
                    eventsDiv.scrollTop = eventsDiv.scrollHeight;
                    
                    if (event.type === 'complete') {
                        eventSource.close();
                        runBtn.disabled = false;
                    }
                };
                
                eventSource.onerror = function() {
                    eventSource.close();
                    runBtn.disabled = false;
                };
                
            } catch (error) {
                resultDiv.innerHTML = `<pre style="color: red;">Error: ${error.message}</pre>`;
                runBtn.disabled = false;
            }
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
    </script>
</body>
</html>
"""

def run_all_tests():
    """Run all tests and return results (for test runner)"""
    monitoring_service = MonitoringService()
    execution_engine = DockerExecutionEngine(monitoring_service)
    platform = EvaluationPlatform(execution_engine, monitoring_service)
    
    return {
        'Monitoring': monitoring_service.self_test(),
        'Engine': execution_engine.self_test(),
        'Platform': platform.self_test()
    }

if __name__ == '__main__':
    import sys
    
    # Check for test-only mode
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
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
    
    # Normal server mode
    monitoring_service = MonitoringService()
    execution_engine = DockerExecutionEngine(monitoring_service)
    platform = EvaluationPlatform(execution_engine, monitoring_service)
    
    # Run self-tests on startup
    print("Running startup tests...")
    startup_tests = {
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
                for test in result['tests']:
                    if not test['passed']:
                        print(f"    - {test['name']}: {test.get('error', 'Failed')}")
        print("\nContinuing anyway, but platform may not function correctly...")
    else:
        print("✅ All startup tests passed!")
    
    # Start server
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print(f"\nCrucible Platform (Monitoring + Testing) running on http://localhost:8000")
    print("Features:")
    print("  - Real-time monitoring via Server-Sent Events")
    print("  - Non-blocking async execution")
    print("  - TestableComponent base class")
    print("  - Self-testing on startup")
    print("  - Test suite accessible via UI")
    server.serve_forever()