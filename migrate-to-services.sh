#!/bin/bash
# Migration script: Restructure evolution/ into service-oriented architecture under src/
# This script creates a microservices-ready structure while maintaining the monolithic option

set -e

echo "🔄 Migrating to service-oriented architecture"
echo "============================================"

# Check if we're in the right directory
if [ ! -d "evolution" ]; then
    echo "❌ Error: evolution/ directory not found"
    echo "   Please run this script from the metr-eval-platform root directory"
    exit 1
fi

# Create src directory structure
echo "📁 Creating service directories..."
mkdir -p src/{execution-engine,api-gateway,monitoring,storage,queue,web-frontend,event-bus,security-scanner,platform,shared}
mkdir -p src/execution-engine/engines
mkdir -p src/api-gateway/{routes,handlers}
mkdir -p src/monitoring/{collectors,exporters}
mkdir -p src/storage/backends
mkdir -p src/queue/handlers
mkdir -p src/web-frontend/{simple,advanced,react}
mkdir -p src/event-bus/handlers
mkdir -p src/security-scanner/scenarios
mkdir -p src/shared/{types,utils}

# Step 1: Copy the main platform file (keeps monolithic option)
echo "📋 Copying main platform orchestrator..."
cp evolution/extreme_mvp_frontier_events.py src/platform/
cp evolution/*.py src/platform/ 2>/dev/null || true

# Step 2: Move components to their respective services
echo "🚚 Moving components to service directories..."

# Execution Engine Service
if [ -f "evolution/components/execution.py" ]; then
    echo "  - Execution engines..."
    cp evolution/components/execution.py src/execution-engine/engines/base.py
    
    # Extract specific engine classes into separate files
    cat > src/execution-engine/engines/__init__.py << 'EOF'
"""Execution engines for running code in various isolation levels"""
from .base import ExecutionEngine
from .subprocess import SubprocessEngine
from .docker import DockerEngine
from .gvisor import GVisorEngine

__all__ = ['ExecutionEngine', 'SubprocessEngine', 'DockerEngine', 'GVisorEngine']
EOF

    # Create subprocess engine
    cat > src/execution-engine/engines/subprocess.py << 'EOF'
"""Subprocess execution engine - NO ISOLATION (development only)"""
import subprocess
import tempfile
import os
from typing import Dict, Any
from .base import ExecutionEngine


class SubprocessEngine(ExecutionEngine):
    """Direct subprocess execution - UNSAFE, development only"""
    
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        """Execute code in subprocess (no isolation)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return {
                'eval_id': eval_id,
                'output': result.stdout,
                'error': result.stderr,
                'exit_code': result.returncode,
                'engine': 'subprocess'
            }
        except subprocess.TimeoutExpired:
            return {
                'eval_id': eval_id,
                'error': 'Execution timeout',
                'exit_code': -1,
                'engine': 'subprocess'
            }
        finally:
            os.unlink(temp_file)
    
    def self_test(self) -> Dict[str, Any]:
        """Test subprocess engine"""
        result = self.execute("print('Subprocess engine test')", "test-subprocess")
        return {
            'engine': 'subprocess',
            'passed': result.get('output', '').strip() == 'Subprocess engine test',
            'result': result
        }
EOF

    # Create main.py for execution service
    cat > src/execution-engine/main.py << 'EOF'
"""Execution Engine Service - Handles code execution in isolated environments"""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from engines import SubprocessEngine, DockerEngine, GVisorEngine

app = FastAPI(title="Execution Engine Service")

# Initialize engine based on environment
ENGINE_TYPE = os.environ.get('ENGINE_TYPE', 'docker')
if ENGINE_TYPE == 'subprocess':
    engine = SubprocessEngine()
elif ENGINE_TYPE == 'gvisor':
    engine = GVisorEngine()
else:
    engine = DockerEngine()


class ExecutionRequest(BaseModel):
    code: str
    eval_id: str
    timeout: Optional[int] = 30


@app.post("/execute")
async def execute_code(request: ExecutionRequest):
    """Execute code in isolated environment"""
    try:
        result = engine.execute(request.code, request.eval_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    test_result = engine.self_test()
    return {
        "status": "healthy" if test_result['passed'] else "unhealthy",
        "engine": ENGINE_TYPE,
        "test": test_result
    }
EOF
fi

# API Gateway Service
if [ -f "evolution/components/api.py" ]; then
    echo "  - API Gateway..."
    cp evolution/components/api.py src/api-gateway/handlers/api_handler.py
    
    cat > src/api-gateway/main.py << 'EOF'
"""API Gateway Service - Main entry point for all API requests"""
from fastapi import FastAPI
from handlers.api_handler import APIHandler

app = FastAPI(title="Crucible API Gateway")
api_handler = APIHandler()

# Mount API routes
app.mount("/api", api_handler.get_app())

@app.get("/")
async def root():
    return {"service": "API Gateway", "version": "1.0.0"}
EOF
fi

# Monitoring Service
if [ -f "evolution/components/monitoring.py" ]; then
    echo "  - Monitoring..."
    cp evolution/components/monitoring.py src/monitoring/collectors/base.py
    
    cat > src/monitoring/main.py << 'EOF'
"""Monitoring Service - Collects and exports metrics"""
from fastapi import FastAPI
from prometheus_client import make_asgi_app

app = FastAPI(title="Monitoring Service")

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/")
async def root():
    return {"service": "Monitoring", "version": "1.0.0"}
EOF
fi

# Storage Service
if [ -f "evolution/components/storage.py" ]; then
    echo "  - Storage..."
    cp evolution/components/storage.py src/storage/backends/base.py
    
    cat > src/storage/main.py << 'EOF'
"""Storage Service - Handles persistent storage for evaluations"""
from fastapi import FastAPI, HTTPException
from typing import Optional
import os

app = FastAPI(title="Storage Service")

# Initialize storage backend based on environment
STORAGE_TYPE = os.environ.get('STORAGE_TYPE', 'filesystem')

@app.get("/evaluations/{eval_id}")
async def get_evaluation(eval_id: str):
    """Retrieve evaluation by ID"""
    # Implementation here
    return {"eval_id": eval_id, "status": "completed"}

@app.post("/evaluations")
async def store_evaluation(evaluation: dict):
    """Store new evaluation"""
    # Implementation here
    return {"stored": True, "id": evaluation.get('eval_id')}
EOF
fi

# Queue Service
if [ -f "evolution/components/queue.py" ]; then
    echo "  - Queue..."
    cp evolution/components/queue.py src/queue/handlers/base.py
    
    cat > src/queue/main.py << 'EOF'
"""Queue Service - Manages evaluation task queue"""
from fastapi import FastAPI
from typing import List

app = FastAPI(title="Queue Service")

# In-memory queue for MVP
task_queue: List[dict] = []

@app.post("/enqueue")
async def enqueue_task(task: dict):
    """Add task to queue"""
    task_queue.append(task)
    return {"queued": True, "position": len(task_queue)}

@app.get("/dequeue")
async def dequeue_task():
    """Get next task from queue"""
    if task_queue:
        return task_queue.pop(0)
    return None

@app.get("/status")
async def queue_status():
    """Get queue status"""
    return {
        "queue_length": len(task_queue),
        "tasks": task_queue[:10]  # First 10 tasks
    }
EOF
fi

# Web Frontend Service
if [ -f "evolution/components/web_frontend.py" ]; then
    echo "  - Web Frontend..."
    cp evolution/components/web_frontend.py src/web-frontend/base.py
    
    cat > src/web-frontend/main.py << 'EOF'
"""Web Frontend Service - Serves the web UI"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from base import SimpleHTTPFrontend, AdvancedHTMLFrontend, ReactFrontend
import os

app = FastAPI(title="Web Frontend Service")

# Select frontend based on environment
FRONTEND_TYPE = os.environ.get('FRONTEND_TYPE', 'advanced')

if FRONTEND_TYPE == 'simple':
    frontend = SimpleHTTPFrontend()
elif FRONTEND_TYPE == 'react':
    frontend = ReactFrontend()
else:
    frontend = AdvancedHTMLFrontend()

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return frontend.get_index_html()
EOF
fi

# Event Bus Service
if [ -f "evolution/components/event_bus.py" ]; then
    echo "  - Event Bus..."
    cp evolution/components/event_bus.py src/event-bus/handlers/base.py
    
    cat > src/event-bus/main.py << 'EOF'
"""Event Bus Service - Coordinates events between services"""
from fastapi import FastAPI, WebSocket
from typing import List
import json

app = FastAPI(title="Event Bus Service")

# Active WebSocket connections
connections: List[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events"""
    await websocket.accept()
    connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast to all connections
            for conn in connections:
                if conn != websocket:
                    await conn.send_text(data)
    except:
        connections.remove(websocket)

@app.post("/publish")
async def publish_event(event: dict):
    """Publish event to all subscribers"""
    event_json = json.dumps(event)
    for conn in connections:
        await conn.send_text(event_json)
    return {"published": True, "subscribers": len(connections)}
EOF
fi

# Security Scanner Service
if [ -d "evolution/security_scenarios" ]; then
    echo "  - Security Scanner..."
    cp -r evolution/security_scenarios/* src/security-scanner/scenarios/
    
    cat > src/security-scanner/main.py << 'EOF'
"""Security Scanner Service - Runs security scenarios against execution engines"""
from fastapi import FastAPI, BackgroundTasks
from scenarios.security_runner import SecurityTestRunner
from scenarios.safe_demo_scenarios import SAFE_DEMO_SCENARIOS
from scenarios.attack_scenarios import ATTACK_SCENARIOS

app = FastAPI(title="Security Scanner Service")

@app.post("/scan/demo")
async def run_demo_scan(background_tasks: BackgroundTasks):
    """Run safe demo security scan"""
    def run_scan():
        runner = SecurityTestRunner(scenarios=SAFE_DEMO_SCENARIOS, include_subprocess=True)
        runner.run_all_scenarios()
    
    background_tasks.add_task(run_scan)
    return {"status": "Demo scan started"}

@app.post("/scan/full")
async def run_full_scan(background_tasks: BackgroundTasks):
    """Run full security scan (dangerous!)"""
    def run_scan():
        runner = SecurityTestRunner(scenarios=ATTACK_SCENARIOS, include_subprocess=False)
        runner.run_all_scenarios()
    
    background_tasks.add_task(run_scan)
    return {"status": "Full scan started", "warning": "This runs real attacks!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Security Scanner"}
EOF
fi

# Move shared components
if [ -f "evolution/components/base.py" ]; then
    echo "  - Shared components..."
    cp evolution/components/base.py src/shared/utils/base_component.py
fi

# Step 3: Create Dockerfiles for each service
echo "🐳 Creating Dockerfiles..."

# Execution Engine Dockerfile
cat > src/execution-engine/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install Docker client for Docker-in-Docker
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
EOF

# API Gateway Dockerfile
cat > src/api-gateway/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Step 4: Create docker-compose for local development
echo "🐳 Creating docker-compose.yml..."
cat > src/docker-compose.yml << 'EOF'
version: '3.8'

services:
  execution-engine:
    build: ./execution-engine
    ports:
      - "8001:8001"
    environment:
      - ENGINE_TYPE=docker
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - crucible-net

  api-gateway:
    build: ./api-gateway
    ports:
      - "8000:8000"
    depends_on:
      - execution-engine
      - storage
      - queue
    networks:
      - crucible-net

  monitoring:
    build: ./monitoring
    ports:
      - "8002:8002"
    networks:
      - crucible-net

  storage:
    build: ./storage
    ports:
      - "8003:8003"
    volumes:
      - evaluation-data:/data
    networks:
      - crucible-net

  queue:
    build: ./queue
    ports:
      - "8004:8004"
    networks:
      - crucible-net

  web-frontend:
    build: ./web-frontend
    ports:
      - "8080:8080"
    environment:
      - FRONTEND_TYPE=advanced
    networks:
      - crucible-net

  event-bus:
    build: ./event-bus
    ports:
      - "8005:8005"
    networks:
      - crucible-net

  security-scanner:
    build: ./security-scanner
    ports:
      - "8006:8006"
    depends_on:
      - execution-engine
    networks:
      - crucible-net

networks:
  crucible-net:
    driver: bridge

volumes:
  evaluation-data:
EOF

# Step 5: Create requirements.txt for each service
echo "📋 Creating requirements files..."
for service in execution-engine api-gateway monitoring storage queue web-frontend event-bus security-scanner; do
    cat > src/$service/requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
prometheus-client==0.19.0
httpx==0.25.2
EOF
done

# Step 6: Update imports in platform orchestrator
echo "📝 Updating imports in platform files..."
sed -i.bak 's|from components|from shared.utils|g' src/platform/*.py 2>/dev/null || true
rm src/platform/*.bak 2>/dev/null || true

# Step 7: Create service registry
cat > src/shared/service_registry.py << 'EOF'
"""Service Registry - Maintains service endpoints"""

SERVICES = {
    'execution-engine': 'http://localhost:8001',
    'api-gateway': 'http://localhost:8000',
    'monitoring': 'http://localhost:8002',
    'storage': 'http://localhost:8003',
    'queue': 'http://localhost:8004',
    'web-frontend': 'http://localhost:8080',
    'event-bus': 'http://localhost:8005',
    'security-scanner': 'http://localhost:8006',
}

def get_service_url(service_name: str) -> str:
    """Get service URL by name"""
    return SERVICES.get(service_name, 'http://localhost:8000')
EOF

# Step 8: Create Kubernetes manifests directory
echo "☸️  Creating Kubernetes manifests..."
mkdir -p src/k8s/{services,deployments,configmaps}

# Step 9: Update documentation references
echo "📚 Updating documentation..."
find docs -type f -name "*.md" -exec sed -i.bak 's|evolution/|src/platform/|g' {} \;
find docs -type f -name "*.md" -exec sed -i.bak 's|/evolution|/src/platform|g' {} \;
rm docs/*.bak 2>/dev/null || true

# Step 10: Update systemd and terraform references
echo "🔧 Updating infrastructure references..."
if [ -d "infrastructure/systemd" ]; then
    find infrastructure/systemd -type f \( -name "*.service" -o -name "*.sh" \) -exec sed -i.bak 's|/evolution/|/src/platform/|g' {} \;
    rm infrastructure/systemd/*.bak 2>/dev/null || true
fi

if [ -d "infrastructure/terraform" ]; then
    find infrastructure/terraform -type f -name "*.tf" -exec sed -i.bak 's|evolution/|src/platform/|g' {} \;
    rm infrastructure/terraform/*.bak 2>/dev/null || true
fi

# Step 11: Create README for new structure
cat > src/README.md << 'EOF'
# Crucible Evaluation Platform - Service Architecture

## Structure

This directory contains the microservices that make up the Crucible platform:

### Core Services

- **execution-engine/** - Handles code execution in isolated environments (Docker/gVisor)
- **api-gateway/** - Main API entry point, routes requests to appropriate services
- **monitoring/** - Metrics collection and export (Prometheus/Grafana ready)
- **storage/** - Persistent storage for evaluations and results
- **queue/** - Task queue management for evaluation jobs
- **web-frontend/** - Web UI service (Simple HTML → Advanced → React)
- **event-bus/** - Event coordination between services
- **security-scanner/** - Security testing scenarios

### Supporting Directories

- **platform/** - Monolithic platform orchestrator (for development/testing)
- **shared/** - Shared utilities and base classes
- **lambda/** - AWS Lambda functions
- **frontend/** - React dashboard (separate from web-frontend service)

## Development

### Run all services locally:
```bash
cd src
docker-compose up
```

### Run monolithic version:
```bash
cd src/platform
python extreme_mvp_frontier_events.py
```

### Run individual service:
```bash
cd src/execution-engine
pip install -r requirements.txt
uvicorn main:app --reload
```

## Service URLs (Local Development)

- API Gateway: http://localhost:8000
- Execution Engine: http://localhost:8001
- Monitoring: http://localhost:8002
- Storage: http://localhost:8003
- Queue: http://localhost:8004
- Event Bus: http://localhost:8005
- Security Scanner: http://localhost:8006
- Web Frontend: http://localhost:8080

## Deployment

Each service has its own Dockerfile and can be deployed independently to Kubernetes.
See `/k8s` directory for Kubernetes manifests.
EOF

# Step 12: Clean up and summary
echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Summary:"
echo "  - Created service-oriented architecture in src/"
echo "  - Each component is now a separate service"
echo "  - Monolithic version preserved in src/platform/"
echo "  - Docker Compose configuration for local development"
echo "  - Kubernetes-ready structure"
echo ""
echo "🚀 Next steps:"
echo "  1. Review the new structure: tree src/ -L 2"
echo "  2. Test monolithic version: cd src/platform && python extreme_mvp_frontier_events.py"
echo "  3. Test services: cd src && docker-compose up"
echo "  4. Remove old evolution directory: rm -rf evolution"
echo ""
echo "📝 Note: You may need to:"
echo "  - Update import statements in the separated files"
echo "  - Add service-specific dependencies to requirements.txt"
echo "  - Configure inter-service communication"
echo "  - Update your IDE workspace settings"