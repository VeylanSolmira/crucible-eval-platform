# Migration Guide: Semantic to Obfuscated Configuration

## Overview

This guide shows how to migrate existing code to support environment variable obfuscation while maintaining backwards compatibility.

## Migration Steps

### Step 1: Replace Direct Environment Access

**Before:**
```python
# app.py
import os

bind_host = os.environ.get('BIND_HOST', 'localhost')
log_level = os.environ.get('LOG_LEVEL', 'INFO')
```

**After:**
```python
# app.py
from src.config import config

bind_host = config.bind_host  # Automatically handles obfuscation
log_level = config.log_level
```

### Step 2: Update Service Components

**Before:**
```python
# src/web_frontend/web_frontend.py
import os

@dataclass
class FrontendConfig:
    host: str = os.environ.get('BIND_HOST', 'localhost')
    port: int = 8080
    platform_host: str = os.environ.get('PLATFORM_HOST', 'localhost')
```

**After:**
```python
# src/web_frontend/web_frontend.py
from ..config import config

@dataclass
class FrontendConfig:
    host: str = config.bind_host
    port: int = config.port
    platform_host: str = config.platform_host
```

### Step 3: Update Docker Configurations

**Before:**
```python
# src/execution_engine/execution.py
class DockerEngine:
    def __init__(self):
        self.memory_limit = '100m'
        self.cpu_limit = '0.5'
```

**After:**
```python
# src/execution_engine/execution.py
from ..config import config

class DockerEngine:
    def __init__(self):
        self.memory_limit = config.memory_limit
        self.cpu_limit = config.cpu_limit
```

## Backwards Compatibility

The config module maintains full backwards compatibility:

```python
# These all work simultaneously:

# 1. New config object (recommended)
from src.config import config
host = config.bind_host

# 2. Legacy function
from src.config import get_env
host = get_env('BIND_HOST', 'localhost')

# 3. Direct access still works in development
import os
host = os.environ.get('BIND_HOST', 'localhost')
```

## Testing Both Modes

### Development Mode Test
```bash
# Run with semantic names
BIND_HOST=0.0.0.0 LOG_LEVEL=DEBUG python app.py
```

### Production Mode Test
```bash
# Create test mapping
cat > test_mapping.json << EOF
{
  "mapping": {
    "BIND_HOST": "X1A2B3C4D5E6F7G8",
    "LOG_LEVEL": "Y9H8G7F6E5D4C3B2"
  }
}
EOF

# Run with obfuscated names
ENV_MAPPING_FILE=test_mapping.json \
X1A2B3C4D5E6F7G8=0.0.0.0 \
Y9H8G7F6E5D4C3B2=DEBUG \
python app.py
```

## Gradual Migration Strategy

### Phase 1: Add Config Module (Current)
- Add the config module
- No breaking changes
- Both old and new methods work

### Phase 2: Update Critical Components
- Security-sensitive components first
- Execution engines
- API authentication

### Phase 3: Update All Components
- Frontend configuration
- Service registry
- Monitoring

### Phase 4: Remove Direct Access
- After all components migrated
- Update documentation
- Add linting rules

## Benefits After Migration

1. **Zero Code Changes for Obfuscation**
   - Same code works in dev and prod
   - Obfuscation happens at build time

2. **Type Safety**
   ```python
   # Config properties have type hints
   config.port  # -> int
   config.enable_network  # -> bool
   config.bind_host  # -> str
   ```

3. **Centralized Validation**
   ```python
   # Can add validation in one place
   @property
   def memory_limit(self) -> str:
       value = _config.get('MEMORY_LIMIT', '100m')
       # Validate format
       if not re.match(r'^\d+[mMgG]$', value):
           raise ValueError(f"Invalid memory limit: {value}")
       return value
   ```

4. **Better IDE Support**
   - Autocomplete for all config options
   - Documentation on hover
   - Type checking

## Example: Full Component Migration

**Original Component:**
```python
# src/api/api_service.py
import os

class APIService:
    def __init__(self):
        self.host = os.environ.get('API_HOST', 'localhost')
        self.port = int(os.environ.get('API_PORT', '8000'))
        self.debug = os.environ.get('DEBUG', 'false').lower() == 'true'
        self.timeout = int(os.environ.get('API_TIMEOUT', '30'))
    
    def start(self):
        if self.debug:
            print(f"Starting API on {self.host}:{self.port}")
```

**Migrated Component:**
```python
# src/api/api_service.py
from ..config import config

class APIService:
    def __init__(self):
        self.host = config.service_host
        self.port = config.port
        self.debug = config.log_level == 'DEBUG'
        self.timeout = config.max_execution_time
    
    def start(self):
        if self.debug:
            print(f"Starting API on {self.host}:{self.port}")
```

## Verification

After migration, verify both modes work:

```python
# test_config.py
from src.config import config

def test_config():
    print(f"Config mode: {config}")
    print(f"Bind host: {config.bind_host}")
    print(f"Is production: {config.is_production()}")
    
    # Should work in both modes
    assert config.bind_host in ['localhost', '0.0.0.0', '127.0.0.1']
    assert config.port > 0
    assert config.max_execution_time > 0
    
    print("✅ Config tests passed")

if __name__ == '__main__':
    test_config()
```

This migration approach ensures a smooth transition to obfuscated environment variables while maintaining code quality and developer experience.