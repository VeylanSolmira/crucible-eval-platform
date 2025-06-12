# Extreme MVP Implementation Plan

## Philosophy: "What's the simplest thing that could possibly teach us something?"

Instead of Lambda + SQS + Kubernetes, let's build something that runs on your laptop in 30 minutes.

## The Extreme MVP Stack

```
Flask API → SQLite "Queue" → Python subprocess → Local filesystem
```

That's it. No AWS, no Kubernetes, no message brokers.

## Implementation Steps

### Step 1: Simple Flask API (10 minutes)
```python
# app.py
from flask import Flask, request, jsonify
import sqlite3
import uuid
import json
from datetime import datetime

app = Flask(__name__)

# Initialize SQLite "queue"
conn = sqlite3.connect('evaluations.db', check_same_thread=False)
conn.execute('''
    CREATE TABLE IF NOT EXISTS evaluations (
        id TEXT PRIMARY KEY,
        script TEXT,
        status TEXT,
        created_at TEXT,
        result TEXT
    )
''')

@app.route('/submit', methods=['POST'])
def submit_evaluation():
    eval_id = str(uuid.uuid4())
    script = request.json['script']
    
    conn.execute(
        'INSERT INTO evaluations VALUES (?, ?, ?, ?, ?)',
        (eval_id, script, 'queued', datetime.now().isoformat(), None)
    )
    conn.commit()
    
    return jsonify({'eval_id': eval_id, 'status': 'queued'})

@app.route('/status/<eval_id>')
def get_status(eval_id):
    cursor = conn.execute('SELECT * FROM evaluations WHERE id = ?', (eval_id,))
    row = cursor.fetchone()
    if row:
        return jsonify({
            'id': row[0],
            'status': row[2],
            'result': row[4]
        })
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
```

### Step 2: Simple Worker (5 minutes)
```python
# worker.py
import sqlite3
import subprocess
import time
import json

def process_evaluations():
    conn = sqlite3.connect('evaluations.db')
    
    while True:
        # Get next queued evaluation
        cursor = conn.execute(
            'SELECT id, script FROM evaluations WHERE status = "queued" LIMIT 1'
        )
        row = cursor.fetchone()
        
        if row:
            eval_id, script = row
            print(f"Processing {eval_id}")
            
            # Update to running
            conn.execute(
                'UPDATE evaluations SET status = "running" WHERE id = ?',
                (eval_id,)
            )
            conn.commit()
            
            # Run in subprocess with timeout
            try:
                result = subprocess.run(
                    ['python', '-c', script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                output = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
                status = 'completed'
            except subprocess.TimeoutExpired:
                output = {'error': 'Timeout'}
                status = 'failed'
            except Exception as e:
                output = {'error': str(e)}
                status = 'failed'
            
            # Update with results
            conn.execute(
                'UPDATE evaluations SET status = ?, result = ? WHERE id = ?',
                (status, json.dumps(output), eval_id)
            )
            conn.commit()
            print(f"Completed {eval_id}: {status}")
        else:
            time.sleep(1)

if __name__ == '__main__':
    process_evaluations()
```

### Step 3: Simple Web UI (5 minutes)
```html
<!-- templates/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>METR Evaluation Platform - Extreme MVP</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        textarea { width: 100%; height: 200px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .status { margin-top: 20px; padding: 10px; background: #f0f0f0; }
    </style>
</head>
<body>
    <h1>METR Evaluation Platform - Extreme MVP</h1>
    
    <h2>Submit Python Code</h2>
    <textarea id="script" placeholder="print('Hello from evaluation!')"></textarea>
    <br><br>
    <button onclick="submitEval()">Submit Evaluation</button>
    
    <div id="status" class="status"></div>
    
    <script>
        let currentEvalId = null;
        
        async function submitEval() {
            const script = document.getElementById('script').value;
            const response = await fetch('/submit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({script})
            });
            
            const data = await response.json();
            currentEvalId = data.eval_id;
            document.getElementById('status').innerHTML = `Submitted: ${data.eval_id}`;
            
            // Poll for results
            pollStatus();
        }
        
        async function pollStatus() {
            if (!currentEvalId) return;
            
            const response = await fetch(`/status/${currentEvalId}`);
            const data = await response.json();
            
            document.getElementById('status').innerHTML = `
                <strong>Status:</strong> ${data.status}<br>
                <strong>Result:</strong> <pre>${JSON.stringify(data.result, null, 2)}</pre>
            `;
            
            if (data.status === 'queued' || data.status === 'running') {
                setTimeout(pollStatus, 1000);
            }
        }
    </script>
</body>
</html>
```

### Step 4: Run It! (2 minutes)

```bash
# Terminal 1
python app.py

# Terminal 2
python worker.py

# Browser
open http://localhost:5000
```

## What This Extreme MVP Gives You

1. **Real submissions** - Actually submit Python code
2. **Real processing** - Code runs in subprocess
3. **Real results** - See output immediately
4. **Real persistence** - SQLite stores everything
5. **Real learning** - Discover what features matter

## Evolution Path (Let AI Help!)

### Week 1 → 2
- Add basic safety checks (no imports, no file access)
- Add Docker containerization for isolation
- Add result storage to filesystem

### Week 2 → 3
- Replace SQLite queue with PostgreSQL
- Add concurrent workers
- Add resource limits

### Week 3 → 4
- Migrate to cloud (AWS/GCP)
- Add real message queue (SQS/Celery)
- Add Kubernetes for isolation

## Key Insights

1. **You can use it TODAY** - Not next month
2. **Real feedback beats perfect architecture**
3. **Every component is upgradeable**
4. **AI can help with each evolution**

## The Extreme MVP Manifesto

- Ship in hours, not weeks
- Learn from users, not from planning
- Embrace "embarrassingly simple"
- Let AI handle the refactoring
- Focus on the core value loop

## For Your METR Demo

This extreme MVP shows:
1. You can ship fast
2. You understand the core problem
3. You're not over-engineering
4. You can evolve architecture
5. You focus on user value

"We built this in 30 minutes to start learning. Here's what we learned and how we'd evolve it..."