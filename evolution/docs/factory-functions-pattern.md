# Factory Functions and Interface Abstraction

## Overview

Factory functions are a design pattern that creates objects while hiding implementation details. They're especially powerful for abstracting different interfaces and allowing systems to evolve without breaking existing code.

## Basic Factory Pattern

```python
def create_engine(engine_type: str = "subprocess") -> ExecutionEngine:
    """Factory function that hides which concrete class is used"""
    if engine_type == "subprocess":
        return SubprocessEngine()
    elif engine_type == "docker":
        return DockerEngine()
    elif engine_type == "gvisor":
        return GVisorEngine()
    else:
        raise ValueError(f"Unknown engine type: {engine_type}")

# User doesn't need to know about specific classes
engine = create_engine("docker")
```

## Key Benefits

### 1. **Decoupling**
Code depends on interfaces, not concrete classes:
```python
# Without factory - tightly coupled
engine = DockerEngine()  # What if we want gVisor later?

# With factory - loosely coupled
engine = create_engine(config.get('engine_type', 'docker'))
```

### 2. **Flexibility**
Easy to add new implementations without changing user code:
```python
def create_storage(storage_type: str) -> StorageService:
    if storage_type == "memory":
        return InMemoryStorage()
    elif storage_type == "file":
        return FileStorage("./storage")
    elif storage_type == "s3":  # New implementation
        return S3Storage(bucket="evaluations")
    # User code doesn't change!
```

### 3. **Configuration**
Choose implementations at runtime based on environment:
```python
def create_api(platform, environment="development"):
    if environment == "development":
        return SimpleHTTPAPI(platform)
    elif environment == "production":
        return FastAPIAdapter(platform)
    elif environment == "testing":
        return MockAPI(platform)
```

### 4. **Testing**
Easy to inject mocks and stubs:
```python
# In tests
mock_engine = Mock(spec=ExecutionEngine)
mock_engine.execute.return_value = {"status": "completed"}

# Factory can return mock for testing
def create_engine(engine_type="mock"):
    if engine_type == "mock":
        return mock_engine
    # ... normal implementations
```

### 5. **Evolution**
Change implementations without breaking users:
```python
# Version 1: Simple implementation
def create_monitor():
    return InMemoryMonitor()

# Version 2: Add advanced features
def create_monitor(advanced=False):
    if advanced:
        return AdvancedMonitor()  # New features!
    return InMemoryMonitor()

# Old code still works, new code gets features
```

## Obscuring Framework Differences

Factory functions excel at hiding complex framework differences:

### Problem: Different Web Frameworks
```python
# Flask style
app = Flask(__name__)
@app.route('/api/status')
def status():
    return jsonify({"status": "ok"})

# FastAPI style
app = FastAPI()
@app.get('/api/status')
async def status():
    return {"status": "ok"}

# http.server style
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/status':
            self.send_response(200)
```

### Solution: Factory Abstraction
```python
def create_web_frontend(platform, framework="auto") -> WebFrontendService:
    """
    Factory that returns a consistent interface regardless of framework.
    The user doesn't need to know Flask vs FastAPI differences.
    """
    if framework == "auto":
        # Detect best available framework
        if _is_fastapi_available():
            framework = "fastapi"
        elif _is_flask_available():
            framework = "flask"
        else:
            framework = "simple"
    
    if framework == "flask":
        return FlaskFrontend(platform)
    elif framework == "fastapi":
        return FastAPIFrontend(platform)
    else:
        return SimpleHTTPFrontend(platform)

# Usage is identical regardless of framework!
frontend = create_web_frontend(platform)
frontend.start(port=8000)
```

## Real Examples from Our Codebase

### 1. API Service Creation
```python
def create_api_service(platform: TestableEvaluationPlatform) -> APIService:
    """Create API service with platform integration"""
    return APIService(platform)

def create_api_handler(api_service: APIService) -> RESTfulAPIHandler:
    """Create handler that maps routes to API methods"""
    return RESTfulAPIHandler(api_service)
```

### 2. Engine Selection
```python
def create_production_engine() -> ExecutionEngine:
    """Smart factory that chooses best available engine"""
    try:
        # Check for gVisor
        if subprocess.run(['docker', 'info'], capture_output=True).returncode == 0:
            if 'runsc' in subprocess.run(['docker', 'info'], capture_output=True, text=True).stdout:
                return GVisorEngine('runsc')
            return DockerEngine()
    except:
        pass
    
    # Fallback
    print("WARNING: Using unsafe subprocess engine")
    return SubprocessEngine()
```

### 3. Storage Backend Selection
```python
def create_storage(config: Dict[str, Any]) -> StorageService:
    """Create storage based on configuration"""
    storage_type = config.get('storage_type', 'file')
    
    if storage_type == 'memory':
        return InMemoryStorage()
    elif storage_type == 'file':
        path = config.get('storage_path', './storage')
        return FileStorage(path)
    elif storage_type == 'redis':
        return RedisStorage(
            host=config.get('redis_host', 'localhost'),
            port=config.get('redis_port', 6379)
        )
    elif storage_type == 's3':
        return S3Storage(
            bucket=config['s3_bucket'],
            prefix=config.get('s3_prefix', 'evaluations/')
        )
```

## Factory Functions in TRACE-AI Architecture

In our modular architecture, factories are essential for component evolution:

```python
# Early stage - monolithic Python
platform = create_platform(
    engine=create_engine("subprocess"),
    storage=create_storage({"type": "memory"}),
    monitor=create_monitor()
)

# Later stage - distributed services
platform = create_platform(
    engine=create_engine("kubernetes"),  # Now talks to K8s API
    storage=create_storage({              # Now uses cloud storage
        "type": "s3",
        "bucket": "prod-evaluations"
    }),
    monitor=create_monitor("prometheus")  # Now exports metrics
)
```

The factory pattern allows components to evolve from simple Python classes to full microservices while maintaining the same interface for users.

## Best Practices

1. **Return Interfaces, Not Concrete Types**
   ```python
   def create_engine() -> ExecutionEngine:  # Good - returns interface
       return DockerEngine()
   
   def create_engine() -> DockerEngine:     # Bad - returns concrete type
       return DockerEngine()
   ```

2. **Use Configuration Objects**
   ```python
   @dataclass
   class EngineConfig:
       type: str = "docker"
       timeout: int = 300
       memory_limit: str = "512m"
   
   def create_engine(config: EngineConfig) -> ExecutionEngine:
       # Easier to extend than multiple parameters
   ```

3. **Provide Sensible Defaults**
   ```python
   def create_api(platform=None, port=8000, framework="auto"):
       if platform is None:
           platform = create_default_platform()
       # ...
   ```

4. **Document Available Options**
   ```python
   def create_frontend(platform, style="advanced") -> WebFrontendService:
       """
       Create web frontend.
       
       Args:
           platform: The evaluation platform
           style: Frontend style - 'simple', 'advanced', or 'react'
       
       Returns:
           WebFrontendService configured with chosen style
       """
   ```

5. **Consider Factory Classes for Complex Creation**
   ```python
   class PlatformFactory:
       """Factory for creating configured platforms"""
       
       def __init__(self, config: Dict[str, Any]):
           self.config = config
       
       def create_development_platform(self) -> Platform:
           """Create platform suitable for development"""
           return Platform(
               engine=SubprocessEngine(),
               storage=InMemoryStorage(),
               monitor=SimpleMonitor()
           )
       
       def create_production_platform(self) -> Platform:
           """Create platform suitable for production"""
           return Platform(
               engine=self._create_secure_engine(),
               storage=self._create_persistent_storage(),
               monitor=self._create_advanced_monitor()
           )
   ```

## Conclusion

Factory functions are a simple but powerful pattern that enables:
- Clean separation between interface and implementation
- Easy testing and mocking
- Runtime configuration
- Gradual system evolution
- Framework abstraction

In modular architectures like TRACE-AI, they're essential for allowing components to evolve independently while maintaining stable interfaces.