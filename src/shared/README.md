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
