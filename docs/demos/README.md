# Platform Demo Guide

## Overview
This guide documents all demo scenarios, their current status, known limitations, and planned improvements.

## Demo Categories

### 1. Basic Flow ✅ COMPLETED
**Status**: Working well
**Script**: [basic-flow-manual-steps.md](./basic-flow-manual-steps.md)
**What it shows**:
- Code submission through Monaco editor
- Real-time status updates
- Successful execution with output

**Known Limitations**: None
**Demo Tips**: 
- Pre-warm with one execution before demo
- Use simple, visual code examples

### 2. Error Handling ✅ COMPLETED (with caveats)
**Status**: Partially working - needs improvements
**Scripts**: Available in `/templates/demos/`

#### 2.1 Syntax Errors
**Status**: ✅ Working perfectly
**Example**: `syntax-error.py`
**What it shows**: Clear Python syntax error messages
**Known Limitations**: None

#### 2.2 Timeouts
**Status**: ⚠️ Works but logs are lost
**Example**: Any code with `time.sleep(40)` 
**What it shows**: Container termination after 30s
**Known Limitations**: 
- Logs disappear with "Container was removed before logs could be retrieved"
- No partial output preserved
**Workaround**: Use [timeout-workaround.md](./timeout-workaround.md) examples
**Fix Timeline**: Post-Kubernetes (logs will persist)

#### 2.3 Memory Exhaustion
**Status**: ✅ Working with exit code messaging
**Example**: `memory-exhaustion.py`
**What it shows**: Container killed when exceeding 512MB
**Improvements Made**:
- Exit code 137 now shows "Memory Limit Exceeded" with explanation
- UI displays "Process killed due to exceeding 512MB memory limit (OOM)"
- Exit status card shows details for completed evaluations
**Remaining Limitations**:
- Logs may be partially lost when container is killed
**Fix Timeline**: 
- Kubernetes migration will provide better OOM handling

#### 2.4 CPU Exhaustion
**Status**: ✅ Working well
**Example**: `cpu-exhaustion.py`
**What it shows**: CPU throttling (limited to 0.5 cores)
**Known Limitations**: 
- CPU/Memory metrics show 0 in UI
- But throttling itself works correctly
**Note**: Unlike memory, CPU limits don't kill containers

### 3. Concurrent Load 🚧 NOT STARTED
**Status**: To be implemented
**What it should show**:
- Submit 10+ evaluations simultaneously
- Queue handling
- Resource allocation
- Scaling behavior

### 4. Monitoring (Flower) 🚧 NOT STARTED
**Status**: To be implemented
**What it should show**:
- Celery queue status
- Active workers
- Task history
- Success/failure rates

### 5. Storage Explorer 🚧 NOT STARTED
**Status**: To be implemented
**What it should show**:
- PostgreSQL entries
- File storage
- Redis cache state

## Known Platform Limitations

### Critical for Demos
1. **Resource Metrics Always Show 0**
   - CPU and Memory usage displays are broken
   - Backend doesn't collect container stats
   - Fix: Hide display (Tier 2) or wait for K8s

2. **Timeout Log Loss** ✅ Exit codes now explained
   - Timeouts still lose all logs
   - OOM kills now show friendly explanation (exit code 137 → "Memory Limit Exceeded")
   - All exit codes have user-friendly messages and descriptions

3. **Log Output Issues**
   - stdout/stderr are mixed
   - Output overwrites instead of appending
   - Logs lost on container termination
   - Fix: Kubernetes migration

### Less Critical
- No evaluation history in UI (API ready, UI not implemented)
- No batch submission UI (API supports it)
- No kill button for running evaluations

## Recommended Demo Flow

### For Success-Oriented Demo (5 mins)
1. Basic "Hello World" execution
2. Show syntax error handling
3. CPU exhaustion (shows throttling)
4. Explain security isolation

### For Technical Deep-Dive (10 mins)
1. Basic execution with explanation
2. All error types with limitations explained
3. Discuss Docker vs Kubernetes improvements
4. Show monitoring if available

### What to Avoid
- Don't rely on resource metrics display
- Don't demo timeout without explaining log loss
- Don't promise features not yet implemented

## Speaking Points for Limitations

**On Resource Metrics**:
> "The resource monitoring is prepared in the UI but not yet connected to the backend. This will be implemented when we migrate to Kubernetes's native metrics server."

**On Timeout Logs**:
> "Currently, when a container times out, Docker removes it before we can retrieve the final logs. This is a known limitation that Kubernetes will solve with proper job management."

**On Memory Limits**:
> "The platform enforces strict memory limits. When exceeded, the container is immediately terminated. We're adding user-friendly messages to explain these terminations."

## Future Improvements (Post-Kubernetes)

### Immediate (Tier 2)
- ✅ Exit code messaging for clear error explanations (COMPLETED)
- Hide or fix resource metrics display

### Kubernetes Migration
- Persistent logs after container termination
- Proper stdout/stderr separation  
- Real resource metrics
- Better timeout handling
- Pod events for debugging

### Long Term
- WebSocket streaming for real-time logs
- Historical evaluation browser
- Advanced monitoring dashboard
- Multi-language support

## Demo Preparation Checklist

- [ ] Test all demos work in current environment
- [ ] Have backup examples ready
- [ ] Know how to explain each limitation
- [ ] Prepare transition statements between demos
- [ ] Have architecture diagrams ready
- [ ] Test Flower dashboard accessibility
- [ ] Ensure clean evaluation state (or explain existing ones)