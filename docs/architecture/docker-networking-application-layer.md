# Docker Networking: Application Layer Architecture

## The Overhead Trade-off

Yes, you're absolutely right - network calls add overhead compared to in-memory function calls:

```
In-memory call: ~0.001ms
Local network call: ~0.1-1ms (100-1000x slower)
```

But we gain:
- **Independent scaling** - Scale queue separately from API
- **Fault isolation** - Queue crash doesn't take down API
- **Technology flexibility** - Could rewrite queue in Go/Rust later
- **Clear contracts** - Network APIs force explicit interfaces

## Performance Methods Ranked

### 1. **Unix Domain Sockets** (Fastest)
```yaml
# docker-compose.yml
services:
  api:
    volumes:
      - socket-vol:/var/run/sockets
  queue:
    volumes:
      - socket-vol:/var/run/sockets
```
- ~0.01ms latency
- No network stack overhead
- Limited to same host

### 2. **gRPC with HTTP/2** (Fast + Features)
```python
# Uses Protocol Buffers for serialization
# Binary protocol, multiplexing, streaming
```
- ~0.5ms latency
- 10x faster serialization than JSON
- Built-in streaming, cancellation
- Type-safe contracts

### 3. **HTTP/1.1 + MessagePack** (Balanced)
```python
# FastAPI with MessagePack instead of JSON
@app.post("/tasks")
async def enqueue(data: bytes):
    task = msgpack.unpackb(data)
```
- ~1ms latency
- 5x faster than JSON
- Still debuggable with tools

### 4. **HTTP/1.1 + JSON** (Simple)
- ~1-2ms latency
- Human readable
- Best tooling support

## Security Methods for AI Evaluation Platform

### 1. **mTLS (Mutual TLS) - Most Secure**
```yaml
# Each container has its own certificate
services:
  api:
    environment:
      - CLIENT_CERT=/certs/api.crt
      - CLIENT_KEY=/certs/api.key
      - CA_CERT=/certs/ca.crt
```
- Both sides authenticate
- Encrypted in transit
- Perfect for untrusted code execution

### 2. **Network Policies + Service Mesh**
```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: queue-ingress
spec:
  podSelector:
    matchLabels:
      app: queue
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api  # Only API can talk to queue
```

### 3. **API Keys + Network Isolation**
```python
# Shared secret between services
API_KEY = os.environ["INTERNAL_API_KEY"]

@app.post("/tasks")
async def enqueue(task: Task, x_api_key: str = Header()):
    if x_api_key != API_KEY:
        raise HTTPException(401)
```

### 4. **Docker Networks (Basic)**
```yaml
# Isolated network
networks:
  internal:
    driver: bridge
    internal: true  # No external access
```

## For This Project: Security Recommendations

Given we're running untrusted code:

```yaml
# Recommended architecture
services:
  nginx:           # Public facing, TLS termination
    networks:
      - public
      - api_network

  api:             # API Gateway
    networks:
      - api_network
      - queue_network
      - storage_network
    environment:
      - QUEUE_API_KEY=${QUEUE_API_KEY}
      - WORKER_API_KEY=${WORKER_API_KEY}

  queue:           # Internal only
    networks:
      - queue_network
    environment:
      - API_KEY=${QUEUE_API_KEY}

  worker:          # Execution worker
    networks:
      - queue_network
      - execution_network
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

  execution:       # Where untrusted code runs
    networks:
      - execution_network  # Fully isolated
    # NO access to other services

networks:
  public:
    # Internet facing
  api_network:
    internal: true
  queue_network:
    internal: true
  storage_network:
    internal: true
  execution_network:
    internal: true
    # Most isolated - only worker can reach
```

## Shared Base Images - Yes, Worth It!

### Multi-stage Build Pattern
```dockerfile
# base.Dockerfile
FROM python:3.11-slim AS python-base
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    httpx==0.25.0
WORKDIR /app

# api.Dockerfile
FROM python-base
RUN pip install --no-cache-dir \
    psycopg2-binary \
    sqlalchemy
COPY src/api /app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

# queue.Dockerfile  
FROM python-base
COPY queue-service/app.py /app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8081"]
```

### Benefits:
1. **Faster builds** - Docker caches base layer
2. **Smaller total size** - Shared layers on disk
3. **Consistent versions** - All services use same FastAPI
4. **Security patches** - Update base, rebuild all

### Build Script:
```bash
#!/bin/bash
# build-all.sh
docker build -f base.Dockerfile -t crucible-base .
docker build -f api.Dockerfile -t crucible-api .
docker build -f queue.Dockerfile -t crucible-queue .
```

## Architecture Pattern: API Gateway vs Microservices

### Option 1: API Gateway Pattern (Recommended)
```
Internet → Nginx → API Gateway → Internal Services
                         ↓
                    (All auth here)
                         ↓
                Queue  Worker  Storage
```

### Option 2: Service Mesh
```
Internet → Ingress → [Envoy sidecars on each service]
```

### Option 3: Direct Service-to-Service
```
Internet → Nginx → API ←→ Queue ←→ Worker
                     ↕      ↕        ↕
                  Storage  Redis  Execution
```

## Implementation Recommendations

### 1. Start Simple, Evolve
```python
# Phase 1: HTTP + JSON (what we have)
# Phase 2: Add API keys
# Phase 3: Add mTLS for worker→execution
# Phase 4: Consider gRPC for hot paths
```

### 2. Security Layers
```yaml
# Layer 1: Network isolation
# Layer 2: API authentication  
# Layer 3: Request validation
# Layer 4: Rate limiting
# Layer 5: Audit logging
```

### 3. Monitoring
```python
# Add tracing
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.post("/tasks")
async def enqueue_task(task: Task):
    with tracer.start_as_current_span("enqueue_task"):
        # Your code here
```

## Common Pitfalls

1. **DNS in Docker** - Services find each other by service name
2. **Port confusion** - Internal ports can differ from exposed
3. **Health checks** - Critical for container orchestration
4. **Graceful shutdown** - Handle SIGTERM properly
5. **Connection pooling** - Reuse HTTP connections

## Performance Tips

1. **Keep connections alive**
```python
# Reuse connections
client = httpx.AsyncClient()
# Use client for multiple requests
```

2. **Batch when possible**
```python
@app.post("/tasks/batch")
async def enqueue_batch(tasks: List[Task]):
    # Single network call for multiple tasks
```

3. **Consider streaming**
```python
@app.post("/results/stream")
async def stream_results():
    # Server-sent events for real-time updates
```

## The "Multiple FastAPI" Question

Yes, it feels redundant, but it's actually a strength:

1. **Consistent tooling** - Same debugging, monitoring, deployment
2. **Shared knowledge** - Team knows one framework well
3. **Easy refactoring** - Can merge/split services easily
4. **Good ecosystem** - FastAPI has excellent async support

Alternatives if you want variety:
- **Queue**: Could use Celery's Flower (Flask-based)
- **Metrics**: Could use Prometheus client directly
- **Worker**: Could be a simple script with `requests`

But consistency often wins in production.