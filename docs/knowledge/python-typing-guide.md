# Python Type Hints and Optional Types

## Overview

Type hints (introduced in Python 3.5 and enhanced through 3.10+) have become **state-of-the-art practice** in modern Python development. Major projects like FastAPI, Pydantic, and most Google/Meta Python codebases now use static typing extensively.

## The `Optional` Type

`Optional[T]` means "either type T or None". It's one of the most commonly used type hints.

### Basic Usage
```python
from typing import Optional

# These are equivalent:
def get_user(user_id: int) -> Optional[str]:
    """Returns username or None if not found"""
    if user_id in database:
        return database[user_id]
    return None

# Python 3.10+ union syntax (preferred in new code)
def get_user(user_id: int) -> str | None:
    """Same as above but with modern syntax"""
    if user_id in database:
        return database[user_id]
    return None
```

### Common Patterns
```python
from typing import Optional, Dict, List

class EvaluationResult:
    def __init__(
        self,
        eval_id: str,
        output: str,
        error: Optional[str] = None,  # May or may not have error
        metadata: Optional[Dict[str, Any]] = None  # Optional metadata
    ):
        self.eval_id = eval_id
        self.output = output
        self.error = error
        self.metadata = metadata or {}  # Common pattern for optional dicts

    def get_error_details(self) -> Optional[Dict[str, str]]:
        """Returns error details if error exists, None otherwise"""
        if self.error:
            return {
                "message": self.error,
                "eval_id": self.eval_id
            }
        return None
```

### Optional in Function Arguments
```python
# Default None makes argument optional
def create_engine(
    engine_type: str,
    timeout: Optional[int] = None,  # Can pass int or None
    config: Optional[Dict[str, Any]] = None
) -> ExecutionEngine:
    if timeout is None:
        timeout = 300  # Default value
    
    if config is None:
        config = {}  # Avoid mutable default
    
    # ... create engine
```

## Why Static Typing is State-of-the-Art

### 1. **Industry Adoption**
- **Google**: Requires type hints in all Python code
- **Meta/Facebook**: Developed Pyre type checker
- **Microsoft**: Created Pylance/PyRight
- **Dropbox**: Developed mypy (the first Python type checker)

### 2. **Tooling Support**
```python
# Modern IDEs provide intelligent autocomplete
platform: TestableEvaluationPlatform = create_platform()
platform.  # IDE shows all available methods with types

# Type checkers catch errors before runtime
def process_result(result: Dict[str, Any]) -> str:
    return result.upper()  # Error: Dict has no .upper() method
```

### 3. **Self-Documenting Code**
```python
# Without types - unclear what function expects/returns
def evaluate(code, options):
    # What type is code? What's in options? What's returned?
    pass

# With types - interface is clear
def evaluate(
    code: str,
    options: Optional[EvalOptions] = None
) -> EvaluationResult:
    """Much clearer what this function does!"""
    pass
```

### 4. **Catch Bugs Early**
```python
from typing import List, Optional

class Platform:
    def __init__(self):
        self.evaluations: List[str] = []
    
    def get_evaluation(self, index: int) -> Optional[str]:
        if 0 <= index < len(self.evaluations):
            return self.evaluations[index]
        return None

# Type checker catches this error:
platform = Platform()
result = platform.get_evaluation("0")  # Error: Expected int, got str
```

## Modern Python Typing Features

### Union Types (Python 3.10+)
```python
# Old style
from typing import Union
def parse_number(value: Union[int, float, str]) -> float:
    return float(value)

# New style (Python 3.10+)
def parse_number(value: int | float | str) -> float:
    return float(value)
```

### Type Aliases
```python
from typing import Dict, List, Optional

# Define complex types once
EvalResult = Dict[str, Any]
EvalHistory = List[EvalResult]
EventHandler = Callable[[str, Dict[str, Any]], None]

class Monitor:
    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.history: EvalHistory = []
    
    def add_handler(self, handler: EventHandler) -> None:
        self.handlers.append(handler)
```

### Generics
```python
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class Cache(Generic[T]):
    """Generic cache that can store any type"""
    def __init__(self):
        self._cache: Dict[str, T] = {}
    
    def get(self, key: str) -> Optional[T]:
        return self._cache.get(key)
    
    def set(self, key: str, value: T) -> None:
        self._cache[key] = value

# Type-safe usage
string_cache: Cache[str] = Cache()
string_cache.set("key", "value")  # OK
string_cache.set("key", 123)      # Error: Expected str, got int
```

### Protocols (Structural Typing)
```python
from typing import Protocol

class Executable(Protocol):
    """Anything that has an execute method"""
    def execute(self, code: str) -> Dict[str, Any]: ...

# Any class with execute method matches this protocol
class DockerEngine:
    def execute(self, code: str) -> Dict[str, Any]:
        return {"status": "completed"}

def run_evaluation(engine: Executable) -> None:
    """Accepts any object with execute method"""
    result = engine.execute("print('hello')")
```

## Best Practices

### 1. **Start with Critical Interfaces**
```python
# Type public APIs first
class APIService:
    def handle_request(self, request: APIRequest) -> APIResponse:
        """Public method - always type hint"""
        pass
    
    def _internal_helper(self, data):
        """Private method - types optional but recommended"""
        pass
```

### 2. **Use Type Checkers in CI**
```yaml
# .github/workflows/ci.yml
- name: Type Check
  run: |
    pip install mypy
    mypy src/ --strict
```

### 3. **Gradual Typing**
```python
# Start with Any, refine over time
def process_data(data: Any) -> Any:  # Start here
    pass

def process_data(data: Dict[str, Any]) -> List[str]:  # Refine later
    pass
```

### 4. **Avoid Over-Typing**
```python
# Too verbose
def add(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    return x + y

# Better - let Python handle numeric types naturally
def add(x: float, y: float) -> float:  # int is subtype of float
    return x + y
```

### 5. **Use Type Guards**
```python
from typing import TypeGuard

def is_error_result(result: EvalResult) -> TypeGuard[ErrorResult]:
    """Type guard that narrows type in if-blocks"""
    return "error" in result and result["error"] is not None

result = get_evaluation_result()
if is_error_result(result):
    # Type checker knows result has 'error' field here
    print(f"Error: {result['error']}")
```

## Common Type Hint Patterns

### Configuration Objects
```python
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class Config:
    api_key: str
    timeout: int = 30
    debug: bool = False
    extra_options: Optional[Dict[str, Any]] = None
```

### Callbacks and Handlers
```python
from typing import Callable, Awaitable

# Sync callback
EventHandler = Callable[[str, Dict[str, Any]], None]

# Async callback  
AsyncEventHandler = Callable[[str, Dict[str, Any]], Awaitable[None]]

class EventEmitter:
    def __init__(self):
        self.handlers: List[EventHandler] = []
        self.async_handlers: List[AsyncEventHandler] = []
```

### Return Types for Errors
```python
from typing import Union, Literal

# Option 1: Union with error
def evaluate(code: str) -> Union[EvalResult, ErrorResult]:
    pass

# Option 2: Result with status
@dataclass
class Result:
    status: Literal["success", "error"]
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Option 3: Raise exceptions (Pythonic)
def evaluate(code: str) -> EvalResult:
    """Raises EvaluationError on failure"""
    pass
```

## Tools and Resources

### Type Checkers
- **mypy**: Original and most mature
- **pyright/pylance**: Microsoft's fast checker (used in VS Code)
- **pyre**: Facebook's checker
- **pytype**: Google's checker with type inference

### Configuration
```ini
# pyproject.toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Per-module options
[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true
```

### Learning Resources
1. [Python Type Hints Documentation](https://docs.python.org/3/library/typing.html)
2. [MyPy Documentation](https://mypy.readthedocs.io/)
3. [Real Python - Type Checking](https://realpython.com/python-type-checking/)
4. [PEP 484](https://www.python.org/dev/peps/pep-0484/) - Original type hints PEP

## Conclusion

Static typing in Python is definitively **state-of-the-art practice** in 2024:
- Major tech companies require it
- Modern frameworks depend on it (FastAPI, Pydantic)
- Tooling support is excellent
- It catches bugs early
- It serves as living documentation
- It enables better refactoring

The Python community has embraced "gradual typing" - you can add types incrementally to existing codebases, making adoption practical for projects of any size.