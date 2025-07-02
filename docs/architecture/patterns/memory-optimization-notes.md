# Memory Optimization Notes

## Current Memory Usage Estimates

### Microservices Mode (All Services)

| Service | Base | Libraries | Runtime | Total | Notes |
|---------|------|-----------|---------|-------|-------|
| Redis | - | - | 50MB | 50MB | Efficient in-memory store |
| PostgreSQL | - | - | 200MB | 200MB | With connection pooling |
| Docker Proxy | - | - | 50MB | 50MB | Lightweight Go binary |
| API Gateway | 20MB | 30MB | 30MB | 80MB | FastAPI + Redis client |
| Queue Service | 20MB | 30MB | 20MB | 70MB | FastAPI + minimal deps |
| Queue Worker | 20MB | 20MB | 20MB | 60MB | httpx + asyncio |
| Executor | 20MB | 45MB | 30MB | 95MB | FastAPI + Docker client |
| Storage Worker | 20MB | 50MB | 30MB | 100MB | FastAPI + Redis + SQLAlchemy |
| **Total** | | | | **700MB** | Under 1GB target! |

### FastAPI Overhead Breakdown

Each FastAPI service adds:
- Python base: ~20MB
- FastAPI + Uvicorn: ~20MB
- Additional per endpoint: ~1-2MB
- **Total per service**: ~40-50MB base

For single health endpoint:
- Could save ~30MB using simple asyncio HTTP
- But lose: auto-docs, validation, consistency

## Memory Optimization Strategies

### 1. Short Term (Keep FastAPI)
- Use single shared Uvicorn worker
- Disable FastAPI features we don't use:
  ```python
  app = FastAPI(docs_url=None, redoc_url=None)  # Save ~5MB
  ```
- Lazy load heavy imports
- Use `__slots__` for frequently created objects

### 2. Medium Term (After Testing)
- Profile actual memory usage in production
- Consider switching storage worker to simple HTTP
- Use Alpine-based images (save ~50MB per container)
- Enable Python optimizations (-O flag)

### 3. Long Term (If Needed)
- Replace FastAPI with aiohttp for internal services
- Use Rust/Go for critical services (executor, proxy)
- Implement connection pooling everywhere
- Consider FaaS for executor (AWS Lambda)

## Testing Memory Usage

```bash
# Get actual memory usage
docker stats --no-stream

# Check memory limits
docker-compose ps

# Memory profiling for Python services
pip install memory-profiler
python -m memory_profiler app.py

# Check for memory leaks
while true; do
  curl http://localhost:8085/health
  sleep 1
done
# Watch docker stats in another terminal
```

## Decision: Keep FastAPI For Now

**Reasons:**
1. Consistency across services
2. Future extensibility (metrics, /ready)
3. Good debugging (auto-generated /docs)
4. 700MB total is under our 1GB target
5. Can optimize later based on real data

**Revisit when:**
- Memory usage exceeds 900MB
- Adding more services
- Performance testing shows issues
- Moving to production scale

## Structured Logging + FastAPI

**How they work together:**
1. **FastAPI** uses standard Python logging for HTTP requests
2. **Structlog** wraps Python logging for our application logs
3. **Configuration** ensures both output JSON:

```python
# Configure Python logging for libraries
logging.basicConfig(level=logging.INFO)

# Configure structlog for our code
structlog.configure(
    processors=[...JSONRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# In FastAPI startup
@app.on_event("startup")
async def startup():
    # Both will output structured JSON
    logger.info("service.started", port=8085)  # structlog
    # FastAPI logs: {"timestamp": "...", "message": "Uvicorn running"}
```

**Benefits:**
- All logs are JSON (parseable)
- Can correlate FastAPI HTTP logs with app logs
- Ready for log aggregation (CloudWatch, Datadog)
- No performance penalty