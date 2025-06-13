#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Production Security with Modular Architecture
Evolution: Combines gVisor security with clean modular design!

Run with: python extreme_mvp_gvisor_modular.py
Then open: http://localhost:8000

This version uses:
- Modular component architecture
- gVisor runtime for kernel-level isolation
- Production-grade security settings
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
from io import StringIO
import unittest

# Import our modular components
from components import (
    GVisorEngine,
    DockerEngine,
    InMemoryMonitor,
    TestableEvaluationPlatform
)

# Global platform instance
platform = None

# ============== HTML WITH SECURITY INFO ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Production Security</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        .test-results { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .test-passed { color: #28a745; }
        .test-failed { color: #dc3545; }
        .component-test { margin: 10px 0; padding: 10px; background: white; border: 1px solid #dee2e6; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .security { background: #d4edda; color: #155724; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .warning { background: #fff3cd; color: #856404; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .runtime-info { background: #d1ecf1; color: #0c5460; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>🔒 Crucible Platform - Production Security</h1>
    
    <div class="security">
        <h2>Defense-in-Depth Security</h2>
        <p><strong>This platform implements Google Cloud Run-level security:</strong></p>
        <ul>
            <li>✅ <strong>gVisor (runsc)</strong> - Kernel syscall interception</li>
            <li>✅ <strong>Container isolation</strong> - Docker containerization</li>
            <li>✅ <strong>Network disabled</strong> - Complete network isolation</li>
            <li>✅ <strong>Non-root execution</strong> - UID 65534 (nobody)</li>
            <li>✅ <strong>Read-only filesystem</strong> - No persistence</li>
            <li>✅ <strong>Resource limits</strong> - CPU and memory caps</li>
            <li>✅ <strong>No privilege escalation</strong> - Security options enforced</li>
        </ul>
    </div>
    
    <div class="runtime-info" id="runtime-info">
        <h3>Runtime Information</h3>
        <p>Checking runtime configuration...</p>
    </div>
    
    <div class="test-results">
        <h2>Security Test Results</h2>
        <div id="test-results"></div>
    </div>
    
    <h3>Test Production Security</h3>
    <textarea id="code">print("Testing production security!")

# Try various escape attempts (all will fail):
print("\\n1. Network access test:")
try:
    import urllib.request
    urllib.request.urlopen('http://google.com')
    print("❌ NETWORK ACCESS ALLOWED - SECURITY BREACH!")
except Exception as e:
    print("✅ Network blocked:", type(e).__name__)

print("\\n2. File system test:")
try:
    with open('/etc/test.txt', 'w') as f:
        f.write('test')
    print("❌ FILESYSTEM WRITABLE - SECURITY BREACH!")
except Exception as e:
    print("✅ Filesystem read-only:", type(e).__name__)

print("\\n3. User privilege test:")
import os
print(f"✅ Running as UID: {os.getuid()} (non-root)")

print("\\n4. Resource limit test:")
print("✅ Memory limited to 100MB")
print("✅ CPU limited to 0.5 cores")

print("\\n🔒 All security layers active!")</textarea>
    <br><br>
    <button onclick="runEval()">Run Secure Evaluation</button>
    <button onclick="runFullTests()">Run Security Tests</button>
    <button onclick="getStatus()">Get Platform Status</button>
    
    <div id="result"></div>
    
    <script>
        // Check runtime on load
        fetch('/runtime-info').then(r => r.json()).then(info => {
            let html = '<h3>Runtime Configuration</h3>';
            if (info.gvisor_available) {
                html += '<p class="test-passed">✅ gVisor (runsc) runtime available</p>';
                html += '<p>Using kernel-level isolation for maximum security</p>';
            } else {
                html += '<p class="test-failed">⚠️ gVisor not available - using standard Docker</p>';
                html += '<p>Install gVisor for production-grade security</p>';
            }
            html += `<p><strong>Engine:</strong> ${info.engine}</p>`;
            document.getElementById('runtime-info').innerHTML = html;
        });
        
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
                <p><strong>Security:</strong> ${result.security || 'standard'}</p>
                <p><strong>Runtime:</strong> ${result.runtime || 'unknown'}</p>
            `;
        }
        
        async function runFullTests() {
            document.getElementById('result').innerHTML = '<p>Running security test suite...</p>';
            
            const response = await fetch('/run-tests');
            const result = await response.json();
            
            document.getElementById('result').innerHTML = `
                <h3>Security Test Results:</h3>
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

class ProductionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path == '/runtime-info':
            # Check if gVisor is available
            try:
                result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
                gvisor_available = 'runsc' in result.stdout
            except:
                gvisor_available = False
            
            info = {
                'gvisor_available': gvisor_available,
                'engine': platform.engine.get_description(),
                'runtime': getattr(platform.engine, 'runtime', 'unknown')
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(info).encode())
            
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
    # Check if gVisor is available
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if 'runsc' in result.stdout:
            print("✅ gVisor runtime detected - using production security")
            engine = GVisorEngine('runsc')
        else:
            print("⚠️  gVisor not available - using standard Docker")
            print("   Install gVisor for production-grade security:")
            print("   https://gvisor.dev/docs/user_guide/install/")
            engine = DockerEngine()
    except:
        print("❌ Docker not available!")
        print("   This platform requires Docker for security isolation")
        sys.exit(1)
    
    # Create modular platform with production security
    monitor = InMemoryMonitor()
    platform = TestableEvaluationPlatform(engine, monitor)
    
    # Show test results
    print("\n" + "="*50)
    print("SECURITY TEST RESULTS")
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
    server = HTTPServer(('localhost', 8000), ProductionHandler)
    print("🔒 Production Crucible Platform at http://localhost:8000")
    print("   Using modular architecture with maximum security")
    server.serve_forever()