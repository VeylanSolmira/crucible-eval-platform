# Crucible Evaluation Platform
## Building AI Safety Infrastructure Through Iterative Design

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

## Our Approach: 10 Levels of Architecture

From understanding to implementation:

1. **Verbal understanding** - Getting requirements right
2. **Domain vocabulary** - Speaking the same language
3. **Workflow diagram** - Mapping the process
4. **Tool selection** - Choosing the tech stack
5. **MVP Implementation** - Basic working system
6. **Core Engine** - The heart of evaluation
7. **Integrations** - Quality of life features
8. **Monitoring** - Visibility into everything
9. **Security** - Production hardening
10. **Enterprise** - Scaling to organizations

---

# Level 1: Understanding the Problem

"You need a platform on which AI Safety Researchers can safely evaluate dangerous or potentially dangerous AI models"

Key questions:
- What does "safely" mean?
- What makes a model "dangerous"?
- Who are the users?

*Architecture starts with understanding, not technology*

---

# Level 2: Domain Vocabulary

**Safety** = Prevention mechanisms
- No escape from testing framework
- No network access
- No persistence beyond session
- No interference between evaluations

**Dangerous models** = Concerning capabilities  
- Self-replication attempts
- Human manipulation
- System access seeking
- Capability deception

---

# Level 3: Workflow Evolution

## v1: Naive Synchronous
```
User → API → Evaluator → User
```
❌ Evaluations take hours/days!

## v2: Add Async + Monitoring
```
User → API → Queue → Evaluator
         ↓
    Monitoring Layer
```

## v3: Complete Architecture
```
User → API → Queue → Evaluator → Storage
         ↓
    Monitoring (all stages)
         ↓
    User Access Points
```

---

# Level 4: TRACE-AI Framework

**Making pragmatic technical decisions:**

- **T**ime to feedback - How quickly do we need user validation?
- **R**eversibility cost - How expensive to change later?
- **A**bstraction possibility - Can we hide behind interfaces?
- **C**ore vs peripheral - Central to value proposition?
- **E**xpertise required - Do we have the skills?
- **F**ungibility - How easily can AI help migrate?

*This framework guides every technology choice*

---

## The Extreme MVP Question

**"What's the simplest thing that could possibly teach us something?"**

TRACE-AI analysis:
- **T**: Need feedback in hours → Simplest possible
- **F**: AI can refactor easily → Start ultra-simple

Answer: **One Python file, 100 lines, zero dependencies**

---

## 🚨 DEMO: The Extreme MVP

**`python extreme_mvp.py`**

What we built:
- ✅ API (HTTP POST endpoint)
- ✅ Task Evaluator (subprocess.run)
- ✅ Web Frontend (embedded HTML)
- ❌ Queue (synchronous)
- ❌ Monitoring (just "Running...")

**WARNING: This executes ANY Python code**

---

## The Visceral Lesson

When you hover over "Run Evaluation", you feel fear:
- "This could delete my files"
- "This could steal my data"
- "This could compromise my system"

**This mirrors AI safety evaluation:**
- "This AI could deceive us"
- "This AI could pursue hidden goals"
- "This AI could manipulate operators"

*The danger is real in both cases*

---

## Extreme MVP vs Requirements

| Requirement | Status | Gap |
|-------------|--------|-----|
| 🛡️ Safe evaluation | ❌ | No sandboxing |
| 👁️ Real-time monitoring | ❌ | No visibility |
| 📈 Scale concurrent | ❌ | Single-threaded |
| 🖥️ User interface | ✅ | Basic but works |

**Learning: We need all four, not just UI**

---

# Level 5: Real MVP Components

Based on TRACE-AI analysis:

| Component | Technology | Why |
|-----------|------------|-----|
| API | Lambda + Gateway | Simple, managed |
| Queue | SQS | Zero infrastructure |
| Storage | PostgreSQL + S3 | Standard, reliable |
| Frontend | React + TypeScript | Industry standard |
| Evaluator | Kubernetes | **Core safety** - invest here |

---

## 🚨 DEMO: Infrastructure as Code

**Show Terraform files:**
- `api.tf` - Lambda function
- `queue.tf` - SQS with DLQ
- `variables.tf` - Configuration

```bash
terraform plan
terraform apply
```

*From single file to cloud infrastructure*

---

# Level 6: Core Evaluation Engine

**The Worker/Orchestrator Pattern**

```python
def process_evaluation(eval_id):
    task = get_from_queue()
    manifest = generate_k8s_manifest(task)
    pod = create_pod(manifest)
    monitor_lifecycle(pod)
```

Key insight: **Manifests as code, not YAML**

See: `/docs/worker-orchestrator-design.md`

---

# Level 7: External Integrations

**What researchers actually want:**
- 🔔 Slack notifications
- 📊 Airtable for results
- 📧 Email alerts
- 🪝 Webhook framework

*Quality of life matters for adoption*

---

# Level 8: Monitoring Dashboard

**Comprehensive visibility:**
- System health metrics
- Evaluation progress
- Resource usage
- Safety alerts

*Can't manage what you can't measure*

---

# Level 9: Security Hardening

**Defense in depth:**
- Container isolation (gVisor)
- Network policies
- Resource limits
- Audit logging
- Emergency stops

*Security isn't a feature, it's pervasive*

---

# Level 10: Enterprise Features

**Scaling to organizations:**
- Single Sign-On (SSO)
- Team management
- Resource quotas
- Isolated environments
- Compliance tools

*From platform to product*

---

## Key Insights

1. **Start dangerously simple** - The extreme MVP teaches viscerally
2. **TRACE-AI guides decisions** - Systematic thinking about tradeoffs
3. **Safety is core, not peripheral** - Invest deeply in isolation
4. **Evolution is intentional** - Each level builds on learnings

---

## The Philosophy

**We keep the unsafe MVP because:**

Just as we can't make AI "safe" by restricting it to "safe" behaviors (it might find ways around), we can't make code execution "safe" with naive filters.

The only path forward is proper containment:
- Docker → VMs → Kubernetes → gVisor

*This extreme MVP isn't just demonstrating platform engineering.*
*It's demonstrating why this work matters existentially.*

---

## Architecture Principles

From our journey:

1. **Understand before building** (Levels 1-3)
2. **Choose reversible options** (TRACE-AI)
3. **Ship to learn** (Extreme MVP)
4. **Invest in core differentiators** (Safety)
5. **Abstract for evolution** (Interfaces)

See: `/docs/mvp-technical-debt-framework.md`

---

## 🚨 DEMO: Git Tag Journey

Show the evolution through git:

```bash
git tag -l "level*"
git checkout level1-understanding
git checkout level4-tools
git checkout level5-mvp
```

*Each tag represents a complete architectural stage*

---

## Real-Time Updates Deep Dive

**WebSocket vs SSE analysis:**

For METR's needs (monitoring):
- Mostly one-way (server → client)
- SSE is simpler and sufficient
- WebSocket for future bidirectional needs

See: `/docs/real-time-updates-comparison.md`

---

## Queue Technology Deep Dive

**Celery vs SQS decision:**

Applied TRACE-AI:
- **T**: SQS faster to implement
- **R**: Both reversible with abstraction
- **F**: Very high - easy to migrate

→ Start with SQS, evolve to Celery if needed

See: `/docs/celery-vs-sqs-comparison.md`

---

## What We Built

**A platform that:**
- ✅ Demonstrates the full journey
- ✅ Works at every level
- ✅ Teaches safety viscerally
- ✅ Scales from laptop to cloud

**A methodology that:**
- ✅ TRACE-AI for decisions
- ✅ Extreme MVP for learning
- ✅ Progressive enhancement
- ✅ Safety-first evolution

---

## Next Steps

1. **Run the extreme MVP** - Feel the danger
2. **Explore the architecture** - See the evolution
3. **Apply TRACE-AI** - Make better decisions
4. **Build safely** - But ship to learn

*The best way to evaluate AI safely is to understand danger viscerally*

---

## Questions?

**Resources:**
- GitHub: [repository-url]
- Docs: `/docs/`
- Extreme MVP: `python extreme_mvp.py`

**Key files:**
- `/docs/iterative-buildup.md` - The complete journey
- `/docs/mvp-technical-debt-framework.md` - Decision philosophy
- `/docs/extreme-mvp-implementation.md` - Starting simple

*Thank you for joining our journey from danger to safety*