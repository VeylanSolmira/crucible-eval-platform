# Storage Service

## Overview

The Storage Service is a RESTful API that provides a unified interface for storing and retrieving evaluation data across multiple storage backends. It implements intelligent storage routing, automatic failover, and optimized storage for different data types.

## Architecture

```
┌─────────────────┐
│   API Gateway   │
│ Storage Worker  │
│ Celery Worker   │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  Storage │
    │  Service │
    └────┬─────┘
         │
    ┌────┴─────────────┬──────────────┬─────────────┐
    ▼                  ▼              ▼             ▼
┌──────────┐    ┌────────────┐  ┌─────────┐  ┌──────────┐
│PostgreSQL│    │File System │  │  Redis  │  │    S3    │
│          │    │            │  │ (Cache) │  │ (Future) │
└──────────┘    └────────────┘  └─────────┘  └──────────┘
```

## Key Features

- **Multi-Backend Support**: PostgreSQL, File System, Redis Cache, S3 (planned)
- **Intelligent Routing**: Automatically routes large outputs to file storage
- **Automatic Failover**: Falls back to alternative storage if primary fails
- **Caching Layer**: Redis cache for frequently accessed data
- **Unified API**: Single interface regardless of storage backend
- **Storage Explorer**: Built-in UI for browsing storage contents
- **Celery Integration**: Special endpoints for Celery task updates

## Storage Strategy

### Data Routing Logic

```python
if output_size > 100KB:
    store_in = "file_system"  # Large outputs go to files
elif frequently_accessed:
    store_in = "redis_cache"  # Hot data in cache
else:
    store_in = "postgresql"   # Default structured storage
```

### Storage Thresholds

- **Inline Threshold**: 10KB - Data stored directly in database
- **Large File Threshold**: 100KB - Data externalized to file system
- **Cache TTL**: 3600 seconds - Redis cache expiration
- **Preview Size**: 1000 characters - Truncated preview for large outputs

## API Endpoints

### Evaluation Management

- `POST /evaluations` - Create new evaluation record
- `GET /evaluations/{eval_id}` - Get evaluation by ID
- `PUT /evaluations/{eval_id}` - Update evaluation
- `DELETE /evaluations/{eval_id}` - Soft delete evaluation
- `GET /evaluations` - List evaluations with pagination

### Running Evaluations

- `GET /evaluations/{eval_id}/running` - Get running container info
- `GET /evaluations/running` - List all running evaluations

### Logs Management

- `POST /evaluations/{eval_id}/logs` - Append logs to evaluation
- `GET /evaluations/{eval_id}/logs` - Get evaluation logs (with Redis cache)

### Event Tracking

- `POST /evaluations/{eval_id}/events` - Add event to evaluation history
- `GET /evaluations/{eval_id}/events` - Get evaluation event timeline

### Celery Integration

- `POST /evaluations/{eval_id}/celery-update` - Update evaluation from Celery task

### Storage Management

- `GET /storage-info` - Get storage configuration details
- `GET /storage/overview` - Get metrics for all storage backends
- `GET /storage/{backend}/details` - Get detailed info for specific backend
- `GET /evaluations/{eval_id}/complete` - Get complete evaluation with all artifacts

### Statistics & Monitoring

- `GET /statistics` - Get aggregated platform statistics
- `GET /health` - Service health check

### Documentation

- `GET /docs` - Interactive API documentation
- `GET /openapi.yaml` - OpenAPI specification

## Configuration

Environment variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://crucible:password@postgres:5432/crucible

# Redis Configuration
REDIS_URL=redis://redis:6379

# Storage Configuration
STORAGE_BACKEND=database|file|memory    # Primary backend
FALLBACK_BACKEND=file|memory           # Fallback if primary fails
ENABLE_CACHING=true|false             # Enable Redis caching
FILE_STORAGE_PATH=/app/data           # Path for file storage
LARGE_FILE_THRESHOLD=102400           # Bytes before externalizing (default: 100KB)

# Service Configuration
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

## Storage Backends

### PostgreSQL (Primary)

- Stores evaluation metadata and structured data
- Handles queries and filtering
- Maintains relationships and indexes

```sql
-- Main tables
evaluations         -- Core evaluation data
evaluation_events   -- Event history timeline
```

### File System

- Stores large outputs and logs
- Organized by evaluation ID
- Automatic compression for text files

```
/app/data/
├── evaluations/
│   ├── eval_20240701_120000_abc/
│   │   ├── output.txt
│   │   └── error.txt
│   └── eval_20240701_120001_def/
│       └── output.txt
```

### Redis Cache

- Caches frequently accessed evaluations
- Stores running evaluation info
- Temporary log storage for active evaluations

```
Keys:
- eval:{eval_id}          # Cached evaluation data
- eval:{eval_id}:running  # Running container info
- logs:{eval_id}:latest   # Latest logs for running eval
- running_evaluations     # Set of running eval IDs
```

### S3 (Future)

- Long-term archive storage
- Cost-effective for cold data
- Lifecycle policies for data aging

## Development

### Running Locally

```bash
# Install dependencies
cd storage-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up database
alembic upgrade head

# Run the service
python app.py
```

### Docker Build

```bash
docker build -f storage-service/Dockerfile -t crucible-storage-service .
```

### Testing

```bash
# Run tests
pytest tests/

# Test storage endpoints
curl http://localhost:8082/storage-info

# Create evaluation
curl -X POST http://localhost:8082/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-123",
    "code": "print(\"Hello\")",
    "language": "python",
    "status": "queued"
  }'
```

## Database Schema

### Evaluations Table

```sql
CREATE TABLE evaluations (
    id VARCHAR(255) PRIMARY KEY,
    code TEXT NOT NULL,
    language VARCHAR(50) DEFAULT 'python',
    status VARCHAR(50) NOT NULL,
    output TEXT,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    runtime_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    -- Storage optimization fields
    output_location VARCHAR(50),  -- 'inline', 'file', 's3'
    output_size INTEGER,
    error_location VARCHAR(50),
    error_size INTEGER,
    -- Celery fields
    celery_task_id VARCHAR(255),
    retries INTEGER DEFAULT 0
);

CREATE INDEX idx_evaluations_status ON evaluations(status);
CREATE INDEX idx_evaluations_created_at ON evaluations(created_at DESC);
```

### Evaluation Events Table

```sql
CREATE TABLE evaluation_events (
    id SERIAL PRIMARY KEY,
    evaluation_id VARCHAR(255) REFERENCES evaluations(id),
    event_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_events_evaluation_id ON evaluation_events(evaluation_id);
CREATE INDEX idx_events_timestamp ON evaluation_events(timestamp DESC);
```

## API Examples

### Create Evaluation

```bash
curl -X POST http://localhost:8082/evaluations \
  -H "Content-Type: application/json" \
  -d '{
    "id": "eval_20240701_120000_abc123",
    "code": "for i in range(10):\n    print(f\"Count: {i}\")",
    "language": "python",
    "status": "queued",
    "metadata": {
      "submitted_by": "api",
      "priority": "normal"
    }
  }'
```

### Update Evaluation with Output

```bash
curl -X PUT http://localhost:8082/evaluations/eval_20240701_120000_abc123 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "output": "Count: 0\nCount: 1\n...",
    "runtime_ms": 150
  }'
```

### Get Evaluation with Storage Info

```bash
curl "http://localhost:8082/evaluations/eval_20240701_120000_abc123?include_storage_info=true"
```

Response includes:
```json
{
  "id": "eval_20240701_120000_abc123",
  "status": "completed",
  "output": "Count: 0\nCount: 1\n...",
  "_storage_info": {
    "output_location": "inline",
    "output_size": 120,
    "output_truncated": false
  }
}
```

### List Running Evaluations

```bash
curl http://localhost:8082/evaluations/running
```

### Update from Celery

```bash
curl -X POST http://localhost:8082/evaluations/eval_123/celery-update \
  -H "Content-Type: application/json" \
  -d '{
    "celery_task_id": "celery-task-456",
    "task_state": "SUCCESS",
    "retries": 0,
    "output": "Task completed successfully"
  }'
```

## Monitoring & Debugging

### Health Check

```bash
curl http://localhost:8082/health
```

### Storage Overview

```bash
curl http://localhost:8082/storage/overview
```

Returns metrics for all backends:
```json
{
  "backends": {
    "database": {
      "type": "postgresql",
      "status": "healthy",
      "metrics": {
        "evaluations": 1523,
        "size_bytes": 10485760
      }
    },
    "file": {
      "type": "filesystem",
      "metrics": {
        "files": 45,
        "total_size_bytes": 52428800
      }
    }
  }
}
```

### Debug Logs

Enable debug logging:
```bash
LOG_LEVEL=DEBUG python app.py
```

## Performance Optimization

### Caching Strategy

1. **Read-Through Cache**: Check Redis before database
2. **Write-Behind**: Update database asynchronously for non-critical data
3. **Cache Warming**: Pre-load frequently accessed evaluations

### Query Optimization

- Indexed columns: status, created_at, evaluation_id
- Pagination for large result sets
- Projection queries to limit data transfer

### Storage Optimization

- Automatic compression for text outputs > 10KB
- External storage for outputs > 100KB
- Cleanup job for old evaluation data

## Error Handling

### Storage Failover

```python
try:
    # Try primary storage (PostgreSQL)
    store_in_database(evaluation)
except DatabaseError:
    # Fallback to file storage
    store_in_filesystem(evaluation)
    log_error("Database unavailable, using file storage")
```

### Data Recovery

- All storage backends maintain evaluation ID as primary key
- File storage includes metadata.json for recovery
- Redis cache can be rebuilt from primary storage

## Security Considerations

### Data Protection

- SQL injection prevention via parameterized queries
- File path validation to prevent directory traversal
- Input sanitization for all user data

### Access Control

- Internal API key validation (current)
- Row-level security planned
- Audit logging for all modifications

## Future Enhancements

1. **S3 Integration**
   - Lifecycle policies for data archival
   - Cost optimization for cold storage
   - Direct presigned URL generation

2. **Advanced Caching**
   - Distributed cache with Redis Cluster
   - Smart cache invalidation
   - Cache analytics

3. **Data Pipeline**
   - Stream processing for real-time analytics
   - Data warehouse integration
   - ETL for business intelligence

4. **Enhanced Security**
   - Encryption at rest
   - Field-level encryption for sensitive data
   - Compliance features (GDPR, etc.)

## Troubleshooting

### Common Issues

1. **"Database connection failed"**
   - Check DATABASE_URL environment variable
   - Verify PostgreSQL is running
   - Check network connectivity

2. **"File storage path not writable"**
   - Verify FILE_STORAGE_PATH exists
   - Check directory permissions
   - Ensure sufficient disk space

3. **"Redis connection refused"**
   - Verify REDIS_URL is correct
   - Check if Redis is running
   - Review Redis logs

### Maintenance Commands

```bash
# Check storage usage
du -sh /app/data/*

# Clean up old files
find /app/data -mtime +30 -delete

# Rebuild cache
python scripts/rebuild_cache.py

# Database vacuum
psql $DATABASE_URL -c "VACUUM ANALYZE evaluations;"
```

## Contributing

1. Test with multiple storage backends
2. Maintain backward compatibility
3. Update API documentation
4. Add integration tests
5. Consider storage costs

## License

See main project LICENSE file.