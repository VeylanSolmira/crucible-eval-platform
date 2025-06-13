#!/bin/bash
# Clean up and reorganize platform folder

echo "🧹 Cleaning up platform folder"
echo "============================="

cd src

# 1. Move security scripts to security-scanner
echo "1. Moving security scripts to security-scanner..."
if [ -f "platform/run_security_demo.py" ]; then
    mv platform/run_security_demo.py security-scanner/
    echo "   ✓ Moved run_security_demo.py"
fi

if [ -f "platform/safe_security_check.py" ]; then
    mv platform/safe_security_check.py security-scanner/
    echo "   ✓ Moved safe_security_check.py"  
fi

# 2. Keep test_components.py in platform
echo -e "\n2. Keeping test_components.py in platform..."
echo "   ℹ️  test_components.py tests the integrated platform, so it belongs here"

# 3. Keep components.py as it's the import wrapper
echo -e "\n3. Keeping components.py..."
echo "   ℹ️  components.py is the import wrapper that allows monolithic operation"

# 4. Document what remains
echo -e "\n4. Creating platform README..."
cat > platform/README.md << 'EOF'
# Platform - Monolithic Implementation

This folder contains the monolithic version of the Crucible platform that integrates all components.

## Files

### Core Platform
- `extreme_mvp_frontier_events.py` - Main platform implementation
- `components.py` - Import wrapper for all service components
- `test_components.py` - Integrated testing of all components

### Demo & Utilities
- `run_demo_servers.py` - Demo server launcher

### Deployment Scripts
- `scripts/package_for_deployment.sh` - Package platform for deployment
- `scripts/quick_deploy.sh` - Quick deployment script

## Running the Platform

```bash
# Basic run
python extreme_mvp_frontier_events.py

# With specific engine
python extreme_mvp_frontier_events.py --engine docker

# Run tests
python test_components.py

# Run demos
python run_demo_servers.py
```

## Security Testing

Security testing scripts have been moved to `../security-scanner/`:
- `run_security_demo.py`
- `safe_security_check.py`

## Dependencies

See `requirements.txt` - all dependencies are optional. The platform runs with Python stdlib by default.
EOF
echo "   ✓ Created platform/README.md"

# 5. Update __init__.py if empty
if [ ! -s "platform/__init__.py" ]; then
    echo -e "\n5. Adding docstring to __init__.py..."
    cat > platform/__init__.py << 'EOF'
"""Monolithic platform implementation - integrates all components for single-process operation"""
EOF
    echo "   ✓ Updated __init__.py"
fi

# 6. Update security-scanner __init__.py to include new scripts
echo -e "\n6. Updating security-scanner imports..."
cat >> security-scanner/__init__.py << 'EOF'

# Demo and testing utilities
try:
    from .run_security_demo import run_security_demo
    from .safe_security_check import run_safe_check
except ImportError:
    # Scripts might not define these functions
    pass
EOF
echo "   ✓ Updated security-scanner/__init__.py"

echo -e "\n✅ Platform cleanup complete!"
echo -e "\nSummary:"
echo "  - Moved security scripts to security-scanner/"
echo "  - Kept test_components.py (tests integrated platform)"
echo "  - Kept components.py (import wrapper)"
echo "  - Added comprehensive README"
echo -e "\nThe platform folder is now focused on the monolithic implementation."