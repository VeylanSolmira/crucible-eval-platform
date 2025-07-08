# The Missing Logs Mystery: A Deep Dive into Docker Event Race Conditions

## The Problem

Users reported that evaluations with uncaught exceptions (like `1/0`) would either:
1. Show as "failed" but with empty `output` and `error` fields
2. Get stuck in "running" status indefinitely

Example test case:
```python
# This simple code would trigger the bug
print("Before error")
1/0  # Uncaught ZeroDivisionError
```

## Initial Investigation

### Symptoms Observed

1. **Test Script Behavior**:
   ```bash
   curl -X POST http://localhost:8000/api/eval \
     -H "Content-Type: application/json" \
     -d '{"code": "print(\"Before error\")\n1/0", ...}'
   ```
   
   Result: Status = "failed", but output = "", error = ""

2. **Log Analysis**:
   ```
   executor-1  | Published failed event for eval_xxx (exit code: 1)
   executor-1  | Error streaming logs: 404 Client Error ... Not Found ("No such container: xxx")
   storage-worker | Received event on evaluation:failed: eval_xxx
   ```

3. **Stuck Evaluations**:
   Some evaluations never received completion events and remained in "running" status forever.

## Initial Hypothesis (Incorrect)

The first theory was that Docker was "missing" or "dropping" events:

> "The claim that Docker 'misses the die event' is where I'd dig deeper. Docker's event system is generally reliable - it's used by orchestrators like Kubernetes and Swarm. Missing events would be a critical bug."

This skepticism proved correct - Docker wasn't the problem.

## Root Cause Analysis

### The Smoking Gun

Found in the Docker event handler code:

```python
# executor-service/app.py around line 654-665
if action in ["die", "stop"]:
    eval_id = attributes.get("eval_id")
    if eval_id:
        logger.debug(f"Container {eval_id} {action} event received")
        # Get container object
        container = running_containers.get(eval_id)
        if container:  # <- THIS IS THE BUG!
            # Queue the event for async processing
            asyncio.run_coroutine_threadsafe(
                event_queue.put((eval_id, container)), loop
            )
```

**The problem**: The event handler only processes events if the container is still in the `running_containers` dictionary.

### Why This Is Broken

1. **Multiple Code Paths Remove Containers**:
   - Log retrieval endpoint
   - Kill endpoint
   - Container status checks
   - Completion handler itself

2. **Race Condition for Fast-Failing Containers**:
   ```
   Timeline:
   1. Container starts → Added to running_containers
   2. Python executes 1/0 → Exits immediately (< 1 second)
   3. Log streaming tries to access → Container already gone
   4. Something removes container from running_containers
   5. Docker sends "die" event
   6. Event handler receives event BUT skips it (container not in dict)
   7. Evaluation stuck forever!
   ```

3. **Ironic Bug Pattern**:
   > "The very containers that need proper error handling (ones that die quickly) are the ones most likely to have their events dropped."

### Additional Issues Found

1. **Log Retrieval After Container Removal**:
   ```python
   # Container is removed immediately after getting logs
   output = container.logs(stdout=True, stderr=False).decode("utf-8")
   error = container.logs(stdout=False, stderr=True).decode("utf-8")
   # ... publish event ...
   container.remove(force=True)  # But log streaming might still be running!
   ```

2. **Stderr/Stdout Separation**:
   - Python tracebacks go to stderr
   - But when combining logs, both might be empty if container was removed

## Design Philosophy Discussion

### Crash-Only Design

This bug exemplifies why "crash-only design" matters:

**Definition**: "The only way to stop the system is to crash it, and the only way to start it is to recover."

**Key Principles**:
1. No graceful shutdown - Handle abrupt termination at any point
2. No initialization - Starting = recovering from a crash  
3. No in-memory state dependencies - Everything important is persisted
4. Idempotent operations - Safe to retry/repeat anything

**Applied to Our Problem**:
```python
# NOT crash-only design:
if eval_id in running_containers:  # Assumes state is consistent
    process_event()

# Crash-only design:
# Assume nothing, verify everything, always recover
try:
    process_event_regardless()
except:
    recover_from_missing_data()
```

### Stateless Event Handlers

**The fundamental principle violated**:
> "Event handlers should be stateless - They shouldn't depend on in-memory state that can be out of sync"

**Why the current design is wrong**:
1. Event handler depends on mutable shared state (`running_containers`)
2. Multiple code paths can modify this state
3. No synchronization between state modifications and event processing

## The Solution

### Minimal Fix (Chosen Approach)

Make the event handler truly stateless by always processing "die" events:

```python
# Fixed event handler
if action in ["die", "stop"]:
    eval_id = attributes.get("eval_id")
    if eval_id:
        logger.debug(f"Container {eval_id} {action} event received")
        
        # Try to get container from our tracking
        container = running_containers.get(eval_id)
        
        # If not in our dict, try Docker API
        if not container:
            try:
                # Use container ID from event
                container_id = event.get("id") or event.get("Actor", {}).get("ID")
                if container_id:
                    container = docker_client.containers.get(container_id)
                    logger.info(f"Retrieved container {eval_id} from Docker API")
            except Exception as e:
                logger.warning(f"Could not retrieve container {eval_id}: {e}")
                # Still process the event with None container
                container = None
        
        # ALWAYS queue the event, even with None container
        asyncio.run_coroutine_threadsafe(
            event_queue.put((eval_id, container)), loop
        )
```

### Handle Missing Containers Gracefully

Update the completion handler to work without a container object:

```python
async def _handle_container_completion(eval_id: str, container):
    """Handle container completion - extract logs and publish event"""
    try:
        logger.debug(f"Processing completion for container {eval_id}")
        
        # Initialize defaults
        output = ""
        error = ""
        exit_code = -1
        
        if container:
            try:
                # Normal path - we have the container
                container.reload()
                exit_code = container.attrs.get("State", {}).get("ExitCode", -1)
                output = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                error = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except docker.errors.NotFound:
                logger.warning(f"Container {eval_id} was removed before we could get logs")
                error = "Container was removed before logs could be retrieved"
            except Exception as e:
                logger.error(f"Error retrieving logs for {eval_id}: {e}")
                error = f"Error retrieving logs: {str(e)}"
        else:
            # No container object - we missed it entirely
            logger.warning(f"Processing completion for {eval_id} without container object")
            error = "Container exited before logs could be captured"
        
        # Always publish completion regardless
        # ... rest of function continues normally ...
```

## What This Fixes

✅ **Evaluations with uncaught exceptions** will properly show as "failed" with error messages  
✅ **No more stuck evaluations** - All container exits will be processed  
✅ **Fast-failing containers** will be handled correctly  
✅ **Better error messages** when logs can't be retrieved

## What This Doesn't Fix (Intentionally)

These are known limitations we're accepting for now:

1. **Executor Service Crashes**: If the executor service itself crashes, in-progress evaluations might get stuck
   - *Why we're not fixing*: Moving to Kubernetes next week
   
2. **Historical Stuck Evaluations**: Past evaluations stuck in "running" won't be fixed
   - *Why we're not fixing*: One-time manual cleanup is simpler

3. **No Reconciliation Loop**: No periodic check for missed events
   - *Why we're not fixing*: Kubernetes provides this automatically

4. **No Startup Recovery**: On restart, orphaned containers aren't detected
   - *Why we're not fixing*: Current deployment pattern doesn't restart often

## Lessons Learned

### 1. Testing Blind Spots
The bug only appeared with fast-failing containers. Testing likely focused on:
- Normal scripts that run for seconds
- Infinite loops killed by timeout  
- Network operations that take time

But missed the most common failure: immediate crashes from exceptions.

### 2. Distributed Systems Principles

**"Happy path" testing isn't enough** - The bug only appears when things go wrong quickly, exactly when error handling is most critical.

**Event handlers must be defensive** - Never assume your internal state matches reality.

**Docker events are reliable** - The problem was our handling, not Docker's delivery.

### 3. Production Patterns

Production systems often use "belt and suspenders":
1. Event-based monitoring (primary)
2. Periodic reconciliation (backup)
3. Timeout-based cleanup (safety net)

We're implementing only #1 for now, knowing Kubernetes will provide #2 and #3.

## Alternative Approaches Considered

### 1. Container.wait() Instead of Events
```python
# Block until container exits
result = await asyncio.to_thread(container.wait)
exit_code = result['StatusCode']
```
*Rejected because*: Major refactor for a temporary fix

### 2. Reconciliation Loop
```python
# Periodically check for stuck containers
async def check_stuck_containers():
    while True:
        await asyncio.sleep(10)
        # Check all containers vs our state
```
*Rejected because*: Kubernetes does this better

### 3. Wrapper Script for Guaranteed Capture
```python
# Wrap execution to always capture output
wrapper_script = f'''
try:
    exec("""{code}""")
except Exception:
    traceback.print_exc()
'''
```
*Rejected because*: Changes execution semantics

## Testing the Fix

### Before Fix
```bash
# Test with fast-failing code
curl -X POST http://localhost:8000/api/eval \
  -d '{"code": "1/0", "language": "python", ...}'

# Result: {"status": "failed", "output": "", "error": ""}
# Or worse: {"status": "running"} forever
```

### After Fix
```bash
# Same test
curl -X POST http://localhost:8000/api/eval \
  -d '{"code": "1/0", "language": "python", ...}'

# Result: {"status": "failed", "output": "", "error": "Container exited before logs could be captured"}
# Or: {"status": "failed", "output": "", "error": "Traceback (most recent call last):\n  ..."}
```

## Kubernetes Migration Note

This entire problem disappears in Kubernetes because:

1. **Jobs API** provides reliable lifecycle management
2. **Watch API** doesn't miss events (reconciliation built-in)
3. **Pod logs** persist after container exit
4. **TTL controller** provides automatic cleanup

The executor becomes a simple Job creator:
```python
# Create Job
job = create_evaluation_job(code)

# Watch for completion (reliable!)
for event in watch.stream(v1.list_namespaced_job):
    if event['object'].status.succeeded:
        logs = v1.read_namespaced_pod_log(pod_name)
```

No more race conditions!

## Additional Deep-Dive Details

### The Suspicious Log Pattern

The logs showed a telling pattern:
```
executor-1  | 2025-07-06 00:55:15,677 - app - INFO - Starting log streaming for eval_20250706_005515_529f833e
executor-1  | 2025-07-06 00:55:16,182 - app - INFO - Log streaming ended for eval_20250706_005515_529f833e
executor-1  | 2025-07-06 00:55:45,691 - app - INFO - Heartbeat monitoring ended for eval_20250706_005515_529f833e
```

Note: Log streaming ended in less than 1 second, but no completion event was published!

### The Working vs Broken Cases

**Working case** (caught exception):
```python
try:
    result = 1/0
except Exception as e:
    print(f"Caught: {e}", file=sys.stderr)
# Exit code: 0, Status: completed
```

**Broken case** (uncaught exception):
```python
print("Before error")
1/0  # Uncaught exception
# Exit code: 1, Status: failed (but no logs) OR stuck in "running"
```

### Why Fast Failures Matter

Your observation: "We should see stdout, too, so the entire log process seems to get disrupted"

This was key - it wasn't just stderr that was missing, but ALL output. This pointed to the container being removed before logs could be retrieved, not just a stdout/stderr issue.

### The Event Handler State Dependency

The critical code section with inline analysis:
```python
container = running_containers.get(eval_id)
if container:  # <- THIS LINE IS THE ENTIRE PROBLEM
    # Process event
```

Why this is fundamentally wrong:
- "Die" events are the MOST important events
- These are exactly the events you can't afford to drop
- The guard condition drops events when you need them most

### Your Observation About Docker

You correctly noted: "There's something odd about the explanation... Docker's event system is generally reliable"

This healthy skepticism led to discovering it was our code, not Docker, that was the problem.

### The Multiple State Mutation Problem

The `running_containers` dict is modified in at least 5 places:
1. When logs are retrieved (line 438)
2. When container is killed (line 474)  
3. When status is checked (line 540)
4. After completion event published (line 740)
5. In the health check endpoint (line 590)

Any of these could race with the event handler!

### The Docker Events Thread Architecture

The system uses a complex thread + async queue pattern:
```python
# Sync thread receives Docker events
def _process_events_sync(event_queue, loop):
    for event in docker_client.events():
        # Checks if container in dict
        asyncio.run_coroutine_threadsafe(
            event_queue.put((eval_id, container)), loop
        )

# Async task processes them
async def process_docker_events():
    eval_id, container = await event_queue.get()
    await _handle_container_completion(eval_id, container)
```

This added complexity made the race condition harder to spot.

### Container Labeling for Event Filtering

Important detail about how containers are tracked:
```python
container = docker_client.containers.run(
    labels={
        "eval_id": eval_id,
        "executor": executor_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "timeout": str(timeout),
    }
)
```

The event filter uses: `{"type": "container", "label": f"executor={executor_id}"}`

### Your Key Insight

"The description feels like it's blaming Docker for what's probably an application-level race condition or subscription timing issue."

This was 100% correct and led directly to finding the bug.

## Summary

A classic distributed systems race condition caused by:
1. Event handler depending on mutable shared state
2. Fast-failing containers exposing the race
3. Silent failure when state doesn't match expectations

Fixed by making the event handler stateless and defensive - a pattern that should have been used from the start.

The irony: The containers most likely to fail (syntax errors, exceptions) were the ones most likely to have their failures go unreported.

## Final Philosophical Note

This bug exemplifies why distributed systems are hard:
- The "happy path" worked perfectly
- The error path failed silently
- The failure mode was data-dependent (fast vs slow failures)
- Multiple subsystems had to align perfectly to trigger it

As you noted: "This is a textbook example of why 'happy path' testing isn't enough."