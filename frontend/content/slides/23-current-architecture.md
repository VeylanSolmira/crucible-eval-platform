---
title: 'The Current Production Architecture'
duration: 3
tags: ['architecture', 'production']
---

## The Current Production Architecture (Week 4)

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  React Frontend │────▶│   API Service    │────▶│  Celery/Redis    │
│  (TypeScript)   │     │   (FastAPI)      │     │  (Task Queue)    │
└─────────────────┘     └──────────────────┘     └────────┬─────────┘
         │                        │                         │
         │                        ▼                         ▼
         │              ┌──────────────────┐     ┌──────────────────┐
         │              │   PostgreSQL     │     │  Celery Workers  │
         │              │   (Persistent)   │     │  (3 instances)   │
         │              └──────────────────┘     └────────┬─────────┘
         │                        ▲                         │
         │                        │                         ▼
         │              ┌──────────────────┐     ┌──────────────────┐
         └──────────────▶│ Storage Service │     │ Executor Pool    │
                        │   (FastAPI)      │     │ (executor-1,2,3) │
                        └──────────────────┘     └────────┬─────────┘
                                  ▲                         │
                                  │                         ▼
                        ┌──────────────────┐     ┌──────────────────┐
                        │ Storage Worker   │     │ Docker Socket    │
                        │ (Redis Sub)      │     │ Proxy (Security) │
                        └──────────────────┘     └──────────────────┘
                                  ▲
                                  │
                        ┌──────────────────┐
                        │     Flower       │
                        │ (Monitoring UI)  │
                        └──────────────────┘
```

### Key Architecture Updates:
- **Celery Workers**: Replaced queue service with enterprise task queue
- **Atomic Allocation**: Redis Lua scripts prevent executor conflicts
- **State Machine**: Handles out-of-order events correctly
- **ML Support**: executor-ml image for PyTorch/TensorFlow workloads