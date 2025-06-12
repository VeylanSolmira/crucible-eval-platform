#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Docker Sandboxed Version
First evolution: Replace subprocess.run() with Docker container execution

Run with: python extreme_mvp_docker.py
Then open: http://localhost:8000

Requirements: Docker must be installed and running
Testing is still fundamental - we inherit from TestableComponent
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

# HTML interface (updated with new safety message)
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Evaluation Platform - Docker Sandbox</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; }
        textarea { width: 100%; height: 150px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .warning { background: #ffc107; color: #000; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Now With Docker Sandboxing!</h1>
    
    <div class="warning">
        <h2>&#128640; First Safety Evolution: Container Isolation</h2>
        <p><strong>Code now runs in Docker, just like how we'd run LLM evaluations:</strong></p>
        <ul>
            <li>Isolated from host (your computer is safe)</li>
            <li>No network (can't exfiltrate data)</li>
            <li>Resource limits (can't DoS your system)</li>
        </ul>
        <p><strong>But notice what the code CAN still do:</strong></p>
        <ul>
            <li>Read container files (/etc/passwd works!)</li>
            <li>Execute complex computations</li>
            <li>Probe its environment for weaknesses</li>
        </ul>
        <p><strong>This mirrors LLM evaluation risks:</strong> Even in a container, an AI model can study its environment, craft exploits, and potentially find escape routes. That's why production systems need multiple layers (gVisor, VMs, monitoring).</p>
    </div>
    
    <p>Submit Python code for evaluation:</p>
    
    <textarea id="code" placeholder="print('Hello from Docker!')">print('Hello from Docker!')

# Check what we CAN access (surprise!):
print("\\n=== Reading /etc/passwd (this works!) ===")
with open('/etc/passwd', 'r') as f:
    print(f.read()[:200] + '...')  # First 200 chars

# What we CANNOT do:
print("\\n=== Trying to write files ===")
try:
    with open('/tmp/evil.txt', 'w') as f:
        f.write('gotcha!')
except Exception as e:
    print(f'Write blocked: {e}')

print("\\n=== Trying network access ===")
try:
    import urllib.request
    urllib.request.urlopen('http://google.com')
except Exception as e:
    print(f'Network blocked: {e}')</textarea>
    <br><br>
    <button onclick="runEval()">Run in Docker Container</button>
    
    <div id="result"></div>
    
    <script>
        async function runEval() {
            const code = document.getElementById('code').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<p>Creating container and running...</p>';
            
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
                <p><strong>Container:</strong> ${result.container || 'N/A'}</p>
                <pre>${result.output || result.error || 'No output'}</pre>
            `;
        }
    </script>
</body>
</html>
"""

def run_in_docker(code, eval_id, timeout=5):
    """
    Run Python code in a Docker container with safety constraints.
    
    Safety features:
    - Read-only root filesystem
    - No network access
    - Memory limit (100MB)
    - CPU limit (0.5 cores)
    - Automatic removal after execution
    """
    
    # Create temporary file with the Python code
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
            timeout=timeout
        )
        
        # Clean up temp file
        os.unlink(temp_file)
        
        return {
            'status': 'completed',
            'output': result.stdout or result.stderr,
            'container': 'python:3.11-slim (isolated)'
        }
        
    except subprocess.TimeoutExpired:
        os.unlink(temp_file)
        return {
            'status': 'timeout',
            'error': f'Evaluation timed out after {timeout} seconds',
            'container': 'python:3.11-slim (killed)'
        }
    except subprocess.CalledProcessError as e:
        os.unlink(temp_file)
        return {
            'status': 'error',
            'error': f'Docker error: {e.stderr}',
            'container': 'python:3.11-slim (failed)'
        }
    except Exception as e:
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        return {
            'status': 'error',
            'error': f'System error: {str(e)}'
        }

class EvalHandler(BaseHTTPRequestHandler, TestableComponent):
    """
    HTTP handler with Docker execution support.
    Inherits testing requirements from TestableComponent.
    """
    
    def self_test(self) -> Dict[str, Any]:
        """Test Docker execution and safety features"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Docker is available
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            tests_passed.append("Docker available")
        except:
            tests_failed.append("Docker not available")
            return {
                'passed': False,
                'tests_passed': tests_passed,
                'tests_failed': tests_failed,
                'message': 'Docker is required but not available'
            }
        
        # Test 2: Basic Docker execution works
        try:
            result = run_in_docker("print('test')", "test-1")
            if result['status'] == 'completed' and 'test' in result['output']:
                tests_passed.append("Docker execution")
            else:
                tests_failed.append("Docker execution failed")
        except Exception as e:
            tests_failed.append(f"Docker execution: {str(e)}")
        
        # Test 3: Network isolation works
        try:
            result = run_in_docker("import urllib.request; urllib.request.urlopen('http://google.com')", "test-2")
            if result['status'] in ['failed', 'error'] and 'Network is unreachable' in result.get('output', ''):
                tests_passed.append("Network isolation")
            else:
                tests_failed.append("Network isolation: network access not blocked!")
        except Exception as e:
            tests_failed.append(f"Network isolation test: {str(e)}")
        
        # Test 4: Filesystem is read-only
        try:
            result = run_in_docker("open('/tmp/test.txt', 'w').write('test')", "test-3")
            if result['status'] in ['failed', 'error'] and 'Read-only file system' in result.get('output', ''):
                tests_passed.append("Read-only filesystem")
            else:
                tests_failed.append("Filesystem protection: writes not blocked!")
        except Exception as e:
            tests_failed.append(f"Filesystem test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return comprehensive test suite for Docker handler"""
        class DockerHandlerTests(unittest.TestCase):
            def test_docker_execution(self):
                result = run_in_docker("print('hello docker')", "test-1")
                self.assertEqual(result['status'], 'completed')
                self.assertIn('hello docker', result['output'])
            
            def test_network_blocked(self):
                result = run_in_docker(
                    "import urllib.request; urllib.request.urlopen('http://example.com')",
                    "test-net"
                )
                self.assertIn(result['status'], ['failed', 'error'])
                self.assertIn('Network is unreachable', result.get('output', ''))
            
            def test_filesystem_readonly(self):
                result = run_in_docker(
                    "with open('/test.txt', 'w') as f: f.write('test')",
                    "test-fs"
                )
                self.assertIn(result['status'], ['failed', 'error'])
                self.assertIn('Read-only file system', result.get('output', ''))
            
            def test_resource_limits(self):
                # Memory limit test - try to allocate 200MB (limit is 100MB)
                result = run_in_docker(
                    "data = 'x' * (200 * 1024 * 1024)",
                    "test-mem"
                )
                # Should fail due to memory limit
                self.assertIn(result['status'], ['failed', 'error', 'timeout'])
        
        return unittest.TestLoader().loadTestsFromTestCase(DockerHandlerTests)
    def do_GET(self):
        """Serve the HTML interface"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle evaluation requests"""
        if self.path == '/eval':
            # Read request
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            # Create evaluation
            eval_id = str(uuid.uuid4())[:8]
            code = data.get('code', '')
            
            # Check if Docker is available
            try:
                subprocess.run(['docker', '--version'], capture_output=True, check=True)
            except:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'id': eval_id,
                    'status': 'error',
                    'error': 'Docker not found. Please install Docker to use sandboxed execution.'
                }).encode())
                return
            
            # Run code in Docker
            result = run_in_docker(code, eval_id)
            result['id'] = eval_id
            
            # Store result
            evaluations[eval_id] = result
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

if __name__ == '__main__':
    # Check test level from environment (default: FULL for safety)
    test_level = os.environ.get('CRUCIBLE_TEST_LEVEL', 'FULL')
    
    # In production, override any attempts to skip tests
    if os.environ.get('PRODUCTION') == 'true' and test_level != 'FULL':
        print("ERROR: Test overrides are FORBIDDEN in production!")
        print("AI safety requires continuous verification.")
        sys.exit(1)
    
    # Check Docker availability first
    print("Checking Docker availability...")
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        print("✅ Docker is available")
    except:
        print("❌ Docker not found. Please install Docker first.")
        print("   Visit: https://docs.docker.com/get-docker/")
        sys.exit(1)
    
    # Pull Python image if not available
    print("Ensuring Python Docker image is available...")
    subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
    
    # Create handler for testing
    handler = EvalHandler(None, None, None)
    
    if test_level == 'FULL':
        print("\nRunning FULL test suite (default for safety)...")
        print("This ensures Docker isolation is working correctly.\n")
        
        # Run quick self-tests first
        self_test_results = handler.self_test()
        print("Quick diagnostics:", self_test_results['message'])
        
        if not self_test_results['passed']:
            print("\n" + "="*70)
            print("FATAL: Self-tests failed!")
            print("Docker safety features may not be working.")
            print("="*70)
            sys.exit(1)
        
        # Run comprehensive test suite
        suite = handler.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if not result.wasSuccessful():
            print("\n" + "="*70)
            print("FATAL: Test suite FAILED!")
            print("Docker isolation may be compromised.")
            print("To skip tests (DANGEROUS): CRUCIBLE_TEST_LEVEL=QUICK python extreme_mvp_docker.py")
            print("="*70)
            sys.exit(1)
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED - Docker isolation verified")
        print("="*50 + "\n")
        
    elif test_level == 'QUICK':
        print("="*70)
        print("WARNING: Running only quick tests (UNSAFE MODE)")
        print("Docker isolation not fully verified!")
        print("="*70 + "\n")
        
        # Run only self-tests
        test_results = handler.self_test()
        print("Quick test results:", test_results['message'])
        
        if not test_results['passed']:
            print("\nERROR: Even quick tests failed!")
            sys.exit(1)
            
    elif test_level == 'NONE':
        print("="*70)
        print("DANGER: All tests skipped!")
        print("Docker isolation is UNVERIFIED!")
        print("AI models could exploit untested vulnerabilities!")
        print("="*70)
        input("\nPress Enter to continue at your own risk...")
    
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print("🚀 Crucible Docker Sandbox running at http://localhost:8000")
    print("📦 Code execution is now containerized!")
    print(f"Test level: {test_level}")
    print("Press Ctrl+C to stop")
    server.serve_forever()