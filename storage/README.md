# Storage System

The Crucible Platform storage system provides a flexible, pluggable architecture for persisting evaluation data across different backends.

## Architecture

```
┌─────────────────┐
│   API Layer     │
└────────┬────────┘
         │
┌────────▼────────┐
│ Storage Manager │ ← Coordinates between backends
└────────┬────────┘
         │
    ┌────┴────┬─────────┬──────────┐
    │         │         │          │
┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌─────▼─────┐
│Memory│ │ File │ │  DB  │ │Redis/S3   │
│Storage│ │Storage│ │Storage│ │(Future)   │
└──────┘ └──────┘ └──────┘ └───────────┘
```

## Storage Backends

### 1. **Database Storage** (PostgreSQL)
- **Purpose**: Primary storage for structured data
- **Features**: ACID transactions, indexed queries, relationships
- **Use cases**: Evaluation metadata, search, analytics

### 2. **File Storage**
- **Purpose**: Simple persistent storage, good for development
- **Features**: JSON files, atomic writes, directory structure
- **Use cases**: Development, small deployments, fallback storage

### 3. **In-Memory Storage**
- **Purpose**: Testing and caching
- **Features**: Fast, thread-safe, no persistence
- **Use cases**: Unit tests, temporary cache

### 4. **Redis Storage** (Future)
- **Purpose**: Fast cache and queue state
- **Features**: TTL support, pub/sub, atomic operations
- **Use cases**: Active evaluations, real-time updates

### 5. **S3 Storage** (Future)
- **Purpose**: Large file storage
- **Features**: Scalable, cost-effective, CDN integration
- **Use cases**: Code artifacts, large outputs, logs

## Usage

### Basic Usage

```python
from storage import FlexibleStorageManager, DatabaseStorage, FileStorage

# Create storage manager
storage = FlexibleStorageManager(
    primary_storage=DatabaseStorage(),
    fallback_storage=FileStorage('./data'),
    cache_storage=InMemoryStorage()
)

# Create evaluation
await storage.create_evaluation("eval-123", "print('Hello')")

# Update status
await storage.update_evaluation("eval-123", status="completed", output="Hello")

# Retrieve
evaluation = await storage.get_evaluation("eval-123")
```

### Configuration by Environment

```python
import os
from storage.integration_example import create_storage_manager

# Automatically configures based on ENVIRONMENT variable
storage = create_storage_manager()
```

## Testing

Each storage backend implements a common test suite to ensure consistent behavior:

```bash
# Run all storage tests
python storage/run_tests.py

# Run specific backend tests
python -m unittest storage.backends.database.tests
python -m unittest storage.backends.file.tests
python -m unittest storage.backends.memory.tests
```

## Database Schema

The database storage uses three main tables:

### evaluations
- `id` (primary key) - Evaluation ID
- `code_hash` - SHA256 of submitted code
- `status` - Current status (queued, running, completed, failed)
- `created_at`, `started_at`, `completed_at` - Timestamps
- `output_preview`, `error_preview` - Inline storage for small outputs
- `output_s3_key`, `error_s3_key` - References for large outputs
- `metadata` - JSON field for flexible data

### evaluation_events
- `id` (primary key)
- `evaluation_id` (foreign key)
- `event_type` - Type of event
- `timestamp` - When it occurred
- `message` - Human-readable message
- `metadata` - Additional event data

### evaluation_metrics
- `id` (primary key)
- `evaluation_id` (foreign key)
- `metric_name` - Name of metric
- `metric_value` - Numeric value
- `unit` - Unit of measurement
- `timestamp` - When recorded

## Storage Strategy

The storage manager implements a smart storage strategy:

1. **Small data (<1MB)**: Stored inline in database
2. **Large data (>1MB)**: Stored in filesystem/S3, preview in database
3. **Hot data**: Cached in memory/Redis
4. **Cold data**: Archived to S3

## Adding New Storage Backends

To add a new storage backend:

1. Create a new module in `storage/backends/`
2. Implement the `StorageService` interface
3. Add backend-specific tests
4. Update the storage manager to support the new backend

Example:
```python
from storage.base import StorageService

class RedisStorage(StorageService):
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url)
    
    def store_evaluation(self, eval_id: str, data: Dict[str, Any]) -> bool:
        # Implementation
        pass
    
    # ... implement other required methods
```

## Migration from Old Storage

If you have data in the old `/src/storage` format, use the migration script:

```bash
python storage/migrate_old_data.py --source /src/storage --target /storage
```

## Best Practices

1. **Always use the storage manager** rather than backends directly
2. **Handle storage failures gracefully** - the manager provides fallback support
3. **Use appropriate storage for data size** - don't store large files in the database
4. **Clean up old data** - implement retention policies
5. **Monitor storage usage** - set up alerts for disk space

## Future Enhancements

- [ ] Redis integration for caching
- [ ] S3 integration for large files
- [ ] Compression for stored data
- [ ] Encryption at rest
- [ ] Data retention policies
- [ ] Storage metrics and monitoring