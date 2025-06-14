#!/bin/bash
# Reorganize security-scanner structure

echo "🔒 Reorganizing security-scanner structure"
echo "========================================"

cd src/security-scanner

# 1. Move security_runner.py to the main directory
echo "Moving security_runner.py to main directory..."
if [ -f "scenarios/security_runner.py" ]; then
    mv scenarios/security_runner.py security_runner.py
    echo "  ✓ Moved security_runner.py from scenarios/ to main directory"
fi

# 2. Fix imports in security_runner.py
echo "Fixing imports in security_runner.py..."
sed -i.bak 's|sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))|# Import from platform components|' security_runner.py
sed -i.bak 's|from components import|from ..platform.components import|' security_runner.py
rm security_runner.py.bak

# 3. Update __init__.py to export SecurityTestRunner
echo "Updating __init__.py..."
cat > __init__.py << 'EOF'
"""Security scanner module - runs security tests against execution engines"""

from .security_runner import SecurityTestRunner
from .scenarios.safe_demo_scenarios import SAFE_DEMO_SCENARIOS
# Note: attack_scenarios should only be imported when explicitly needed

__all__ = ['SecurityTestRunner', 'SAFE_DEMO_SCENARIOS']
EOF

# 4. Add README to explain the structure
echo "Adding documentation..."
cat > README.md << 'EOF'
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
EOF

# 5. Update scenarios/__init__.py
echo "Updating scenarios/__init__.py..."
cat > scenarios/__init__.py << 'EOF'
"""
Security test scenarios - both safe demos and real attack patterns

WARNING: attack_scenarios.py contains real security attacks.
Only run these in isolated environments with proper sandboxing!
"""

from .safe_demo_scenarios import SAFE_DEMO_SCENARIOS
# Deliberately not importing attack_scenarios by default for safety

__all__ = ['SAFE_DEMO_SCENARIOS']
EOF

echo ""
echo "✅ Security scanner reorganization complete!"
echo ""
echo "Summary:"
echo "  - Moved security_runner.py to main directory (where it belongs)"
echo "  - Fixed imports to use proper paths"
echo "  - Updated __init__.py files for clean exports"
echo "  - Added README with safety warnings"
echo ""
echo "The security runner is now properly organized as the main component,"
echo "with scenarios kept separate in the scenarios/ subdirectory."