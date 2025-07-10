# Exit Code Messaging Improvement

## Current Issue
When containers are killed due to resource limits, we get the exit code but don't translate it to meaningful messages. Users see empty output or generic errors.

## Common Exit Codes
- **137**: SIGKILL - Usually means OOM (Out of Memory) kill
- **143**: SIGTERM - Graceful termination requested  
- **1**: General errors (could be Python exception)
- **0**: Successful completion

## Quick Fix (Can implement now)

### In executor-service/app.py:
```python
def get_exit_code_message(exit_code: int) -> str:
    """Translate exit codes to user-friendly messages"""
    if exit_code == 137:
        return "Process killed due to memory limit exceeded (512MB)"
    elif exit_code == 143:
        return "Process terminated (timeout or manual kill)"
    elif exit_code == 1:
        return "Process exited with error"
    elif exit_code == 0:
        return "Process completed successfully"
    else:
        return f"Process exited with code {exit_code}"
```

### In the event handler:
When publishing completion events, include the exit code interpretation in the error message.

### In frontend ExecutionMonitor:
Display the exit code message prominently when execution fails.

## Benefits
- Immediate improvement to user experience
- Helps users understand why their code failed
- No need to wait for Kubernetes
- Simple to implement (~30 minutes)

## Future Enhancement
In Kubernetes, we'll get even better information:
- Actual memory usage at time of kill
- More detailed termination reasons
- Pod events showing exact cause

But we shouldn't wait - this basic improvement helps now!