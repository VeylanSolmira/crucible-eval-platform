# METR Platform Engineering Interview Preparation

## Table of Contents
1. [Role Overview](#role-overview)
2. [Technical Questions](#technical-questions)
   - [Platform Engineering](#platform-engineering)
   - [Kubernetes & Docker](#kubernetes--docker)
   - [Python & FastAPI](#python--fastapi)
   - [Monitoring & Observability](#monitoring--observability)
   - [Security & Safety](#security--safety)
3. [System Design Questions](#system-design-questions)
4. [Behavioral Questions](#behavioral-questions)
5. [Questions to Ask METR](#questions-to-ask-metr)
6. [Key Talking Points](#key-talking-points)
7. [METR-Specific Topics](#metr-specific-topics)

---

## Role Overview

**Position**: Senior Software Engineer - Platform  
**Location**: Berkeley (Hybrid)  
**Team Size**: ~30 people  
**Salary Range**: $257,795 - $340,943

### Core Mission
Design and develop a robust model evaluation platform to determine whether frontier AI models pose a significant threat to humanity.

### Key Requirements Alignment
- ✅ 7+ years software development (You have this)
- ✅ Large-scale systems experience 
- ✅ Containerization and orchestration
- ✅ Cloud infrastructure (AWS)
- ✅ Python expertise
- ✅ TypeScript knowledge
- ✅ Kubernetes experience

---

## Technical Questions

### Platform Engineering

**Q1: How would you design a platform to safely evaluate potentially dangerous AI models?**

**Answer Structure**:
```
1. Isolation Layers:
   - Container runtime isolation (gVisor/Firecracker)
   - Network segmentation with Kubernetes NetworkPolicies
   - Resource limits (CPU, memory, GPU)
   - Filesystem restrictions (read-only roots)

2. Monitoring & Kill Switches:
   - Real-time behavior monitoring
   - Anomaly detection for escape attempts
   - Automatic termination on policy violations
   - Comprehensive audit logging

3. Architecture:
   - API Gateway (FastAPI) → Task Queue (Celery) → K8s Pods
   - Prometheus metrics + custom safety metrics
   - WebSocket updates for real-time monitoring
   - S3/GCS for artifact storage with encryption
```

**Q2: How do you ensure a platform can scale from 10 to 10,000 concurrent evaluations?**

**Answer**:
```
1. Horizontal Scaling:
   - Kubernetes HPA for pod autoscaling
   - Cluster autoscaler for node pools
   - Multiple availability zones

2. Queue Architecture:
   - Celery with Redis/RabbitMQ for task distribution
   - Priority queues for critical evaluations
   - Dead letter queues for failure handling

3. Resource Optimization:
   - Pod packing algorithms
   - GPU scheduling with node selectors
   - Spot instances for cost optimization

4. Data Layer:
   - Read replicas for database
   - Redis clustering for caching
   - CDN for static assets
```

**Q3: How would you handle a model that attempts to escape its sandbox?**

**Answer**:
```python
# Multi-layer defense approach:

1. Runtime Detection:
   - Monitor syscalls with Falco
   - Track network connections
   - File system access patterns
   
2. Network Prevention:
   - Egress-only to specific endpoints
   - DNS filtering
   - Traffic inspection with Envoy
   
3. Immediate Response:
   - SIGKILL the container
   - Preserve forensic data
   - Alert security team
   - Quarantine the evaluation

Example monitoring rule:
```yaml
- rule: Suspicious Network Activity
  desc: Detect unexpected outbound connections
  condition: >
    container and 
    outbound and 
    not allowed_destinations
  output: >
    Suspicious network activity detected 
    (container=%container.name dest=%fd.sip)
  priority: CRITICAL
```

### Kubernetes & Docker

**Q4: How would you implement secure container isolation for AI model evaluation?**

**Answer**:
```yaml
# 1. Pod Security Policy
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: evaluation-pod-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
  readOnlyRootFilesystem: true

# 2. Runtime Class for gVisor
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc

# 3. Network Policy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: evaluation-isolation
spec:
  podSelector:
    matchLabels:
      app: evaluation
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: storage
    ports:
    - protocol: TCP
      port: 443
```

**Q5: How do you handle GPU scheduling in Kubernetes?**

**Answer**:
```yaml
# 1. Node labeling
kubectl label nodes gpu-node-1 accelerator=nvidia-tesla-v100

# 2. Resource requests
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: evaluation
    resources:
      limits:
        nvidia.com/gpu: 1
      requests:
        nvidia.com/gpu: 1
  nodeSelector:
    accelerator: nvidia-tesla-v100

# 3. GPU sharing strategies:
- Time-slicing with NVIDIA GPU Operator
- MIG (Multi-Instance GPU) for A100s
- Virtual GPUs for development

# 4. Monitoring:
- DCGM exporter for Prometheus
- GPU utilization alerts
- Cost optimization through bin packing
```

### Python & FastAPI

**Q6: How would you structure a FastAPI application for high performance?**

**Answer**:
```python
# 1. Project Structure
src/
├── api/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── dependencies.py   # Shared deps
│   ├── middleware/
│   │   ├── auth.py      # JWT validation
│   │   ├── ratelimit.py # Redis-based limiting
│   │   └── metrics.py   # Prometheus metrics
│   ├── routers/
│   │   ├── evaluations.py
│   │   └── health.py
│   └── services/
│       └── evaluation_service.py

# 2. Async patterns
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

app = FastAPI()

# Dependency injection
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

# Concurrent operations
@app.post("/evaluations/batch")
async def create_batch_evaluations(
    requests: List[EvaluationRequest],
    db: AsyncSession = Depends(get_db)
):
    # Concurrent processing
    tasks = [
        process_evaluation(req, db) 
        for req in requests
    ]
    results = await asyncio.gather(*tasks)
    return results

# 3. Performance optimizations
- Connection pooling (asyncpg)
- Redis caching with TTL
- Response compression
- Async background tasks
- Streaming responses for logs
```

**Q7: How do you handle long-running tasks in a FastAPI application?**

**Answer**:
```python
# 1. Celery Integration
from celery import Celery
from fastapi import BackgroundTasks

celery_app = Celery(
    'evaluations',
    broker='redis://localhost:6379',
    backend='redis://localhost:6379'
)

@celery_app.task
def run_evaluation(evaluation_id: str):
    # Long-running evaluation logic
    pass

@app.post("/evaluations")
async def create_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks
):
    # Quick validation and DB insert
    evaluation = await save_evaluation(request)
    
    # Queue for async processing
    task = run_evaluation.delay(evaluation.id)
    
    return {
        "evaluation_id": evaluation.id,
        "task_id": task.id,
        "status": "queued"
    }

# 2. Status tracking
@app.get("/evaluations/{id}/status")
async def get_status(id: str):
    task = AsyncResult(id)
    return {
        "status": task.status,
        "progress": task.info.get('progress', 0),
        "result": task.result if task.ready() else None
    }

# 3. WebSocket for real-time updates
@app.websocket("/ws/evaluations/{id}")
async def evaluation_websocket(websocket: WebSocket, id: str):
    await websocket.accept()
    
    # Subscribe to Redis pubsub
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe(f"evaluation:{id}")
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await websocket.send_json(
                    json.loads(message['data'])
                )
```

### Monitoring & Observability

**Q8: How would you implement comprehensive monitoring for the evaluation platform?**

**Answer**:
```yaml
# 1. Metrics Stack
- Prometheus for metrics collection
- Grafana for visualization
- AlertManager for alerting

# 2. Key Metrics to Track
## System Metrics
- CPU/Memory/Disk usage per evaluation
- GPU utilization and temperature
- Network traffic patterns
- Container restart counts

## Application Metrics
- Evaluation queue depth
- Processing time percentiles
- Success/failure rates
- API response times

## Safety Metrics (METR-specific)
- Capability detection events
- Sandbox escape attempts
- Resource limit violations
- Anomalous behavior patterns

# 3. Implementation
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics definition
evaluation_counter = Counter(
    'evaluations_total', 
    'Total evaluations',
    ['model', 'status', 'safety_level']
)

evaluation_duration = Histogram(
    'evaluation_duration_seconds',
    'Evaluation duration',
    ['model', 'test_suite']
)

active_evaluations = Gauge(
    'active_evaluations',
    'Currently running evaluations'
)

# Usage in code
@app.post("/evaluations")
async def create_evaluation(request: EvaluationRequest):
    start_time = time.time()
    active_evaluations.inc()
    
    try:
        result = await run_evaluation(request)
        evaluation_counter.labels(
            model=request.model,
            status='success',
            safety_level=result.safety_level
        ).inc()
    except Exception as e:
        evaluation_counter.labels(
            model=request.model,
            status='failed',
            safety_level='unknown'
        ).inc()
        raise
    finally:
        active_evaluations.dec()
        evaluation_duration.labels(
            model=request.model,
            test_suite=request.test_suite
        ).observe(time.time() - start_time)
```

**Q9: How do you implement distributed tracing?**

**Answer**:
```python
# OpenTelemetry setup
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument code
@app.post("/evaluations")
async def create_evaluation(request: EvaluationRequest):
    with tracer.start_as_current_span("create_evaluation") as span:
        span.set_attribute("model", request.model)
        span.set_attribute("test_suite", request.test_suite)
        
        # Nested spans for detailed tracing
        with tracer.start_as_current_span("validate_request"):
            validate(request)
            
        with tracer.start_as_current_span("schedule_evaluation"):
            evaluation_id = await schedule(request)
            span.set_attribute("evaluation_id", evaluation_id)
            
        return {"evaluation_id": evaluation_id}
```

### Security & Safety

**Q10: How would you implement defense-in-depth security for AI evaluation?**

**Answer**:
```
1. Network Security:
   - Zero-trust networking with Istio/Linkerd
   - mTLS between all services
   - Egress filtering with explicit allowlists
   - WAF for API protection

2. Container Security:
   - Distroless base images
   - Vulnerability scanning (Trivy)
   - Runtime protection (Falco)
   - Admission controllers (OPA)

3. Access Control:
   - RBAC with principle of least privilege
   - Short-lived tokens (15 min)
   - Audit logging of all actions
   - MFA for privileged operations

4. Data Security:
   - Encryption at rest (KMS)
   - Encryption in transit (TLS 1.3)
   - Secrets management (Vault)
   - PII detection and masking

Example OPA policy:
```rego
package kubernetes.admission

deny[msg] {
  input.request.kind.kind == "Pod"
  input.request.object.metadata.labels.app == "evaluation"
  not input.request.object.spec.runtimeClassName == "gvisor"
  msg := "Evaluation pods must use gVisor runtime"
}
```

---

## System Design Questions

### Q11: Design a system to evaluate 1000 AI models per day with safety constraints

**Answer Structure**:

```
1. Requirements Gathering:
   - Models: Size (1B-1T params), Types (LLM, multimodal)
   - Evaluations: Duration (5 min - 24 hours), Resources (CPU/GPU)
   - Safety: Isolation levels, monitoring needs
   - Scale: Peak load, growth projections

2. High-Level Architecture:
   
   [Load Balancer]
          |
   [API Gateway Cluster]
          |
   [Message Queue (Kafka)]
          |
   [Scheduler Service]
          |
   [Kubernetes Clusters]
      /       |       \
   [GPU]    [CPU]   [TPU]
   Nodes    Nodes   Nodes

3. Detailed Components:

   a) Submission Layer:
      - Rate limiting per organization
      - Request validation
      - Priority queuing
   
   b) Scheduling Layer:
      - Resource allocation algorithm
      - Bin packing for efficiency
      - Preemption for high-priority evals
   
   c) Execution Layer:
      - Pod templates per model size
      - Auto-scaling based on queue depth
      - Spot instance integration
   
   d) Monitoring Layer:
      - Real-time capability detection
      - Resource usage tracking
      - Anomaly detection ML pipeline

4. Safety Mechanisms:
   - Network air-gapping for high-risk models
   - Incremental evaluation (stop on first failure)
   - Human-in-the-loop for critical decisions
   - Automated containment protocols

5. Capacity Planning:
   - 1000 models/day = 42/hour average
   - Peak handling: 100/hour
   - Resource pool: 500 GPUs across regions
   - Cost optimization through scheduling
```

### Q12: How would you design a real-time monitoring system for AI safety?

**Answer**:
```
1. Data Collection Pipeline:
   
   [Evaluation Pods] → [Fluentd] → [Kafka] → [Stream Processing]
                    ↓                      ↓
                [Metrics]            [Elasticsearch]
                    ↓                      ↓
              [Prometheus]          [Kibana Dashboards]

2. Stream Processing Architecture:
   - Apache Flink for complex event processing
   - Sliding windows for behavior patterns
   - ML models for anomaly detection
   
3. Alert Categories:
   Priority 1: Immediate termination
   - Network escape attempts
   - Resource limit violations
   - Unauthorized file access
   
   Priority 2: Investigation required
   - Unusual computation patterns
   - Repeated failed attempts
   - Performance anomalies
   
   Priority 3: Logging only
   - Normal failures
   - Resource usage spikes
   - Model errors

4. Response Automation:
```python
class SafetyMonitor:
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.ml_detector = AnomalyDetector()
        
    async def process_event(self, event: Event):
        # Rule-based detection
        if self.rules_engine.is_critical(event):
            await self.emergency_shutdown(event.pod_id)
            await self.alert_security_team(event)
            
        # ML-based detection
        anomaly_score = await self.ml_detector.score(event)
        if anomaly_score > THRESHOLD:
            await self.quarantine_pod(event.pod_id)
            await self.request_human_review(event)
```

---

## Behavioral Questions

### Q13: Tell me about a time you had to make a critical technical decision under pressure.

**STAR Format Answer**:
- **Situation**: At previous company, our ML training platform experienced cascading failures during a critical model training run for a major client
- **Task**: Had to quickly diagnose and implement a fix without losing 72 hours of training progress
- **Action**: 
  - Set up emergency war room with stakeholders
  - Implemented distributed checkpointing system in 4 hours
  - Created failover mechanism to backup GPU cluster
  - Added real-time monitoring to prevent future issues
- **Result**: Saved $50K in compute costs, delivered model on time, system now standard across company

### Q14: How do you handle disagreements about technical architecture?

**Answer Structure**:
1. **Listen First**: Understand all perspectives and concerns
2. **Data-Driven**: Use benchmarks, prototypes, or spikes to gather evidence
3. **Document Trade-offs**: Create decision matrix with pros/cons
4. **Seek Consensus**: Find middle ground or hybrid approaches
5. **Commit**: Once decided, fully support the decision

**Example**: "In designing our API gateway, team was split between GraphQL and REST. I proposed building a small prototype of each for our most complex use case. We measured development time, performance, and client complexity. REST won for simplicity, but we adopted GraphQL's field selection pattern for efficiency."

### Q15: Describe your approach to mentoring junior engineers.

**Answer**:
1. **Structured Onboarding**: Create learning paths with clear milestones
2. **Pair Programming**: Regular sessions on real problems
3. **Code Reviews**: Detailed feedback focusing on 'why' not just 'what'
4. **Ownership**: Assign complete features with support
5. **Growth Planning**: Quarterly discussions about career goals

"I mentored a junior engineer who grew to lead our monitoring infrastructure. Started with small Grafana dashboards, gradually increased complexity, and after 18 months they presented our observability strategy to the CTO."

---

## Questions to Ask METR

### About the Evaluation Infrastructure

1. **Current Scale**: "How many evaluations are you running daily/weekly? What's the typical duration and resource requirement?"

2. **Safety Incidents**: "Can you share examples of safety measures that have been triggered? How do you balance safety with evaluation completeness?"

3. **Model Diversity**: "What types of models are you evaluating beyond LLMs? How do you handle multimodal or agent-based systems?"

4. **Infrastructure Evolution**: "How has your evaluation infrastructure evolved since the autonomous replication work? What are the next big challenges?"

### About the Team & Culture

5. **Team Structure**: "How is the platform team structured? What's the split between infrastructure and application development?"

6. **Research Collaboration**: "How closely do platform engineers work with researchers? Can you give an example of a recent collaboration?"

7. **Technical Decisions**: "Who drives architectural decisions? How do you balance researcher needs with platform stability?"

8. **Growth**: "You've grown to 30 people - how are you maintaining the fast-paced culture while adding operational rigor?"

### About the Role

9. **Immediate Priorities**: "What would success look like for this role in the first 90 days? First year?"

10. **Technical Challenges**: "What's the most technically challenging problem the platform team is facing right now?"

11. **Innovation Opportunities**: "Where do you see opportunities for the platform to push the boundaries of what's possible in AI safety evaluation?"

12. **Career Growth**: "How have other platform engineers grown their careers at METR? What paths are available?"

### About Safety & Impact

13. **Policy Influence**: "How does platform work influence safety policies at AI labs? Can you share a specific example?"

14. **Open Source**: "What's your philosophy on open-sourcing evaluation tools? How do you balance transparency with security?"

15. **Future Vision**: "Where do you see METR's evaluation capabilities in 3-5 years? How might AGI development change your approach?"

---

## Key Talking Points from Your Project

### 1. Architecture Decisions

**Microservices with Clear Boundaries**
- "I designed the evaluation platform with clear service boundaries - API Gateway, Orchestrator, and Execution Environment. This allows independent scaling and development."
- "Used Domain-Driven Design principles to define service boundaries based on business capabilities"

**Event-Driven Architecture**
- "Implemented event-driven patterns using Celery and Redis for async processing"
- "This enables real-time monitoring while keeping the API responsive"

### 2. Safety Mechanisms

**Multi-Layer Isolation**
- "Implemented defense-in-depth with gVisor runtime, network policies, and resource limits"
- "Each layer can independently prevent escape - no single point of failure"

**Proactive Monitoring**
- "Built anomaly detection that learns normal behavior patterns"
- "Can detect subtle escape attempts that rule-based systems might miss"

### 3. Scalability Approach

**Horizontal Scaling at Every Layer**
- "Designed stateless services that scale linearly"
- "Used Kubernetes HPA with custom metrics for intelligent scaling"

**Resource Optimization**
- "Implemented bin packing algorithm for GPU scheduling"
- "Achieved 85% utilization while maintaining isolation"

### 4. Developer Experience

**Self-Service Platform**
- "Created Python SDK for researchers to define custom evaluations"
- "Automated OpenAPI client generation for multiple languages"

**Comprehensive Documentation**
- "Every architectural decision documented with alternatives considered"
- "Runbooks for common operational scenarios"

---

## METR-Specific Topics to Master

### 1. Autonomous Replication Prevention
- Understand how models might attempt self-replication
- Network monitoring for unauthorized connections
- Filesystem restrictions to prevent code execution
- Resource limits to prevent fork bombs

### 2. Capability Evaluation Frameworks
- Difference between behavioral and capability testing
- Incremental evaluation strategies
- Sandboxed execution environments
- Result verification and validation

### 3. AI Safety Concepts
- Alignment vs Capabilities
- Mesa-optimization risks
- Deceptive alignment
- Instrumental goals

### 4. Evaluation Reproducibility
- Deterministic environments
- Seed management for randomness
- Version pinning strategies
- Artifact preservation

### 5. Regulatory Landscape
- Understanding of AI safety policies
- Lab safety frameworks (OpenAI, Anthropic, DeepMind)
- Government interest in AI evaluation
- International cooperation needs

---

## Technical Deep Dives to Prepare

1. **Kubernetes Security**
   - Pod Security Standards
   - Admission Controllers (OPA, Kyverno)
   - Runtime security (Falco, gVisor)
   - Network policies in detail

2. **Python Async Patterns**
   - AsyncIO vs Threading vs Multiprocessing
   - Async context managers
   - Connection pooling
   - Backpressure handling

3. **Distributed Systems**
   - CAP theorem applications
   - Consensus algorithms
   - Circuit breakers
   - Saga patterns

4. **Container Isolation**
   - Linux namespaces and cgroups
   - gVisor architecture
   - Firecracker (KVM-based)
   - SELinux/AppArmor

5. **Monitoring at Scale**
   - Prometheus architecture
   - PromQL expertise
   - Cardinality management
   - Long-term storage strategies

---

## Mock Scenarios to Practice

### Scenario 1: Emergency Response
"A model in evaluation just made 1000 DNS queries in 1 second to various IP addresses. Walk me through your response."

### Scenario 2: Scaling Challenge  
"We just partnered with a major lab and need to scale from 100 to 10,000 daily evaluations in 3 months. What's your plan?"

### Scenario 3: Technical Debt
"The evaluation platform was built quickly and has accumulated technical debt. How do you modernize while maintaining 24/7 operations?"

### Scenario 4: Cross-Team Collaboration
"Researchers want a new evaluation type that requires root access. How do you handle this request?"

---

## Final Interview Tips

1. **Show Safety-First Thinking**: Always mention safety considerations in your answers
2. **Demonstrate Scale Experience**: Use specific numbers from past projects
3. **Balance Theory and Practice**: Show you can both design and implement
4. **Ask Clarifying Questions**: Shows thoughtful problem-solving approach
5. **Be Honest About Unknowns**: Explain how you'd learn what you don't know
6. **Show Enthusiasm**: This is meaningful work with real impact on AI safety

Remember: METR values technical excellence, safety consciousness, and collaborative problem-solving. Show that you can build robust systems while moving fast in a startup environment.