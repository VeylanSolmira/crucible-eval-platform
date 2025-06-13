# Understanding platform.py in the Architecture

## What is platform.py?

`platform.py` contains the **Orchestrator/Coordinator** component - it's the glue that brings all other components together and coordinates their interactions.

## Architectural Mapping

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface (HTTP Server)               │
│                 (extreme_mvp_modular.py main)                │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              TestableEvaluationPlatform                      │
│                    (platform.py)                             │
│                                                              │
│  Responsibilities:                                           │
│  • Orchestrates execution flow                               │
│  • Ensures all components are healthy                        │
│  • Coordinates between Engine and Monitor                    │
│  • Generates evaluation IDs                                  │
│  • Enforces safety (won't start if tests fail)              │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│    ExecutionEngine       │  │    MonitoringService         │
│   (execution.py)         │  │    (monitoring.py)           │
│                          │  │                              │
│  • DockerEngine          │  │  • InMemoryMonitor           │
│  • SubprocessEngine      │  │  • (Future: Redis)           │
│  • (Future: K8s Jobs)    │  │  • (Future: OpenTelemetry)   │
└──────────────────────────┘  └──────────────────────────────┘
```

## Why is platform.py needed?

### Without platform.py (Bad Design):
```python
# Web handler would directly manage everything
def handle_evaluation(code):
    engine = DockerEngine()
    monitor = InMemoryMonitor()
    
    # Web handler shouldn't know about:
    eval_id = str(uuid.uuid4())[:8]  # ID generation
    monitor.emit_event(eval_id, 'start', 'Starting')  # Event sequencing
    result = engine.execute(code, eval_id)  # Execution details
    monitor.emit_event(eval_id, 'complete', 'Done')  # More sequencing
    
    return result
```

### With platform.py (Good Design):
```python
# Web handler just delegates
def handle_evaluation(code):
    return platform.evaluate(code)  # Platform handles all orchestration
```

## Current Responsibilities

1. **Component Wiring** - Connects Engine and Monitor
2. **Health Checking** - Runs tests on startup, refuses to start if unhealthy
3. **Evaluation Flow** - Generates IDs, emits events, executes code
4. **Test Aggregation** - Collects tests from all components

## Future Evolution Paths

### As a Microservice API:
```python
# platform.py evolves into api_service.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/evaluate")
async def evaluate(code: str):
    # Platform logic here
    pass

@app.get("/health")
async def health():
    # Component health checks
    pass
```

### As a Workflow Orchestrator:
```python
# platform.py evolves into workflow_orchestrator.py
class WorkflowOrchestrator:
    def create_evaluation_workflow(self, code: str):
        # Step 1: Validate input
        # Step 2: Queue for execution
        # Step 3: Monitor progress
        # Step 4: Collect results
        # Step 5: Store in database
        pass
```

### As a Job Scheduler:
```python
# platform.py evolves into job_scheduler.py
class EvaluationScheduler:
    def schedule_evaluation(self, code: str, priority: int):
        # Create Kubernetes Job
        # Set resource limits
        # Configure security policies
        # Submit to cluster
        pass
```

## Summary

`platform.py` is the **Orchestration Layer** that:

1. **Currently**: Coordinates execution and monitoring in a single process
2. **Future**: Can become an API service, workflow engine, or job scheduler
3. **Purpose**: Keeps business logic separate from infrastructure concerns

It's the "brain" that knows HOW to run an evaluation, while:
- `execution.py` knows HOW to execute code safely
- `monitoring.py` knows HOW to track events
- The web server knows HOW to handle HTTP requests

This separation allows each component to evolve independently!