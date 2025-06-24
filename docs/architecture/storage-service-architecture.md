# Storage Service Architecture (Option 3)

## Overview
A dedicated storage microservice that handles all storage operations, providing a unified API for reading and writing evaluation data.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ API Service │     │Queue Worker │     │   Other     │
│  (Reader)   │     │  (Writer)   │     │  Services   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                     │
       │ GET /storage/     │ POST /storage/     │
       │ evaluations/{id}  │ evaluations        │
       └───────────┬───────┴─────────────────────┘
                   │
           ┌───────▼────────┐
           │Storage Service │
           │   (FastAPI)    │
           └───────┬────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐    ┌───────▼────────┐
│   PostgreSQL   │    │  File Storage  │
│   (Primary)    │    │  (Large Files) │
└────────────────┘    └────────────────┘
```

## Benefits

1. **Single Source of Truth**: All storage operations go through one service
2. **Access Control**: Can implement fine-grained permissions at the API level
3. **Consistency**: Ensures all services use the same storage logic
4. **Flexibility**: Can swap storage backends without affecting other services
5. **Caching**: Centralized caching layer for all services
6. **Monitoring**: Single point to monitor storage operations

## Implementation Details

### API Endpoints

```yaml
/storage/evaluations:
  post:
    description: Store a new evaluation
    security: [write_key]
    
/storage/evaluations/{id}:
  get:
    description: Retrieve an evaluation
    security: [read_key]
  put:
    description: Update an evaluation
    security: [write_key]
    
/storage/evaluations:
  get:
    description: List evaluations
    parameters: [limit, offset, status]
    security: [read_key]
```

### Service Configuration

```python
class StorageServiceConfig:
    # API Configuration
    port: int = 8086
    host: str = "0.0.0.0"
    
    # Authentication
    read_api_keys: List[str]  # Keys that can read
    write_api_keys: List[str]  # Keys that can write
    
    # Storage backends
    database_url: str
    file_storage_path: str
    s3_bucket: Optional[str]
    
    # Performance
    cache_ttl: int = 300
    max_request_size: int = 100 * 1024 * 1024  # 100MB
```

## Trade-offs

### Pros
- Clean separation of concerns
- Easy to scale storage independently
- Can implement complex storage logic (sharding, replication)
- Better security through API-level access control
- Easier to test and mock

### Cons
- Additional network hop for all storage operations
- More complexity (another service to deploy and monitor)
- Potential single point of failure (needs HA setup)
- Increased latency for storage operations

## Migration Path

1. **Phase 1**: Create storage service with same interface as current storage library
2. **Phase 2**: Update services to use storage service API instead of direct storage
3. **Phase 3**: Remove storage library imports from other services
4. **Phase 4**: Optimize storage service (caching, batching, etc.)

## When to Choose This Option

Use a dedicated storage service when:
- Multiple services need different access patterns (read vs write)
- Storage logic is complex (multi-backend, caching, etc.)
- Need fine-grained access control
- Want to scale storage independently
- Planning to implement advanced features (replication, sharding)

Don't use when:
- Simple application with few services
- Low latency is critical
- Want to minimize operational complexity