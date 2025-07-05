# Flower Health Check Configuration

## Update: Solution Found

Flower 2.0+ includes a dedicated `/healthcheck` endpoint that:
- Returns "OK" with 200 status when healthy
- **Does not require authentication**
- Perfect for load balancers and container orchestrators

## Previous Understanding (Incorrect)

We initially believed Flower had these limitations:
1. ~~No dedicated health endpoint~~ - `/healthcheck` exists in newer versions
2. ~~All endpoints require authentication~~ - Health check endpoint is public
3. No granular permissions - All authenticated users have full admin access (still true)
4. No read-only endpoints - Can't create limited users (still true)

## Recommended Solution

Use the dedicated health check endpoint:
```yaml
healthcheck:
  test: ["CMD", "wget", "--quiet", "--spider", "http://localhost:5555/healthcheck"]
  interval: 30s
  timeout: 10s
  retries: 3
```

This verifies:
- Flower process is running and responsive
- Web server is functioning
- Application is initialized

## Why Previous Attempts Failed

### Using API endpoints with auth
- Requires embedding credentials in health check (security risk)
- Credentials might appear in logs
- No way to create a limited-access health check user
- The `wget` in Flower's container is BusyBox version with limited auth support

### Custom health endpoint
- Would require forking/patching Flower
- Maintenance burden
- Still wouldn't solve the auth problem

## Alternatives to Flower

### 1. Custom Celery Monitoring Dashboard
- **Pros**: Full control, proper health checks, granular permissions
- **Cons**: Development effort, maintenance burden

### 2. Prometheus + Grafana
- **Pros**: Industry standard, powerful querying, proper health checks
- **Cons**: More complex setup, requires Celery exporters

### 3. ELK Stack (Elasticsearch, Logstash, Kibana)
- **Pros**: Good for log aggregation, powerful search
- **Cons**: Heavy resource usage, complex setup

### 4. Commercial Solutions
- **Datadog**: Celery integration available
- **New Relic**: APM with Celery support
- **Sentry**: Error tracking with performance monitoring

### 5. Celery Events + Custom API
- **Pros**: Built on Celery's event system, lightweight
- **Cons**: Requires custom development

### 6. Redis Commander / RedisInsight
- **Pros**: Can view Celery queues directly
- **Cons**: No task-specific features, just queue inspection

## Recommendation

For production systems, consider:
1. **Short term**: Accept Flower's limitations with basic port check
2. **Medium term**: Add Prometheus metrics to Celery workers
3. **Long term**: Build or adopt a solution with proper health checks and RBAC

## References

- [Flower GitHub Issue #945](https://github.com/mher/flower/issues/945) - Open feature request for health check endpoint
- [Celery Monitoring Guide](https://docs.celeryq.dev/en/stable/userguide/monitoring.html)

## Related Issues

### Frontend Cache Coherency
- **Issue**: Running evaluations list doesn't update immediately when evaluation completes
- **Cause**: React Query cache invalidation timing with polling intervals
- **Solution**: Added invalidation in `useEvaluationLogs` when `is_running` becomes false
- **See**: `/frontend/hooks/useEvaluation.ts`