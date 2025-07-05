# Buildtime Security Tests

This directory contains tests that verify the platform's security features are implemented correctly. These are distinct from the runtime security assessments in `/security/`.

## Purpose

These tests ensure that:
- Security features work as designed
- Security controls are properly integrated
- Security regressions don't occur
- Security policies are enforced by the code

## Test Categories

### Unit Tests
Test individual security components in isolation:
- **Input validation** - Verify sanitization prevents injection attacks
- **Authentication** - Test auth token validation, session management
- **Authorization** - Verify permission checks work correctly
- **Encryption** - Test data encryption/decryption functions
- **Rate limiting** - Verify request throttling logic

Example:
```python
def test_code_input_sanitization():
    """Verify dangerous code patterns are caught"""
    dangerous_code = "import os; os.system('rm -rf /')"
    assert not is_code_safe(dangerous_code)
```

### Integration Tests
Test security features across components:
- **Container creation** - Verify security policies are applied
- **API security** - Test authentication/authorization on endpoints
- **Network isolation** - Verify containers can't make external connections
- **Resource limits** - Test that limits are enforced
- **Audit logging** - Verify security events are logged

Example:
```python
def test_container_security_policies_applied():
    """Verify containers are created with proper security options"""
    response = api.submit_evaluation(code="print('test')")
    container = get_container(response.eval_id)
    
    assert container.config["SecurityOpt"] == ["no-new-privileges"]
    assert container.config["CapDrop"] == ["ALL"]
    assert container.config["ReadonlyRootfs"] == True
    assert container.config["NetworkMode"] == "none"
```

### Security Regression Tests
Prevent previously fixed vulnerabilities from returning:
- **Known CVEs** - Test that patched vulnerabilities stay fixed
- **Past incidents** - Verify previous security issues don't reoccur
- **Configuration drift** - Ensure secure defaults aren't changed

Example:
```python
def test_no_docker_socket_mount():
    """Regression test: ensure Docker socket is never mounted"""
    # This was a vulnerability in v1.0
    response = api.submit_evaluation(code="print('test')")
    container = get_container(response.eval_id)
    
    for mount in container.mounts:
        assert "/var/run/docker.sock" not in mount.source
```

## Running Security Tests

```bash
# Run all security tests
pytest tests/security/

# Run only unit tests
pytest tests/security/unit/

# Run with security markers
pytest -m security
```

## Key Distinction

- **`/tests/security/`** - "Do our security features work correctly?" (buildtime)
- **`/security/`** - "Is our environment actually secure?" (runtime)

Both are critical for platform security:
- These tests run in CI/CD to catch issues before deployment
- Runtime assessments verify production environments are secure

## Writing Security Tests

When adding security tests:
1. Test both positive and negative cases
2. Use realistic attack patterns
3. Document the threat being tested
4. Add regression tests for any security fixes
5. Consider edge cases and bypass attempts

Remember: Security tests are your first line of defense against vulnerabilities making it to production.