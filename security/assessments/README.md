# Security Assessments

This directory contains tools and scenarios for assessing the security posture of the platform's execution environments.

## Tools

### container_check.py
A safe, read-only tool that assesses the security configuration of container environments. It checks:
- Container detection and type
- User permissions and root access
- Network interface availability
- Filesystem permissions
- Resource limits
- Access to sensitive paths (Docker socket, host processes)

**Usage:**
```bash
# Run on host
python security/assessments/container_check.py

# Run inside a container
docker run -v $(pwd):/app python /app/security/assessments/container_check.py
```

## Network Tests

The `network_tests/` directory contains code designed to be executed inside containers to verify network isolation:

- **network_isolation_test_code.py** - Basic network isolation test
- **test_network_isolation.py** - Comprehensive 9-test network isolation suite
- **simple_network_test.py** - Quick 3-test network check

These are meant to be submitted as evaluation code to verify containers are properly isolated.

## Scenarios

The `scenarios/` directory contains security test scenarios as Python dictionaries:

### Safe Scenarios
- **safe_demo_scenarios.py** - Read-only demonstrations of security concepts
- Can be safely run in any environment
- Used for demos and non-destructive testing

### Attack Scenarios
- **attack_scenarios.py** - Real attack patterns for security boundary testing
- **DANGEROUS** - Only run in fully isolated test environments
- Used to verify security controls are effective

### Usage Example
```python
from security.assessments.scenarios import SAFE_DEMO_SCENARIOS

# Submit scenario as evaluation
for scenario_id, scenario in SAFE_DEMO_SCENARIOS.items():
    eval_request = {
        "code": scenario["code"],
        "timeout": 30,
        "engine": "docker"
    }
    # Submit to platform API
```

## Safety Considerations

- Always use safe scenarios for demos and regular testing
- Only use attack scenarios in dedicated security testing environments
- Network tests will fail on properly isolated systems (that's good!)
- Container check tool is always safe to run