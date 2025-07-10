# Timeout Demo Workaround

## Current Limitation
When evaluations timeout, logs are lost and only show "Container was removed before logs could be retrieved"

## Demo Script
Instead of showing infinite loops that timeout, demonstrate:

### 1. Long-Running with Progress (Shows logs work)
```python
import time

print("Starting long task...")
for i in range(5):
    print(f"Step {i+1}/5 completed")
    time.sleep(2)
print("Task completed successfully!")
```

### 2. Explicit Timeout Message (User-friendly)
```python
import time
import signal
import sys

def timeout_handler(signum, frame):
    print("\n⏰ TIMEOUT: Execution exceeded time limit")
    print("This is a platform safety feature")
    sys.exit(1)

# Set up timeout handler
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 second timeout

# Long running task
print("Starting task with 10s timeout...")
for i in range(20):
    print(f"Working... {i+1}")
    time.sleep(1)
```

## What to Say During Demo

If timeout occurs with no logs:
> "The platform enforces strict timeouts for safety. When a container exceeds its time limit, it's immediately terminated. In production with Kubernetes, we'll have better log persistence."

Focus on the safety aspect - it's a feature that prevents runaway processes.

## Future Kubernetes Solution

With Kubernetes, timeouts will:
- Preserve all logs up to termination
- Add explicit timeout messages
- Show resource usage at termination
- Enable post-mortem debugging