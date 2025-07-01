# Shared Contracts and Types

This directory contains shared contracts, types, and schemas used across all services in the Crucible platform. It ensures type safety and consistency between frontend and backend services.

## Directory Structure

```
shared/
├── contracts/          # YAML contract definitions
│   ├── events/        # Event schemas for Redis pub/sub
│   └── types/         # Shared type definitions
├── generated/         # Auto-generated code from contracts
│   ├── python/        # Python types for backend services
│   └── typescript/    # TypeScript types for frontend
├── constants/         # Shared constants and enums
├── docker/           # Shared Docker configurations
│   └── base.Dockerfile  # Base image for all Python services
└── scripts/          # Generation and utility scripts
```

## Key Concepts

### 1. Contract-First Development

All shared types are defined in YAML contracts first, then code is generated:

```yaml
# contracts/types/evaluation-status.yaml
EvaluationStatus:
  type: string
  enum:
    - queued
    - running
    - completed
    - failed
    - cancelled
  description: Status of an evaluation task
```

### 2. Type Generation

Generate types after modifying contracts:

```bash
# Generate all types
cd shared
./scripts/generate-types.sh

# Or manually:
python scripts/generate_python_types.py
python scripts/generate_typescript_types.py
```

### 3. Event Contracts

Events published to Redis follow defined schemas:

```yaml
# contracts/events/evaluation-events.yaml
EvaluationQueuedEvent:
  type: object
  properties:
    eval_id:
      type: string
    code:
      type: string
    timestamp:
      type: string
      format: date-time
```

## Usage

### Python Services

```python
# Import generated types
from shared.generated.python import EvaluationStatus, EvaluationQueuedEvent

# Use enum
status = EvaluationStatus.RUNNING

# Type hints
def update_status(eval_id: str, status: EvaluationStatus) -> None:
    pass
```

### TypeScript/Frontend

```typescript
// Import generated types
import { EvaluationStatus, EvaluationQueuedEvent } from '@/shared/generated/typescript';

// Use enum
const status = EvaluationStatus.Running;

// Type safety
interface Props {
  status: EvaluationStatus;
}
```

### Adding New Types

1. Create YAML contract in `contracts/types/`:
   ```yaml
   # contracts/types/my-new-type.yaml
   MyNewType:
     type: object
     properties:
       id:
         type: string
       name:
         type: string
     required: [id, name]
   ```

2. Run generation script:
   ```bash
   ./scripts/generate-types.sh
   ```

3. Import and use in services:
   ```python
   from shared.generated.python import MyNewType
   ```

## Event System

### Publishing Events

```python
# In any service
import redis
from shared.generated.python import EvaluationCompletedEvent

async def publish_completion(redis_client, eval_id: str):
    event = EvaluationCompletedEvent(
        eval_id=eval_id,
        timestamp=datetime.utcnow().isoformat()
    )
    await redis_client.publish("evaluation:completed", event.json())
```

### Subscribing to Events

```python
# In storage-worker or other subscribers
async def handle_evaluation_completed(data: dict):
    event = EvaluationCompletedEvent(**data)
    # Process event
```

## Constants

Shared constants prevent magic strings:

```python
# constants/queues.py
QUEUE_NAMES = {
    'HIGH_PRIORITY': 'high_priority',
    'DEFAULT': 'default', 
    'LOW_PRIORITY': 'low_priority'
}

# constants/events.py
EVENT_CHANNELS = {
    'EVAL_QUEUED': 'evaluation:queued',
    'EVAL_COMPLETED': 'evaluation:completed',
    'EVAL_FAILED': 'evaluation:failed'
}
```

## Docker Base Image

All Python services use the shared base image:

```dockerfile
# Service Dockerfile
ARG BASE_IMAGE=crucible-base
FROM ${BASE_IMAGE}

# Service-specific additions...
```

Build base image first:
```bash
docker-compose build base
```

## Best Practices

1. **Always modify contracts first** - Never edit generated code directly
2. **Run type generation** - After any contract changes
3. **Version carefully** - Contract changes affect all services
4. **Document schemas** - Add descriptions to YAML contracts
5. **Test compatibility** - Ensure changes don't break existing services

## Common Issues

### Types Not Found
- Ensure you've run the generation scripts
- Check import paths match generated structure
- Verify YAML contract is valid

### Generation Fails
- Check YAML syntax with a validator
- Ensure all required fields are present
- Look for circular dependencies

### Version Mismatch
- Regenerate types in all services after changes
- Ensure all services use same shared version
- Consider backwards compatibility

## Future Improvements

1. **Automatic Generation** - Run on contract changes via Git hooks
2. **Version Management** - Semantic versioning for contracts
3. **Proto/gRPC** - Consider Protocol Buffers for service communication
4. **Contract Tests** - Validate services comply with contracts
5. **Documentation Generation** - Auto-generate API docs from contracts

## Contributing

1. Discuss breaking changes before implementing
2. Update all affected services when changing contracts
3. Add tests for new event types
4. Document complex types with examples
5. Consider backwards compatibility for production systems