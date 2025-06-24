# Docker PrivateTmp Systemd Isolation Fix

## Problem Description

When running the Crucible platform as a systemd service with `PrivateTmp=true`, Docker containers couldn't find mounted Python files. This resulted in errors like:
```
python: can't open file '/code.py': [Errno 2] No such file or directory
```

## Root Cause

Systemd's `PrivateTmp=true` creates an isolated `/tmp` namespace for the service. When our execution engine created temporary Python files in `/tmp`, they were only visible within the systemd service's namespace. Docker, running in a different namespace, couldn't access these files.

## Solution

Move temporary files from `/tmp` to `~/crucible/storage/tmp`, which is accessible to both the systemd service and Docker containers.

### Code Changes

1. **Add configurable temp directory to execution engines**:
```python
def __init__(self, image: str = "python:3.11-slim", temp_base_dir: str = None):
    # Default to ~/crucible/storage if not specified
    self.temp_base_dir = temp_base_dir or os.path.expanduser("~/crucible/storage")
```

2. **Create temp files in the configured directory**:
```python
def execute(self, code: str, eval_id: str) -> Dict[str, Any]:
    # Create temp files in a directory accessible to both systemd service and Docker
    temp_dir = os.path.join(self.temp_base_dir, "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=temp_dir) as f:
        f.write(code)
        temp_file = f.name
```

3. **Refactor GVisorEngine to inherit from DockerEngine**:
   - Eliminates code duplication
   - Ensures both engines use the same temp directory logic
   - Makes maintenance easier

## Benefits

1. **Works with systemd isolation** - No need to disable security features
2. **Cleaner architecture** - GVisorEngine properly extends DockerEngine
3. **Configurable** - Can specify different temp directories if needed
4. **Automatic cleanup** - Old temp files (>1 hour) are cleaned up

## Alternative Solutions Considered

1. **Disable PrivateTmp** - Would reduce security
2. **Use stdin instead of files** - Would complicate the implementation
3. **Mount /tmp into Docker** - Would break isolation

## Testing

To verify the fix:
```bash
# Check if service uses PrivateTmp
systemctl show crucible-compose | grep PrivateTmp

# Run an evaluation
curl -X POST http://localhost:8080/api/eval \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello from Docker\")"}'

# Check temp files are created in the right location
ls -la ~/crucible/storage/tmp/
```

## Related Issues

- This issue only affects deployments running as systemd services
- Local development (running directly) was not affected
- The fix is backwards compatible with non-systemd deployments