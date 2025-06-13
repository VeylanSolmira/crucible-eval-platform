#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Adding Monitoring to Abstracted Version
Evolution: We have ExecutionEngine abstraction, now adding monitoring...
          But it's getting messy! We're mixing monitoring into execution.

Run with: python extreme_mvp_monitoring_v2.py [--unsafe]
Then open: http://localhost:8000

This version shows the PAIN of not having a monitoring abstraction yet.
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
from abc import ABC, abstractmethod

# In-memory "database" 
evaluations = {}
# Monitoring events (getting messy - global state!)
monitoring_events = {}

# ============== EXECUTION ENGINE ABSTRACTION ==============
class ExecutionEngine(ABC):
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        pass

class SubprocessEngine(ExecutionEngine):
    """Direct subprocess execution - UNSAFE but simple"""
    
    def execute(self, code: str, eval_id: str) -> dict:
        # PAIN POINT: Monitoring code mixed with execution!
        emit_event(eval_id, 'info', 'Starting subprocess execution (UNSAFE!)...')
        
        try:
            emit_event(eval_id, 'warning', 'Running directly on host - this is dangerous!')
            
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # More monitoring mixed in...
            emit_event(eval_id, 'output', result.stdout or result.stderr)
            emit_event(eval_id, 'success', 'Subprocess completed')
            
            return {
                'id': eval_id,
                'status': 'completed',
                'output': result.stdout or result.stderr,
                'engine': 'subprocess (UNSAFE!)'
            }
        except subprocess.TimeoutExpired:
            emit_event(eval_id, 'error', 'Timeout after 5 seconds')
            return {
                'id': eval_id,
                'status': 'timeout',
                'error': 'Evaluation timed out after 5 seconds',
                'engine': 'subprocess'
            }
        except Exception as e:
            emit_event(eval_id, 'error', f'Error: {str(e)}')
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'engine': 'subprocess'
            }
    
    def get_description(self) -> str:
        return "Subprocess (UNSAFE - Direct execution on host)"

class DockerEngine(ExecutionEngine):
    """Docker containerized execution - Safer but requires Docker"""
    
    def execute(self, code: str, eval_id: str) -> dict:
        # PAIN POINT: Duplicating monitoring logic!
        emit_event(eval_id, 'info', 'Creating temporary file...')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        emit_event(eval_id, 'info', 'Building Docker command...')
        
        try:
            # PAIN POINT: Want real-time output but it's getting complex!
            docker_cmd = [
                'docker', 'run',
                '--rm', '--network', 'none',
                '--memory', '100m', '--cpus', '0.5',
                '--read-only',
                '-v', f'{temp_file}:/code.py:ro',
                'python:3.11-slim',
                'python', '-u', '/code.py'  # -u for unbuffered
            ]
            
            emit_event(eval_id, 'info', 'Starting Docker container...')
            
            # PAIN POINT: Streaming output code duplicated from monitoring example!
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            emit_event(eval_id, 'success', 'Container started')
            
            output_lines = []
            start_time = time.time()
            
            while True:
                if time.time() - start_time > 30:
                    emit_event(eval_id, 'error', 'Timeout after 30 seconds')
                    process.terminate()
                    break
                    
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                    
                line = line.rstrip()
                output_lines.append(line)
                # PAIN POINT: Real-time output events mixed with execution logic
                emit_event(eval_id, 'output', f'> {line}')
            
            return_code = process.wait()
            
            if return_code == 0:
                emit_event(eval_id, 'success', 'Container exited successfully')
                status = 'completed'
            else:
                emit_event(eval_id, 'error', f'Container exited with code {return_code}')
                status = 'failed'
                
            return {
                'id': eval_id,
                'status': status,
                'output': '\n'.join(output_lines),
                'engine': 'docker (sandboxed)'
            }
            
        except Exception as e:
            emit_event(eval_id, 'error', f'System error: {str(e)}')
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'engine': 'docker'
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                emit_event(eval_id, 'info', 'Cleaned up temporary file')
    
    def get_description(self) -> str:
        return "Docker (Containerized - Isolated from host)"

# ============== MONITORING (NOT ABSTRACTED YET!) ==============
# PAIN POINT: This is global state, hard to test, hard to swap implementations

def emit_event(eval_id: str, event_type: str, message: str):
    """Emit a monitoring event - but this is tightly coupled!"""
    if eval_id not in monitoring_events:
        monitoring_events[eval_id] = []
    
    event = {
        'type': event_type,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'eval_id': eval_id
    }
    monitoring_events[eval_id].append(event)

# ============== PLATFORM ==============
class EvaluationPlatform:
    def __init__(self, engine: ExecutionEngine):
        self.engine = engine
    
    def evaluate_async(self, code: str) -> str:
        """Start evaluation in background thread"""
        eval_id = str(uuid.uuid4())[:8]
        evaluations[eval_id] = {
            'id': eval_id,
            'status': 'running',
            'output': None,
            'error': None
        }
        
        # PAIN POINT: Monitoring initialization scattered around
        monitoring_events[eval_id] = []
        emit_event(eval_id, 'info', 'Evaluation started')
        
        thread = threading.Thread(
            target=self._run_evaluation,
            args=(code, eval_id)
        )
        thread.start()
        
        return eval_id
    
    def _run_evaluation(self, code: str, eval_id: str):
        """Run evaluation with monitoring"""
        result = self.engine.execute(code, eval_id)
        evaluations[eval_id] = result
        emit_event(eval_id, 'complete', 'Evaluation finished')

# Global platform instance
platform = None

# ============== HTML WITH SSE MONITORING ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Monitoring Pain Points</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        button:disabled { background: #ccc; }
        .warning { background: #dc3545; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .info { background: #17a2b8; color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .event { margin: 3px 0; padding: 5px; background: white; font-size: 14px; }
        .event.error { border-left: 3px solid #dc3545; }
        .event.warning { border-left: 3px solid #ffc107; }
        .event.success { border-left: 3px solid #28a745; }
        .event.info { border-left: 3px solid #17a2b8; }
    </style>
</head>
<body>
    <h1>Crucible Platform - The Monitoring Mess</h1>
    
    <div class="warning">
        <h2>&#128683; Pain Points Emerging!</h2>
        <p><strong>Problems with current approach:</strong></p>
        <ul>
            <li>Monitoring code mixed into execution engines</li>
            <li>Global state for events (hard to test)</li>
            <li>Duplicated emit_event calls everywhere</li>
            <li>Can't easily swap monitoring implementations</li>
            <li>Real-time streaming logic tangled with Docker execution</li>
        </ul>
        <p><strong>Next evolution:</strong> We need a MonitoringService abstraction!</p>
    </div>
    
    <div class="info">
        <strong>Current Engine:</strong> <span id="engine-name">Loading...</span>
    </div>
    
    <textarea id="code">import time
print("Watch the monitoring events appear in real-time!")
time.sleep(1)
print("Step 1: Checking environment...")
time.sleep(1)
print("Step 2: Running calculations...")
time.sleep(1)
print("Step 3: Complete!")</textarea>
    <br><br>
    <button id="runBtn" onclick="runEval()">Run with Monitoring</button>
    
    <div class="monitoring">
        <h3>Monitoring Events</h3>
        <div id="events"></div>
    </div>
    
    <script>
        let eventSource = null;
        
        fetch('/engine-info').then(r => r.json()).then(data => {
            document.getElementById('engine-name').textContent = data.engine;
        });
        
        async function runEval() {
            const code = document.getElementById('code').value;
            const eventsDiv = document.getElementById('events');
            const runBtn = document.getElementById('runBtn');
            
            eventsDiv.innerHTML = '';
            runBtn.disabled = true;
            
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            const evalId = data.eval_id;
            
            // Connect to SSE
            if (eventSource) eventSource.close();
            eventSource = new EventSource(`/monitor/${evalId}`);
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const eventDiv = document.createElement('div');
                eventDiv.className = `event ${data.type}`;
                const time = new Date(data.timestamp).toLocaleTimeString();
                eventDiv.innerHTML = `<strong>${time}</strong> [${data.type}] ${data.message}`;
                eventsDiv.appendChild(eventDiv);
                
                if (data.type === 'complete') {
                    eventSource.close();
                    runBtn.disabled = false;
                }
            };
        }
    </script>
</body>
</html>
"""

class EvalHandler(BaseHTTPRequestHandler):
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
            
        elif self.path.startswith('/monitor/'):
            # Server-Sent Events
            eval_id = self.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            last_event_idx = 0
            
            while True:
                # PAIN POINT: Direct access to global monitoring_events
                if eval_id in monitoring_events:
                    events = monitoring_events[eval_id]
                    while last_event_idx < len(events):
                        event = events[last_event_idx]
                        self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                        self.wfile.flush()
                        last_event_idx += 1
                        
                        if event['type'] == 'complete':
                            return
                
                time.sleep(0.1)
                
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/eval':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            eval_id = platform.evaluate_async(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'eval_id': eval_id}).encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    import sys
    
    # Choose engine
    if '--unsafe' in sys.argv:
        print("⚠️  Running with UNSAFE subprocess execution!")
        engine = SubprocessEngine()
    else:
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
            engine = DockerEngine()
            print("🐳 Using Docker engine")
        except:
            print("Docker not available, using subprocess")
            engine = SubprocessEngine()
    
    platform = EvaluationPlatform(engine)
    
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print(f"🚀 Crucible Platform at http://localhost:8000")
    print("😫 Notice how monitoring is mixed into everything!")
    server.serve_forever()