# Deployment Gate Tests

This directory contains deployment gate tests that verify critical requirements before deploying to specific environments.

## Purpose

Unlike functional tests that verify features work correctly, gate tests assert that deployment prerequisites are met. These tests should fail fast if the target environment doesn't meet minimum requirements.

## Structure

```
gates/
├── production/         # Production environment gates
│   └── test_gvisor_required.py
├── staging/           # Staging environment gates (future)
└── development/       # Development environment checks (future)
```

## Running Gate Tests

```bash
# Check production readiness
pytest tests/gates/production/

# Run with production marker
pytest -m production tests/gates/

# Include in CI/CD pipeline before production deployment
```

## Writing Gate Tests

Gate tests should:
1. Check for hard requirements (fail if not met)
2. Provide clear error messages with remediation steps
3. Be environment-aware (skip in inappropriate environments)
4. Run quickly (these are pre-deployment checks)

Example:
```python
@pytest.mark.production
@pytest.mark.skipif(
    os.getenv("ENVIRONMENT") == "development",
    reason="Only applies to production"
)
def test_critical_requirement():
    if not requirement_met():
        pytest.fail(
            "DEPLOYMENT BLOCKED: Requirement not met!\n"
            "To fix: [specific steps]"
        )
```

## Environment Variables

- `ENVIRONMENT`: Current environment (development/staging/production)
- `HOST_OS`: Host operating system (linux/darwin)
- `SKIP_GATES`: Set to "true" to skip all gate tests (use with caution!)