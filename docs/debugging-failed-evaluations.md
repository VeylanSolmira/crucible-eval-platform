# Debugging Failed Evaluations

## Core Principles

1. **Logs are in Loki** - All evaluation logs are stored in Loki for 24 hours
2. **We must be able to determine failure reasons** - It is unacceptable to not know why evaluations fail
3. **Resource constraints are expected** - Tests run under serious resource constraints by design
4. **Mechanisms exist to handle constraints** - We have capacity checking, retries, queueing, and cleanup controllers
5. **When mechanisms fail, we need specifics** - Generic statements about "resource constraints" are insufficient

## When an Evaluation Fails

### Your Job
1. **Find the logs in Loki** - Use the Loki query guide
2. **Determine the specific failure reason** - Not generic possibilities
3. **If logs are insufficient, modify the platform** - Add logging/observability to capture what's needed

### What NOT to Do
- Don't give up on Loki queries after one attempt
- Don't make generic statements about possible causes
- Don't tell anyone that logs are necessary (we know)
- Don't say we need better observability without first exhausting current options

## Process
1. Query Loki for the specific evaluation ID
2. Check logs from all relevant services (API, Celery, Dispatcher, Storage)
3. Look for the exact error message or failure point
4. If logs are missing, identify what logging needs to be added
5. Rerun the test with enhanced logging if needed

## Important: Pod Cleanup
**Pods are cleaned up with a 10s grace period by the cleanup controller.** The pods themselves will not be available for inspection, but logs are retained in Loki. Never tell the human that pods aren't available - just query Loki for the logs.

## Reference
See [Loki Query Guide](./loki-query-guide.md) for query examples and techniques.