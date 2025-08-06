# Parallel Test Failure Debugging

## Problem Statement
When running e2e and integration tests in parallel, both test suites fail, but when run individually they pass. The cluster shows similar resource pressure (87-92% CPU) in both scenarios.

## Key Evidence
1. Evaluation `20250803_044322_03b080cd` stayed in "provisioning" for 66s and never got a pod
2. E2e test output stops abruptly without pytest summary line
3. Both integration and e2e tests fail when run in parallel (both missing pytest summary line)
4. Performance tests with 20-50 evaluations work fine
5. Resource pressure is identical whether running tests individually or in parallel

## Top 5 Most Likely Causes (Ranked)

### 1. **Dispatcher Queue Processing Under Parallel Load**
- **Evidence**: Evaluation `20250803_044322_03b080cd` stayed in "provisioning" for 66s and never got a pod
- **Why this ranks #1**: The evaluation exists in the API but no Kubernetes job was created, pointing directly to dispatcher failure
- **Specific to parallel**: Single test suites work fine, suggesting the dispatcher can't handle concurrent evaluation submissions

### 2. **Test Output Stream Cutoff / Log Collection Race**
- **Evidence**: E2e test output stops abruptly at `[0.5s] 20250803_044454_fbc6081b: provisioning` then shows as failed
- **Why this ranks #2**: No pytest summary line found = marked as failed, even if tests actually passed
- **Specific to parallel**: Multiple log streams competing, kubectl logs process might be terminated prematurely

### 3. **E2E Test-Specific Timing/State Issues**
- **Evidence**: Both test suites fail in parallel with missing pytest summary lines
- **Why this ranks #3**: E2e tests submit evaluations that intentionally fail (sys.exit, division by zero) which might interact poorly under load
- **Specific to parallel**: Error handling paths might have race conditions when processing multiple failures simultaneously

### 4. **API Connection/Session Limits Between Test Pods**
- **Evidence**: Two test runner pods making concurrent API requests from inside the cluster
- **Why this ranks #4**: Could cause submission failures or timeouts that manifest as "provisioning" stuck states
- **Specific to parallel**: Single test suite = single connection source, parallel = multiple sources

### 5. **Kubernetes API Rate Limiting for Job Creation**
- **Evidence**: Some evaluations get jobs created, others don't
- **Why this ranks #5**: K8s API might throttle job creation when receiving from multiple sources
- **Specific to parallel**: Sequential job creation works, but concurrent submissions might hit rate limits

## Investigation Steps

### For Cause #1 (Dispatcher Queue Processing)
- [ ] Check dispatcher logs during parallel run for errors
- [ ] Monitor Redis queue depth during parallel tests
- [ ] Look for evaluation submission confirmations
- [ ] Check if dispatcher has concurrency limits

### For Cause #2 (Log Stream Cutoff)
- [ ] Compare captured_logs length vs actual test output
- [ ] Check if kubectl logs process is being terminated
- [ ] Monitor log thread completion status
- [ ] Add debugging to track when/why logs stop

### For Cause #3 (E2E Test Timing)
- [ ] Compare exact test failures between parallel and individual runs
- [ ] Check if error evaluations behave differently under load
- [ ] Look for timeout differences in adaptive waiter
- [ ] Monitor evaluation state transitions

### For Cause #4 (API Connection Limits)
- [ ] Check API logs for connection errors
- [ ] Monitor connection pool usage
- [ ] Look for HTTP timeout/retry patterns
- [ ] Check if test pods can communicate properly

### For Cause #5 (K8s API Limits)
- [ ] Check Kubernetes API server logs
- [ ] Monitor job creation rate
- [ ] Look for throttling errors
- [ ] Check if jobs are created but with delays

## Next Steps
1. Analyze the logs in this folder to validate/eliminate causes
2. Focus on #1 and #2 as most likely based on evidence
3. Create targeted debugging for dispatcher behavior under parallel load

## Fix Applied

### Log Termination Race Condition (Cause #2)
Fixed in coordinator.py by removing premature termination of kubectl logs process:
- Previously: Terminated logs immediately when job showed as complete
- Now: Wait up to 30 seconds for kubectl logs to finish naturally
- This ensures we capture the pytest summary line which often comes last

See `log-termination-fix.md` for detailed explanation.

## Critical Discovery

The pods are NOT actually terminating early! Instead:
1. Integration tests show only 17/25 PASSED before logs stop (should be 25)
2. Tests are still running when coordinator marks job as failed
3. Kubernetes reports `active: 0` (no active pods) prematurely

This means either:
- The test pod is crashing/being killed (OOM, CPU throttling, eviction)
- Kubernetes API is incorrectly reporting job status
- There's a race condition in how Kubernetes tracks pod completion

Added debug logging to coordinator.py to capture:
- Job status and conditions when marked complete
- Pod phase and termination reasons
- Container exit codes and messages