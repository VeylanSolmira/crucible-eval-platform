# Log Termination Race Condition Fix

## Problem
The coordinator.py `monitor_job` method terminates kubectl logs process as soon as Kubernetes reports the job as complete (no active pods). This causes missing output, especially the pytest summary line which is critical for determining test success.

## Root Cause
Line 375 in coordinator.py:
```python
if log_process and log_process.poll() is None:
    log_process.terminate()  # This kills log streaming immediately!
```

## Solution Options

### Option 1: Don't Terminate Log Process (Recommended)
Let `kubectl logs -f` terminate naturally when the pod is deleted. The process will exit cleanly when there's no more output.

### Option 2: Add Delay Before Termination
Give the log process time to catch up before terminating:
```python
# Wait for logs to catch up (2-3 seconds)
time.sleep(3)
if log_process and log_process.poll() is None:
    log_process.terminate()
```

### Option 3: Check for Expected Output
Only terminate after seeing the pytest summary line:
```python
# Check if we've seen the summary line
has_summary = any("====" in line and "passed" in line for line in captured_logs[-10:])
if has_summary and log_process and log_process.poll() is None:
    log_process.terminate()
```

## Recommended Implementation

Remove the premature termination and let kubectl logs finish naturally:

```python
# Line 371-380 in coordinator.py
if status.get("active", 0) == 0 and (status.get("succeeded", 0) > 0 or status.get("failed", 0) > 0):
    # Job is complete - no pods are running
    # DON'T terminate logs immediately - let it finish naturally
    
    # Wait for log streaming to complete (up to 30 seconds)
    if not log_streaming_complete.wait(timeout=30):
        print(f"  ⚠️  Log streaming timeout for {job_name}")
        # Only terminate after timeout
        if log_process and log_process.poll() is None:
            log_process.terminate()
```

This gives kubectl logs time to:
1. Flush any buffered output
2. Receive the final pytest summary line
3. Exit cleanly when the pod is removed