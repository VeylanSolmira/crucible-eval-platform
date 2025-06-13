# Monkey Patching Guide

**Monkey-patching** is a Python technique where you dynamically modify a class or module at runtime, changing or extending its behavior without modifying the original source code.

## Basic Example:

```python
# Original module behavior
import datetime

# Monkey-patch the datetime module
def custom_now(cls):
    return "It's party time!"

datetime.datetime.now = classmethod(custom_now)

# Now datetime.now() returns our custom message
print(datetime.datetime.now())  # "It's party time!"
```

## Common Use Cases:

**1. Testing/Mocking:**
```python
# Mock external API calls during tests
import requests

def mock_get(url):
    return {"status": "success", "data": "test data"}

# Monkey-patch requests.get for testing
requests.get = mock_get
```

**2. Fixing third-party bugs:**
```python
# Fix a bug in an external library without forking
import broken_library

def fixed_function(self, arg):
    # Your fixed implementation
    return arg * 2

# Replace the broken method
broken_library.SomeClass.broken_method = fixed_function
```

**3. Adding functionality:**
```python
# Add a method to built-in types
def is_palindrome(self):
    return self == self[::-1]

str.is_palindrome = is_palindrome

print("racecar".is_palindrome())  # True
```

## For Security/Sandboxing (relevant to your adversarial AI testing):

```python
# Restrict file operations
import builtins

original_open = builtins.open

def restricted_open(file, mode='r', *args, **kwargs):
    if '/etc/' in file or mode in ['w', 'a']:
        raise PermissionError(f"Access denied: {file}")
    return original_open(file, mode, *args, **kwargs)

builtins.open = restricted_open
```

## Dangers:
- Makes code harder to debug
- Can break when libraries update
- Action at a distance - changes affect all code
- Not thread-safe
- Can be bypassed by importing modules differently

## Better Alternatives:
- Dependency injection
- Proper mocking libraries (unittest.mock)
- Subclassing
- Wrapper functions

For your adversarial AI testing platform, monkey-patching could be used to intercept and monitor model behavior, but be careful as malicious code might detect or bypass patches.

## When Monkey Patching Might Be Acceptable:
1. **Testing/Mocking** - Temporarily replacing functions for unit tests
   ```python
   # OK: Mocking external API for tests
   def test_api_call(monkeypatch):
       monkeypatch.setattr(requests, 'get', mock_api_response)
   ```

2. **Debugging** - Adding temporary logging to diagnose issues
   ```python
   # OK: Temporary debugging (remove after fixing)
   original_func = module.function
   def debug_wrapper(*args, **kwargs):
       print(f"Called with: {args}")
       return original_func(*args, **kwargs)
   module.function = debug_wrapper
   ```

3. **Third-party Bug Fixes** - When you can't wait for upstream fix
   ```python
   # OK: Fixing known bug in external library
   # Document with issue link and remove when fixed upstream
   ```

## When NOT to Monkey Patch:
1. **Security-Critical Code** - NEVER monkey patch security functions
2. **Runtime Behavior Changes** - Don't swap implementations at runtime
3. **Module Import Side Effects** - Don't rely on import order for patches
4. **Production Code** - Prefer proper inheritance/composition
5. **Cross-Module Dependencies** - Creates hidden coupling

## The Security Runner Bug:
The bug in our security test runner happened because:
```python
# BAD: Tried to monkey patch after import
import security_scenarios.attack_scenarios
security_scenarios.attack_scenarios.ATTACK_SCENARIOS = SAFE_DEMOS  # Too late!
```

The module had already imported ATTACK_SCENARIOS, so our patch didn't affect it.

## Better Patterns:
1. **Dependency Injection** - Pass dependencies as parameters
2. **Strategy Pattern** - Pass behavior as objects
3. **Configuration Objects** - Use explicit config instead of module globals
4. **Factory Functions** - Create instances with proper parameters

Remember: Explicit is better than implicit, especially for security-critical code.