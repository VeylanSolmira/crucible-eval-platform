#!/usr/bin/env python3
"""
Demo script showing how to use the new API component.
This demonstrates the flexibility and modularity of the API design.
"""

import time
import requests
import json
from components import (
    SubprocessEngine,
    DockerEngine,
    TaskQueue,
    AdvancedMonitor,
    QueuedEvaluationPlatform,
    create_api,
    RESTfulAPI
)

# Custom HTML UI
CUSTOM_UI = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - API Component Demo</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
            max-width: 1200px; 
            margin: 40px auto; 
            padding: 0 20px;
            background: #f5f7fa;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .container { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .card h3 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 10px;
        }
        textarea { 
            width: 100%; 
            height: 150px; 
            font-family: 'Monaco', 'Menlo', monospace; 
            font-size: 13px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
        }
        button { 
            background: #667eea; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 4px;
            cursor: pointer; 
            margin: 5px; 
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }
        button:hover { 
            background: #5a67d8; 
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status { 
            background: #f8f9fa; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 4px;
            border-left: 4px solid #28a745;
            font-family: monospace;
            font-size: 13px;
        }
        .status.error {
            border-left-color: #dc3545;
            background: #fff5f5;
        }
        pre { 
            background: #f5f5f5; 
            padding: 10px; 
            overflow-x: auto;
            border-radius: 4px;
            font-size: 13px;
            line-height: 1.4;
        }
        .info { 
            background: #e3f2fd; 
            color: #1565c0; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 4px;
            border-left: 4px solid #1976d2;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 15px;
        }
        .metric {
            text-align: center;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        }
        .metric .value {
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }
        .metric .label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
        .endpoint-list {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
        }
        .endpoint {
            margin: 8px 0;
            font-family: monospace;
            font-size: 13px;
        }
        .endpoint .method {
            display: inline-block;
            width: 60px;
            padding: 2px 6px;
            border-radius: 3px;
            text-align: center;
            font-weight: bold;
            font-size: 11px;
        }
        .endpoint .method.get { background: #61affe; color: white; }
        .endpoint .method.post { background: #49cc90; color: white; }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            vertical-align: middle;
            margin-left: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Crucible Platform - API Component Demo</h1>
        <p>Modular, testable API architecture with support for multiple web frameworks</p>
    </div>
    
    <div class="info">
        <strong>New API Component Features:</strong>
        <ul style="margin: 10px 0;">
            <li>✅ Framework-agnostic design (supports http.server, FastAPI, Flask)</li>
            <li>✅ RESTful conventions with proper HTTP methods</li>
            <li>✅ Comprehensive error handling and validation</li>
            <li>✅ Built-in CORS support for browser access</li>
            <li>✅ Extensible route registration system</li>
            <li>✅ Full test coverage with unittest integration</li>
        </ul>
    </div>
    
    <div class="container">
        <div class="card">
            <h3>📝 Code Evaluation</h3>
            <textarea id="code" placeholder="Enter Python code to evaluate...">import time
import sys

print("API Component Demo")
print(f"Python {sys.version}")

# Simulate some work
for i in range(3):
    print(f"Processing step {i+1}/3...")
    time.sleep(0.5)

# Test isolation
try:
    import requests
    print("❌ Network access allowed!")
except:
    print("✅ Network properly isolated")

print("Evaluation complete!")</textarea>
            <div style="margin-top: 15px;">
                <button onclick="evaluateSync()">🔄 Evaluate (Sync)</button>
                <button onclick="evaluateAsync()">⚡ Evaluate (Async)</button>
                <button onclick="testEndpoints()">🧪 Test All Endpoints</button>
            </div>
            <div id="result"></div>
        </div>
        
        <div class="card">
            <h3>📊 Platform Status</h3>
            <div class="metrics" id="metrics">
                <div class="metric">
                    <div class="value">-</div>
                    <div class="label">Queued</div>
                </div>
                <div class="metric">
                    <div class="value">-</div>
                    <div class="label">Running</div>
                </div>
                <div class="metric">
                    <div class="value">-</div>
                    <div class="label">Completed</div>
                </div>
                <div class="metric">
                    <div class="value">-</div>
                    <div class="label">Failed</div>
                </div>
            </div>
            
            <h4 style="margin-top: 20px;">Available Endpoints</h4>
            <div class="endpoint-list">
                <div class="endpoint">
                    <span class="method get">GET</span> <code>/</code> - Web UI (this page)
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span> <code>/eval</code> - Synchronous evaluation
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span> <code>/eval-async</code> - Asynchronous evaluation
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span> <code>/eval-status/{eval_id}</code> - Get evaluation status
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span> <code>/status</code> - Platform health/status
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span> <code>/queue-status</code> - Queue statistics
                </div>
            </div>
            
            <div id="platform-status" style="margin-top: 20px;"></div>
        </div>
    </div>
    
    <div class="card">
        <h3>🧪 API Test Results</h3>
        <div id="test-results"></div>
    </div>
    
    <script>
        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus();
        
        async function evaluateSync() {
            const code = document.getElementById('code').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<div class="status">Evaluating synchronously... <span class="loading"></span></div>';
            
            try {
                const response = await fetch('/eval', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code})
                });
                
                const result = await response.json();
                
                if (result.success) {
                    resultDiv.innerHTML = `
                        <div class="status">
                            <strong>✅ Synchronous Evaluation Complete</strong>
                            <pre>${result.output || 'No output'}</pre>
                            ${result.error ? `<div style="color: red;">Error: ${result.error}</div>` : ''}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="status error">
                            <strong>❌ Evaluation Failed</strong>
                            <pre>${result.error || 'Unknown error'}</pre>
                        </div>
                    `;
                }
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="status error">
                        <strong>❌ Request Failed</strong>
                        <pre>${error.message}</pre>
                    </div>
                `;
            }
        }
        
        async function evaluateAsync() {
            const code = document.getElementById('code').value;
            const resultDiv = document.getElementById('result');
            
            resultDiv.innerHTML = '<div class="status">Submitting for async evaluation... <span class="loading"></span></div>';
            
            try {
                const response = await fetch('/eval-async', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code})
                });
                
                const result = await response.json();
                
                resultDiv.innerHTML = `
                    <div class="status">
                        <strong>📋 Async Evaluation Submitted</strong><br>
                        Evaluation ID: <code>${result.eval_id}</code><br>
                        Status: ${result.status}
                    </div>
                `;
                
                // Poll for results
                pollEvaluationStatus(result.eval_id, resultDiv);
                
            } catch (error) {
                resultDiv.innerHTML = `
                    <div class="status error">
                        <strong>❌ Request Failed</strong>
                        <pre>${error.message}</pre>
                    </div>
                `;
            }
        }
        
        async function pollEvaluationStatus(evalId, resultDiv) {
            const pollInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/eval-status/${evalId}`);
                    const status = await response.json();
                    
                    if (status.status === 'completed' || status.status === 'failed') {
                        clearInterval(pollInterval);
                        
                        if (status.result) {
                            resultDiv.innerHTML = `
                                <div class="status">
                                    <strong>✅ Async Evaluation Complete</strong><br>
                                    Evaluation ID: <code>${evalId}</code>
                                    <pre>${status.result.output || 'No output'}</pre>
                                    ${status.result.error ? `<div style="color: red;">Error: ${status.result.error}</div>` : ''}
                                </div>
                            `;
                        } else {
                            resultDiv.innerHTML = `
                                <div class="status error">
                                    <strong>❌ Evaluation Failed</strong><br>
                                    Status: ${status.status}
                                </div>
                            `;
                        }
                    }
                } catch (error) {
                    clearInterval(pollInterval);
                    resultDiv.innerHTML += `<div style="color: red;">Polling error: ${error.message}</div>`;
                }
            }, 1000);
        }
        
        async function updateStatus() {
            try {
                // Update queue status
                const queueResponse = await fetch('/queue-status');
                const queueData = await queueResponse.json();
                
                if (queueData.queue) {
                    const metrics = document.querySelectorAll('.metric .value');
                    metrics[0].textContent = queueData.queue.queued || 0;
                    metrics[1].textContent = queueData.queue.running || 0;
                    metrics[2].textContent = queueData.queue.completed || 0;
                    metrics[3].textContent = queueData.queue.failed || 0;
                }
                
                // Update platform status
                const statusResponse = await fetch('/status');
                const statusData = await statusResponse.json();
                
                let statusHtml = '<h4>Platform Components</h4>';
                statusHtml += '<div style="font-family: monospace; font-size: 13px;">';
                
                if (statusData.components) {
                    for (const [name, comp] of Object.entries(statusData.components)) {
                        const icon = comp.healthy ? '✅' : '❌';
                        statusHtml += `<div>${icon} ${name}: ${comp.component || 'Unknown'}</div>`;
                    }
                }
                
                statusHtml += `<div style="margin-top: 10px;">`;
                statusHtml += `<strong>Engine:</strong> ${statusData.engine || 'Unknown'}<br>`;
                statusHtml += `<strong>Version:</strong> ${statusData.version || '1.0.0'}<br>`;
                statusHtml += `<strong>Health:</strong> ${statusData.healthy ? '✅ Healthy' : '❌ Unhealthy'}`;
                statusHtml += `</div>`;
                statusHtml += '</div>';
                
                document.getElementById('platform-status').innerHTML = statusHtml;
                
            } catch (error) {
                console.error('Status update error:', error);
            }
        }
        
        async function testEndpoints() {
            const resultsDiv = document.getElementById('test-results');
            resultsDiv.innerHTML = '<div>Running API tests... <span class="loading"></span></div>';
            
            const tests = [
                { name: 'GET /', method: 'GET', path: '/' },
                { name: 'GET /status', method: 'GET', path: '/status' },
                { name: 'GET /queue-status', method: 'GET', path: '/queue-status' },
                { name: 'POST /eval', method: 'POST', path: '/eval', body: {code: 'print("test")'} },
                { name: 'POST /eval-async', method: 'POST', path: '/eval-async', body: {code: 'print("async test")'} },
                { name: 'GET /eval-status/test-id', method: 'GET', path: '/eval-status/test-123' },
                { name: 'OPTIONS / (CORS)', method: 'OPTIONS', path: '/' }
            ];
            
            const results = [];
            
            for (const test of tests) {
                try {
                    const options = {
                        method: test.method,
                        headers: test.body ? {'Content-Type': 'application/json'} : {}
                    };
                    
                    if (test.body) {
                        options.body = JSON.stringify(test.body);
                    }
                    
                    const response = await fetch(test.path, options);
                    
                    results.push({
                        test: test.name,
                        status: response.status,
                        success: response.ok,
                        cors: response.headers.get('Access-Control-Allow-Origin') === '*'
                    });
                } catch (error) {
                    results.push({
                        test: test.name,
                        status: 'Error',
                        success: false,
                        error: error.message
                    });
                }
            }
            
            let html = '<table style="width: 100%; font-size: 13px;">';
            html += '<tr><th style="text-align: left;">Endpoint</th><th>Status</th><th>CORS</th><th>Result</th></tr>';
            
            for (const result of results) {
                const icon = result.success ? '✅' : '❌';
                const corsIcon = result.cors ? '✅' : (result.success ? '⚠️' : '-');
                html += `<tr>`;
                html += `<td><code>${result.test}</code></td>`;
                html += `<td style="text-align: center;">${result.status}</td>`;
                html += `<td style="text-align: center;">${corsIcon}</td>`;
                html += `<td style="text-align: center;">${icon}</td>`;
                html += `</tr>`;
            }
            
            html += '</table>';
            
            const passed = results.filter(r => r.success).length;
            html += `<div style="margin-top: 15px; font-weight: bold;">`;
            html += `${passed}/${results.length} tests passed`;
            html += `</div>`;
            
            resultsDiv.innerHTML = html;
        }
    </script>
</body>
</html>
"""

def main():
    """Demo the API component with different configurations"""
    
    print("=== Crucible Platform API Component Demo ===\n")
    
    # 1. Create evaluation platform with advanced features
    print("1. Setting up evaluation platform...")
    engine = SubprocessEngine()  # Could also use DockerEngine() or GVisorEngine()
    queue = TaskQueue(max_workers=3)
    monitor = AdvancedMonitor()
    platform = QueuedEvaluationPlatform(engine, queue, monitor)
    
    # Run platform self-test
    platform_test = platform.self_test()
    print(f"   Platform self-test: {platform_test['message']}")
    
    # 2. Create API with custom UI
    print("\n2. Creating API component...")
    api = create_api(platform, framework='http.server', ui_html=CUSTOM_UI)
    
    # Run API self-test
    api_test = api.self_test()
    print(f"   API self-test: {api_test['message']}")
    
    # 3. Demonstrate programmatic API testing
    print("\n3. Running programmatic API tests...")
    
    # Test request/response abstractions
    from components.api import APIRequest, HTTPMethod
    test_request = api.handle_request(
        APIRequest(
            method=HTTPMethod.GET,
            path='/status',
            headers={}
        )
    )
    status_data = json.loads(test_request.body)
    print(f"   - Status endpoint: {status_data.get('healthy', False)}")
    
    # Test evaluation endpoint
    test_request = api.handle_request(
        APIRequest(
            method=HTTPMethod.POST,
            path='/eval',
            headers={'Content-Type': 'application/json'},
            body=json.dumps({'code': 'print("API test")'}).encode()
        )
    )
    eval_result = json.loads(test_request.body)
    print(f"   - Eval endpoint: {eval_result.get('output', '').strip()}")
    
    # 4. Start the server
    print("\n4. Starting API server...")
    api.start(host='localhost', port=8000)
    
    print("\n✅ API server is running!")
    print("   - Open http://localhost:8000 in your browser")
    print("   - Try the different evaluation modes")
    print("   - Click 'Test All Endpoints' to run browser-based tests")
    print("   - Press Ctrl+C to stop\n")
    
    # 5. Optional: Demonstrate API calls
    print("5. Making sample API calls...")
    time.sleep(1)  # Let server start
    
    try:
        # Test status endpoint
        response = requests.get('http://localhost:8000/status')
        print(f"   - GET /status: {response.status_code}")
        
        # Test async evaluation
        response = requests.post(
            'http://localhost:8000/eval-async',
            json={'code': 'import time; time.sleep(1); print("Async result")'}
        )
        result = response.json()
        print(f"   - POST /eval-async: {result.get('eval_id', 'No ID')[:8]}... ({result.get('status')})")
        
    except Exception as e:
        print(f"   - API calls failed (this is normal if requests is not installed): {e}")
    
    # Keep running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        api.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()