# Advanced Security: Environment Variable Obfuscation

## Concept

Even generic environment variable names like `BIND_HOST` or `SERVICE_HOST` can leak information about system architecture to sophisticated attackers. Randomized variable names add an additional layer of security through obscurity.

## Implementation Approaches

### 1. Build-Time Randomization

```python
# build_config.py - Run during build process
import secrets
import json

def generate_env_mapping():
    """Generate random environment variable names"""
    mapping = {
        'BIND_HOST': f'X{secrets.token_hex(8).upper()}',
        'SERVICE_HOST': f'Y{secrets.token_hex(8).upper()}',
        'PLATFORM_HOST': f'Z{secrets.token_hex(8).upper()}',
        'LOG_LEVEL': f'L{secrets.token_hex(8).upper()}'
    }
    
    # Save mapping to secure location
    with open('.env.mapping.json', 'w') as f:
        json.dump(mapping, f)
    
    return mapping

# Generated mapping example:
# {
#   "BIND_HOST": "XA3F2E9B8C1D4E7F9",
#   "SERVICE_HOST": "Y2B4F6A8D0E2C4A6",
#   "PLATFORM_HOST": "Z9E1D3C5B7A9F1E3",
#   "LOG_LEVEL": "L4C6E8A0B2D4F6E8"
# }
```

### 2. Config Loader with Mapping

```python
# config.py
import os
import json
from pathlib import Path

class ObfuscatedConfig:
    """Load configuration with obfuscated environment variables"""
    
    def __init__(self, mapping_file='.env.mapping.json'):
        self._mapping = {}
        self._reverse_mapping = {}
        
        if Path(mapping_file).exists():
            with open(mapping_file) as f:
                self._mapping = json.load(f)
                self._reverse_mapping = {v: k for k, v in self._mapping.items()}
    
    def get(self, key: str, default=None):
        """Get config value using original key name"""
        # In production, use obfuscated name
        if self._mapping and key in self._mapping:
            obfuscated_key = self._mapping[key]
            return os.environ.get(obfuscated_key, default)
        
        # Fallback for development
        return os.environ.get(key, default)
    
    @property
    def bind_host(self):
        return self.get('BIND_HOST', 'localhost')
    
    @property
    def service_host(self):
        return self.get('SERVICE_HOST', 'localhost')

# Usage
config = ObfuscatedConfig()
host = config.bind_host  # Internally uses XA3F2E9B8C1D4E7F9
```

### 3. Docker Compose Template Generator

```python
# generate_compose.py
def generate_docker_compose(mapping):
    """Generate docker-compose with obfuscated env vars"""
    
    template = f"""version: '3.8'
services:
  crucible:
    image: crucible:latest
    environment:
      - {mapping['BIND_HOST']}=0.0.0.0
      - {mapping['SERVICE_HOST']}=crucible
      - {mapping['LOG_LEVEL']}=INFO
"""
    
    with open('docker-compose.generated.yml', 'w') as f:
        f.write(template)
```

### 4. Runtime Obfuscation (Most Secure)

```python
# secure_config.py
import os
import hashlib
import hmac

class RuntimeObfuscatedConfig:
    """Generate obfuscated names at runtime using HMAC"""
    
    def __init__(self, secret_key=None):
        # Get secret from secure location (AWS Secrets Manager, etc)
        self.secret = secret_key or os.environ.get('CONFIG_SECRET', 'default')
    
    def _obfuscate_name(self, original_name: str) -> str:
        """Generate deterministic but obfuscated name"""
        return 'E' + hmac.new(
            self.secret.encode(),
            original_name.encode(),
            hashlib.sha256
        ).hexdigest()[:16].upper()
    
    def get(self, key: str, default=None):
        """Get value using obfuscated lookup"""
        obfuscated = self._obfuscate_name(key)
        return os.environ.get(obfuscated, os.environ.get(key, default))
```

## Deployment Strategies

### Development Mode
```bash
# Use readable names for debugging
BIND_HOST=localhost python app.py
```

### Staging Mode
```bash
# Use semi-obfuscated names
CRUCIBLE_4F2A=localhost python app.py
```

### Production Mode
```bash
# Fully randomized names
XA3F2E9B8C1D4E7F9=10.0.0.5 python app.py
```

## Security Benefits

1. **Prevents Architecture Inference**
   - Attackers can't guess system design from env var names
   - No hints about services, hosts, or network topology

2. **Blocks Automated Scanning**
   - Security scanners looking for common patterns fail
   - Makes reconnaissance more difficult

3. **Reduces Attack Surface**
   - Even if attacker gains read access to environment
   - Variable names reveal nothing about their purpose

## Trade-offs

### Pros
- Additional security layer
- Makes attacks more difficult
- Prevents information leakage
- Can be automated in CI/CD

### Cons
- Increased complexity
- Harder debugging
- Requires secure mapping storage
- Team needs documentation

## Implementation Recommendations

### Phase 1: Current (Good Security)
```python
# Clear but generic names
bind_host = os.environ.get('BIND_HOST', 'localhost')
```

### Phase 2: Future (Better Security)
```python
# Prefixed obfuscation
bind_host = os.environ.get('CRUCIBLE_BIND_4F2A', 'localhost')
```

### Phase 3: Production (Best Security)
```python
# Full obfuscation with secure config loader
config = SecureConfig()
bind_host = config.bind_host  # Uses XA3F2E9B8C1D4E7F9 internally
```

## Example Integration

```python
# app.py with obfuscation support
from config import ObfuscatedConfig

config = ObfuscatedConfig()

def main():
    # Developers still use readable names
    host = config.bind_host
    port = config.port
    
    # But runtime uses obfuscated lookups
    print(f"Starting on {host}:{port}")
```

## Monitoring Considerations

With obfuscated variables, logging needs care:

```python
# Good: Log values, not variable names
logger.info(f"Server started on {host}:{port}")

# Bad: Don't log the obfuscated names
logger.info(f"Using {config._mapping}")
```

## Summary

Environment variable obfuscation is an advanced security technique appropriate for:
- High-security environments
- Systems handling sensitive data
- Infrastructure where reconnaissance must be prevented
- Defense against sophisticated attackers

For METR's evaluation platform, this would be a "Phase 2" security enhancement after core security measures are in place.