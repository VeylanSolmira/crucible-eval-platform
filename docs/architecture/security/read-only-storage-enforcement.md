# Read-Only Storage Enforcement

## Current State

The API Gateway has full read-write access to storage but only uses read methods by convention. This is a security risk - a bug or compromised service could write directly to the database, bypassing the event-driven architecture.

## The Problem

```python
# Current: API Gateway can do this (but shouldn't!)
storage.create_evaluation(...)  # Works but violates architecture
storage.update_evaluation(...)  # Works but violates architecture

# Only storage worker should write
# API Gateway should only read
```

## Implementation Options

### Option 1: Read-Only Wrapper Class (Simple)
```python
class ReadOnlyStorage:
    """Wrapper that only exposes read methods"""
    def __init__(self, storage: FlexibleStorageManager):
        self._storage = storage
    
    def get_evaluation(self, eval_id: str):
        return self._storage.get_evaluation(eval_id)
    
    def list_evaluations(self, limit: int, offset: int):
        return self._storage.list_evaluations(limit, offset)
    
    def health_check(self):
        return self._storage.health_check()
    
    # No create_evaluation or update_evaluation methods!

# In API Gateway:
storage = ReadOnlyStorage(FlexibleStorageManager(config))
```

**Pros:**
- Easy to implement
- Clear API contract
- Fails at runtime if write attempted

**Cons:**
- Not enforced at database level
- Developer could still access `_storage` directly

### Option 2: Database Read-Only User (Most Secure)
```yaml
# docker-compose.yml
environment:
  # Storage Worker (read-write)
  - DATABASE_URL=postgresql://crucible_rw:${DB_PASSWORD}@postgres:5432/crucible
  
  # API Gateway (read-only)
  - DATABASE_URL=postgresql://crucible_ro:${DB_RO_PASSWORD}@postgres:5432/crucible
```

```sql
-- In PostgreSQL
CREATE USER crucible_ro WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE crucible TO crucible_ro;
GRANT USAGE ON SCHEMA public TO crucible_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO crucible_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO crucible_ro;
```

**Pros:**
- Enforced at database level
- Cannot be bypassed in code
- Standard security practice

**Cons:**
- More complex setup
- Need to manage two sets of credentials
- Migrations need care

### Option 3: Separate Storage Services
```
StorageReader (read-only service)
├── GET /evaluations
├── GET /evaluations/{id}
└── GET /health

StorageWriter (write-only service)
├── POST /evaluations
├── PUT /evaluations/{id}
└── (only accessible internally)
```

**Pros:**
- Clear service boundaries
- Can scale readers independently
- Natural caching point

**Cons:**
- Another service to deploy
- More network calls

### Option 4: Event-Sourced Reads
```python
# API Gateway reads from Redis cache
async def get_evaluation(eval_id: str):
    # Check Redis first
    cached = await redis_client.get(f"eval:{eval_id}")
    if cached:
        return json.loads(cached)
    
    # Fall back to database
    return storage.get_evaluation(eval_id)

# Storage Worker updates cache
await redis_client.set(f"eval:{eval_id}", json.dumps(evaluation))
```

**Pros:**
- Fast reads
- Eventually consistent
- Reduces database load

**Cons:**
- Cache invalidation complexity
- Eventual consistency issues

## Recommendation

For production, implement **Option 2 (Database Read-Only User)** because:

1. **Security**: Cannot be bypassed by code changes
2. **Standard**: Common pattern in production systems
3. **Auditable**: Database logs show who did what
4. **Simple**: Just different connection strings

For development/MVP, **Option 1 (Read-Only Wrapper)** is fine because:
- Quick to implement
- Makes intent clear
- Can upgrade to Option 2 later

## Implementation Steps

### Phase 1: Read-Only Wrapper (Now)
1. Create `ReadOnlyStorage` class
2. Use in API Gateway
3. Document the pattern

### Phase 2: Database Enforcement (Production)
1. Create read-only PostgreSQL user
2. Update docker-compose with separate credentials
3. Use AWS Secrets Manager for credentials
4. Update connection strings
5. Test thoroughly

### Phase 3: Monitoring
1. Add alerts for write attempts from API Gateway
2. Log all database queries
3. Regular security audits

## Testing

```python
# Test read-only enforcement
def test_readonly_storage():
    storage = ReadOnlyStorage(mock_storage)
    
    # These should work
    storage.get_evaluation("test-123")
    storage.list_evaluations(10, 0)
    
    # These should not exist
    with pytest.raises(AttributeError):
        storage.create_evaluation(...)
    
    with pytest.raises(AttributeError):
        storage.update_evaluation(...)
```

## Security Benefits

1. **Defense in Depth**: Multiple layers of protection
2. **Principle of Least Privilege**: Services only get permissions they need
3. **Audit Trail**: Clear logs of who writes data
4. **Compliance**: Meets security standards (SOC2, etc.)

## Related Patterns

- **CQRS**: Command Query Responsibility Segregation
- **Event Sourcing**: All changes as events
- **Read Replicas**: Separate databases for reads
- **API Gateway Pattern**: Central entry point with limited backend access