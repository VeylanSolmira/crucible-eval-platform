# Test Fixtures

This directory contains test data, mock responses, and example code used by the test suite.

## Structure

```
fixtures/
└── README.md          # This file
```

## Purpose

Test fixtures serve several purposes:

1. **Test Data** - Static data files (JSON, YAML, CSV) used by tests
2. **Mock Responses** - Expected API responses, database results, or external service responses
3. **Example Code** - Code snippets that tests submit to the evaluation platform
4. **Templates** - Reusable test configurations or boilerplate code

## Usage

Tests reference fixtures using relative paths:

```python
# In a test file
def test_network_isolation():
    with open("tests/fixtures/security/network_isolation_test_code.py") as f:
        test_code = f.read()
    
    # Submit test_code to the evaluation platform
    response = api.submit_evaluation(code=test_code)
```

## Guidelines

- Keep fixtures minimal and focused on specific test scenarios
- Use descriptive names that indicate the fixture's purpose
- Document complex fixtures with comments explaining their use
- Remove outdated fixtures when tests no longer need them
- Sensitive data should never be committed as fixtures

