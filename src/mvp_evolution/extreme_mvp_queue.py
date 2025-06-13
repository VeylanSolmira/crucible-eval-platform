#!/usr/bin/env python3
"""
Crucible Evaluation Platform - Adding Queue for Concurrent Evaluations
Evolution: We need to handle multiple users without blocking!

Run with: python extreme_mvp_queue.py [--unsafe]
Then open: http://localhost:8000

This version adds a proper task queue so multiple evaluations can run concurrently.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import uuid
import tempfile
import os
import threading
import time
import queue
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

# In-memory "database" 
evaluations = {}

# ============== QUEUE ABSTRACTION (NEW!) ==============
# The pain: Single-threaded execution blocks all users!

class TaskQueue:
    """
    Simple task queue for concurrent evaluations.
    This abstraction emerged from the pain of blocking execution.
    """
    def __init__(self, max_workers: int = 3):
        self.queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running = True
        self.active_tasks = {}
        
        # Start worker threads
        for i in range(max_workers):
            self.executor.submit(self._worker, f"worker-{i}")
    
    def submit(self, eval_id: str, func, *args, **kwargs):
        """Submit a task to the queue"""
        task = {
            'eval_id': eval_id,
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'submitted_at': datetime.utcnow()
        }
        self.queue.put(task)
        self.active_tasks[eval_id] = 'queued'
    
    def _worker(self, worker_name: str):
        """Worker thread that processes tasks"""
        while self.running:
            try:
                task = self.queue.get(timeout=1)
                eval_id = task['eval_id']
                
                # Update status
                self.active_tasks[eval_id] = 'running'
                
                # Execute the task
                try:
                    task['func'](*task['args'], **task['kwargs'])
                    self.active_tasks[eval_id] = 'completed'
                except Exception as e:
                    self.active_tasks[eval_id] = f'failed: {str(e)}'
                finally:
                    self.queue.task_done()
                    
            except queue.Empty:
                continue
    
    def get_status(self) -> dict:
        """Get queue status"""
        return {
            'queued': self.queue.qsize(),
            'active_tasks': dict(self.active_tasks),
            'workers': self.executor._max_workers
        }
    
    def shutdown(self):
        """Gracefully shutdown the queue"""
        self.running = False
        self.executor.shutdown(wait=True)

# ============== EXISTING ABSTRACTIONS ==============

class MonitoringService(ABC):
    @abstractmethod
    def emit_event(self, eval_id: str, event_type: str, message: str):
        pass
    
    @abstractmethod
    def get_events(self, eval_id: str, start_idx: int = 0) -> List[Dict]:
        pass

class InMemoryMonitor(MonitoringService):
    def __init__(self):
        self.events = {}
        self.lock = threading.Lock()  # Thread safety!
    
    def emit_event(self, eval_id: str, event_type: str, message: str):
        with self.lock:
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
        with self.lock:
            return self.events.get(eval_id, [])[start_idx:]

class ExecutionEngine(ABC):
    def __init__(self, monitor: Optional[MonitoringService] = None):
        self.monitor = monitor
    
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> dict:
        pass
    
    def emit(self, eval_id: str, event_type: str, message: str):
        if self.monitor:
            self.monitor.emit_event(eval_id, event_type, message)

class DockerEngine(ExecutionEngine):
    def execute(self, code: str, eval_id: str) -> dict:
        self.emit(eval_id, 'info', 'Task picked up by worker')
        self.emit(eval_id, 'info', 'Creating temporary file...')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
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

class SubprocessEngine(ExecutionEngine):
    def execute(self, code: str, eval_id: str) -> dict:
        self.emit(eval_id, 'warning', 'Running with UNSAFE subprocess execution!')
        try:
            result = subprocess.run(
                ['python', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {
                'id': eval_id,
                'status': 'completed',
                'output': result.stdout or result.stderr,
                'engine': 'subprocess (UNSAFE!)'
            }
        except subprocess.TimeoutExpired:
            return {
                'id': eval_id,
                'status': 'timeout',
                'error': 'Evaluation timed out after 5 seconds',
                'engine': 'subprocess'
            }
        except Exception as e:
            return {
                'id': eval_id,
                'status': 'error',
                'error': str(e),
                'engine': 'subprocess'
            }

# ============== PLATFORM WITH QUEUE ==============

class EvaluationPlatform:
    """Platform now handles concurrent evaluations!"""
    
    def __init__(self, engine: ExecutionEngine, monitor: MonitoringService, task_queue: TaskQueue):
        self.engine = engine
        self.monitor = monitor
        self.queue = task_queue
        self.evaluations_lock = threading.Lock()
    
    def submit_evaluation(self, code: str) -> str:
        """Submit evaluation to queue"""
        eval_id = str(uuid.uuid4())[:8]
        
        # Initialize evaluation
        with self.evaluations_lock:
            evaluations[eval_id] = {
                'id': eval_id,
                'status': 'queued',
                'output': None,
                'error': None,
                'submitted_at': datetime.utcnow().isoformat()
            }
        
        self.monitor.emit_event(eval_id, 'info', 'Evaluation submitted to queue')
        
        # Submit to queue
        self.queue.submit(eval_id, self._run_evaluation, code, eval_id)
        
        return eval_id
    
    def _run_evaluation(self, code: str, eval_id: str):
        """Run evaluation (called by worker thread)"""
        # Update status
        with self.evaluations_lock:
            evaluations[eval_id]['status'] = 'running'
            evaluations[eval_id]['started_at'] = datetime.utcnow().isoformat()
        
        # Execute
        result = self.engine.execute(code, eval_id)
        
        # Update result
        with self.evaluations_lock:
            evaluations[eval_id].update(result)
            evaluations[eval_id]['completed_at'] = datetime.utcnow().isoformat()
        
        self.monitor.emit_event(eval_id, 'complete', 'Evaluation finished')

# Global instances
platform = None
task_queue = None

# ============== HTML WITH QUEUE STATUS ==============
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Crucible Platform - Concurrent Evaluations!</title>
    <style>
        body { font-family: Arial; max-width: 900px; margin: 50px auto; }
        textarea { width: 100%; height: 120px; font-family: monospace; }
        button { background: #28a745; color: white; padding: 10px 20px; border: none; cursor: pointer; margin-right: 10px; }
        button:disabled { background: #ccc; }
        .success { background: #d4edda; color: #155724; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .info { background: #cce5ff; color: #004085; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .monitoring { background: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; margin: 10px 0; }
        .event { margin: 3px 0; padding: 5px; background: white; font-size: 14px; }
        .event.error { border-left: 3px solid #dc3545; }
        .event.warning { border-left: 3px solid #ffc107; }
        .event.success { border-left: 3px solid #28a745; }
        .event.info { border-left: 3px solid #17a2b8; }
        .queue-status { background: #e8f4f8; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .two-column { display: flex; gap: 20px; }
        .column { flex: 1; }
        pre { background: #f5f5f5; padding: 10px; font-family: monospace; }
    </style>
</head>
<body>
    <h1>Crucible Platform - Now with Concurrent Evaluations!</h1>
    
    <div class="success">
        <h2>Concurrent Processing Unlocked!</h2>
        <p><strong>What's new:</strong></p>
        <ul>
            <li>Task queue with multiple workers (3 by default)</li>
            <li>Non-blocking submission - UI stays responsive</li>
            <li>Multiple evaluations can run simultaneously</li>
            <li>Queue status visibility</li>
        </ul>
        <p><strong>Try it:</strong> Submit multiple evaluations quickly and watch them process concurrently!</p>
    </div>
    
    <div class="queue-status">
        <h3>Queue Status</h3>
        <div id="queue-info">Loading...</div>
    </div>
    
    <div class="two-column">
        <div class="column">
            <h3>Submit New Evaluation</h3>
            <textarea id="code">import time
import random

delay = random.randint(3, 8)
print(f"This evaluation will take {delay} seconds...")

for i in range(delay):
    print(f"Step {i+1}/{delay}")
    time.sleep(1)

print("Complete!")</textarea>
            <br><br>
            <button onclick="runEval()">Submit Evaluation</button>
            <button onclick="submitMultiple()">Submit 5 Evaluations</button>
        </div>
        
        <div class="column">
            <h3>Active Evaluations</h3>
            <div id="active-evals"></div>
        </div>
    </div>
    
    <div class="monitoring">
        <h3>Latest Events</h3>
        <div id="events"></div>
    </div>
    
    <script>
        let activeEvals = new Set();
        let eventSources = new Map();
        
        // Update queue status every second
        setInterval(updateQueueStatus, 1000);
        
        async function updateQueueStatus() {
            const response = await fetch('/queue-status');
            const data = await response.json();
            
            document.getElementById('queue-info').innerHTML = `
                <strong>Queued:</strong> ${data.queued} | 
                <strong>Workers:</strong> ${data.workers} | 
                <strong>Active:</strong> ${Object.keys(data.active_tasks).length}
            `;
            
            // Update active evaluations list
            const activeDiv = document.getElementById('active-evals');
            const activeHtml = Object.entries(data.active_tasks)
                .map(([id, status]) => `<div>${id}: ${status}</div>`)
                .join('') || '<div>No active evaluations</div>';
            activeDiv.innerHTML = activeHtml;
        }
        
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
        
        async function submitMultiple() {
            // Submit 5 evaluations with different delays
            for (let i = 0; i < 5; i++) {
                const code = `import time\\nprint(f"Evaluation ${i+1} starting...")\\ntime.sleep(${3 + i})\\nprint(f"Evaluation ${i+1} complete!")`;
                
                const response = await fetch('/eval', {
                    method: 'POST',
                    body: JSON.stringify({code}),
                    headers: {'Content-Type': 'application/json'}
                });
                
                const data = await response.json();
                monitorEvaluation(data.eval_id);
                
                // Small delay between submissions
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        }
        
        function monitorEvaluation(evalId) {
            if (eventSources.has(evalId)) return;
            
            const eventSource = new EventSource(`/monitor/${evalId}`);
            eventSources.set(evalId, eventSource);
            activeEvals.add(evalId);
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addEvent(data);
                
                if (data.type === 'complete') {
                    eventSource.close();
                    eventSources.delete(evalId);
                    activeEvals.delete(evalId);
                }
            };
        }
        
        function addEvent(event) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${event.type}`;
            const time = new Date(event.timestamp).toLocaleTimeString();
            eventDiv.innerHTML = `<strong>${time}</strong> [${event.eval_id}] ${event.message}`;
            
            // Keep only last 20 events
            if (eventsDiv.children.length >= 20) {
                eventsDiv.removeChild(eventsDiv.firstChild);
            }
            
            eventsDiv.appendChild(eventDiv);
        }
    </script>
</body>
</html>
"""

class QueueHandler(BaseHTTPRequestHandler):
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
            self.wfile.write(json.dumps(task_queue.get_status()).encode())
            
        elif self.path.startswith('/monitor/'):
            eval_id = self.path.split('/')[-1]
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            last_event_idx = 0
            
            while True:
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
            
            eval_id = platform.submit_evaluation(data['code'])
            
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
            print("Using Docker engine for safe execution")
        except:
            print("Docker not available, using subprocess")
            engine = SubprocessEngine()
    
    # Create services
    monitor = InMemoryMonitor()
    engine.monitor = monitor
    task_queue = TaskQueue(max_workers=3)
    
    # Create platform
    platform = EvaluationPlatform(engine, monitor, task_queue)
    
    # Start server
    server = HTTPServer(('localhost', 8000), QueueHandler)
    print("Crucible Platform with Concurrent Evaluations at http://localhost:8000")
    print("Queue: 3 workers processing evaluations concurrently")
    print("Try submitting multiple evaluations to see concurrent processing!")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        task_queue.shutdown()