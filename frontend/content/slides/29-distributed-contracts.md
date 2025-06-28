---
title: 'From Monolith to Microservices: The Hidden Contract Problem'
theme: 'night'
---

# The 90-Second Mystery 🔍

<div style="text-align: left; font-size: 0.8em;">

**Symptom**: Hello World execution time went from 3s → 90s

**Trigger**: Migrating from custom polling to React Query

**Root Cause**: Hidden coupling in distributed systems

</div>

---

## The Investigation 🕵️

```typescript
// Frontend polling (React Query)
if (data.status === 'pending' || data.status === 'running') {
  return 1000 // Poll every second
}

// Backend returns
status: "queued"  // Not "pending"!
```

<div class="fragment" style="margin-top: 40px; color: #ff6b6b;">
Services speaking different languages!
</div>

---

## Monolith vs Microservices

<div class="columns">
<div class="column">

### Monolith
```python
# Everything in one place
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"

# Implicit consistency
```

</div>
<div class="column">

### Microservices
```python
# API Service
status = "queued"

# Frontend
status === "pending"

# Storage
status = "QUEUED"
```

</div>
</div>

<div class="fragment" style="margin-top: 40px; color: #51cf66;">
Each service evolved its own "truth"
</div>

---

## The Solution: Shared Contracts 📜

```yaml
# /shared/types/evaluation-status.yaml
components:
  schemas:
    EvaluationStatus:
      type: string
      enum: [queued, running, completed, failed]
```

<div style="margin-top: 40px;">
<p><strong>Single source of truth</strong> for all services</p>
</div>

---

## Implementation Architecture

```
/shared/
  /types/          # OpenAPI schemas
    evaluation-status.yaml
    event-contracts.yaml
  /constants/      # Shared limits
    limits.yaml    # Security constraints
    events.yaml    # Channel names
  /generated/      # Language-specific
    /python/       # For backend services
    /typescript/   # For frontend
```

---

## Type Safety Across Services

<div style="font-size: 0.9em;">

**Python (Backend)**:
```python
class EvaluationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

**TypeScript (Frontend)**:
```typescript
export enum EvaluationStatus {
  Queued = "queued",
  Running = "running",
  Completed = "completed",
  Failed = "failed"
}
```

</div>

<div class="fragment" style="margin-top: 40px; color: #51cf66;">
Generated from the same source!
</div>

---

## Lessons Learned 💡

<div style="text-align: left;">

1. **Implicit coupling is dangerous**
   - Works in monoliths, breaks in microservices

2. **Performance issues reveal architecture flaws**
   - 90s delay exposed missing contracts

3. **Type safety must cross service boundaries**
   - OpenAPI + code generation = consistency

4. **Distributed systems need explicit contracts**
   - Can't rely on "everyone knows"

</div>

---

## The Result ✨

<div style="font-size: 1.2em;">

- ✅ Execution time back to **3 seconds**
- ✅ Type-safe communication
- ✅ Single source of truth
- ✅ Future changes propagate automatically

</div>

<div class="fragment" style="margin-top: 60px; font-size: 0.9em; color: #51cf66;">
Production-ready distributed systems thinking
</div>