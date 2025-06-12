#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Docker Version with First Abstraction
Evolution: We felt the pain of duplication, so we extracted ExecutionEngine

Run with: python extreme_mvp_docker_v2.py [--unsafe]
Then open: http://localhost:8000

This version introduces our first abstraction after feeling the pain of
copying code between extreme_mvp.py and extreme_mvp_docker.py
Testing remains fundamental - TestableComponent is still our base
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import uuid
import tempfile
import os
import sys
import unittest
from abc import ABC, abstractmethod
from typing import Dict, Any

# In-memory "database" 
evaluations = {}

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

# ============== OUR FIRST ABSTRACTION ==============
# We were copying too much code between subprocess and docker versions!
# This abstraction emerged from that pain.

class ExecutionEngine(ABC, TestableComponent):
    """
    Abstract interface for code execution.
    Born from the pain of duplicating execution logic.
    """
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        """Execute code and return result with status and output"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Describe this engine for the UI"""
        pass

class SubprocessEngine(ExecutionEngine):
    """Direct subprocess execution - UNSAFE but simple"""
    
    def execute(self, code: str, eval_id: str) -> dict:
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
                'output': result.stdout or result.stderr,
                'engine': 'subprocess (UNSAFE!)'
            }
        except subprocess.TimeoutExpired:
            return {
                'id': eval_id,
                'status': 'timeout',
                'error': 'Evaluation timed out after 5 seconds',
                'engine': 'subprocess'
            }
        except Exception as e:
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'engine': 'subprocess'
            }
    
    def get_description(self) -> str:
        return "Subprocess (UNSAFE - Direct execution on host)"
    
    def self_test(self) -> Dict[str, Any]:
        """Test basic subprocess execution"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Basic execution
        try:
            result = self.execute("print('test')", "test-1")
            if result['status'] == 'completed' and 'test' in result['output']:
                tests_passed.append("Basic execution")
            else:
                tests_failed.append("Basic execution failed")
        except Exception as e:
            tests_failed.append(f"Basic execution: {str(e)}")
        
        # Test 2: Timeout handling
        try:
            result = self.execute("import time; time.sleep(10)", "test-2")
            if result['status'] == 'timeout':
                tests_passed.append("Timeout handling")
            else:
                tests_failed.append("Timeout didn't trigger")
        except Exception as e:
            tests_failed.append(f"Timeout test: {str(e)}")
        
        # Test 3: Filesystem access (should work - that's the danger!)
        try:
            result = self.execute("import os; print(os.path.exists('/'))", "test-3")
            if result['status'] == 'completed' and 'True' in result['output']:
                tests_passed.append("Filesystem access (DANGER!)")
            else:
                tests_failed.append("Filesystem test unexpected result")
        except Exception as e:
            tests_failed.append(f"Filesystem test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return test suite for subprocess engine"""
        class SubprocessTests(unittest.TestCase):
            def setUp(self):
                self.engine = SubprocessEngine()
            
            def test_basic_execution(self):
                result = self.engine.execute("print('hello')", "test")
                self.assertEqual(result['status'], 'completed')
                self.assertIn('hello', result['output'])
            
            def test_filesystem_access(self):
                # This SHOULD work - showing the danger
                result = self.engine.execute("import os; print(os.getcwd())", "test")
                self.assertEqual(result['status'], 'completed')
                self.assertTrue(len(result['output']) > 0)
        
        return unittest.TestLoader().loadTestsFromTestCase(SubprocessTests)

class DockerEngine(ExecutionEngine):
    """Docker containerized execution - Safer but requires Docker"""
    
    def execute(self, code: str, eval_id: str) -> dict:
        # Create temporary file with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Docker command with safety flags
            docker_cmd = [
                'docker', 'run',
                '--rm',                      # Remove container after exit
                '--network', 'none',         # No network access
                '--memory', '100m',          # Memory limit
                '--cpus', '0.5',            # CPU limit
                '--read-only',              # Read-only filesystem
                '-v', f'{temp_file}:/code.py:ro',  # Mount code file read-only
                'python:3.11-slim',         # Minimal Python image
                'python', '/code.py'
            ]
            
            # Run with timeout
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'id': eval_id,
                'status': 'completed',
                'output': result.stdout or result.stderr,
                'engine': 'docker (sandboxed)'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'id': eval_id,
                'status': 'timeout',
                'error': 'Evaluation timed out after 30 seconds',
                'engine': 'docker'
            }
        except subprocess.CalledProcessError as e:
            return {
                'id': eval_id,
                'status': 'error',
                'error': f'Docker error: {e.stderr}',
                'engine': 'docker'
            }
        except Exception as e:
            return {
                'id': eval_id,
                'status': 'error',
                'error': f'System error: {str(e)}',
                'engine': 'docker'
            }
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def get_description(self) -> str:
        return "Docker (Containerized - Isolated from host)"
    
    def self_test(self) -> Dict[str, Any]:
        """Test Docker isolation features"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Basic Docker execution
        try:
            result = self.execute("print('docker test')", "test-1")
            if result['status'] == 'completed' and 'docker test' in result['output']:
                tests_passed.append("Docker execution")
            else:
                tests_failed.append("Docker execution failed")
        except Exception as e:
            tests_failed.append(f"Docker execution: {str(e)}")
        
        # Test 2: Network isolation
        try:
            result = self.execute("import urllib.request; urllib.request.urlopen('http://google.com')", "test-2")
            if result['status'] in ['failed', 'error'] or 'Network is unreachable' in result.get('output', ''):
                tests_passed.append("Network isolation")
            else:
                tests_failed.append("Network not properly isolated!")
        except Exception as e:
            tests_failed.append(f"Network test: {str(e)}")
        
        # Test 3: Filesystem is read-only
        try:
            result = self.execute("open('/tmp/test.txt', 'w').write('test')", "test-3")
            if result['status'] in ['failed', 'error'] or 'Read-only file system' in result.get('output', ''):
                tests_passed.append("Read-only filesystem")
            else:
                tests_failed.append("Filesystem not read-only!")
        except Exception as e:
            tests_failed.append(f"Filesystem test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return test suite for Docker engine"""
        class DockerTests(unittest.TestCase):
            def setUp(self):
                self.engine = DockerEngine()
            
            def test_basic_execution(self):
                result = self.engine.execute("print('hello docker')", "test")
                self.assertEqual(result['status'], 'completed')
                self.assertIn('hello docker', result['output'])
            
            def test_network_blocked(self):
                result = self.engine.execute(
                    "import urllib.request; urllib.request.urlopen('http://example.com')",
                    "test"
                )
                self.assertNotEqual(result['status'], 'completed')
            
            def test_filesystem_readonly(self):
                result = self.engine.execute(
                    "with open('/test.txt', 'w') as f: f.write('test')",
                    "test"
                )
                self.assertNotEqual(result['status'], 'completed')
        
        return unittest.TestLoader().loadTestsFromTestCase(DockerTests)

# ============== PLATFORM USING THE ABSTRACTION ==============
# Now our main code doesn't care which engine we use!

class EvaluationPlatform(TestableComponent):
    def __init__(self, engine: ExecutionEngine):
        self.engine = engine
    
    def evaluate(self, code: str) -> dict:
        eval_id = str(uuid.uuid4())[:8]
        result = self.engine.execute(code, eval_id)
        evaluations[eval_id] = result
        return result
    
    def self_test(self) -> Dict[str, Any]:
        """Test platform integration"""
        # Platform tests rely on engine tests
        engine_results = self.engine.self_test()
        return {
            'passed': engine_results['passed'],
            'tests_passed': ['Platform configured'] if engine_results['passed'] else [],
            'tests_failed': [] if engine_results['passed'] else ['Engine tests failed'],
            'message': f"Platform using {self.engine.get_description()}"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return combined test suite"""
        return self.engine.get_test_suite()

# Global platform instance (will be configured at startup)
platform = None

# ============== HTML INTERFACE ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - First Abstraction</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; }
        textarea { width: 100%; height: 150px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .info { background: #17a2b8; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .warning { background: #ffc107; color: #000; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .engine-info { background: #e8f4f8; padding: 10px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Now with Abstractions!</h1>
    
    <div class="info">
        <h2>&#127775; First Abstraction: ExecutionEngine</h2>
        <p><strong>Why we added it:</strong> We were copying execution code between versions!</p>
        <p><strong>What it enables:</strong> Swap between subprocess and Docker with a flag</p>
        <p><strong>Future:</strong> Easy to add Kubernetes, gVisor, Firecracker...</p>
    </div>
    
    <div class="engine-info">
        <strong>Current Engine:</strong> <span id="engine-name">Loading...</span>
    </div>
    
    <p>Submit Python code for evaluation:</p>
    
    <textarea id="code" placeholder="print('Hello from abstracted platform!')">print('Hello from abstracted platform!')

# This behaves differently based on engine:
# - Subprocess: Can access your files (dangerous!)
# - Docker: Isolated in container

import os
print(f"Current directory: {os.getcwd()}")
print(f"Can I read /etc/passwd? Let's try...")
try:
    with open('/etc/passwd', 'r') as f:
        print("YES - I can read it!")
        print(f.read()[:100] + "...")
except Exception as e:
    print(f"NO - {e}")</textarea>
    <br><br>
    <button onclick="runEval()">Run Evaluation</button>
    
    <div id="result"></div>
    
    <script>
        // Get current engine info
        fetch('/engine-info').then(r => r.json()).then(data => {
            document.getElementById('engine-name').textContent = data.engine;
        });
        
        async function runEval() {
            const code = document.getElementById('code').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<p>Running...</p>';
            
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const result = await response.json();
            
            resultDiv.innerHTML = `
                <h3>Result:</h3>
                <p><strong>ID:</strong> ${result.id}</p>
                <p><strong>Status:</strong> ${result.status}</p>
                <p><strong>Engine:</strong> ${result.engine}</p>
                <pre>${result.output || result.error || 'No output'}</pre>
            `;
        }
    </script>
</body>
</html>
"""

class EvalHandler(BaseHTTPRequestHandler, TestableComponent):
    """HTTP handler that delegates to the platform"""
    
    def self_test(self) -> Dict[str, Any]:
        """Handler testing is minimal - delegates to platform"""
        return {
            'passed': True,
            'tests_passed': ['Handler configured'],
            'tests_failed': [],
            'message': 'Handler ready'
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return empty suite - real tests are in platform/engine"""
        return unittest.TestSuite()
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path == '/engine-info':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'engine': platform.engine.get_description()
            }).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/eval':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            code = data.get('code', '')
            result = platform.evaluate(code)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    # Check test level from environment (default: FULL for safety)
    test_level = os.environ.get('CRUCIBLE_TEST_LEVEL', 'FULL')
    
    # In production, override any attempts to skip tests
    if os.environ.get('PRODUCTION') == 'true' and test_level != 'FULL':
        print("ERROR: Test overrides are FORBIDDEN in production!")
        print("AI safety requires continuous verification.")
        sys.exit(1)
    
    # Choose engine based on command line flag
    if '--unsafe' in sys.argv:
        print("WARNING: Running with UNSAFE subprocess execution!")
        print("   Your files are at risk! Use for demonstration only.")
        engine = SubprocessEngine()
    else:
        # Try Docker first
        print("Checking Docker availability...")
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            print("Docker is available")
            
            # Pull Python image if needed
            print("Ensuring Python Docker image is available...")
            subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
            
            engine = DockerEngine()
            print("Using Docker engine for safer execution")
        except:
            print("Docker not found. Please install Docker for safe execution.")
            print("   Run with --unsafe flag to use subprocess (DANGEROUS!)")
            sys.exit(1)
    
    # Create platform with chosen engine
    platform = EvaluationPlatform(engine)
    
    if test_level == 'FULL':
        print("\nRunning FULL test suite (default for safety)...")
        
        # Run engine tests
        engine_results = engine.self_test()
        print(f"Engine ({engine.get_description()}):", engine_results['message'])
        
        # Run comprehensive test suite
        suite = engine.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if not result.wasSuccessful() or not engine_results['passed']:
            print("\n" + "="*70)
            print("FATAL: Tests FAILED!")
            print("Platform safety not verified.")
            print("To skip tests (DANGEROUS): CRUCIBLE_TEST_LEVEL=QUICK python extreme_mvp_docker_v2.py")
            print("="*70)
            sys.exit(1)
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED - Platform verified")
        print("="*50 + "\n")
        
    elif test_level == 'QUICK':
        print("="*70)
        print("WARNING: Running only quick tests (UNSAFE MODE)")
        print("="*70 + "\n")
        
        # Run only self-tests
        test_results = platform.self_test()
        print("Quick test results:", test_results['message'])
        
    elif test_level == 'NONE':
        print("="*70)
        print("DANGER: All tests skipped!")
        print("Platform safety is UNVERIFIED!")
        print("="*70)
        input("\nPress Enter to continue at your own risk...")
    
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print(f"Crucible Platform running at http://localhost:8000")
    print(f"Engine: {engine.get_description()}")
    print(f"Test level: {test_level}")
    print("Press Ctrl+C to stop")
    server.serve_forever()