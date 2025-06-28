---
title: "The Current Production Architecture"
duration: 3
tags: ["architecture", "production"]
---

## The Current Production Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  React Frontend │────▶│   API Service    │────▶│     Redis        │
│  (TypeScript)   │     │   (FastAPI)      │     │   (Pub/Sub)      │
└─────────────────┘     └──────────────────┘     └────────┬─────────┘
         │                        │                         │
         │                        ▼                         ▼
         │              ┌──────────────────┐     ┌──────────────────┐
         │              │   PostgreSQL     │     │  Storage Worker  │
         │              │   (Persistent)   │◀────│  (Subscriber)    │
         │              └──────────────────┘     └──────────────────┘
         │                                                  
         │              ┌──────────────────┐     ┌──────────────────┐
         └──────────────▶│  Queue Service   │────▶│  Queue Worker    │
                        │   (HTTP API)     │     │   (Router)       │
                        └──────────────────┘     └────────┬─────────┘
                                                          │
                                                          ▼
                                                ┌──────────────────┐
                                                │Executor Service  │
                                                │  (Containers)    │
                                                └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │ Docker Socket    │
                                                │     Proxy        │
                                                │ (Limited perms)  │
                                                └──────────────────┘
```