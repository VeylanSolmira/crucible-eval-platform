# Production Testing Strategy

## Overview

We use a multi-layered approach to ensure production deployments meet security requirements:

1. **Adaptive Tests**: Tests that work differently in dev vs production
2. **Production-Only Tests**: Tests that enforce production requirements
3. **Environment Detection**: Multiple ways to identify production

## Running Tests

### Development Mode (Default)
```bash
# Run all tests - some will adapt to missing gVisor
pytest tests/integration/

# Filesystem isolation will pass with warnings about limited isolation
```

### Production Mode
```bash
# Set environment to production
export ENVIRONMENT=production

# Or use the REQUIRE_GVISOR flag
export REQUIRE_GVISOR=true

# Run tests - will FAIL if gVisor is missing
pytest tests/integration/

# Run only production-critical tests
pytest -m production tests/
```

## Test Categories

### 1. Adaptive Tests
Example: `test_filesystem_isolation.py`
- In development: Passes with limited isolation (warns about /etc/passwd being readable)
- In production: FAILS if gVisor is not available

### 2. Production-Only Tests
Example: `test_production_requirements.py`
- Only run with `-m production` marker
- Hard requirements that MUST pass in production
- Include: gVisor availability, network isolation, resource limits

### 3. Regular Tests
All other tests that should pass in any environment

## Environment Detection

Tests detect production in multiple ways:

```python
IS_PRODUCTION = any([
    os.getenv("ENVIRONMENT") == "production",
    os.getenv("REQUIRE_GVISOR", "false").lower() == "true",
    os.getenv("K8S_CLUSTER_TYPE") == "production"
])
```

## CI/CD Integration

### Staging Pipeline
```yaml
- name: Run tests (staging mode)
  env:
    ENVIRONMENT: staging
  run: |
    pytest tests/integration/
    # May show warnings but won't fail on gVisor
```

### Production Pipeline
```yaml
- name: Validate production requirements
  env:
    ENVIRONMENT: production
    REQUIRE_GVISOR: true
  run: |
    # This WILL FAIL if gVisor is not available
    pytest -m production tests/
    
    # Run all tests in production mode
    pytest tests/integration/
```

## Key Production Requirements

1. **gVisor Runtime**: MANDATORY
   - Test: `test_gvisor_required()`
   - Why: Kernel isolation for untrusted code

2. **Network Isolation**: MANDATORY
   - Test: `test_network_isolation()`
   - Why: Prevent data exfiltration

3. **Filesystem Isolation**: MANDATORY
   - Test: `test_filesystem_isolation()` 
   - Why: Hide system information from AI models

## Deployment Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Run `pytest -m production` - MUST pass
- [ ] Verify gVisor RuntimeClass exists
- [ ] Check NetworkPolicies are applied
- [ ] Confirm resource limits are set

## Handling Test Failures

### "gVisor not available" in production
1. **GKE**: Deploy with `--enable-sandbox`
2. **EKS**: Use custom AMI with gVisor
3. See: [gVisor Production Deployment Guide](../security/gvisor-production-deployment.md)

### "Filesystem readable" in production
- Indicates gVisor is not working properly
- Check RuntimeClass is applied to pods
- Verify nodes have runsc installed

### Network test failures
- Check NetworkPolicy is applied
- Verify CNI plugin supports NetworkPolicies
- Test with `kubectl exec` to verify isolation