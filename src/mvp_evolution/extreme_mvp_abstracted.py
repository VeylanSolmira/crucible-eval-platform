#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Properly Abstracted MVP
Demonstrates TRACE-AI principle: Abstraction for evolution

Run with: python extreme_mvp_abstracted.py
Then open: http://localhost:8000
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
from typing import Dict, List, Any, Optional

# ============== ABSTRACTIONS ==============
# These interfaces enable evolution without changing core logic

class ExecutionEngine(ABC):
    """Abstract interface for code execution - can be subprocess, docker, k8s, etc."""
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        pass

class MonitoringService(ABC):
    """Abstract interface for monitoring - can be print, SSE, Prometheus, etc."""
    @abstractmethod
    def emit_event(self, eval_id: str, event_type: str, message: str):
        pass
    
    @abstractmethod
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        pass

class StorageService(ABC):
    """Abstract interface for storage - can be dict, file, database, S3, etc."""
    @abstractmethod
    def store_evaluation(self, eval_id: str, data: Dict):
        pass
    
    @abstractmethod
    def get_evaluation(self, eval_id: str) -> Optional[Dict]:
        pass

# ============== EVOLUTION 1: SIMPLE IMPLEMENTATIONS ==============

class SubprocessEngine(ExecutionEngine):
    """Unsafe direct execution - our starting point"""
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                'status': 'completed',
                'output': result.stdout or result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'error': 'Execution timed out'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

# ============== EVOLUTION 2: DOCKER IMPLEMENTATION ==============

class DockerEngine(ExecutionEngine):
    """Safer Docker-based execution"""
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            docker_cmd = [
                'docker', 'run', '--rm',
                '--network', 'none',
                '--memory', '100m',
                '--cpus', '0.5',
                '--read-only',
                '-v', f'{temp_file}:/code.py:ro',
                'python:3.11-slim',
                'python', '-u', '/code.py'
            ]
            
            # For monitoring integration
            if hasattr(self, 'monitor'):
                return self._execute_with_monitoring(docker_cmd, eval_id)
            else:
                result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
                return {
                    'status': 'completed' if result.returncode == 0 else 'failed',
                    'output': result.stdout or result.stderr
                }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def _execute_with_monitoring(self, cmd: List[str], eval_id: str) -> Dict[str, Any]:
        """Execute with real-time monitoring support"""
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output_lines = []
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.rstrip()
                output_lines.append(line)
                if hasattr(self, 'monitor'):
                    self.monitor.emit_event(eval_id, 'output', f'Output: {line}')
        
        return {
            'status': 'completed' if process.returncode == 0 else 'failed',
            'output': '\n'.join(output_lines)
        }

# ============== EVOLUTION 3: MONITORING IMPLEMENTATIONS ==============

class InMemoryMonitor(MonitoringService):
    """Simple in-memory event storage with SSE support"""
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

class InMemoryStorage(StorageService):
    """Simple dictionary storage"""
    def __init__(self):
        self.evaluations = {}
    
    def store_evaluation(self, eval_id: str, data: Dict):
        self.evaluations[eval_id] = data
    
    def get_evaluation(self, eval_id: str) -> Optional[Dict]:
        return self.evaluations.get(eval_id)

# ============== PLATFORM WITH PLUGGABLE COMPONENTS ==============

class EvaluationPlatform:
    """Main platform that uses abstracted services"""
    def __init__(self, engine: ExecutionEngine, monitor: MonitoringService, storage: StorageService):
        self.engine = engine
        self.monitor = monitor
        self.storage = storage
        
        # Wire up monitoring if engine supports it
        if hasattr(engine, 'monitor'):
            engine.monitor = monitor
    
    def submit_evaluation(self, code: str) -> str:
        """Submit code for evaluation"""
        eval_id = str(uuid.uuid4())[:8]
        
        # Initialize evaluation
        self.storage.store_evaluation(eval_id, {
            'id': eval_id,
            'status': 'running',
            'output': None,
            'error': None
        })
        
        # Start async execution
        thread = threading.Thread(target=self._run_evaluation, args=(code, eval_id))
        thread.start()
        
        return eval_id
    
    def _run_evaluation(self, code: str, eval_id: str):
        """Run evaluation with monitoring"""
        self.monitor.emit_event(eval_id, 'info', 'Starting evaluation...')
        
        # Execute code using configured engine
        result = self.engine.execute(code, eval_id)
        
        # Update storage
        evaluation = self.storage.get_evaluation(eval_id)
        evaluation.update(result)
        self.storage.store_evaluation(eval_id, evaluation)
        
        self.monitor.emit_event(eval_id, 'complete', 'Evaluation complete')

# ============== HTTP HANDLERS ==============

# Global platform instance (configured at startup)
platform = None

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible - Abstracted Architecture</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; }
        .config { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .event { margin: 5px 0; padding: 5px; background: white; border-left: 3px solid #17a2b8; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Properly Abstracted</h1>
    
    <div class="config">
        <h3>Current Configuration (via Abstractions)</h3>
        <p><strong>Execution Engine:</strong> <span id="engine">Loading...</span></p>
        <p><strong>Monitoring Service:</strong> <span id="monitor">Loading...</span></p>
        <p><strong>Storage Service:</strong> <span id="storage">Loading...</span></p>
        <p><em>These can be swapped without changing core logic!</em></p>
    </div>
    
    <textarea id="code" placeholder="print('Hello from abstracted platform!')">print('Hello from abstracted platform!')
import time
for i in range(3):
    print(f'Step {i+1}...')
    time.sleep(1)</textarea>
    <br><br>
    <button onclick="runEval()">Run Evaluation</button>
    
    <div class="monitoring">
        <h3>Events</h3>
        <div id="events"></div>
    </div>
    
    <script>
        // Show current configuration
        fetch('/config').then(r => r.json()).then(data => {
            document.getElementById('engine').textContent = data.engine;
            document.getElementById('monitor').textContent = data.monitor;
            document.getElementById('storage').textContent = data.storage;
        });
        
        async function runEval() {
            const code = document.getElementById('code').value;
            const response = await fetch('/eval', {
                method: 'POST',
                body: JSON.stringify({code}),
                headers: {'Content-Type': 'application/json'}
            });
            
            const data = await response.json();
            monitorEvaluation(data.eval_id);
        }
        
        function monitorEvaluation(evalId) {
            const eventSource = new EventSource(`/monitor/${evalId}`);
            const eventsDiv = document.getElementById('events');
            eventsDiv.innerHTML = '';
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event';
                eventDiv.textContent = `${data.timestamp} - ${data.message}`;
                eventsDiv.appendChild(eventDiv);
                
                if (data.type === 'complete') {
                    eventSource.close();
                }
            };
        }
    </script>
</body>
</html>
"""

class AbstractedHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
            
        elif self.path == '/config':
            # Report current configuration
            config = {
                'engine': type(platform.engine).__name__,
                'monitor': type(platform.monitor).__name__,
                'storage': type(platform.storage).__name__
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(config).encode())
            
        elif self.path.startswith('/monitor/'):
            # SSE endpoint
            eval_id = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            last_idx = 0
            while True:
                events = platform.monitor.get_events(eval_id, last_idx)
                for event in events:
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                    self.wfile.flush()
                    last_idx += 1
                    
                    if event['type'] == 'complete':
                        return
                
                time.sleep(0.1)
    
    def do_POST(self):
        if self.path == '/eval':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            eval_id = platform.submit_evaluation(data['code'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'eval_id': eval_id}).encode())
    
    def log_message(self, format, *args):
        pass

# ============== MAIN: CONFIGURE AND RUN ==============

if __name__ == '__main__':
    import sys
    
    # Choose configuration based on command line
    if len(sys.argv) > 1 and sys.argv[1] == '--unsafe':
        print("⚠️  Running with UNSAFE subprocess execution!")
        engine = SubprocessEngine()
    else:
        print("🐳 Running with Docker isolation")
        # Check Docker availability
        try:
            subprocess.run(['docker', '--version'], capture_output=True, check=True)
            subprocess.run(['docker', 'pull', 'python:3.11-slim'], capture_output=True)
            engine = DockerEngine()
        except:
            print("Docker not available, falling back to subprocess")
            engine = SubprocessEngine()
    
    # Create platform with chosen components
    platform = EvaluationPlatform(
        engine=engine,
        monitor=InMemoryMonitor(),
        storage=InMemoryStorage()
    )
    
    # Start server
    server = HTTPServer(('localhost', 8000), AbstractedHandler)
    print("🚀 Crucible Abstracted Platform at http://localhost:8000")
    print("📦 Components can be swapped without changing core logic!")
    server.serve_forever()