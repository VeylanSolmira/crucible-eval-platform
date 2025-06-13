# Testing Guide for Crucible Platform

## Overview

The Crucible platform has multiple testing approaches to ensure reliability at different levels.

## Testing Methods

### 1. Integration Testing (`python app.py --test`)

**Purpose**: Test components working together in the full application context

**What it does**:
- Initializes all components with real dependencies
- Tests component interactions
- Verifies the platform works as a whole
- Runs component self-tests in application context

**When to use**:
- Before deployment
- After major changes
- To verify system integration

**Example**:
```bash
python app.py --test --unsafe
```

### 2. Component Testing (`python test_components.py`)

**Purpose**: Test individual components in isolation

**What it does**:
- Tests each component separately
- Uses timeouts to prevent hanging
- Provides detailed per-component results
- Better error isolation and debugging

**When to use**:
- When debugging specific component failures
- During component development
- For quick component validation

**Example**:
```bash
python test_components.py
```

### 3. Unit Testing (Future)

**Purpose**: Traditional unit tests with pytest

**What it would do**:
- Test individual methods/functions
- Mock dependencies
- Fast, isolated tests
- CI/CD integration

**Status**: Not yet implemented, but components have `get_test_suite()` methods ready for this.

## Component Self-Test Pattern

Each component implements a `self_test()` method that:

1. Returns a dictionary with:
   - `passed`: boolean indicating overall success
   - `message`: summary message
   - `tests`: optional list of individual test results

2. Tests core functionality without external dependencies

3. Should complete quickly (< 10 seconds)

Example:
```python
def self_test(self) -> Dict[str, Any]:
    tests = []
    
    # Test 1: Basic functionality
    try:
        result = self.do_something()
        tests.append({
            'name': 'basic_operation',
            'passed': result is not None,
            'message': 'Basic operation works'
        })
    except Exception as e:
        tests.append({
            'name': 'basic_operation',
            'passed': False,
            'message': f'Failed: {str(e)}'
        })
    
    passed = all(t['passed'] for t in tests)
    return {
        'passed': passed,
        'tests': tests,
        'message': f"Passed {sum(t['passed'] for t in tests)}/{len(tests)} tests"
    }
```

## Test Results

### Current Status (as of last run):

**Integration Tests (`--test`)**: 6/7 pass
- ✅ SubprocessEngine
- ✅ TaskQueue  
- ✅ AdvancedMonitor
- ✅ InMemoryStorage
- ✅ Platform (QueuedEvaluationPlatform)
- ✅ EventBus
- ❓ Frontend (may timeout)

**Component Tests**: 7/8 pass
- ✅ SubprocessEngine
- ❌ DockerEngine (requires Docker running)
- ✅ TaskQueue
- ✅ AdvancedMonitor
- ✅ InMemoryStorage
- ✅ FileStorage
- ✅ EventBus
- ✅ SimpleHTTPFrontend

## Known Issues

1. **Frontend Test Timeout**: The frontend self-test starts/stops a server which can interfere with the main app server

2. **Docker Test Failures**: DockerEngine tests fail if Docker isn't running or user lacks permissions

3. **Port Conflicts**: Running tests while app is running can cause port binding failures

## Best Practices

1. **Run component tests first** to identify specific failures
2. **Use `--unsafe` flag** for faster testing without Docker
3. **Check Docker is running** before full test suite
4. **Stop the app** before running integration tests to avoid port conflicts
5. **Review individual test output** not just pass/fail counts

## Future Improvements

1. Add pytest unit tests using the `get_test_suite()` methods
2. Add performance benchmarks
3. Add stress tests for queue and platform
4. Add security test scenarios
5. Create CI/CD pipeline with automated testing