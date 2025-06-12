# Crucible Evaluation Platform
## Building AI Safety Infrastructure Through Iterative Design
### From Extreme MVP to Production-Ready Platform

---

## The Vision

**Democratizing AI Safety Evaluation**

- Enable distributed safety research
- Lower barriers to entry
- Maintain security standards
- Open and extensible platform

*Why "Crucible"? Where materials are tested under extreme conditions*

---

## The Challenge

**Core Requirements (Our North Star)**

1. 🛡️ **Safely evaluate AI models** that might try to escape
2. 👁️ **Monitor evaluations** in real-time  
3. 📈 **Scale to many concurrent evaluations**
4. 🖥️ **Provide a user interface** for researchers

Every decision traces back to these four.

---

## Our Journey: From Danger to Safety

1. **Extreme MVP** - Feel the danger viscerally
2. **Evolution Series** - Progressive enhancement
3. **Modular Architecture** - TRACE-AI components
4. **Infrastructure Deployment** - Real AWS resources
5. **Security Hardening** - SSH, VPC, comprehensive guide
6. **OpenAPI Integration** - Contract-first development
7. **Event-Driven Architecture** - Loose coupling
8. **Production Readiness** - METR submission ready

---

# Act 1: The Extreme MVP
## Feeling the Danger

---

## 🚨 DEMO: The Original Sin

**`python extreme_mvp.py`**

```python
# 100 lines of PURE DANGER
result = subprocess.run(
    ['python', '-c', code],  # NO ISOLATION!
    capture_output=True,
    text=True,
    timeout=30
)
```

When you hover over "Run Evaluation", you feel **fear**.

---

## The Visceral Lesson

Your fear mirrors AI safety concerns:

| Your Fear | AI Safety Fear |
|-----------|----------------|
| "Could delete my files" | "AI could self-replicate" |
| "Could steal my data" | "AI could exfiltrate info" |
| "Could compromise system" | "AI could escape sandbox" |

*The danger is real in both cases*

---

# Act 2: The Evolution Series
## Progressive Enhancement Through Code

---

## The Evolution Tree

```
extreme_mvp.py (100 lines, UNSAFE)
    ├── extreme_mvp_queue.py (+50 lines)
    │   └── Added async task queue
    ├── extreme_mvp_monitoring.py (+80 lines)
    │   └── Added real-time events
    ├── extreme_mvp_docker.py (+100 lines)
    │   └── Added container isolation
    ├── extreme_mvp_gvisor.py (+150 lines)
    │   └── Added kernel-level security
    └── extreme_mvp_advanced.py (+300 lines)
        └── Full production features
```

Each file **works independently** but builds on concepts.

---

## 🚨 DEMO: Evolution in Action

```bash
# Feel the progression
python extreme_mvp.py                # Terrifying
python extreme_mvp_docker.py        # Safer
python extreme_mvp_gvisor.py        # Production-ready

# Compare the code
diff extreme_mvp.py extreme_mvp_queue.py
```

**Key insight**: Safety isn't binary, it's progressive.

---

# Act 3: Modular Architecture
## TRACE-AI Components

---

## Component Independence

```python
# Each component is self-contained
from components import (
    SubprocessEngine,      # Execution
    DockerEngine,         # + Container isolation  
    GVisorEngine,         # + Kernel isolation
    TaskQueue,            # Async processing
    AdvancedMonitor,      # Event tracking
    FileStorage,          # Persistence
    RESTfulAPI           # HTTP interface
)
```

**TestableComponent**: Every component self-tests!

---

## 🚨 DEMO: Component Testing

```bash
python test_components.py

# Output:
Testing EXECUTION Component
✅ SubprocessEngine: PASSED
✅ DockerEngine: PASSED  
✅ GVisorEngine: PASSED

Testing MONITORING Component
✅ AdvancedMonitor: PASSED
...
```

Each component can evolve to a microservice.

---

# Act 4: Real Infrastructure
## From Laptop to Cloud

---

## Infrastructure as Code

```bash
cd infrastructure/terraform
tofu apply

# Created:
✅ EC2 instance (ubuntu@44.246.137.198)
✅ API Gateway + Lambda
✅ SQS Queue with DLQ
✅ Security Groups
```

**From 100 lines to real AWS resources!**

---

## 🚨 DEMO: SSH Security Evolution

**Before (DANGEROUS):**
```hcl
ingress {
  from_port   = 22
  cidr_blocks = ["0.0.0.0/0"]  # 😱 OPEN TO WORLD
}
```

**After (SECURE):**
```hcl
resource "aws_key_pair" "eval_server_key" {
  key_name   = "crucible-eval-key"
  public_key = file("~/.ssh/id_ed25519_metr.pub")
}

ingress {
  from_port   = 22
  cidr_blocks = [var.allowed_ssh_ip]  # ✅ YOUR IP ONLY
}
```

---

## The VPC Decision

**Question**: Should EC2 be in private subnet?

**Analysis**:
- ✅ **Security**: No direct internet access
- ✅ **Best Practice**: Defense in depth
- ❌ **Complexity**: NAT Gateway, Session Manager
- ❌ **Cost**: NAT Gateway charges

**Decision**: Start public, document migration path

See: `/infrastructure/terraform/docs/NETWORK_SECURITY_CONSIDERATIONS.md`

---

# Act 5: Comprehensive Security
## Defense in Depth

---

## Security Layers

```
Application Level
    ↓ Input validation
Container Level  
    ↓ Docker isolation
Runtime Level
    ↓ gVisor kernel isolation
Network Level
    ↓ Complete isolation (--network none)
Infrastructure Level
    ↓ Private subnets, IAM policies
Monitoring Level
    ↓ Behavioral tracking, audit logs
```

**100+ security checklist items** documented!

---

## 🚨 DEMO: Security Guide

```bash
cat docs/COMPREHENSIVE_SECURITY_GUIDE.md

# Shows:
- ✅ Current implementations
- ⚠️  Partial implementations  
- ❌ TODO items
- Importance ratings (🔴 Critical → ⚪ Low)
- Effort estimates (💪 High → ✋ Low)
```

Security isn't a feature, it's pervasive.

---

# Act 6: OpenAPI Integration
## Contract-First Development

---

## API Specification as Code

```yaml
# api/openapi.yaml
paths:
  /eval:
    post:
      summary: Submit evaluation
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/EvaluationRequest'
```

**Benefits**:
- ✅ Auto request/response validation
- ✅ Client SDK generation
- ✅ Interactive documentation
- ✅ Type safety

---

## 🚨 DEMO: OpenAPI in Action

```bash
# Run with validation
python extreme_mvp_frontier.py --openapi

# Try invalid request
curl -X POST localhost:8000/eval \
  -d '{}'  # Missing required 'code' field

# Response:
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": ["Missing required field: code"]
}
```

The API self-enforces its contract!

---

# Act 7: Event-Driven Architecture
## Loose Coupling at Scale

---

## The Event Bus Pattern

```python
# Before: Tight coupling
platform.evaluate(code)
storage.store(result)     # Platform knows about storage
monitor.track(result)     # Platform knows about monitor

# After: Event-driven
platform.evaluate(code)
event_bus.publish(EventTypes.EVALUATION_COMPLETED, {
    "eval_id": "123", 
    "result": result
})
# Storage and Monitor subscribe independently!
```

---

## 🚨 DEMO: Events in Action

```bash
python extreme_mvp_frontier_events.py

# New endpoint shows event flow:
curl localhost:8000/events

{
  "events": [
    {"type": "platform.ready", "data": {...}},
    {"type": "evaluation.queued", "data": {...}},
    {"type": "evaluation.completed", "data": {...}},
    {"type": "storage.saved", "data": {...}}
  ]
}
```

Perfect observability and extensibility!

---

## Event-Driven Benefits

1. **Components don't know about each other**
   - Easy to add new features
   - No ripple effects

2. **Natural audit trail**
   - Every action is an event
   - Built-in observability

3. **Evolution path**
   - Start: In-memory
   - Later: Redis Pub/Sub
   - Future: Kafka/EventBridge

---

# Act 8: The Frontier Edition
## Everything Integrated

---

## 🚨 DEMO: The Complete Platform

```bash
# All features combined
python extreme_mvp_frontier_events.py \
  --openapi \     # Contract validation
  --fastapi \     # Modern async framework
  --gvisor        # Maximum security

# What you get:
✅ Component architecture (TRACE-AI)
✅ Event-driven design
✅ OpenAPI validation  
✅ Comprehensive security
✅ Real-time monitoring
✅ Persistent storage
```

From 100 lines to production-ready!

---

## The Journey in Numbers

| Stage | Lines | Components | Security Layers | Features |
|-------|-------|------------|-----------------|----------|
| extreme_mvp.py | 100 | 1 | 0 | Basic UI |
| + queue | 150 | 2 | 0 | Async |
| + monitoring | 230 | 3 | 0 | Events |
| + docker | 330 | 3 | 1 | Containers |
| + gvisor | 480 | 3 | 2 | Kernel isolation |
| + components | 2000+ | 8 | 3 | Modular |
| + infrastructure | 3000+ | 8 | 4 | Cloud |
| + openapi | 3500+ | 9 | 4 | Contracts |
| + events | 4000+ | 10 | 4 | Loose coupling |

---

## METR Submission Readiness

**Day 1** ✅ 
- Infrastructure deployed
- SSH security hardened
- Evolution demos working
- Security documented

**Day 2-5 Plan**:
- Connect Lambda → SQS → Worker
- Add safety test suite
- Create monitoring dashboard
- Private subnet migration
- Production deployment

See: `/docs/5-day-metr-submission-plan.md`

---

## Key Architectural Insights

1. **Start dangerously simple** - The extreme MVP teaches viscerally

2. **Evolution > Revolution** - Each step builds on the last

3. **Components enable evolution** - TestableComponent pattern

4. **Events enable scaling** - Loose coupling from day one

5. **Security is progressive** - Not binary, but layered

6. **Contracts prevent drift** - OpenAPI keeps everyone aligned

---

## The Philosophy

**We keep the unsafe MVP because:**

Just as we can't make AI "safe" by restricting it to "safe" behaviors (it might find ways around), we can't make code execution "safe" with naive filters.

The only path forward is proper containment:
- Process isolation → Containers → VMs → gVisor → Physical isolation

*This platform isn't just demonstrating engineering.*
*It's demonstrating why AI safety matters existentially.*

---

## What We Actually Built

A **learning platform** that:
- ✅ Demonstrates the full journey (extreme_mvp → frontier)
- ✅ Works at every level of sophistication
- ✅ Teaches safety viscerally through progression
- ✅ Scales from laptop to cloud seamlessly

A **methodology** that:
- ✅ TRACE-AI for systematic decisions
- ✅ Evolution series for incremental progress
- ✅ Component architecture for flexibility
- ✅ Event-driven design for extensibility

---

## Try It Yourself

```bash
# 1. Feel the danger
python extreme_mvp.py

# 2. See the evolution
ls -la extreme_mvp*.py
python extreme_mvp_monitoring.py

# 3. Test components
python test_components.py

# 4. Deploy infrastructure
cd infrastructure/terraform && tofu apply

# 5. Run production version
python extreme_mvp_frontier_events.py --openapi
```

Each command teaches something essential.

---

## Questions?

**Resources:**
- GitHub: [repository-url]
- Live Demo: ubuntu@44.246.137.198
- Evolution Series: `/evolution/extreme_mvp*.py`

**Key Documentation:**
- `/docs/COMPREHENSIVE_SECURITY_GUIDE.md` - 100+ security items
- `/docs/OPENAPI_INTEGRATION.md` - Contract-first development
- `/evolution/EVOLUTION_TREE.md` - Complete code evolution
- `/docs/5-day-metr-submission-plan.md` - What's next

*Thank you for joining our journey from danger to safety*