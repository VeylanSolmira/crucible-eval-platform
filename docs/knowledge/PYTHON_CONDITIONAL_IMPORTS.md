# Python Conditional Imports Guide

## Overview
Conditional imports (imports inside functions, methods, or conditional blocks) are a common Python pattern used to solve specific problems. While top-level imports are preferred for clarity, conditional imports are reasonable and accepted in certain scenarios.

## When to Use Conditional Imports

### 1. Breaking Circular Dependencies
The most common and accepted use case:

```python
# In module A
class PlatformManager:
    def create_queue(self):
        # Import here to avoid circular import
        from .queue import TaskQueue
        return TaskQueue()
```

### 2. Optional Dependencies
For features that require external packages:

```python
def export_to_excel(data):
    try:
        import pandas as pd
        return pd.DataFrame(data).to_excel()
    except ImportError:
        raise ImportError("Excel export requires pandas: pip install pandas")
```

### 3. Performance Optimization (Lazy Loading)
For heavy libraries used in specific functions:

```python
class ImageProcessor:
    def process_image(self, path):
        # Only load when actually processing images
        import cv2
        import numpy as np
        return cv2.imread(path)
```

### 4. Platform-Specific Code
For OS-dependent functionality:

```python
def get_system_info():
    import platform
    if platform.system() == 'Windows':
        import winreg
        # Windows-specific code
    else:
        import pwd
        # Unix-specific code
```

### 5. Plugin/Extension Systems
For dynamically loaded modules:

```python
def load_plugin(plugin_name):
    import importlib
    try:
        return importlib.import_module(f'plugins.{plugin_name}')
    except ImportError:
        return None
```

## Best Practices

### ✅ DO:
- **Document why** the import is conditional with a comment
- **Keep imports at function/method level** - not deeply nested in loops
- **Use for truly optional features** or circular dependency resolution
- **Consider restructuring** if you have many conditional imports
- **Use TYPE_CHECKING** for type hints that would cause cycles:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from .models import User  # Only imported by type checkers
  ```

### ❌ DON'T:
- **Don't use in tight loops** - imports have overhead
- **Don't hide real dependencies** - make requirements clear
- **Don't nest deeply** - keep at function level max
- **Don't use for standard library** unless necessary
- **Don't use just to "organize"** - that's what modules are for

## Performance Considerations

```python
# BAD: Import in loop
for item in large_list:
    import json  # This runs every iteration!
    data = json.loads(item)

# GOOD: Import once
import json
for item in large_list:
    data = json.loads(item)

# ACCEPTABLE: Import in rarely-called function
def rarely_used_feature():
    import specialized_library
    return specialized_library.process()
```

## Real-World Examples

### Django
Django uses conditional imports extensively:
```python
# From django/conf/__init__.py
class LazySettings:
    def _setup(self):
        # Import settings module when first accessed
        settings_module = os.environ.get(ENVIRONMENT_VARIABLE)
        self._wrapped = Settings(settings_module)
```

### Requests Library
Handles optional dependencies:
```python
try:
    import chardet
except ImportError:
    chardet = None
```

### Our Platform Example
Breaking circular dependency between core.py and queue.py:
```python
class QueuedEvaluationPlatform:
    def __init__(self, queue=None):
        if queue is None:
            # Import here to avoid circular import
            from ..queue.queue import TaskQueue
            queue = TaskQueue()
        self.queue = queue
```

## Decision Framework

Ask yourself:
1. **Is this solving a real problem?** (circular import, optional dep, performance)
2. **Is the import at function/method level?** (not deeply nested)
3. **Is it well documented?** (comment explaining why)
4. **Could restructuring avoid it?** (sometimes better to refactor)

If yes to 1-3 and no to 4, then conditional import is reasonable.

## Common Patterns

### Factory Functions
```python
def create_storage(storage_type):
    if storage_type == 's3':
        from .s3_storage import S3Storage
        return S3Storage()
    elif storage_type == 'local':
        from .local_storage import LocalStorage
        return LocalStorage()
```

### Backwards Compatibility
```python
try:
    # Python 3.9+
    from collections.abc import Callable
except ImportError:
    # Python 3.8
    from typing import Callable
```

### Test Utilities
```python
def mock_external_service():
    # Only import mocking library in tests
    from unittest.mock import Mock
    return Mock()
```

## Conclusion

Conditional imports are a legitimate Python pattern when used appropriately. They're particularly valuable for:
- Resolving circular dependencies
- Handling optional features
- Improving startup performance
- Supporting platform-specific code

The key is to use them judiciously, document clearly, and always consider if restructuring might be cleaner.