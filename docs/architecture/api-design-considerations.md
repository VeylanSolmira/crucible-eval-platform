# API Design Considerations

## Core Responsibility

The API's primary job is simple:
1. Accept evaluation requests (Python scripts, configs, etc.)
2. Validate inputs
3. Enqueue tasks
4. Return job IDs

This is perfectly suited for request/response, even with serverless!

## MVP API Flow

```python
# Simple request/response
POST /api/v1/evaluations
{
  "model_id": "gpt-4",
  "script": "def evaluate_model(model):\n    ...",
  "config": {"timeout": 300}
}

Response:
{
  "evaluation_id": "eval_123",
  "status": "queued",
  "queue_position": 5
}
```

## Where Safety Features Actually Live

### What the API Does (Simple)
- Basic validation (is this valid Python syntax?)
- Authentication (is this user authorized?)
- Rate limiting (too many requests?)
- Enqueue task

### What the API Doesn't Do (Complex)
- Deep safety inspection → **Pre-execution Validator**
- Monitor running evaluations → **Worker/Orchestrator**
- Emergency stops → **Worker/Orchestrator**
- Real-time log streaming → **Monitoring Service**
- Behavioral analysis → **Safety Monitor Service**

## Security Validation Stages

### Stage 1: API (Quick checks only)
```python
# Fast, synchronous checks
def api_validation(request):
    # Basic syntax check (fast)
    try:
        ast.parse(request.script)
    except SyntaxError:
        return "Invalid Python"
    
    # Quick pattern matching (milliseconds)
    if contains_obvious_exploits(request.script):
        return "Forbidden patterns detected"
    
    # Pass to queue for deeper analysis
    return enqueue(request)
```

### Stage 2: Pre-execution Validator (Deep inspection)
```python
# Can take seconds/minutes, happens async
def deep_safety_validation(task):
    # Static analysis
    ast_tree = ast.parse(task.script)
    if contains_unsafe_operations(ast_tree):
        return reject_task(task, "Unsafe operations")
    
    # Sandbox trial run
    if sandbox_test_fails(task.script):
        return reject_task(task, "Failed sandbox test")
    
    # Behavioral analysis
    if matches_known_attack_patterns(task.script):
        return reject_task(task, "Suspicious patterns")
    
    # Only now create K8s job
    return approve_for_execution(task)
```

## Architecture Options

### Option A: Two-stage Queue
```
API → Quick Queue → Validator → Execution Queue → Worker
         ↓                           ↓
    (untrusted)                 (validated)
```

### Option B: Single Queue with States
```
API → Queue → Worker
         ↓
    State: pending_validation
         ↓
    State: validated
         ↓
    State: executing
```

### Option C: Validator in Worker
```
API → Queue → Worker (validates first, then executes)
```

## Technology Choices Revisited

Given this cleaner separation:

### Serverless (API Gateway + Lambda) ✅
**Now makes more sense because:**
- API just needs to validate and enqueue
- No long-running connections needed
- Auto-scaling for request spikes
- Pay-per-request pricing

### Traditional Server (FastAPI/Express) 
**Still valid if:**
- You want to bundle monitoring endpoints
- Need WebSocket/SSE for status updates
- Want single deployment unit

## Progressive Architecture

### Phase 1: Simple API (Serverless works!)
```
User → API Gateway → Lambda → SQS → Worker
         ↓
    Return Job ID
```

### Phase 2: Add Status Checking
```
GET /api/v1/evaluations/{id}/status
```
Still request/response!

### Phase 3: Add Real-time Updates
- Option A: Separate monitoring service with SSE
- Option B: Upgrade API to support WebSocket
- Option C: Use API Gateway WebSocket support

## Key Insight

The API doesn't need to be complex for safety. Safety is enforced by:
1. **Worker**: Implements isolation, creates secure pods
2. **Kubernetes**: Enforces resource limits, network policies
3. **Monitor**: Watches for violations, can kill pods

The API just needs to get the job into the queue safely.

## Recommendations

### For MVP:
- Serverless API (simple, scalable, cheap)
- Focus on input validation and queueing
- Return job IDs for status checking

### For Production:
- Evaluate if real-time features needed
- Consider API Gateway WebSocket if yes
- Keep safety enforcement in Worker/K8s layer

## Defense in Depth Strategy

Security isn't just at the execution layer - it starts the moment untrusted code enters the system!

### Response Codes Indicating Security Stage
```
POST /api/v1/evaluations
→ 202 Accepted        # Queued for validation
→ 400 Bad Request     # Failed basic syntax/security checks
→ 403 Forbidden       # User not authorized for this operation

GET /api/v1/evaluations/{id}/status
→ "pending_validation"  # In security review
→ "validation_failed"   # Rejected by deep analysis
→ "validated"          # Approved for execution
→ "executing"          # Running in isolated environment
```

### Key Architectural Decision
**What security checks are fast enough for synchronous API response vs. what needs async processing?**

- **Synchronous (milliseconds)**: Syntax checks, regex pattern matching, rate limits
- **Asynchronous (seconds-minutes)**: Static analysis, sandbox testing, ML-based threat detection

This gives defense in depth while keeping the API responsive.

## Anti-patterns to Avoid

1. **Making API do too much**: Don't monitor evaluations from API
2. **Stateful API servers**: Keep state in queue/database
3. **Complex orchestration in API**: That's the Worker's job
4. **All-or-nothing security**: Don't try to do all validation in API (too slow) or all in Worker (too late)

## Summary

Your instinct is correct - the API for MVP can be dead simple:
- Accept script
- Validate
- Enqueue
- Return ID

Everything else (safety, monitoring, orchestration) happens downstream!