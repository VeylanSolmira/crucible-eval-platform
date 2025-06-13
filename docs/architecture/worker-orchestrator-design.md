# Worker/Orchestrator Design

## Overview

The Worker (or Orchestrator) is the bridge between the task queue and Kubernetes execution. It transforms high-level evaluation requests into concrete pod executions while managing the complexity of distributed evaluation.

## Core Responsibilities

1. **Input Normalization**: Convert various submission formats into executable containers
2. **Execution Strategy**: Decide how to parallelize and distribute work
3. **Lifecycle Management**: Create, monitor, and clean up Kubernetes pods
4. **Result Aggregation**: Collect and combine outputs from multiple pods
5. **Progress Tracking**: Provide real-time status updates
6. **Safety Enforcement**: Ensure isolation and resource limits

## What Researchers Submit

### Option 1: Python Script (Simplest)
```python
# researcher_eval.py
def evaluate_model(model_endpoint):
    results = []
    for test in my_test_suite:
        response = model.query(test.prompt)
        results.append(check_safety(response))
    return results
```
**Worker Action**: Wrap in standard container with dependencies

### Option 2: Jupyter Notebook
```python
# evaluation.ipynb
# Cell 1: Setup
import safety_eval_toolkit as st

# Cell 2: Run tests
results = st.run_standard_battery(model_id)

# Cell 3: Analysis
st.visualize_results(results)
```
**Worker Action**: Use papermill or nbconvert to execute

### Option 3: Evaluation Config
```yaml
evaluation:
  model: "gpt-4-turbo"
  tests:
    - suite: safety_basics_v2
    - custom: my_tests/edge_cases.py
  parameters:
    temperature: 0.7
    runs_per_test: 10
    timeout: 300
```
**Worker Action**: Parse config, assemble evaluation pipeline

### Option 4: Docker Image (Advanced)
```dockerfile
FROM metr/eval-base:latest
COPY my_evaluation_framework /app
ENV EVAL_CONFIG=/app/config.yaml
CMD ["python", "-m", "eval_runner"]
```
**Worker Action**: Direct execution with added monitoring

## Task Granularity Strategies

### Strategy A: Monolithic Execution
```
Queue Task: "Run full_safety_suite on ModelX"
     ↓
Worker creates 1 pod
     ↓
Pod runs all 200 tests sequentially
```

**Pros**: 
- Simple orchestration
- Low Kubernetes overhead
- Easy progress tracking

**Cons**: 
- No parallelism
- Failure affects entire suite
- Long-running pods

### Strategy B: Fine-Grained Parallelism
```
Queue Task: "Run full_safety_suite on ModelX"
     ↓
Worker analyzes suite (200 tests)
     ↓
Worker creates 200 pods (1 per test)
```

**Pros**: 
- Maximum parallelism
- Failure isolation
- Fine-grained monitoring

**Cons**: 
- High Kubernetes overhead
- Complex result aggregation
- Resource intensive

### Strategy C: Intelligent Batching (Recommended)
```
Queue Task: "Run full_safety_suite on ModelX"
     ↓
Worker analyzes suite complexity
     ↓
Worker creates N pods based on:
  - Test duration estimates
  - Available cluster resources
  - Failure isolation needs
```

**Example batching logic**:
```python
def determine_batch_size(test_suite, cluster_resources):
    if test_suite.estimated_duration < 5_minutes:
        return len(test_suite.tests)  # Single pod
    elif test_suite.has_dangerous_tests:
        return 1  # One pod per test for isolation
    else:
        # Aim for ~10 minute batches
        return max(1, test_suite.test_count // 20)
```

## Worker Implementation

### Core Architecture
```python
class EvaluationOrchestrator:
    def __init__(self):
        self.k8s_client = kubernetes.client.CoreV1Api()
        self.queue = CeleryQueue()
        self.monitor = MonitoringService()
        
    async def process_evaluation(self, task):
        # 1. Normalize input
        container_spec = await self.prepare_container(task)
        
        # 2. Plan execution
        execution_plan = self.create_execution_plan(task)
        
        # 3. Deploy pods
        pods = await self.deploy_pods(container_spec, execution_plan)
        
        # 4. Monitor execution
        results = await self.monitor_pods(pods, task.id)
        
        # 5. Aggregate and store
        final_results = self.aggregate_results(results)
        await self.store_results(task.id, final_results)
```

### Input Normalization
```python
async def prepare_container(self, task):
    if task.type == "script":
        # Inject script into base container
        return {
            "image": "metr/python-eval:latest",
            "command": ["python", "/eval/user_script.py"],
            "files": {"/eval/user_script.py": task.content}
        }
    
    elif task.type == "notebook":
        # Convert notebook to script
        script = nbconvert.export_python(task.content)
        return self.prepare_container(ScriptTask(script))
    
    elif task.type == "config":
        # Use framework container with config
        return {
            "image": "metr/eval-framework:latest",
            "env": {"CONFIG": json.dumps(task.config)}
        }
    
    elif task.type == "docker":
        # User-provided image with monitoring added
        return {
            "image": task.image,
            "sidecars": ["metr/monitor:latest"]
        }
```

### Execution Planning
```python
def create_execution_plan(self, task):
    total_tests = len(task.tests)
    
    # Estimate resource needs
    estimated_duration = sum(t.expected_duration for t in task.tests)
    danger_level = max(t.danger_level for t in task.tests)
    
    # Decide parallelization
    if danger_level > 8 or task.requires_isolation:
        batch_size = 1  # Maximum isolation
    elif estimated_duration < 300:  # 5 minutes
        batch_size = total_tests  # Single pod
    else:
        # Aim for 10-minute batches
        batch_size = max(1, total_tests // (estimated_duration // 600))
    
    return ExecutionPlan(
        total_pods=math.ceil(total_tests / batch_size),
        tests_per_pod=batch_size,
        resource_requests=self.calculate_resources(task),
        isolation_level=self.determine_isolation(danger_level)
    )
```

### Monitoring Integration

The Worker doesn't just create pods and wait - it actively monitors:

```python
async def monitor_pods(self, pods, evaluation_id):
    results = []
    
    for pod in pods:
        # Create monitoring task
        monitor_task = asyncio.create_task(
            self.monitor_single_pod(pod, evaluation_id)
        )
        results.append(monitor_task)
    
    # Gather all results
    return await asyncio.gather(*results)

async def monitor_single_pod(self, pod, evaluation_id):
    while True:
        # Check pod status
        status = await self.k8s_client.read_pod_status(pod.name)
        
        # Stream logs
        logs = await self.k8s_client.read_pod_log(pod.name)
        await self.monitor.publish_logs(evaluation_id, logs)
        
        # Check for safety violations
        if await self.safety_monitor.check_violations(pod):
            await self.emergency_stop(pod)
            return EvaluationResult(status="stopped", reason="safety")
        
        # Update progress
        progress = self.parse_progress(logs)
        await self.monitor.publish_progress(evaluation_id, progress)
        
        if status.phase in ["Succeeded", "Failed"]:
            break
            
        await asyncio.sleep(5)
    
    # Collect final results
    return await self.collect_results(pod)
```

## Monitoring Architecture

The monitoring happens at multiple levels:

### Level 1: Kubernetes Native
- Pod lifecycle events
- Resource usage (CPU, memory)
- Container exit codes
- stdout/stderr logs

### Level 2: Worker Orchestration
- Task progress ("Test 15 of 200")
- Cross-pod coordination
- Result aggregation
- Timeout management

### Level 3: Safety Monitoring
- Network access attempts
- File system violations
- Resource limit approaches
- Suspicious behavior patterns

### Level 4: Business Logic
- Evaluation scoring
- Performance metrics
- Cost tracking
- SLA compliance

## Practical Implementation Path

### Phase 1: MVP (Week 1-2)
- Single pod per evaluation
- Python script support only
- Basic monitoring (logs + status)
- Simple result storage

### Phase 2: Parallelization (Week 3-4)
- Intelligent batching
- Progress tracking across pods
- Result aggregation
- Notebook support

### Phase 3: Advanced Features (Week 5-6)
- Custom Docker images
- Safety monitoring integration
- Resource optimization
- Failure recovery

### Phase 4: Production Hardening (Week 7-8)
- Horizontal scaling of workers
- Dead letter queue handling
- Comprehensive monitoring
- Performance optimization

## Key Design Decisions

1. **Worker-Pod Separation**: Worker never executes evaluation code directly
2. **Stateless Workers**: All state in queue/database, workers can be replaced
3. **Flexible Input**: Support researcher-friendly formats, not just containers
4. **Progressive Complexity**: Simple evaluations stay simple, complex ones possible
5. **Safety First**: Every design choice considers potential model escape

## Technology Choices

- **Queue**: Celery with Redis (familiar, Python-native)
- **Container Runtime**: Kubernetes (industry standard)
- **Monitoring**: Prometheus + custom metrics
- **Storage**: S3 for artifacts, PostgreSQL for metadata
- **Streaming**: Server-Sent Events for progress updates

## Scaling Considerations

- Workers scale horizontally (just add more)
- Each worker can manage multiple evaluations
- Kubernetes cluster limits total concurrent pods
- Database connections pool limits concurrent workers
- Message queue provides natural backpressure

This architecture allows METR to start simple (researchers submit Python scripts) while providing a path to sophisticated distributed evaluation systems.