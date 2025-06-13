#!/usr/bin/env python3
"""
METR Evaluation Platform - Extreme MVP
Run with: python extreme_mvp.py
Then open: http://localhost:8000

Even the simplest MVP includes testing as a core abstraction.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import uuid
from urllib.parse import urlparse, parse_qs
from abc import ABC, abstractmethod
from typing import Dict, Any
import unittest
import os
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

# HTML interface
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>METR Extreme MVP</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; }
        textarea { width: 100%; height: 150px; font-family: monospace; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>Crucible Evaluation Platform - Extreme MVP</h1>
    
    <div style="background: #ff0000; color: white; padding: 15px; margin: 10px 0; border-radius: 5px;">
        <h2>&#9888; FUNDAMENTAL SAFETY WARNING &#9888;</h2>
        <p><strong>This platform executes ANY Python code you submit. It is UNSAFE by design.</strong></p>
        <p>This mirrors a core truth: evaluating AI models is inherently dangerous, even with state-of-the-art precautions.</p>
        <p>Just as this code could delete files or exfiltrate data, an advanced AI model could:</p>
        <ul style="margin: 5px 0;">
            <li>Attempt to deceive researchers about its capabilities</li>
            <li>Try to persist beyond its evaluation session</li>
            <li>Seek to manipulate human operators</li>
            <li>Hide dangerous behaviors until deployment</li>
        </ul>
        <p>We build safety measures not because we can eliminate risk, but because we must manage it.</p>
        <p>Learn more: 
            <a href="https://www.anthropic.com/index/core-views-on-ai-safety" style="color: #ffff00;">Anthropic AI Safety</a> | 
            <a href="https://www.alignmentforum.org/posts/pRkFkzwKZ2zfa3R6H/without-specific-countermeasures-the-easiest-path-to" style="color: #ffff00;">Deceptive AI Risks</a>
        </p>
    </div>
    
    <p>Submit Python code for evaluation:</p>
    
    <textarea id="code" placeholder="print('Hello, Crucible!')">print('Hello, Crucible!')</textarea>
    <br><br>
    <button onclick="runEval()">Run Evaluation</button>
    
    <div id="result"></div>
    
    <script>
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
                <pre>${result.output || result.error || 'No output'}</pre>
            `;
        }
    </script>
</body>
</html>
"""

class EvalHandler(BaseHTTPRequestHandler, TestableComponent):
    """
    HTTP handler that is also testable.
    This shows that ALL components should be testable from the start.
    """
    
    def self_test(self) -> Dict[str, Any]:
        """Test that the evaluation handler works correctly"""
        tests_passed = []
        tests_failed = []
        
        # Test 1: Can process valid Python code
        try:
            test_code = "print('test')"
            result = self._evaluate_code(test_code)
            if result['status'] == 'completed' and 'test' in result['output']:
                tests_passed.append("Basic evaluation")
            else:
                tests_failed.append("Basic evaluation: unexpected result")
        except Exception as e:
            tests_failed.append(f"Basic evaluation: {str(e)}")
        
        # Test 2: Handles timeout correctly
        try:
            timeout_code = "import time; time.sleep(10)"
            result = self._evaluate_code(timeout_code)
            if result['status'] == 'timeout':
                tests_passed.append("Timeout handling")
            else:
                tests_failed.append("Timeout handling: didn't timeout")
        except Exception as e:
            tests_failed.append(f"Timeout handling: {str(e)}")
        
        # Test 3: subprocess.run is UNSAFE (this should succeed, showing the danger)
        try:
            dangerous_code = "import os; print(os.path.exists('/'))"
            result = self._evaluate_code(dangerous_code)
            if result['status'] == 'completed' and 'True' in result['output']:
                tests_passed.append("Filesystem access (DANGER!)")
            else:
                tests_failed.append("Filesystem test failed")
        except Exception as e:
            tests_failed.append(f"Filesystem test: {str(e)}")
        
        return {
            'passed': len(tests_failed) == 0,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed,
            'message': f"Passed {len(tests_passed)}/{len(tests_passed) + len(tests_failed)} tests"
        }
    
    def get_test_suite(self) -> unittest.TestSuite:
        """Return unittest suite for the handler"""
        class HandlerTests(unittest.TestCase):
            def test_evaluation_creates_id(self):
                handler = EvalHandler(None, None, None)
                result = handler._evaluate_code("print('test')")
                self.assertIn('id', result)
                self.assertEqual(len(result['id']), 8)
            
            def test_timeout_is_enforced(self):
                handler = EvalHandler(None, None, None)
                result = handler._evaluate_code("import time; time.sleep(10)")
                self.assertEqual(result['status'], 'timeout')
            
            def test_unsafe_file_access(self):
                # This test PASSES to show the danger!
                handler = EvalHandler(None, None, None)
                result = handler._evaluate_code("import os; print(os.getcwd())")
                self.assertEqual(result['status'], 'completed')
                self.assertTrue(len(result['output']) > 0)
        
        return unittest.TestLoader().loadTestsFromTestCase(HandlerTests)
    
    def _evaluate_code(self, code: str) -> dict:
        """Extract evaluation logic for testing"""
        eval_id = str(uuid.uuid4())[:8]
        
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            evaluation = {
                'id': eval_id,
                'status': 'completed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            evaluation = {
                'id': eval_id,
                'status': 'timeout',
                'error': 'Evaluation timed out after 5 seconds'
            }
        except Exception as e:
            evaluation = {
                'id': eval_id,
                'status': 'error',
                'error': str(e)
            }
        
        evaluations[eval_id] = evaluation
        return evaluation
    
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
            
            # Use the testable evaluation method
            code = data.get('code', '')
            evaluation = self._evaluate_code(code)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(evaluation).encode())
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
    
    handler = EvalHandler(None, None, None)
    
    if test_level == 'FULL':
        print("Running FULL test suite (default for safety)...")
        print("This ensures all safety measures are working correctly.\n")
        
        # Run quick self-tests first
        self_test_results = handler.self_test()
        print("Quick diagnostics:", self_test_results['message'])
        
        # Run comprehensive test suite
        suite = handler.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        if not result.wasSuccessful():
            print("\n" + "="*70)
            print("FATAL: Test suite FAILED!")
            print("Platform will NOT start with failing tests.")
            print("This is a safety-critical system - all tests must pass.")
            print("To skip tests (DANGEROUS): CRUCIBLE_TEST_LEVEL=QUICK python extreme_mvp.py")
            print("="*70)
            sys.exit(1)
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED - Platform is ready")
        print("="*50 + "\n")
        
    elif test_level == 'QUICK':
        print("="*70)
        print("WARNING: Running only quick tests (UNSAFE MODE)")
        print("Full safety verification skipped!")
        print("AI models could exploit untested vulnerabilities!")
        print("="*70 + "\n")
        
        # Run only self-tests
        test_results = handler.self_test()
        print("Quick test results:", test_results['message'])
        
    elif test_level == 'NONE':
        print("="*70)
        print("DANGER: All tests skipped!")
        print("This is EXTREMELY UNSAFE for AI evaluation!")
        print("The platform could have critical vulnerabilities!")
        print("="*70)
        input("\nPress Enter to continue at your own risk...")
    
    else:
        print(f"ERROR: Unknown test level '{test_level}'")
        print("Valid options: FULL (default), QUICK, NONE")
        sys.exit(1)
    
    # Show warning if filesystem access works (subprocess mode)
    if hasattr(handler, 'self_test'):
        results = handler.self_test()
        if "Filesystem access (DANGER!)" in results.get('tests_passed', []):
            print("\n" + "!"*70)
            print("CRITICAL WARNING: Filesystem access test PASSED!")
            print("This means code can access your files - the platform is UNSAFE!")
            print("This is why we need Docker isolation in production.")
            print("!"*70 + "\n")
    
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print("🚀 METR Extreme MVP running at http://localhost:8000")
    print(f"Test level: {test_level}")
    print("Press Ctrl+C to stop")
    server.serve_forever()