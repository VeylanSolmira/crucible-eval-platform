# Security Scanner

This module tests the security boundaries of different execution engines.

## Structure

```
security-scanner/
├── security_runner.py      # Main test runner
├── scenarios/              # Test scenarios
│   ├── attack_scenarios.py # Real attack patterns (handle with care!)
│   └── safe_demo_scenarios.py # Safe demonstrations
└── results/                # Test results storage
```

## Usage

```python
from security_scanner import SecurityTestRunner, SAFE_DEMO_SCENARIOS

# Run safe demos only
runner = SecurityTestRunner(SAFE_DEMO_SCENARIOS)
results = runner.run_all_tests()
runner.save_results("results/demo_results.json")
```

## Safety Notes

1. **NEVER** run attack_scenarios.py against SubprocessEngine
2. Always use Docker or gVisor for testing real attacks
3. Run in isolated environments only
4. Review scenarios before execution

## Scenarios

### Safe Demos
- Resource limit testing
- Network isolation verification
- Filesystem restrictions

### Attack Scenarios (Use with caution)
- Container escape attempts
- Privilege escalation
- Resource exhaustion
- Network exfiltration

See `scenarios/` directory for full list.
