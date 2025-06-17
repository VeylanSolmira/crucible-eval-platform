# Environment Variable Obfuscation Example

## Development Code (What You Write)

```python
# app.py - Development version with semantic names
import os

class Config:
    """Clean, readable configuration"""
    bind_host = os.environ.get('BIND_HOST', 'localhost')
    service_host = os.environ.get('SERVICE_HOST', 'localhost') 
    platform_host = os.environ.get('PLATFORM_HOST', 'localhost')
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Security settings
    max_execution_time = int(os.environ.get('MAX_EXECUTION_TIME', '30'))
    memory_limit = os.environ.get('MEMORY_LIMIT', '100m')
    enable_network = os.environ.get('ENABLE_NETWORK', 'false').lower() == 'true'

# Usage remains clean and semantic
print(f"Starting server on {Config.bind_host}:8080")
print(f"Service host: {Config.service_host}")
print(f"Max execution time: {Config.max_execution_time}s")
```

## Production Code (After Build Transformation)

```python
# app.py - Production version with obfuscated names
import os

class Config:
    """Obfuscated configuration"""
    bind_host = os.environ.get('A7X9K3M2P5Q8R1T4', 'localhost')
    service_host = os.environ.get('B2N5V8C1X4Z7Q9W3', 'localhost') 
    platform_host = os.environ.get('C4T7Y1U8I5O2P9S6', 'localhost')
    log_level = os.environ.get('D9W3E6R2T5Y8U1I4', 'INFO')
    
    # Security settings  
    max_execution_time = int(os.environ.get('E5F8G2H6J9K3L7M1', '30'))
    memory_limit = os.environ.get('F1M4N7O2P5Q8R3S6', '100m')
    enable_network = os.environ.get('G6S9T3U7V1W4X8Y2', 'false').lower() == 'true'

# Usage code unchanged - still readable!
print(f"Starting server on {Config.bind_host}:8080")
print(f"Service host: {Config.service_host}")
print(f"Max execution time: {Config.max_execution_time}s")
```

## Development docker-compose.yml

```yaml
version: '3.8'
services:
  crucible:
    image: crucible:latest
    environment:
      - BIND_HOST=0.0.0.0
      - SERVICE_HOST=crucible
      - LOG_LEVEL=INFO
      - MAX_EXECUTION_TIME=60
      - MEMORY_LIMIT=200m
      - ENABLE_NETWORK=false
```

## Production docker-compose.yml (After Transformation)

```yaml
version: '3.8'
services:
  crucible:
    image: crucible:prod
    environment:
      - A7X9K3M2P5Q8R1T4=0.0.0.0
      - B2N5V8C1X4Z7Q9W3=crucible
      - D9W3E6R2T5Y8U1I4=INFO
      - E5F8G2H6J9K3L7M1=60
      - F1M4N7O2P5Q8R3S6=200m
      - G6S9T3U7V1W4X8Y2=false
```

## Benefits of This Approach

### 1. **Development Experience**
- Clean, semantic variable names
- Easy to understand and debug
- IDE autocomplete works
- Self-documenting code

### 2. **Production Security**
- No architecture information leaked
- Variable names reveal nothing
- Automated transformation
- Different per deployment

### 3. **Attack Scenarios Prevented**

**Without Obfuscation:**
```bash
# Attacker sees in process environment:
BIND_HOST=0.0.0.0
SERVICE_HOST=api-gateway
DATABASE_HOST=postgres.internal
REDIS_CLUSTER=redis-prod

# Attacker learns:
# - It's a web service (BIND_HOST)
# - Has microservices architecture (SERVICE_HOST)
# - Uses PostgreSQL and Redis
# - Internal network structure
```

**With Obfuscation:**
```bash
# Attacker sees:
A7X9K3M2P5Q8R1T4=0.0.0.0
B2N5V8C1X4Z7Q9W3=api-gateway
H3Z6C9V2B5N8M1Q4=postgres.internal
I8Q4W7E1R5T9Y2U6=redis-prod

# Attacker learns:
# - Nothing about architecture
# - No technology hints
# - No service relationships
# - Must reverse engineer everything
```

## Build Process Integration

```bash
# Development
make dev  # Uses semantic names

# CI/CD Pipeline
make build-prod  # Transforms to obfuscated names
make test-prod   # Tests with obfuscated build
make deploy-prod # Deploys obfuscated version
```

## Debugging Production

For debugging production issues, use the secure mapping file:

```python
# debug_tool.py (restricted access)
import json

def decode_env_var(obfuscated_name, mapping_file='env_mapping.secure.json'):
    """Decode obfuscated environment variable name"""
    with open(mapping_file) as f:
        mapping = json.load(f)['mapping']
    
    # Reverse lookup
    for semantic, obfuscated in mapping.items():
        if obfuscated == obfuscated_name:
            return semantic
    return "Unknown"

# Usage
print(decode_env_var('A7X9K3M2P5Q8R1T4'))  # Output: BIND_HOST
```

## Security Considerations

1. **Mapping File Security**
   - Store in secure location (Vault, AWS Secrets Manager)
   - Never commit to git
   - Restrict access to ops team only

2. **Build Environment**
   - Run obfuscation in secure CI/CD
   - Don't expose mapping in build logs
   - Use different mappings per environment

3. **Rotation Strategy**
   - Regenerate mappings periodically
   - Coordinate with deployment cycles
   - Keep historical mappings for debugging

This approach provides the best of both worlds: clean development experience with hardened production security.