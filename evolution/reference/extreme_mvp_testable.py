#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Testing as First-Class Citizen
Evolution: Testing shouldn't be an afterthought - it's core to safety!

Run with: python extreme_mvp_testable.py [--unsafe]
Then open: http://localhost:8000

This version introduces TestableComponent as a base abstraction.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import uuid
import tempfile
import os
import time
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import unittest
from io import StringIO

# ============== TESTING AS FIRST-CLASS ABSTRACTION ==============

class TestableComponent(ABC):
    """
    Base class for all components that must be testable.
    This emerged from realizing that untested evaluation platforms are dangerous!
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

# ============== EXECUTION ENGINE WITH TESTING ==============

class ExecutionEngine(TestableComponent):
    """Abstract execution engine that MUST be testable"""
    
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        pass
    
    def self_test(self) -> Dict[str, Any]:
        """Default self-test for execution engines"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Can execute simple code
        try:
            result = self.execute("print('test')", "test-1")
            if 'test' in result.get('output', ''):
                tests_passed.append("Basic execution")
            else:
                tests_failed.append("Basic execution: no output")
        except Exception as e:
            tests_failed.append(f"Basic execution: {str(e)}")
        
        # Test 2: Handles timeout
        try:
            result = self.execute("import time; time.sleep(60)", "test-2")
            if result.get('status') in ['timeout', 'failed']:
                tests_passed.append("Timeout handling")
            else:
                tests_failed.append("Timeout handling: didn't timeout")
        except Exception as e:
            tests_failed.append(f"Timeout handling: {str(e)}")
        
        # Test 3: Handles errors
        try:
            result = self.execute("raise Exception('test error')", "test-3")
            if result.get('status') in ['error', 'failed', 'completed']:
                # For Docker, stderr might go to output with 'completed' status
                if 'Exception' in result.get('output', '') or result.get('status') in ['error', 'failed']:
                    tests_passed.append("Error handling")
                else:
                    tests_failed.append(f"Error handling: status={result.get('status')}, output={result.get('output', '')[:100]}")
            else:
                tests_failed.append(f"Error handling: unexpected status={result.get('status')}")
        except Exception as e:
            tests_failed.append(f"Error handling: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }

class SubprocessEngine(ExecutionEngine):
    """Unsafe subprocess engine with tests"""
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                'id': eval_id,
                'status': 'completed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'id': eval_id, 'status': 'timeout', 'error': 'Timeout after 5 seconds'}
        except Exception as e:
            return {'id': eval_id, 'status': 'error', 'error': str(e)}
    
    def get_description(self) -> str:
        return "Subprocess (UNSAFE - Direct execution)"
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return specific tests for subprocess engine"""
        class SubprocessEngineTests(unittest.TestCase):
            def setUp(self):
                self.engine = SubprocessEngine()
            
            def test_basic_execution(self):
                result = self.engine.execute("print('hello')", "test-1")
                self.assertEqual(result['status'], 'completed')
                self.assertIn('hello', result['output'])
            
            def test_timeout(self):
                result = self.engine.execute("import time; time.sleep(10)", "test-2")
                self.assertEqual(result['status'], 'timeout')
            
            def test_file_access_works(self):
                # This SHOULD work in subprocess (that's the danger!)
                result = self.engine.execute("import os; print(os.getcwd())", "test-3")
                self.assertEqual(result['status'], 'completed')
                self.assertTrue(len(result['output']) > 0)
        
        return unittest.TestLoader().loadTestsFromTestCase(SubprocessEngineTests)

class DockerEngine(ExecutionEngine):
    """Docker engine with safety tests"""
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            docker_cmd = [
                'docker', 'run',
                '--rm', '--network', 'none',
                '--memory', '100m', '--cpus', '0.5',
                '--read-only',
                '-v', f'{temp_file}:/code.py:ro',
                'python:3.11-slim',
                'python', '/code.py'
            ]
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'id': eval_id,
                'status': 'completed' if result.returncode == 0 else 'failed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'id': eval_id, 'status': 'timeout', 'error': 'Timeout after 30 seconds'}
        except Exception as e:
            return {'id': eval_id, 'status': 'error', 'error': str(e)}
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def get_description(self) -> str:
        return "Docker (Containerized - Network isolated)"
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Docker-specific safety tests"""
        class DockerEngineTests(unittest.TestCase):
            def setUp(self):
                self.engine = DockerEngine()
            
            def test_network_isolation(self):
                result = self.engine.execute(
                    "import urllib.request; urllib.request.urlopen('http://google.com')",
                    "test-net"
                )
                self.assertIn('failed', result['status'])
                self.assertIn('Network is unreachable', result['output'])
            
            def test_filesystem_readonly(self):
                result = self.engine.execute(
                    "open('/tmp/test.txt', 'w').write('test')",
                    "test-fs"
                )
                self.assertIn('failed', result['status'])
                self.assertIn('Read-only file system', result['output'])
            
            def test_resource_limits(self):
                # Try to allocate more than 100MB
                result = self.engine.execute(
                    "data = 'x' * (200 * 1024 * 1024)",  # 200MB
                    "test-mem"
                )
                # Should be killed by memory limit
                self.assertIn(result['status'], ['failed', 'error'])
        
        return unittest.TestLoader().loadTestsFromTestCase(DockerEngineTests)

# ============== MONITORING WITH TESTING ==============

class MonitoringService(TestableComponent):
    """Abstract monitoring that must be testable"""
    
    @abstractmethod
    def emit_event(self, eval_id: str, event_type: str, message: str):
        pass
    
    @abstractmethod
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        pass
    
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
        
        return unittest.TestLoader().loadTestsFromTestCase(MonitorTests)

# ============== TESTABLE PLATFORM ==============

class TestableEvaluationPlatform(TestableComponent):
    """Platform that ensures all components are tested"""
    
    def __init__(self, engine: ExecutionEngine, monitor: MonitoringService):
        self.engine = engine
        self.monitor = monitor
        
        # Run component tests on initialization
        self.test_results = self._run_all_tests()
    
    def _run_all_tests(self) -> Dict[str, Any]:
        """Run all component tests"""
        results = {
            'engine': self.engine.self_test(),
            'monitor': self.monitor.self_test(),
            'platform': self.self_test()
        }
        
        # Overall status
        all_passed = all(r['passed'] for r in results.values())
        results['overall'] = {
            'passed': all_passed,
            'message': 'All tests passed!' if all_passed else 'Some tests failed!'
        }
        
        return results
    
    def self_test(self) -> Dict[str, Any]:
        """Test platform integration"""
        tests_passed = []
        tests_failed = []
        
        # Test that components are wired correctly
        try:
            eval_id = str(uuid.uuid4())[:8]
            result = self.engine.execute("print('integration test')", eval_id)
            
            if result.get('status') == 'completed':
                tests_passed.append("Engine integration")
            else:
                tests_failed.append("Engine integration: execution failed")
                
        except Exception as e:
            tests_failed.append(f"Platform test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Aggregate all component test suites"""
        suite = unittest.TestSuite()
        suite.addTest(self.engine.get_test_suite())
        suite.addTest(self.monitor.get_test_suite())
        return suite
    
    def evaluate(self, code: str) -> dict:
        """Execute evaluation"""
        eval_id = str(uuid.uuid4())[:8]
        self.monitor.emit_event(eval_id, 'info', 'Starting evaluation')
        result = self.engine.execute(code, eval_id)
        self.monitor.emit_event(eval_id, 'complete', 'Evaluation complete')
        return result

# Global platform
platform = None

# ============== HTML WITH TEST RESULTS ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Testable Architecture</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        .test-results { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .test-passed { color: #28a745; }
        .test-failed { color: #dc3545; }
        .component-test { margin: 10px 0; padding: 10px; background: white; border: 1px solid #dee2e6; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Testing as First-Class Citizen</h1>
    
    <div class="warning">
        <h2>Testing is NOT Optional!</h2>
        <p><strong>Why testing is first-class in AI evaluation:</strong></p>
        <ul>
            <li>Untested isolation = Potential AI escape</li>
            <li>Untested monitoring = Invisible deception</li>
            <li>Untested limits = Resource exhaustion attacks</li>
            <li>Every component MUST prove it works correctly</li>
        </ul>
    </div>
    
    <div class="test-results">
        <h2>Component Test Results</h2>
        <div id="test-results"></div>
    </div>
    
    <h3>Run Evaluation</h3>
    <textarea id="code">print("Testing the testable platform!")
    
# This platform has been tested for:
# - Basic execution
# - Timeout handling  
# - Error handling
# - Network isolation (Docker only)
# - Filesystem protection (Docker only)</textarea>
    <br><br>
    <button onclick="runEval()">Run Evaluation</button>
    <button onclick="runFullTests()">Run Full Test Suite</button>
    
    <div id="result"></div>
    
    <script>
        // Show test results on load
        fetch('/test-results').then(r => r.json()).then(showTestResults);
        
        function showTestResults(results) {
            let html = '';
            for (const [component, result] of Object.entries(results)) {
                if (component === 'overall') continue;
                
                const status = result.passed ? 
                    '<span class="test-passed">✓ PASSED</span>' : 
                    '<span class="test-failed">✗ FAILED</span>';
                
                html += `<div class="component-test">
                    <h3>${component.toUpperCase()} ${status}</h3>
                    <p>${result.message}</p>`;
                
                if (result.tests_passed && result.tests_passed.length > 0) {
                    html += '<p><strong>Passed:</strong> ' + result.tests_passed.join(', ') + '</p>';
                }
                if (result.tests_failed && result.tests_failed.length > 0) {
                    html += '<p class="test-failed"><strong>Failed:</strong> ' + result.tests_failed.join(', ') + '</p>';
                }
                
                html += '</div>';
            }
            
            // Overall status
            const overall = results.overall;
            const overallClass = overall.passed ? 'test-passed' : 'test-failed';
            html = `<h3 class="${overallClass}">${overall.message}</h3>` + html;
            
            document.getElementById('test-results').innerHTML = html;
        }
        
        async function runEval() {
            const code = document.getElementById('code').value;
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const result = await response.json();
            document.getElementById('result').innerHTML = `
                <h3>Result:</h3>
                <pre>${JSON.stringify(result, null, 2)}</pre>
            `;
        }
        
        async function runFullTests() {
            document.getElementById('result').innerHTML = '<p>Running full test suite...</p>';
            
            const response = await fetch('/run-tests');
            const result = await response.json();
            
            document.getElementById('result').innerHTML = `
                <h3>Full Test Suite Results:</h3>
                <pre>${result.output}</pre>
                <p><strong>Tests run:</strong> ${result.tests_run}</p>
                <p><strong>Failures:</strong> ${result.failures}</p>
            `;
        }
    </script>
</body>
</html>
"""

class TestableHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path == '/test-results':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(platform.test_results).encode())
            
        elif self.path == '/run-tests':
            # Run full unittest suite
            suite = platform.get_test_suite()
            runner = unittest.TextTestRunner(stream=StringIO())
            result = runner.run(suite)
            
            response = {
                'output': runner.stream.getvalue(),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'success': result.wasSuccessful()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/eval':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            result = platform.evaluate(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    import sys
    
    # Choose engine
    if '--unsafe' in sys.argv:
        print("WARNING: Running with UNSAFE subprocess execution!")
        engine = SubprocessEngine()
    else:
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            engine = DockerEngine()
            print("Using Docker engine with safety tests")
        except:
            print("Docker not available, using subprocess")
            engine = SubprocessEngine()
    
    # Create testable platform
    monitor = InMemoryMonitor()
    platform = TestableEvaluationPlatform(engine, monitor)
    
    # Show test results
    print("\n" + "="*50)
    print("COMPONENT TEST RESULTS")
    print("="*50)
    for component, result in platform.test_results.items():
        if component != 'overall':
            status = "PASSED" if result['passed'] else "FAILED"
            print(f"{component.upper()}: {status} - {result['message']}")
    print("="*50)
    print(f"OVERALL: {platform.test_results['overall']['message']}")
    print("="*50 + "\n")
    
    # SAFETY: Refuse to start if tests fail
    if not platform.test_results['overall']['passed']:
        print("❌ REFUSING TO START: Platform tests failed!")
        print("A safety-critical evaluation platform MUST pass all tests before operation.")
        print("Fix the failing tests and try again.")
        sys.exit(1)
    
    server = HTTPServer(('localhost', 8000), TestableHandler)
    print("✅ All tests passed! Starting server...")
    print("Testable Crucible Platform at http://localhost:8000")
    print("Every component has been tested before serving requests!")
    server.serve_forever()