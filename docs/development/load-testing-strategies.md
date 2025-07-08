# Load Testing Strategies with Rate Limits

## Current Rate Limits

The platform implements nginx rate limiting:
- **API endpoints**: 10 requests/second per IP (burst: 10)
- **General traffic**: 30 requests/second per IP (burst: 20)

## Testing Strategies

### 1. Rate-Aware Load Testing (Implemented)

The `test_load.py` script uses a token bucket algorithm to stay within rate limits while maximizing load:

```bash
# Run with specific concurrency and total evaluations
python tests/integration/test_load.py 20 100

# Run sustained load for 60 seconds
python tests/integration/test_load.py sustained 60
```

**Advantages:**
- Works with existing infrastructure
- Tests realistic user behavior
- No security implications
- Measures actual user experience

**Limitations:**
- Maximum 10 req/s throughput
- Can't test system limits
- May not reveal scaling issues

### 2. Testing Override via Custom Header (Proposed)

Add a bypass for authorized testing by checking for a special header:

```nginx
# In nginx.conf - create a separate zone for testing
map $http_x_load_test_key $limit_zone {
    default "api";
    "YOUR_SECRET_TEST_KEY" "test";
}

# Define test zone with higher limits
limit_req_zone $binary_remote_addr zone=test:10m rate=100r/s;

# In crucible.conf - use mapped zone
location /api/ {
    limit_req zone=$limit_zone burst=10 nodelay;
    proxy_pass http://api-service:8080;
}
```

Then in tests:
```python
headers = {"X-Load-Test-Key": "YOUR_SECRET_TEST_KEY"}
response = requests.post(f"{API_BASE_URL}/eval", json=eval_request, headers=headers)
```

**Advantages:**
- Can test true system limits
- Controlled access via secret key
- Easy to enable/disable

**Security Considerations:**
- Key must be kept secret
- Should only work in non-production environments
- Consider IP allowlist for extra security

### 3. Internal Testing Endpoint (Proposed)

Create a separate internal endpoint that bypasses rate limits:

```nginx
# Internal testing endpoint - no rate limiting
location /internal/api/ {
    # Restrict to local/internal IPs only
    allow 127.0.0.1;
    allow 172.16.0.0/12;  # Docker networks
    deny all;
    
    # No rate limiting
    proxy_pass http://api-service:8080/api/;
}
```

**Advantages:**
- Complete isolation from public endpoints
- No risk of abuse
- Can test at full capacity

**Limitations:**
- Only works from internal network
- May not reflect real-world routing

### 4. Temporary Rate Limit Adjustment (Simplest)

For load testing sessions, temporarily adjust nginx config:

```bash
# Before testing - increase limits
docker exec -it metr-eval-platform-nginx-1 sed -i 's/rate=10r/rate=100r/' /etc/nginx/nginx.conf
docker exec -it metr-eval-platform-nginx-1 nginx -s reload

# Run load tests
python tests/integration/test_load.py 50 200

# After testing - restore limits
docker exec -it metr-eval-platform-nginx-1 sed -i 's/rate=100r/rate=10r/' /etc/nginx/nginx.conf
docker exec -it metr-eval-platform-nginx-1 nginx -s reload
```

**Advantages:**
- No code changes needed
- Full control over limits
- Easy to implement

**Disadvantages:**
- Manual process
- Risk of forgetting to restore
- Affects all users during test

## Recommendations

1. **For routine testing**: Use the rate-aware load test to verify normal operation
2. **For capacity planning**: Implement the custom header approach with proper security
3. **For stress testing**: Use temporary rate limit adjustment in isolated environments
4. **For CI/CD**: Rate-aware tests ensure tests don't fail due to rate limits

## Metrics to Track

Regardless of approach, track these key metrics:
- Request throughput (req/s)
- Response times (p50, p95, p99)
- Queue depth over time
- Executor utilization
- Resource usage (CPU, memory, I/O)
- Error rates and types

## Example Test Scenarios

### Scenario 1: Normal Load
- 10 concurrent users
- 5 req/s sustained
- Mix of fast/slow evaluations
- Expected: All complete successfully

### Scenario 2: Peak Load
- 50 concurrent users
- 10 req/s (at rate limit)
- 80% fast, 20% slow evaluations
- Expected: Some queueing, all eventually complete

### Scenario 3: Stress Test (with bypass)
- 100 concurrent users
- 50+ req/s
- Even mix of evaluation types
- Expected: Find system breaking point