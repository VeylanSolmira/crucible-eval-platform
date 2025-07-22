# Chaos Engineering Tests

This directory contains chaos engineering tests that verify the platform's resilience to failures and disruptions.

## Structure

- **`docker/`** - Chaos tests for Docker Compose deployments
- **`kubernetes/`** - Chaos tests for Kubernetes deployments (future)

## Running Chaos Tests

### Docker Compose Tests

These tests are **destructive** and will stop/restart services:

```bash
# Run all chaos tests
pytest -m destructive tests/chaos/docker/

# Run specific test
pytest tests/chaos/docker/test_service_resilience.py
```

### Kubernetes Tests

Future location for Kubernetes-based chaos tests using tools like:
- Chaos Mesh
- Litmus
- Pod deletion/restart tests

## Warning

⚠️ **DESTRUCTIVE TESTS** ⚠️

These tests intentionally break services to test recovery. They should:
- Never run in production
- Run in isolated test environments only
- Be excluded from regular CI/CD pipelines
- Require explicit opt-in via pytest markers

## Test Categories

1. **Service Resilience** - Service restart/failure scenarios
2. **Network Chaos** - Network partitions, latency, packet loss
3. **Resource Chaos** - CPU/memory pressure, disk failures
4. **Data Chaos** - Database failures, cache evictions