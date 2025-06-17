# Monolith to Microservices: Thoughtful Decomposition

## Current State: Modular Monolith

We currently have a well-structured monolith with clear module boundaries:
```
app.py (orchestrator)
├── execution_engine/
├── queue/
├── storage/
├── monitoring/
├── api/
└── web_frontend/
```

## Why Consider Microservices?

### Forcing Functions:
1. **Security Boundary**: Execution needs Docker access, UI doesn't
2. **Scaling**: Execution is CPU-intensive, UI is not
3. **Technology**: Future UI might be React/Node.js, backend Python
4. **Team Structure**: Different teams might own different services

## Decomposition Strategy

### Phase 1: Extract Execution Service (Current Need)
**Why**: Security boundary - needs Docker socket access
```yaml
services:
  platform:     # Everything except execution
  executor:     # Just execution_engine module
```

### Phase 2: Extract Frontend (Future)
**Why**: Different technology stack, different scaling needs
```yaml
services:
  api:          # Python backend
  frontend:     # React/nginx
  executor:     # Execution service
```

### Phase 3: Full Microservices (Much Later)
**Why**: Independent scaling, team ownership
```yaml
services:
  api-gateway:
  auth-service:
  execution-service:
  queue-service:
  storage-service:
  monitoring-service:
  frontend:
```

## Decision Criteria for Service Extraction

1. **Different Security Requirements**
   - Execution needs Docker access
   - Frontend needs public internet access
   - Storage might need cloud credentials

2. **Different Scaling Patterns**
   - Execution: CPU/memory intensive, scale horizontally
   - Storage: I/O intensive, might need different storage
   - Frontend: Static files, can use CDN

3. **Different Technology Stacks**
   - Current: All Python
   - Future: Frontend (React), API (Python), Execution (Go?)

4. **Different Release Cycles**
   - Frontend: Frequent UI updates
   - Execution: Careful security updates
   - API: Feature additions

## Implementation Approach

### Option 1: Shared Codebase, Multiple Dockerfiles
```
Dockerfile.platform    # Main platform without execution
Dockerfile.executor    # Just execution service
Dockerfile.frontend    # Future: just frontend
```

**Pros**: 
- Easy refactoring
- Shared code still works
- Gradual migration

**Cons**:
- Larger images (include all code)
- Not truly independent

### Option 2: Separate Projects
```
platform/
  ├── Dockerfile
  └── src/
executor/
  ├── Dockerfile
  └── src/
shared/
  └── src/
```

**Pros**:
- True independence
- Smaller images
- Clear boundaries

**Cons**:
- Harder to refactor
- Need shared library management

### Option 3: Monorepo with Service Directories (Recommended)
```
services/
  ├── platform/
  │   ├── Dockerfile
  │   └── requirements.txt
  ├── executor/
  │   ├── Dockerfile
  │   └── requirements.txt
  └── shared/
      └── python/
```

**Pros**:
- Clear structure
- Can share code via symlinks/packages
- Each service has own dependencies
- Easy to understand

**Cons**:
- Need build orchestration
- More complex than single Dockerfile

## Current Recommendation

For METR submission, I recommend:

1. **Keep current monolith as primary**: Shows we can build integrated systems
2. **Add execution service as proof-of-concept**: Shows we understand microservices
3. **Document the journey**: Show thoughtful architecture evolution

This demonstrates:
- You can build both monoliths and microservices
- You understand the tradeoffs
- You make decisions based on actual needs, not trends

## Example: Extracting Execution Service

### Step 1: Create service interface
```python
# src/execution_engine/interface.py
class ExecutionInterface(ABC):
    @abstractmethod
    def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
        pass
```

### Step 2: Create implementations
```python
# Local implementation (current)
class LocalExecutionEngine(ExecutionInterface):
    def __init__(self):
        self.engine = DockerEngine()
    
    def execute(self, code, eval_id):
        return self.engine.execute(code, eval_id)

# Remote implementation (new)
class RemoteExecutionEngine(ExecutionInterface):
    def __init__(self, service_url):
        self.service_url = service_url
    
    def execute(self, code, eval_id):
        # HTTP call to execution service
        pass
```

### Step 3: Configuration-based selection
```python
# app.py
if os.environ.get('EXECUTION_MODE') == 'remote':
    engine = RemoteExecutionEngine(os.environ['EXECUTION_SERVICE_URL'])
else:
    engine = LocalExecutionEngine()
```

This allows running in both modes without major refactoring.