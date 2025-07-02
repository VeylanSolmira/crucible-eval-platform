# Storage Patterns and Events Documentation

## Overview
This document enumerates all storage event types, patterns, and recommended storage locations for the METR platform.

## Storage Event Types

### 1. Evaluation Lifecycle Events

#### EVALUATION_QUEUED
- **When**: New evaluation submitted to the platform
- **Data**: eval_id, code, language, engine, timeout, metadata
- **Storage**: PostgreSQL (evaluations table)
- **Why**: Small data, needs quick retrieval, benefits from ACID

#### EVALUATION_STARTED
- **When**: Executor begins processing
- **Data**: eval_id, executor_id, start_time
- **Storage**: PostgreSQL (update evaluations table)
- **Why**: Status update, needs consistency

#### EVALUATION_COMPLETED
- **When**: Execution finishes successfully
- **Data**: eval_id, output, success, end_time
- **Storage**: 
  - PostgreSQL: Metadata and output preview (first 1KB)
  - File/S3: Full output if > 1MB
- **Why**: Large outputs can overwhelm database

#### EVALUATION_FAILED
- **When**: Execution fails or times out
- **Data**: eval_id, error, traceback
- **Storage**: PostgreSQL
- **Why**: Error data is typically small, needs to be queryable

### 2. System Events

#### EXECUTOR_HEALTH
- **When**: Periodic health checks
- **Data**: executor_id, status, metrics
- **Storage**: Redis (ephemeral)
- **Why**: Temporary data, needs fast access

#### QUEUE_METRICS
- **When**: Queue status changes
- **Data**: queue_length, processing_count
- **Storage**: Redis or in-memory
- **Why**: Real-time metrics, don't need persistence

### 3. Security Events

#### CONTAINER_CREATED
- **When**: New container spawned for evaluation
- **Data**: container_id, eval_id, image, limits
- **Storage**: PostgreSQL (security_audit table)
- **Why**: Audit trail requirement

#### RESOURCE_VIOLATION
- **When**: Container exceeds limits
- **Data**: container_id, violation_type, details
- **Storage**: PostgreSQL (security_events table)
- **Why**: Security analysis, compliance

## Storage Patterns

### Pattern 1: Write-Through Cache
```
Request → Cache → Database → Response
```
- Use for: Frequently accessed evaluations
- Implementation: Redis cache with PostgreSQL backing

### Pattern 2: Event Sourcing
```
Event → Event Store → Projections → Read Models
```
- Use for: Audit requirements, replay capability
- Implementation: PostgreSQL events table + materialized views

### Pattern 3: CQRS (Command Query Responsibility Segregation)
```
Commands → Write Model (PostgreSQL)
Queries → Read Model (Redis/Elasticsearch)
```
- Use for: High read/write ratio
- Current: Storage worker (write) + API service (read)

### Pattern 4: Tiered Storage
```
Hot: Redis (last 24h)
Warm: PostgreSQL (last 30d)
Cold: S3 (archive)
```
- Use for: Cost optimization
- Future implementation

## Storage Decision Matrix

| Data Type | Size | Access Pattern | Recommended Storage |
|-----------|------|----------------|-------------------|
| Evaluation metadata | <1KB | Frequent reads | PostgreSQL + Redis cache |
| Code snippets | <100KB | Write once, read many | PostgreSQL |
| Small outputs | <1MB | Read occasionally | PostgreSQL |
| Large outputs | >1MB | Read rarely | S3 with PostgreSQL reference |
| Logs | Variable | Write heavy | File system → S3 |
| Metrics | Small | Time-series | Redis → Prometheus |
| Events | Small | Append-only | PostgreSQL events table |

## File Storage Use Cases

Current `/data` directory usage:
1. **Temporary execution artifacts**: Should use tmpfs
2. **Large evaluation outputs**: Should migrate to S3
3. **Debug logs**: Should use centralized logging
4. **File-based queues**: Already migrated to Redis

## Migration Recommendations

### Phase 1: Current State
- Database for evaluation metadata ✓
- File storage for outputs ✓
- Redis for events ✓

### Phase 2: Optimize Storage
- [ ] Implement S3 for large outputs
- [ ] Add Redis caching layer
- [ ] Create read-only database user for API

### Phase 3: Advanced Patterns
- [ ] Event sourcing for audit trail
- [ ] Time-series database for metrics
- [ ] CDN for static assets

## Security Considerations

1. **Encryption at Rest**
   - PostgreSQL: Enable transparent data encryption
   - S3: Use SSE-S3 or SSE-KMS
   - File system: Use encrypted volumes

2. **Access Control**
   - Database: Row-level security for multi-tenancy
   - S3: Presigned URLs for output access
   - Redis: AUTH and ACLs

3. **Data Retention**
   - Evaluations: 90 days active, then archive
   - Logs: 30 days hot, 1 year cold
   - Security events: 7 years (compliance)

## Implementation Priority

1. **High Priority**
   - Fix PostgreSQL as default ✓
   - Document storage patterns ✓
   - Implement S3 for large outputs

2. **Medium Priority**
   - Add Redis caching
   - Implement storage metrics
   - Create storage service (Option 3)

3. **Low Priority**
   - Event sourcing
   - Time-series metrics
   - Multi-region replication