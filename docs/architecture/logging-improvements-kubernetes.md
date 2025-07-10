# Logging Improvements for Kubernetes Migration

## Current Docker Limitations

### 1. Log Loss on Timeout
- Container.stop() removes container before final log retrieval
- No built-in way to preserve logs after container removal
- Generic error message provides no debugging info

### 2. Output Overwriting in UI
- Frontend displays only latest stdout value
- No accumulation of output lines
- Each update replaces previous content

### 3. stdout/stderr Mixing
- Docker log API combines streams
- Cannot distinguish error output from standard output
- Known limitation documented in Week 4

## Kubernetes Solutions

### 1. Timeout Handling
```yaml
apiVersion: batch/v1
kind: Job
spec:
  activeDeadlineSeconds: 30  # Kubernetes-native timeout
  template:
    spec:
      containers:
      - name: evaluation
        image: executor:latest
        # Logs persist after pod completion/termination
```

**Benefits:**
- Logs available via `kubectl logs` even after timeout
- Can add preStop lifecycle hook for graceful shutdown
- Automatic "DeadlineExceeded" status

### 2. Log Streaming Architecture
```yaml
# Sidecar pattern for log collection
containers:
- name: evaluation
  image: executor:latest
- name: log-forwarder
  image: fluentbit:latest
  # Streams logs to storage in real-time
```

**Benefits:**
- Real-time log forwarding prevents loss
- Separate stdout/stderr handling
- Built-in buffering and retry

### 3. Frontend Improvements (Post-K8s)
```typescript
// Accumulating log viewer
interface LogEntry {
  timestamp: string
  stream: 'stdout' | 'stderr'
  content: string
}

const [logEntries, setLogEntries] = useState<LogEntry[]>([])

// Append new entries instead of replacing
const handleLogUpdate = (newEntry: LogEntry) => {
  setLogEntries(prev => [...prev, newEntry])
}
```

## Implementation Priority

### Don't Implement Now (Docker)
- Log buffering in executor service
- Complex state management for accumulation  
- Custom timeout handling with log preservation
- stdout/stderr separation workarounds

### Do Implement in Kubernetes
- Native job timeouts with `activeDeadlineSeconds`
- Fluentd/Fluent Bit sidecar for log streaming
- Persistent volume for log storage
- WebSocket streaming from log aggregator
- Proper log entry accumulation in frontend

## Migration Path

1. **Phase 1**: Document current limitations
2. **Phase 2**: Kubernetes deployment with basic logging
3. **Phase 3**: Add log aggregation layer
4. **Phase 4**: Implement streaming to frontend
5. **Phase 5**: Add search, filtering, and export

## Estimated Effort

- Docker workaround: 2-3 days (throwaway code)
- Kubernetes solution: 2-3 days (permanent architecture)

## Recommendation

**Wait for Kubernetes migration** to implement proper logging. Current Docker limitations make any solution temporary and complex. Focus demo scripts on successful executions rather than timeout scenarios.