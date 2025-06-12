#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Advanced Production Configuration
This is the main entry point combining all advanced features.

Run with: python extreme_mvp_advanced.py [--unsafe]
Then open: http://localhost:8000

Features:
- Modular component architecture
- Queue-based async execution
- Real-time event streaming
- Production security (gVisor if available)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
import threading
from io import StringIO
import unittest

# Import our modular components
from components import (
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    QueuedEvaluationPlatform
)

# Global platform instance
platform = None

# ============== HTML WITH ADVANCED FEATURES ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Advanced Edition</title>
    <style>
        body { font-family: Arial; max-width: 1000px; margin: 50px auto; }
        .container { display: flex; gap: 20px; }
        .left-panel { flex: 1; }
        .right-panel { flex: 1; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; margin: 5px; }
        button:hover { background: #218838; }
        .status { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .events { background: #f5f5f5; padding: 10px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        .event { margin: 2px 0; }
        .event-info { color: #17a2b8; }
        .event-complete { color: #28a745; }
        .event-error { color: #dc3545; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .info { background: #d1ecf1; color: #0c5460; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .queue-status { background: #e7f3ff; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .eval-status { padding: 10px; margin: 5px 0; border: 1px solid #dee2e6; border-radius: 5px; }
        .eval-status.queued { background: #fff3cd; }
        .eval-status.running { background: #cfe2ff; }
        .eval-status.completed { background: #d1e7dd; }
        .eval-status.failed { background: #f8d7da; }
    </style>
</head>
<body>
    <h1>🚀 Crucible Platform - Advanced Edition</h1>
    
    <div class="info">
        <h3>Advanced Features Active</h3>
        <ul>
            <li>✅ <strong>Queue-based execution</strong> - Non-blocking, concurrent evaluations</li>
            <li>✅ <strong>Real-time monitoring</strong> - Live event streaming</li>
            <li>✅ <strong>Modular architecture</strong> - Production-ready components</li>
            <li>✅ <strong>Security isolation</strong> - Docker/gVisor sandboxing</li>
        </ul>
    </div>
    
    <div class="container">
        <div class="left-panel">
            <h3>Submit Evaluation</h3>
            <textarea id="code" placeholder="Enter Python code to evaluate...">import time
import random

print("Advanced evaluation starting...")
time.sleep(random.uniform(1, 3))  # Simulate variable work

# Generate some results
result = sum(range(100))
print(f"Calculation result: {result}")

# Test isolation
try:
    import requests
    print("❌ Network access allowed!")
except:
    print("✅ Network properly isolated")

print("Evaluation complete!")</textarea>
            <br><br>
            <button onclick="submitEvaluation()">Submit to Queue</button>
            <button onclick="submitMultiple()">Submit 5 Evaluations</button>
            <button onclick="getQueueStatus()">Queue Status</button>
            
            <div id="submission-result"></div>
            
            <h3>Active Evaluations</h3>
            <div id="evaluations"></div>
        </div>
        
        <div class="right-panel">
            <h3>Queue Status</h3>
            <div id="queue-status" class="queue-status">Loading...</div>
            
            <h3>Real-time Event Stream</h3>
            <div id="events" class="events">
                <div class="event event-info">Waiting for events...</div>
            </div>
            
            <h3>Platform Status</h3>
            <div id="platform-status" class="status">Loading...</div>
        </div>
    </div>
    
    <script>
        let activeEvaluations = new Map();
        let eventSources = new Map();
        
        // Poll for updates
        setInterval(updateStatus, 2000);
        updateStatus();
        
        async function submitEvaluation() {
            const code = document.getElementById('code').value;
            
            const response = await fetch('/eval-async', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const result = await response.json();
            
            document.getElementById('submission-result').innerHTML = `
                <div class="status">
                    <strong>Submitted!</strong><br>
                    Evaluation ID: ${result.eval_id}<br>
                    Status: ${result.status}
                </div>
            `;
            
            // Track evaluation
            activeEvaluations.set(result.eval_id, result);
            updateEvaluationsList();
            
            // Subscribe to events
            subscribeToEvents(result.eval_id);
        }
        
        async function submitMultiple() {
            for (let i = 0; i < 5; i++) {
                const code = `
import time
print(f"Batch evaluation ${i} starting...")
time.sleep(${1 + i * 0.5})  # Variable duration
result = ${i} * 100
print(f"Result: {result}")
print("Done!")
                `;
                
                const response = await fetch('/eval-async', {
                    method: 'POST',
                    body: JSON.stringify({code}),
                    headers: {'Content-Type': 'application/json'}
                });
                
                const result = await response.json();
                activeEvaluations.set(result.eval_id, result);
                subscribeToEvents(result.eval_id);
            }
            
            updateEvaluationsList();
            document.getElementById('submission-result').innerHTML = `
                <div class="status">
                    <strong>Submitted 5 evaluations!</strong>
                </div>
            `;
        }
        
        function subscribeToEvents(evalId) {
            // In a real system, this would be WebSocket or SSE
            // For demo, we'll poll for events
            if (!eventSources.has(evalId)) {
                eventSources.set(evalId, {lastIndex: 0});
            }
        }
        
        async function updateStatus() {
            // Update queue status
            try {
                const queueResp = await fetch('/queue-status');
                const queueStatus = await queueResp.json();
                
                document.getElementById('queue-status').innerHTML = `
                    <strong>Queue:</strong> ${queueStatus.queue.queued} queued<br>
                    <strong>Workers:</strong> ${queueStatus.queue.workers} active<br>
                    <strong>Completed:</strong> ${queueStatus.queue.completed}<br>
                    <strong>Failed:</strong> ${queueStatus.queue.failed}
                `;
            } catch (e) {}
            
            // Update platform status
            try {
                const statusResp = await fetch('/status');
                const status = await statusResp.json();
                
                let componentHtml = '<strong>Components:</strong><br>';
                for (const [name, comp] of Object.entries(status.components)) {
                    const health = comp.healthy ? '&#x2705;' : '&#x274C;';
                    componentHtml += `${health} ${name}: ${comp.component || 'Unknown'}<br>`;
                }
                
                document.getElementById('platform-status').innerHTML = `
                    ${componentHtml}
                    <strong>Engine:</strong> ${status.engine}
                `;
            } catch (e) {}
            
            // Update evaluation statuses
            for (const evalId of activeEvaluations.keys()) {
                try {
                    const resp = await fetch(`/eval-status/${evalId}`);
                    const evalStatus = await resp.json();
                    
                    activeEvaluations.set(evalId, evalStatus);
                    
                    // Update events
                    if (evalStatus.events && eventSources.has(evalId)) {
                        const source = eventSources.get(evalId);
                        const newEvents = evalStatus.events.slice(source.lastIndex);
                        
                        for (const event of newEvents) {
                            addEvent(evalId, event);
                        }
                        
                        source.lastIndex = evalStatus.events.length;
                    }
                } catch (e) {}
            }
            
            updateEvaluationsList();
        }
        
        function updateEvaluationsList() {
            let html = '';
            
            for (const [evalId, evalData] of activeEvaluations) {
                html += `
                    <div class="eval-status ${evalData.status}">
                        <strong>${evalId}</strong>: ${evalData.status}
                        ${evalData.result ? `<br>Output: <pre>${evalData.result.output}</pre>` : ''}
                    </div>
                `;
            }
            
            document.getElementById('evaluations').innerHTML = html || '<em>No active evaluations</em>';
        }
        
        function addEvent(evalId, event) {
            const eventsDiv = document.getElementById('events');
            const eventClass = event.type === 'error' ? 'event-error' : 
                               event.type === 'complete' ? 'event-complete' : 
                               'event-info';
            
            const eventHtml = `
                <div class="event ${eventClass}">
                    [${evalId.substring(0, 8)}] ${event.type}: ${event.message}
                </div>
            `;
            
            eventsDiv.innerHTML = eventHtml + eventsDiv.innerHTML;
            
            // Keep only last 50 events
            while (eventsDiv.children.length > 50) {
                eventsDiv.removeChild(eventsDiv.lastChild);
            }
        }
        
        async function getQueueStatus() {
            await updateStatus();
        }
    </script>
</body>
</html>
"""

class AdvancedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path == '/queue-status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(platform.get_queue_status()).encode())
            
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(platform.get_status()).encode())
            
        elif self.path.startswith('/eval-status/'):
            eval_id = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(platform.get_evaluation_status(eval_id)).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/eval-async':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            result = platform.evaluate_async(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        elif self.path == '/eval':
            # Synchronous evaluation (backward compatibility)
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
    # Choose engine based on arguments and availability
    if '--unsafe' in sys.argv:
        print("WARNING: Running with UNSAFE subprocess execution!")
        engine = SubprocessEngine()
    else:
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            
            # Check for gVisor
            docker_info = subprocess.run(['docker', 'info'], capture_output=True, text=True)
            if 'runsc' in docker_info.stdout:
                print("✅ gVisor runtime detected - using production security")
                engine = GVisorEngine('runsc')
            else:
                print("Using Docker engine (install gVisor for enhanced security)")
                engine = DockerEngine()
        except:
            print("❌ Docker not available!")
            print("   Please install Docker or use --unsafe flag")
            sys.exit(1)
    
    # Create advanced platform with all features
    monitor = AdvancedMonitor()
    queue = TaskQueue(max_workers=3)
    platform = QueuedEvaluationPlatform(engine, monitor, queue)
    
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
    server = HTTPServer(('localhost', 8000), AdvancedHandler)
    print("🚀 Advanced Crucible Platform at http://localhost:8000")
    print("   Features: Queue-based execution, real-time monitoring, modular architecture")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        platform.shutdown()
        print("Shutdown complete.")