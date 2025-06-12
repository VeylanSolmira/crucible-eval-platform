# Evolution Tree of extreme_mvp Files

```
extreme_mvp.py (Original - UNSAFE!)
│
├─► extreme_mvp_testable.py (Testing philosophy)
│   │
│   └─► extreme_mvp_modular.py ★ (CURRENT - Fully modular architecture)
│       └─► components/
│           ├── base.py (TestableComponent)
│           ├── execution.py (ExecutionEngine, DockerEngine, SubprocessEngine)
│           ├── monitoring.py (MonitoringService, InMemoryMonitor)
│           └── platform.py (TestableEvaluationPlatform)
│
├─► extreme_mvp_docker.py (First safety attempt)
│   │
│   └─► extreme_mvp_docker_v2.py (ExecutionEngine abstraction)
│       │
│       ├─► extreme_mvp_monitoring.py (Add visibility)
│       │   │
│       │   ├─► extreme_mvp_monitoring_v2.py (Better structure)
│       │   │   │
│       │   │   └─► extreme_mvp_monitoring_v3.py ★ (Clean abstraction)
│       │   │
│       │   └─► extreme_mvp_monitoring_testable.py ★ (Monitoring + Testing)
│       │
│       └─► extreme_mvp_queue.py (Concurrent execution)
│           │
│           └─► extreme_mvp_queue_testable.py ★ (Queue + Testing)
│
└─► extreme_mvp_gvisor.py ★ (Production security with gVisor)


Additional experimental branches:
└─► extreme_mvp_abstracted.py (Future exploration)
```

## Legend
- ★ = CURRENT (actively used)
- No star = OBSOLETE or EDUCATIONAL

## Key Evolution Milestones

### 1. **Safety Evolution**
```
extreme_mvp.py (subprocess - DANGEROUS!)
    ↓
extreme_mvp_docker.py (container isolation)
    ↓
extreme_mvp_gvisor.py (kernel-level isolation)
```

### 2. **Architecture Evolution**
```
extreme_mvp.py (monolithic)
    ↓
extreme_mvp_docker_v2.py (ExecutionEngine abstraction)
    ↓
extreme_mvp_modular.py (full component separation)
```

### 3. **Testing Evolution**
```
extreme_mvp.py (no tests)
    ↓
extreme_mvp_testable.py (TestableComponent base)
    ↓
extreme_mvp_*_testable.py (all components testable)
```

### 4. **Feature Evolution**
```
Basic execution
    ↓
+ Monitoring (visibility)
    ↓
+ Queue (concurrency)
    ↓
+ Modular (scalability)
```

## File Relationships Summary

### Core Lineage (Main Evolution Path):
1. extreme_mvp.py → extreme_mvp_docker.py → extreme_mvp_docker_v2.py → extreme_mvp_modular.py

### Feature Branches:
- **Monitoring Branch**: docker_v2 → monitoring → monitoring_v2 → monitoring_v3/monitoring_testable
- **Queue Branch**: docker_v2 → queue → queue_testable
- **Security Branch**: docker → gvisor
- **Testing Branch**: mvp → testable → all *_testable variants

### Current Architecture (extreme_mvp_modular.py):
- Combines all learnings from previous iterations
- Separates components for independent evolution
- Maintains testability as core principle
- Ready for microservices transformation

## Final Architecture

```
components/                          ← Modular architecture
├── base.py                         ← TestableComponent foundation
├── execution.py                    ← Engines: Subprocess, Docker, GVisor
├── monitoring.py                   ← Event tracking
└── platform.py                     ← Orchestration

extreme_mvp_gvisor_modular.py ★★★  ← PRODUCTION RECOMMENDED
(Combines all learnings: modular + testable + secure)
```

## Cleanup Recommendations

### Keep These Files:
1. **extreme_mvp.py** - Original (educational - shows the danger)
2. **extreme_mvp_modular.py** - Clean modular architecture
3. **extreme_mvp_gvisor_modular.py** - Production deployment (modular + secure)
4. **components/** - Modular architecture modules

### Archive These Files:
1. extreme_mvp_docker.py, docker_v2.py (concepts now in components/execution.py)
2. extreme_mvp_monitoring*.py (concepts now in components/monitoring.py)
3. extreme_mvp_queue*.py (can add QueueEngine to components if needed)
4. extreme_mvp_testable.py (TestableComponent now in components/base.py)
5. extreme_mvp_abstracted.py (abstractions realized in components/)
6. extreme_mvp_gvisor.py (superseded by gvisor_modular)

### Consider Keeping for Reference:
1. extreme_mvp_abstracted.py - Shows future direction
2. extreme_mvp_monitoring_testable.py - Good testing example