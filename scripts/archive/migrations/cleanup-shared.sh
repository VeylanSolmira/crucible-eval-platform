#!/bin/bash
# Clean up and organize shared folder

echo "🧹 Cleaning up shared folder"
echo "==========================="

cd src/shared

# 1. Remove duplicates from utils folder
echo "Removing duplicate files from utils/..."
rm -f utils/base_component.py utils/openapi_validator.py utils/platform.py
echo "✓ Removed duplicates from utils/"

# 2. Check if utils is now empty
if [ -z "$(ls -A utils 2>/dev/null)" ]; then
    echo "Removing empty utils folder..."
    rmdir utils
    echo "✓ Removed empty utils/"
fi

# 3. Add README to types folder explaining its purpose
echo "Adding documentation to types folder..."
cat > types/README.md << 'EOF'
# Shared Types

This folder is reserved for shared type definitions when the platform migrates to:
- Stronger typing with TypedDict, Protocol, etc.
- Shared data models across services
- API contracts and schemas

## Future Contents

```python
# types/models.py
from typing import TypedDict, Protocol, Literal

class EvaluationRequest(TypedDict):
    id: str
    code: str
    language: Literal['python', 'javascript', 'go']
    timeout: int
    resources: ResourceLimits

class ExecutionResult(TypedDict):
    id: str
    status: Literal['completed', 'failed', 'timeout']
    output: str
    metrics: ExecutionMetrics

# types/interfaces.py
class StorageBackend(Protocol):
    def store(self, key: str, data: Dict[str, Any]) -> None: ...
    def retrieve(self, key: str) -> Optional[Dict[str, Any]]: ...
```

Currently, type definitions are inline within each module.
EOF

echo "✓ Added types/README.md"

# 4. Check what components_init.py is for
echo "Checking components_init.py purpose..."
if grep -q "backward compatibility" components_init.py 2>/dev/null; then
    echo "✓ components_init.py appears to be for backward compatibility"
else
    echo "  Note: Review components_init.py purpose"
fi

# 5. Check service_registry.py
echo "Checking service_registry.py..."
head -20 service_registry.py > /tmp/service_registry_check.txt
if grep -q "class ServiceRegistry" /tmp/service_registry_check.txt; then
    echo "✓ service_registry.py contains ServiceRegistry implementation"
else
    echo "  Note: Review service_registry.py contents"
fi

# 6. Update __init__.py to export the key components
echo "Updating __init__.py..."
cat > __init__.py << 'EOF'
"""Shared components and utilities used across all services"""

from .base import TestableComponent
from .platform import EvaluationPlatform, QueuedEvaluationPlatform
from .openapi_validator import OpenAPIValidator

# Optional imports for future microservices
try:
    from .service_registry import ServiceRegistry
except ImportError:
    ServiceRegistry = None

__all__ = [
    'TestableComponent',
    'EvaluationPlatform',
    'QueuedEvaluationPlatform',
    'OpenAPIValidator',
    'ServiceRegistry'
]
EOF

echo "✓ Updated __init__.py"

# 7. Add main README for shared module
echo "Creating shared module README..."
cat > README.md << 'EOF'
# Shared Module

Core components and utilities shared across all services in the Crucible platform.

## Contents

### Core Classes
- **`base.py`** - `TestableComponent` base class for all components
- **`platform.py`** - Platform implementations (base and queued versions)
- **`openapi_validator.py`** - OpenAPI schema validation utilities

### Future Components
- **`service_registry.py`** - Service discovery and registration (for microservices)
- **`types/`** - Shared type definitions and data models

## Design Principles

1. **Minimal Dependencies** - Shared code should have minimal external deps
2. **Backward Compatible** - Changes here affect all services
3. **Well Tested** - All shared components must include tests
4. **Clear Contracts** - Interfaces should be well-defined

## Usage

```python
from shared.base import TestableComponent

class MyService(TestableComponent):
    def self_test(self) -> Dict[str, Any]:
        # Implementation
        pass
```

## Migration Notes

When moving to microservices:
1. This becomes a separate package (`crucible-shared`)
2. Published to private PyPI or included as git submodule
3. Versioned independently
4. Each service pins specific version
EOF

echo "✓ Created README.md"

echo ""
echo "✅ Shared folder cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed duplicate files from utils/"
echo "  - Added documentation to types/ folder"
echo "  - Updated __init__.py with proper exports"
echo "  - Created README explaining the module's purpose"
echo ""
echo "The shared folder now contains only unique, essential components"
echo "that are truly shared across services."