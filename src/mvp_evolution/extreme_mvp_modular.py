#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Modular Architecture
Evolution: Components are now properly separated for independent evolution!

Run with: python extreme_mvp_modular.py [--unsafe]
Then open: http://localhost:8000

This version demonstrates TRACE-AI principles with modular components.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
from io import StringIO
import unittest

# Import our modular components
from components import (
    SubprocessEngine,
    DockerEngine,
    InMemoryMonitor,
    TestableEvaluationPlatform
)

# Global platform instance
platform = None

# ============== HTML WITH TEST RESULTS ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Modular Architecture</title>
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
        .info { background: #d1ecf1; color: #0c5460; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Modular Architecture</h1>
    
    <div class="info">
        <h2>TRACE-AI Modular Design</h2>
        <p><strong>Components are now properly separated:</strong></p>
        <ul>
            <li><code>components.base</code> - Testable component foundation</li>
            <li><code>components.execution</code> - Execution engines (can become K8s jobs)</li>
            <li><code>components.monitoring</code> - Event tracking (can become OpenTelemetry)</li>
            <li><code>components.platform</code> - Orchestration (can become API service)</li>
        </ul>
        <p>Each component can evolve independently into microservices!</p>
    </div>
    
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
    <textarea id="code">print("Testing the modular platform!")

# This platform demonstrates TRACE-AI principles:
# - Testable components
# - Replaceable execution engines  
# - Abstracted monitoring
# - Composable architecture
# - Evolutionary design

import platform
print(f"Python: {platform.python_version()}")
print("Components can evolve independently!")</textarea>
    <br><br>
    <button onclick="runEval()">Run Evaluation</button>
    <button onclick="runFullTests()">Run Full Test Suite</button>
    <button onclick="getStatus()">Get Platform Status</button>
    
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
        
        async function getStatus() {
            const response = await fetch('/status');
            const result = await response.json();
            
            document.getElementById('result').innerHTML = `
                <h3>Platform Status:</h3>
                <pre>${JSON.stringify(result, null, 2)}</pre>
            `;
        }
    </script>
</body>
</html>
"""

class ModularHandler(BaseHTTPRequestHandler):
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
            
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(platform.get_status()).encode())
            
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
    # Choose engine based on arguments
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
    
    # Create modular platform
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
    
    # Ensure platform is healthy before starting
    platform.start_if_healthy()
    
    # Start server
    server = HTTPServer(('localhost', 8000), ModularHandler)
    print("Modular Crucible Platform at http://localhost:8000")
    print("Components are now properly separated for independent evolution!")
    server.serve_forever()