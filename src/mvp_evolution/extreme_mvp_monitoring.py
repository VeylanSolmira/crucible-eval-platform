#!/usr/bin/env python3
"""
Crucible Evaluation Platform - With Real-time Monitoring
Evolution 2: Add Server-Sent Events for execution progress

Run with: python extreme_mvp_monitoring.py
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

# In-memory "database"
evaluations = {}

# HTML interface with SSE support
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Real-time Monitoring</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        textarea { width: 100%; height: 150px; font-family: monospace; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        button:disabled { background: #ccc; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
        .info { background: #17a2b8; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .event { margin: 5px 0; padding: 5px; background: white; border-left: 3px solid #28a745; }
        .event.error { border-left-color: #dc3545; }
        .event.warning { border-left-color: #ffc107; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Now With Real-time Monitoring!</h1>
    
    <div class="info">
        <h2>&#128200; Evolution 2: Real-time Progress</h2>
        <p><strong>New capabilities:</strong></p>
        <ul>
            <li>See execution progress in real-time</li>
            <li>Monitor container lifecycle events</li>
            <li>Non-blocking UI (can submit while running)</li>
            <li>Timestamp for each event</li>
        </ul>
        <p><strong>This addresses Requirement #2:</strong> Monitor evaluations in real-time</p>
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
    
    <div class="monitoring">
        <h3>&#128200; Real-time Monitoring</h3>
        <div id="events">
            <div class="event">Waiting for evaluation...</div>
        </div>
    </div>
    
    <div id="result"></div>
    
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
            
            // Disable button
            runBtn.disabled = true;
            
            // Submit evaluation
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            const evalId = data.eval_id;
            
            // Connect to SSE for monitoring
            if (eventSource) eventSource.close();
            eventSource = new EventSource(`/monitor/${evalId}`);
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addEvent(data.type, data.message, data.timestamp);
                
                if (data.type === 'complete' || data.type === 'error') {
                    eventSource.close();
                    runBtn.disabled = false;
                    
                    // Show final result
                    resultDiv.innerHTML = `
                        <h3>Final Result:</h3>
                        <pre>${data.output || data.error || 'No output'}</pre>
                    `;
                }
            };
            
            eventSource.onerror = () => {
                addEvent('error', 'Lost connection to monitor', new Date().toISOString());
                eventSource.close();
                runBtn.disabled = false;
            };
        }
        
        function addEvent(type, message, timestamp) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${type}`;
            const time = new Date(timestamp).toLocaleTimeString();
            eventDiv.innerHTML = `<strong>${time}</strong> - ${message}`;
            eventsDiv.appendChild(eventDiv);
            eventsDiv.scrollTop = eventsDiv.scrollHeight;
        }
    </script>
</body>
</html>
"""

def run_in_docker_with_monitoring(code, eval_id):
    """
    Run Python code in Docker with real-time monitoring events.
    """
    evaluation = evaluations[eval_id]
    
    def emit_event(event_type, message):
        event = {
            'type': event_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'eval_id': eval_id
        }
        evaluation['events'].append(event)
    
    # Create temporary file
    emit_event('info', 'Creating code file...')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        emit_event('info', 'Building Docker command...')
        # Docker command with real-time output
        docker_cmd = [
            'docker', 'run',
            '--rm',
            '--network', 'none',
            '--memory', '100m',
            '--cpus', '0.5',
            '--read-only',
            '-v', f'{temp_file}:/code.py:ro',
            'python:3.11-slim',
            'python', '-u', '/code.py'  # -u for unbuffered output
        ]
        
        emit_event('info', 'Starting container...')
        process = subprocess.Popen(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        emit_event('success', 'Container running')
        
        # Stream output line by line
        output_lines = []
        start_time = time.time()
        timeout = 30
        
        while True:
            if time.time() - start_time > timeout:
                emit_event('error', f'Timeout after {timeout} seconds')
                process.terminate()
                break
                
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
                
            line = line.rstrip()
            output_lines.append(line)
            emit_event('output', f'Output: {line}')
        
        return_code = process.wait()
        
        if return_code == 0:
            emit_event('success', 'Container exited successfully')
            evaluation['status'] = 'completed'
        else:
            emit_event('error', f'Container exited with code {return_code}')
            evaluation['status'] = 'failed'
            
        evaluation['output'] = '\n'.join(output_lines)
        emit_event('complete', 'Evaluation complete')
        
    except Exception as e:
        emit_event('error', f'System error: {str(e)}')
        evaluation['status'] = 'error'
        evaluation['error'] = str(e)
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
            emit_event('info', 'Cleaned up temporary files')

class EvalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Serve HTML or SSE streams"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path.startswith('/monitor/'):
            # Server-Sent Events for monitoring
            eval_id = self.path.split('/')[-1]
            
            if eval_id not in evaluations:
                self.send_response(404)
                self.end_headers()
                return
                
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            
            evaluation = evaluations[eval_id]
            last_event_idx = 0
            
            # Send events as they appear
            while evaluation['status'] == 'running':
                # Send new events
                while last_event_idx < len(evaluation['events']):
                    event = evaluation['events'][last_event_idx]
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                    self.wfile.flush()
                    last_event_idx += 1
                
                time.sleep(0.1)
            
            # Send any remaining events
            while last_event_idx < len(evaluation['events']):
                event = evaluation['events'][last_event_idx]
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
                last_event_idx += 1
                
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle evaluation submission"""
        if self.path == '/eval':
            # Read request
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            # Create evaluation
            eval_id = str(uuid.uuid4())[:8]
            code = data.get('code', '')
            
            # Initialize evaluation record
            evaluations[eval_id] = {
                'id': eval_id,
                'status': 'running',
                'events': [],
                'output': None,
                'error': None
            }
            
            # Start evaluation in background thread
            thread = threading.Thread(
                target=run_in_docker_with_monitoring,
                args=(code, eval_id)
            )
            thread.start()
            
            # Return evaluation ID immediately
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'eval_id': eval_id,
                'status': 'started'
            }).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

if __name__ == '__main__':
    print("Checking Docker availability...")
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        print("✅ Docker is available")
    except:
        print("❌ Docker not found. Please install Docker first.")
        exit(1)
    
    print("Ensuring Python Docker image is available...")
    subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
    
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print("🚀 Crucible Monitoring MVP running at http://localhost:8000")
    print("📊 Real-time monitoring via Server-Sent Events!")
    print("Press Ctrl+C to stop")
    server.serve_forever()