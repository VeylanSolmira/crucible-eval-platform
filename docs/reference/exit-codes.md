# Container Exit Codes Reference

## Overview

When an evaluation completes, the container exits with a specific code that indicates the result. All non-zero exit codes result in a "failed" status, but the exit code provides specific information about what happened.

## Common Exit Codes

### Success
- **0** - Success
  - Process completed normally
  - All code executed without errors

### General Errors
- **1** - General Error
  - Unhandled exception
  - Syntax error
  - Runtime error
  - Division by zero
  - Import error

- **2** - Misuse of Shell Built-in
  - Incorrect command usage
  - Invalid syntax in shell command

### Resource Limits
- **137** - SIGKILL (Out of Memory)
  - Container exceeded 512MB memory limit
  - Process was killed by the OOM killer
  - Common with large data structures or memory leaks

### Timeouts
- **124** - Timeout (coreutils)
  - Process exceeded the 30-second time limit
  - Standard timeout exit code

- **143** - SIGTERM
  - Process was terminated gracefully
  - Often indicates timeout via Docker stop

### Signal-Based Exit Codes
Exit codes 128+n indicate termination by signal n:

- **130** - SIGINT (128+2)
  - Process interrupted (Ctrl+C equivalent)

- **134** - SIGABRT (128+6)
  - Process aborted
  - Often from assertion failures

- **139** - SIGSEGV (128+11)
  - Segmentation fault
  - Invalid memory access

## Platform Behavior

### Resource Limits Enforced
- **Memory**: 512MB hard limit
- **CPU**: 0.5 cores (throttled, won't cause exit)
- **Time**: 30 seconds maximum execution
- **Network**: Disabled (no internet access)
- **Filesystem**: Read-only except /tmp

### How Exit Codes Are Used
1. Container completes execution
2. Exit code is captured by executor service
3. Status is set:
   - Exit code 0 → Status: "completed"
   - Any other code → Status: "failed"
4. Exit code is stored with the evaluation
5. UI displays user-friendly interpretation

## Examples

### Python Syntax Error
```python
print("Hello"  # Missing closing parenthesis
```
- Exit Code: 1
- UI Shows: "General Error"

### Memory Exhaustion
```python
huge_list = [0] * (10**9)  # Try to allocate ~4GB
```
- Exit Code: 137
- UI Shows: "Memory Limit Exceeded"

### Timeout
```python
import time
time.sleep(60)  # Sleep for 60 seconds
```
- Exit Code: 143 (or 124)
- UI Shows: "Terminated" or "Timeout"

### Successful Execution
```python
print("Hello, World!")
```
- Exit Code: 0
- UI Shows: "✓" (Success)

## Debugging Tips

1. **Exit Code 1**: Check the error output for Python traceback
2. **Exit Code 137**: Reduce memory usage or process data in chunks
3. **Exit Code 143/124**: Optimize code to complete within 30 seconds
4. **Exit Code 139**: Check for pointer/memory access issues (rare in Python)

## See Also
- [Platform Limits](/docs/reference/platform-limits.md)
- [Error Handling Best Practices](/docs/guides/error-handling.md)
- [Resource Optimization Guide](/docs/guides/resource-optimization.md)