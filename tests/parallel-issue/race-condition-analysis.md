# Race Condition Analysis - Parallel Test Failures

## Key Evidence
1. **Resource usage is identical** between sequential and parallel runs (87-92% CPU)
2. **Tests terminate prematurely** - only 17/25 integration tests complete
3. **Both test suites fail** when run in parallel for extended periods
4. **E2e succeeds** when integration fails quickly (import error)
5. **No resource exhaustion** - same load in both scenarios

## This Points To: Coordination/State Issues

### Most Likely Causes (Ranked)

#### 1. **Test Pod Memory Limits** (512Mi)
When running in parallel, test runner pods might be competing for memory:
- Each test suite loads its own pytest, fixtures, libraries
- Memory pressure could cause OOMKill without clear logs
- Check: Add memory monitoring to coordinator debug output

#### 2. **Shared Redis/Database State**
Both test suites use the same Redis and PostgreSQL:
```python
REDIS_URL = f"redis://redis.{namespace}.svc.cluster.local:6379/0"
TEST_DATABASE_URL = f"postgresql://crucible:changeme@postgres.{namespace}.svc.cluster.local:5432/test_crucible"
```
- Possible key collisions in Redis
- Database connection pool exhaustion
- Transaction conflicts

#### 3. **Evaluation Status Race Conditions**
If both suites are monitoring evaluations:
- WebSocket/SSE event streams might cross
- Status updates could affect wrong evaluations
- Polling loops might interfere

#### 4. **Storage Service Bottlenecks**
Storage service might have:
- File locking issues
- S3 rate limiting
- Connection pool limits

#### 5. **Test Cleanup Interference**
One test suite might be cleaning up resources while the other is using them:
- Deleting evaluation data
- Clearing Redis keys
- Removing S3 objects

## How to Verify

### 1. Check Pod Termination Reason
The debug code added to coordinator.py will show:
- Pod phase and termination reason
- Container exit codes
- Whether it's OOMKill or another issue

### 2. Run with Isolated Resources
```python
# Give each test suite its own Redis database
integration: REDIS_URL = "redis://redis:6379/1"
e2e: REDIS_URL = "redis://redis:6379/2"

# Or separate PostgreSQL schemas
integration: TEST_DATABASE_URL = "postgresql://...test_crucible_integration"
e2e: TEST_DATABASE_URL = "postgresql://...test_crucible_e2e"
```

### 3. Add Connection Pool Monitoring
Log active connections in:
- Redis client
- PostgreSQL connections
- Storage service HTTP clients

### 4. Trace Evaluation Lifecycle
Add request IDs to track evaluation flow:
- Which test submitted it
- Which services processed it
- Where it might be getting mixed up

## Next Steps
1. Run with --verbose to see pod termination reasons
2. Increase test pod memory limit to 1Gi
3. Monitor Redis/PostgreSQL connections during parallel runs
4. Add mutual exclusion around shared resource access