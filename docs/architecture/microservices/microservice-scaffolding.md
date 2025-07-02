# About the main.py Files

## What Are These Files?

The `main.py` files in various service directories are **scaffolding** for future microservice deployment. They were auto-generated during migration to show how each component could become a standalone REST API service.

## Current Status

### Files That Exist:
- `execution-engine/main.py` - FastAPI service wrapper for execution engines
- `event-bus/main.py` - FastAPI service for event coordination
- `monitoring/main.py` - Metrics collection service
- `storage/main.py` - Storage service API
- `queue/main.py` - Task queue service
- `security-scanner/main.py` - Security testing API
- `web-frontend/main.py` - Web UI service

### What They Do:
Each `main.py`:
1. Imports FastAPI
2. Creates service endpoints
3. Wraps the component functionality in REST APIs
4. Provides health check endpoints

## The Problem

These files assume:
- FastAPI is installed (it's not required for monolithic operation)
- Components will run as separate services (they currently don't)
- Inter-service communication via HTTP (currently direct function calls)

## Options

### Option 1: Keep as Documentation (Recommended)
Rename them to show they're examples:
```bash
mv execution-engine/main.py execution-engine/main.py.example
```

Benefits:
- Clear they're not active code
- Serve as migration guide
- No confusion about what's running

### Option 2: Delete Them
Remove since we're not using microservices yet:
```bash
rm */main.py
```

Benefits:
- Less clutter
- No confusion
- Can recreate when needed

### Option 3: Move to Examples Directory
```bash
mkdir src/examples/microservices
mv */main.py src/examples/microservices/
```

Benefits:
- Preserves the examples
- Removes from service directories
- Clear separation

## Recommendation

**Option 1** - Rename to `.example` files with added comments:

```python
# main.py.example
"""
EXAMPLE: How execution-engine could work as a standalone service

This shows how to wrap the execution engine in a REST API for
microservice deployment. Currently, the execution engine is used
directly by the platform.

To use this:
1. Install FastAPI: pip install fastapi uvicorn
2. Run: uvicorn main:app --reload
3. Access API at: http://localhost:8000/docs

Note: The monolithic platform doesn't need this file.
"""
```

This makes it clear these are architectural examples, not active code.

## Why Keep These Examples?

1. **Migration Path**: Shows how to break apart the monolith
2. **API Design**: Documents intended service interfaces  
3. **Learning**: Helps understand microservice patterns
4. **Planning**: Guides future development

## Current Architecture vs Future

### Current (Monolithic):
```
platform/app.py
    └── Directly imports and uses all components
```

### Future (Microservices):
```
Multiple Services:
- execution-engine (port 8001)
- event-bus (port 8005)  
- storage (port 8003)
- etc.

Each with main.py running FastAPI
Communication via HTTP/REST
```

The main.py files show this future state.