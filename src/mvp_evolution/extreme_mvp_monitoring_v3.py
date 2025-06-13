#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Clean Monitoring with Second Abstraction
Evolution: The pain of mixed monitoring led us to extract MonitoringService!

Run with: python extreme_mvp_monitoring_v3.py [--unsafe]
Then open: http://localhost:8000

This version shows how the MonitoringService abstraction cleans everything up.
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
from typing import List, Dict, Optional

# In-memory "database" 
evaluations = {}

# ============== MONITORING ABSTRACTION (NEW!) ==============
# Born from the pain of monitoring code scattered everywhere!

class MonitoringService(ABC):
    """
    Abstract interface for monitoring events.
    This abstraction emerged from the mess in v2!
    """
    @abstractmethod
    def emit_event(self, eval_id: str, event_type: str, message: str):
        """Emit a monitoring event"""
        pass
    
    @abstractmethod
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        """Get events for an evaluation starting from index"""
        pass
    
    @abstractmethod
    def clear_events(self, eval_id: str):
        """Clear events for an evaluation"""
        pass

class InMemoryMonitor(MonitoringService):
    """Simple in-memory monitoring implementation"""
    
    def __init__(self):
        self.events = {}
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        if eval_id not in self.events:
            self.events[eval_id] = []
        
        event = {
            'type': event_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'eval_id': eval_id
        }
        self.events[eval_id].append(event)
    
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        return self.events.get(eval_id, [])[start_idx:]
    
    def clear_events(self, eval_id: str):
        if eval_id in self.events:
            del self.events[eval_id]

# Could easily add other implementations:
# class PrometheusMonitor(MonitoringService): ...
# class CloudWatchMonitor(MonitoringService): ...
# class FileMonitor(MonitoringService): ...

# ============== EXECUTION ENGINE WITH CLEAN MONITORING ==============

class ExecutionEngine(ABC):
    """Now engines can use monitoring without being coupled to it!"""
    
    def __init__(self, monitor: Optional[MonitoringService] = None):
        self.monitor = monitor
    
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        pass
    
    def emit(self, eval_id: str, event_type: str, message: str):
        """Helper method to emit events if monitor is available"""
        if self.monitor:
            self.monitor.emit_event(eval_id, event_type, message)

class SubprocessEngine(ExecutionEngine):
    """Direct subprocess execution - UNSAFE but simple"""
    
    def execute(self, code: str, eval_id: str) -> dict:
        # CLEAN: Just use self.emit() instead of global functions!
        self.emit(eval_id, 'info', 'Starting subprocess execution (UNSAFE!)...')
        
        try:
            self.emit(eval_id, 'warning', 'Running directly on host - this is dangerous!')
            
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout or result.stderr
            if output:
                for line in output.strip().split('\n'):
                    self.emit(eval_id, 'output', f'> {line}')
            
            self.emit(eval_id, 'success', 'Subprocess completed')
            
            return {
                'id': eval_id,
                'status': 'completed',
                'output': output,
                'engine': 'subprocess (UNSAFE!)'
            }
        except subprocess.TimeoutExpired:
            self.emit(eval_id, 'error', 'Timeout after 5 seconds')
            return {
                'id': eval_id,
                'status': 'timeout',
                'error': 'Evaluation timed out after 5 seconds',
                'engine': 'subprocess'
            }
        except Exception as e:
            self.emit(eval_id, 'error', f'Error: {str(e)}')
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'engine': 'subprocess'
            }
    
    def get_description(self) -> str:
        return "Subprocess (UNSAFE - Direct execution on host)"

class DockerEngine(ExecutionEngine):
    """Docker containerized execution - Now much cleaner!"""
    
    def execute(self, code: str, eval_id: str) -> dict:
        # CLEAN: No more global emit_event calls!
        self.emit(eval_id, 'info', 'Creating temporary file...')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        self.emit(eval_id, 'info', 'Building Docker command...')
        
        try:
            docker_cmd = [
                'docker', 'run',
                '--rm', '--network', 'none',
                '--memory', '100m', '--cpus', '0.5',
                '--read-only',
                '-v', f'{temp_file}:/code.py:ro',
                'python:3.11-slim',
                'python', '-u', '/code.py'
            ]
            
            self.emit(eval_id, 'info', 'Starting Docker container...')
            
            process = subprocess.Popen(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.emit(eval_id, 'success', 'Container started')
            
            output_lines = []
            start_time = time.time()
            
            while True:
                if time.time() - start_time > 30:
                    self.emit(eval_id, 'error', 'Timeout after 30 seconds')
                    process.terminate()
                    break
                    
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                    
                line = line.rstrip()
                output_lines.append(line)
                self.emit(eval_id, 'output', f'> {line}')
            
            return_code = process.wait()
            
            if return_code == 0:
                self.emit(eval_id, 'success', 'Container exited successfully')
                status = 'completed'
            else:
                self.emit(eval_id, 'error', f'Container exited with code {return_code}')
                status = 'failed'
                
            return {
                'id': eval_id,
                'status': status,
                'output': '\n'.join(output_lines),
                'engine': 'docker (sandboxed)'
            }
            
        except Exception as e:
            self.emit(eval_id, 'error', f'System error: {str(e)}')
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'engine': 'docker'
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
                self.emit(eval_id, 'info', 'Cleaned up temporary file')
    
    def get_description(self) -> str:
        return "Docker (Containerized - Isolated from host)"

# ============== PLATFORM WITH BOTH ABSTRACTIONS ==============

class EvaluationPlatform:
    """Platform now cleanly uses both abstractions!"""
    
    def __init__(self, engine: ExecutionEngine, monitor: MonitoringService):
        self.engine = engine
        self.monitor = monitor
        # Wire them together
        self.engine.monitor = monitor
    
    def evaluate_async(self, code: str) -> str:
        """Start evaluation in background thread"""
        eval_id = str(uuid.uuid4())[:8]
        evaluations[eval_id] = {
            'id': eval_id,
            'status': 'running',
            'output': None,
            'error': None
        }
        
        # CLEAN: Use the monitor abstraction
        self.monitor.emit_event(eval_id, 'info', 'Evaluation started')
        
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
        self.monitor.emit_event(eval_id, 'complete', 'Evaluation finished')

# Global platform instance
platform = None

# ============== HTML CELEBRATING CLEAN ARCHITECTURE ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Clean Architecture</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        button:disabled { background: #ccc; }
        .success { background: #d4edda; color: #155724; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .info { background: #e8f4f8; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .event { margin: 3px 0; padding: 5px; background: white; font-size: 14px; }
        .event.error { border-left: 3px solid #dc3545; }
        .event.warning { border-left: 3px solid #ffc107; }
        .event.success { border-left: 3px solid #28a745; }
        .event.info { border-left: 3px solid #17a2b8; }
        pre { background: #f5f5f5; padding: 10px; font-family: monospace; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Two Clean Abstractions!</h1>
    
    <div class="success">
        <h2>Clean Architecture Achieved!</h2>
        <p><strong>We now have two beautiful abstractions:</strong></p>
        <ol>
            <li><strong>ExecutionEngine</strong> - Handles HOW code runs (subprocess, Docker, K8s...)</li>
            <li><strong>MonitoringService</strong> - Handles HOW we observe (memory, file, Prometheus...)</li>
        </ol>
        <p><strong>Benefits:</strong></p>
        <ul>
            <li>Each concern is separate and testable</li>
            <li>Easy to add new implementations</li>
            <li>No more global state or mixed concerns</li>
            <li>Can mix and match: any engine with any monitor!</li>
        </ul>
    </div>
    
    <div class="info">
        <strong>Current Configuration:</strong><br>
        Engine: <span id="engine-name">Loading...</span><br>
        Monitor: <span id="monitor-name">Loading...</span>
    </div>
    
    <textarea id="code">import time
print("Clean architecture in action!")
time.sleep(1)
print("Notice how the monitoring is separate from execution")
time.sleep(1)
print("We could swap to file-based monitoring with one line!")
time.sleep(1)
print("Or use Prometheus, CloudWatch, etc...")
time.sleep(1)
print("All without changing the execution engine!")</textarea>
    <br><br>
    <button id="runBtn" onclick="runEval()">Run with Clean Architecture</button>
    
    <div class="monitoring">
        <h3>Monitoring Events (via MonitoringService)</h3>
        <div id="events"></div>
    </div>
    
    <div style="margin-top: 20px;">
        <h3>Architecture Evolution Summary</h3>
        <pre>
1. extreme_mvp.py           -> Just make it work
2. extreme_mvp_docker.py    -> Copy-paste pain
3. extreme_mvp_docker_v2.py -> Extract ExecutionEngine
4. extreme_mvp_monitoring_v2.py -> Monitoring pain
5. extreme_mvp_monitoring_v3.py -> Extract MonitoringService <- We are here!
        </pre>
    </div>
    
    <script>
        let eventSource = null;
        
        fetch('/config').then(r => r.json()).then(data => {
            document.getElementById('engine-name').textContent = data.engine;
            document.getElementById('monitor-name').textContent = data.monitor;
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
            
        elif self.path == '/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'engine': platform.engine.get_description(),
                'monitor': type(platform.monitor).__name__
            }).encode())
            
        elif self.path.startswith('/monitor/'):
            # Server-Sent Events - now using the abstraction!
            eval_id = self.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            last_event_idx = 0
            
            while True:
                # CLEAN: Use the monitor abstraction instead of global state
                events = platform.monitor.get_events(eval_id, last_event_idx)
                for event in events:
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
        print("WARNING: Running with UNSAFE subprocess execution!")
        engine = SubprocessEngine()
    else:
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
            engine = DockerEngine()
            print("Using Docker engine")
        except:
            print("Docker not available, using subprocess")
            engine = SubprocessEngine()
    
    # Create monitoring service
    monitor = InMemoryMonitor()
    
    # Create platform with BOTH abstractions
    platform = EvaluationPlatform(engine, monitor)
    
    server = HTTPServer(('localhost', 8000), EvalHandler)
    print(f"Crucible Platform at http://localhost:8000")
    print(f"Clean architecture with {type(engine).__name__} and {type(monitor).__name__}")
    print("Try swapping implementations - it's easy now!")
    server.serve_forever()