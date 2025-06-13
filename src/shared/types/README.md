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
