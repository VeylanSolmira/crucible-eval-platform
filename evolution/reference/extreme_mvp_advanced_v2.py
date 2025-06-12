#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Advanced Production Configuration V2
Now using the modular API component for cleaner architecture.

Run with: python extreme_mvp_advanced_v2.py [--unsafe]
Then open: http://localhost:8000

This version demonstrates:
- Using the new API component instead of inline HTTP handlers
- Clean separation of concerns between API and platform logic
- Easy framework switching (could use FastAPI with --fastapi flag)
"""

import sys
import time

# Import our modular components
from components import (
    SubprocessEngine,
    DockerEngine,
    GVisorEngine,
    AdvancedMonitor,
    TaskQueue,
    QueuedEvaluationPlatform,
    create_api
)

# ============== ADVANCED UI HTML ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Advanced Edition V2</title>
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
        .architecture-note { background: #e8f5e9; color: #2e7d32; padding: 15px; margin: 10px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>🚀 Crucible Platform - Advanced Edition V2</h1>
    
    <div class="architecture-note">
        <h3>🏗️ New Architecture Features</h3>
        <ul>
            <li>✨ <strong>Modular API Component</strong> - Clean separation of HTTP handling</li>
            <li>🔌 <strong>Framework Agnostic</strong> - Easy to switch between http.server, FastAPI, Flask</li>
            <li>🧪 <strong>Fully Testable</strong> - Every component has comprehensive tests</li>
            <li>📊 <strong>RESTful Design</strong> - Proper HTTP methods and status codes</li>
        </ul>
    </div>
    
    <div class="info">
        <h3>Platform Features</h3>
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
print("Using new modular API component!")
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
            <br>
            <button onclick="submitCode()">▶️ Evaluate (Async)</button>
            <button onclick="submitSync()">⏸️ Evaluate (Sync)</button>
            <button onclick="submitMultiple()">📦 Submit 5 Tasks</button>
            <button onclick="getQueueStatus()">📊 Refresh Status</button>
            
            <div id="submission-result"></div>
        </div>
        
        <div class="right-panel">
            <h3>System Status</h3>
            <div class="queue-status" id="queue-status">Loading...</div>
            <div class="status" id="platform-status">Loading...</div>
            
            <h3>Active Evaluations</h3>
            <div id="evaluations"></div>
        </div>
    </div>
    
    <h3>Live Events</h3>
    <div class="events" id="events">
        <div class="event event-info">System initialized - using modular API component</div>
    </div>
    
    <script>
        // Track active evaluations
        const activeEvaluations = new Map();
        const eventSources = new Map();
        
        async function submitCode() {
            const code = document.getElementById('code').value;
            const response = await fetch('/eval-async', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const result = await response.json();
            document.getElementById('submission-result').innerHTML = `
                <div class="status">
                    <strong>Submitted!</strong> Evaluation ID: ${result.eval_id}<br>
                    Status: ${result.status}
                </div>
            `;
            
            // Track evaluation
            activeEvaluations.set(result.eval_id, result);
            updateEvaluationsList();
            
            // Subscribe to events
            subscribeToEvents(result.eval_id);
        }
        
        async function submitSync() {
            const code = document.getElementById('code').value;
            const resultDiv = document.getElementById('submission-result');
            
            resultDiv.innerHTML = '<div class="status">Running synchronous evaluation...</div>';
            
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const result = await response.json();
            
            if (result.success) {
                resultDiv.innerHTML = `
                    <div class="status">
                        <strong>✅ Evaluation Complete (Sync)</strong>
                        <pre>${result.output || 'No output'}</pre>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `
                    <div class="status">
                        <strong>❌ Evaluation Failed</strong>
                        <pre>${result.error || 'Unknown error'}</pre>
                    </div>
                `;
            }
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
                for (const [name, comp] of Object.entries(status.components || {})) {
                    const health = comp.healthy ? '✅' : '❌';
                    componentHtml += `${health} ${name}: ${comp.component || 'Unknown'}<br>`;
                }
                
                document.getElementById('platform-status').innerHTML = `
                    ${componentHtml}
                    <strong>Engine:</strong> ${status.engine || 'Unknown'}<br>
                    <strong>API Framework:</strong> http.server (modular)
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
        
        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>
"""

def main():
    """Main entry point using the new API component"""
    
    print("=== Crucible Evaluation Platform V2 ===")
    print("Now with modular API component!\n")
    
    # Parse command line arguments
    use_unsafe = '--unsafe' in sys.argv
    use_fastapi = '--fastapi' in sys.argv
    
    # Select execution engine based on flags
    if use_unsafe:
        print("⚠️  Running in UNSAFE mode (subprocess only)")
        engine = SubprocessEngine()
    else:
        # Try Docker first, fall back to subprocess
        try:
            engine = DockerEngine()
            print("🐳 Using Docker for isolation")
        except:
            try:
                engine = GVisorEngine()
                print("🛡️  Using gVisor for enhanced isolation")
            except:
                print("⚠️  Docker/gVisor not available, using subprocess")
                engine = SubprocessEngine()
    
    # Create the platform with all components
    queue = TaskQueue(max_workers=3)
    monitor = AdvancedMonitor()
    platform = QueuedEvaluationPlatform(engine, queue, monitor)
    
    # Run self-tests
    print("\nRunning component self-tests...")
    test_results = platform.run_all_tests()
    
    total_passed = sum(r['passed'] for r in test_results.values())
    total_components = len(test_results)
    
    print(f"\n✅ Self-tests complete: {total_passed}/{total_components} components passed")
    
    if total_passed < total_components:
        print("\n⚠️  Some tests failed. Platform may not work correctly.")
        for component, result in test_results.items():
            if not result['passed']:
                print(f"  - {component}: {result['message']}")
    
    # Create API using the new component
    framework = 'fastapi' if use_fastapi else 'http.server'
    print(f"\nCreating API using {framework}...")
    
    api = create_api(platform, framework=framework, ui_html=HTML)
    
    # Test the API component
    api_test = api.self_test()
    print(f"API component test: {api_test['message']}")
    
    # Start the server
    print(f"\n🚀 Starting server on http://localhost:8000")
    print("   Press Ctrl+C to stop\n")
    
    try:
        api.start(port=8000)
        
        # If using http.server, we need to keep the main thread alive
        if framework == 'http.server':
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        api.stop()
        print("Goodbye!")

if __name__ == "__main__":
    main()