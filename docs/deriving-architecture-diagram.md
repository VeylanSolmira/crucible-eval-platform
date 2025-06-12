# Deriving the Architecture Diagram: A Step-by-Step Process

## Starting Point: Core Requirements

Let's derive the architecture diagram from METR's fundamental needs:

1. **Safely evaluate AI models** that might try to escape
2. **Monitor evaluations** in real-time
3. **Scale to many concurrent evaluations**
4. **Provide a user interface** for researchers

## Step 1: Identify the Core Workflow

What's the simplest possible flow?

```
User → Submit Evaluation → Run Evaluation → Get Results
```

This gives us our first components:
- Something to accept user input (Frontend)
- Something to process requests (API)
- Something to run evaluations (Executor)

## Step 2: Add Constraints

### Constraint 1: Evaluations are long-running (hours/days)
**Problem**: Can't have user wait for HTTP response
**Solution**: Async processing with task queue

```
User → API → Queue → Worker → Results
       ↑                        │
       └────── Status ──────────┘
```

### Constraint 2: Need real-time monitoring
**Problem**: Polling for updates is inefficient
**Solution**: WebSocket for push updates

```
User ←── WebSocket ←── Worker
 │                        ↑
 └→ API → Queue → Worker →┘
```

### Constraint 3: Dangerous AI isolation
**Problem**: AI might try to escape, affect other evals
**Solution**: Container orchestration (Kubernetes)

```
Worker → Kubernetes → [Isolated Pod]
```

## Step 3: Organize into Layers

Now we group related components:

### Layer 1: User Interface
- Frontend (TypeScript/React)
- Handles user interaction
- Displays real-time updates

### Layer 2: API Layer  
- API Gateway (FastAPI)
- WebSocket Server
- Authentication

### Layer 3: Processing Layer
- Task Queue (Celery)
- Orchestrator
- Result Processor

### Layer 4: Execution Layer
- Kubernetes Cluster
- Isolated Evaluation Pods
- Monitoring/Storage

## Step 4: Draw the Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                     METR Evaluation Platform                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │ ← User-facing
│  │   Frontend  │────│   API Gateway │────│  Auth Service │  │   components
│  │  TypeScript │    │    (FastAPI)  │    │    (OAuth2)   │  │
│  └─────────────┘    └───────┬───────┘    └───────────────┘  │
│                             │                               │
│  ┌──────────────────────────┴────────────────────────────┐  │ ← Business
│  │              Evaluation Orchestrator                   │  │   logic
│  │  ┌─────────┐  ┌────────────┐  ┌─────────────────┐    │  │
│  │  │Scheduler│  │ Task Queue │  │ Result Processor│    │  │
│  │  └─────────┘  └────────────┘  └─────────────────┘    │  │
│  └─────────────────────┬─────────────────────────────────┘  │
│                        │                                    │
│  ┌─────────────────────┴────────────────────────────────┐  │ ← Execution
│  │            Kubernetes Cluster (EKS/GKE)              │  │   environment
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐   │  │
│  │  │ Eval Pods  │  │ Monitoring │  │   Storage    │   │  │
│  │  │ (Isolated) │  │ Prometheus │  │   (S3/GCS)   │   │  │
│  │  └────────────┘  └────────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Step 5: Validate the Design

Ask yourself:
1. **Can a user submit an evaluation?** ✓ (Frontend → API → Queue)
2. **Can we run it safely?** ✓ (Queue → Orchestrator → K8s Pod)
3. **Can we monitor progress?** ✓ (Pod → Monitoring → WebSocket → Frontend)
4. **Can we scale?** ✓ (Horizontal scaling at each layer)

## The Key Insight

The architecture emerges from constraints:
- **Long-running tasks** → Queue-based architecture
- **Dangerous AI** → Container isolation
- **Real-time needs** → WebSocket layer
- **Scale requirements** → Kubernetes orchestration

## Practice Exercise: Derive Your Own

Try deriving an architecture for:
1. **A code compilation service** (like Compiler Explorer)
   - What isolation do you need?
   - How do you handle different languages?
   - What about resource limits?

2. **A web scraping platform** (like ScrapingBee)
   - How do you handle rate limits?
   - What about rotating IPs?
   - How do you scale?

## Common Patterns You'll See

1. **API Gateway Pattern**: Single entry point
2. **Queue + Worker Pattern**: Async processing
3. **Sidecar Pattern**: Monitoring alongside workload
4. **Bulkhead Pattern**: Isolation between components

## Interview Tip

When asked "How would you design X?":
1. Start with requirements
2. Identify constraints
3. Choose patterns that address constraints
4. Draw simple boxes and arrows
5. Iterate and refine

Don't jump straight to "microservices" or "Kubernetes" - show your reasoning!