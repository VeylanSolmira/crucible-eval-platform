# Status Update Issue Test Plan

## Root Cause Analysis

We discovered the frontend was hardcoding `status: 'running' as const` for all evaluations from the running endpoint. However, the real issue is more complex:

1. **Frontend Issue (Fixed)**: RunningEvaluations.tsx was hardcoding status
2. **Backend Issue**: The `/api/evaluations?status=running` endpoint might return completed evaluations if Redis cleanup fails
3. **Event Flow Issue**: The completion events might not be published or processed correctly

## Test Strategy

### Unit Tests

#### Frontend Unit Tests

1. **RunningEvaluations Component**
   - Test that it preserves status from API response
   - Test proper transformation of evaluation data
   - Test handling of missing/invalid status values
   - Test status badge displays correct styling

2. **useRunningEvaluations Hook**
   - Test data transformation preserves all fields
   - Test polling behavior with mock timers
   - Test error handling

3. **ExecutionMonitor Component**
   - Test status updates propagate correctly
   - Test polling stops when evaluation completes

#### Backend Unit Tests

1. **Storage Service API**
   - Test `/evaluations?status=running` filters correctly
   - Test evaluation status enum validation
   - Test Redis cleanup on status updates

2. **Storage Worker**
   - Test event handler for completed/failed events
   - Test Redis cleanup logic (srem from set, delete keys)
   - Test error handling doesn't prevent cleanup

### Integration Tests

1. **Redis Cleanup Test** (`test_redis_cleanup.py`)
   - Submit evaluation
   - Verify it appears in Redis running set
   - Wait for completion
   - Verify Redis is cleaned up
   - Verify running endpoint doesn't return it

2. **Event Flow Test**
   - Monitor Redis pub/sub channels
   - Submit evaluation
   - Verify all expected events are published:
     - evaluation:queued
     - evaluation:running
     - evaluation:completed/failed
   - Verify storage-worker processes events

3. **Status Consistency Test**
   - Submit multiple evaluations
   - Complete them in different orders
   - Poll both endpoints:
     - `/api/eval/{id}` - specific evaluation
     - `/api/evaluations?status=running` - running list
   - Verify status is always consistent

4. **Race Condition Test**
   - Submit evaluation
   - Poll status while it's transitioning
   - Verify no intermediate inconsistent states
   - Test with service restarts

### End-to-End Tests

1. **UI Status Sync Test** (Playwright)
   - Submit evaluation via UI
   - Verify ExecutionMonitor shows correct status
   - Verify Evaluations list shows correct status
   - Complete evaluation
   - Verify both components update without refresh

2. **Page Refresh Test**
   - Submit evaluation
   - Let it complete
   - Refresh page
   - Verify correct status shows immediately

## Key Test Commands

```bash
# Run Redis cleanup test
python tests/integration/test_redis_cleanup.py

# Monitor Redis events
python tests/integration/test_redis_cleanup.py monitor

# Check current Redis state
python tests/integration/check_redis_state.py

# Run status diagnostics
python tests/integration/diagnose_status_update.py <eval_id>

# Run comprehensive test suite
python tests/integration/test_status_update_comprehensive.py
```

## Expected Behaviors

### When Working Correctly:

1. Evaluation submitted → appears in running list
2. Evaluation completes → removed from running list within 2-3 seconds
3. Redis `running_evaluations` set only contains actually running evaluations
4. Frontend shows consistent status across all components
5. Page refresh shows correct current status

### Common Failure Modes:

1. **Event Not Published**: Storage service doesn't publish completion event
2. **Event Not Received**: Storage-worker subscription issue
3. **Cleanup Fails**: Redis operations fail but error is swallowed
4. **Race Condition**: Status checked during transition
5. **Cache Issue**: Frontend caches stale data

## Implementation Priority

1. **High Priority**: Integration tests for Redis cleanup and event flow
2. **Medium Priority**: Frontend component unit tests
3. **Low Priority**: E2E UI tests (requires more setup)

## Success Criteria

- Zero instances of completed evaluations showing as "running"
- Redis cleanup happens within 5 seconds of completion
- All status transitions are atomic and consistent
- No manual page refresh required for status updates