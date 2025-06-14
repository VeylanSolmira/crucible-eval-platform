#!/bin/bash
# Organize remaining files in platform folder

echo "📁 Organizing remaining platform files"
echo "===================================="

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

# 2. Move test_components.py to tests folder (create if needed)
echo -e "\n2. Moving test_components.py to tests/..."
mkdir -p ../tests
if [ -f "platform/test_components.py" ]; then
    mv platform/test_components.py ../tests/
    echo "   ✓ Moved test_components.py to tests/"
    
    # Update imports in test_components.py
    sed -i.bak "s|sys.path.append('.')|sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'platform'))|" ../tests/test_components.py
    rm -f ../tests/test_components.py.bak
    echo "   ✓ Updated import paths in test_components.py"
fi

# 3. Move run_demo_servers.py to a demos folder
echo -e "\n3. Moving demo script..."
mkdir -p ../demos
if [ -f "platform/run_demo_servers.py" ]; then
    mv platform/run_demo_servers.py ../demos/
    echo "   ✓ Moved run_demo_servers.py to demos/"
    
    # Create a README for demos
    cat > ../demos/README.md << 'EOF'
# Demos

This folder contains demonstration scripts for the Crucible platform.

## Available Demos

### run_demo_servers.py
Launches demo servers to showcase platform capabilities.

```bash
cd demos
python run_demo_servers.py
```

## Running Demos

All demos should be run from the demos directory. They will import from the src/ directory.
EOF
    echo "   ✓ Created demos/README.md"
fi

# 4. Update platform folder to be minimal
echo -e "\n4. Creating minimal platform README..."
cat > platform/README.md << 'EOF'
# Platform

Core platform implementation files.

## Contents

- `extreme_mvp_frontier_events.py` - Main platform implementation
- `platform.py` - Platform base classes (EvaluationPlatform, QueuedEvaluationPlatform)
- `components.py` - Import helper for all service components
- `requirements.txt` - Optional dependencies

## Running the Platform

```bash
cd src/platform
python extreme_mvp_frontier_events.py
```

## Testing

Tests have been moved to `/tests/test_components.py`

```bash
cd tests
python test_components.py
```

## Security Testing

Security testing scripts are in `/src/security-scanner/`:
- `run_security_demo.py`
- `safe_security_check.py`

## Demos

Demo scripts are in `/demos/`:
- `run_demo_servers.py`
EOF
echo "   ✓ Created platform/README.md"

# 5. Clean up __init__.py
echo -e "\n5. Updating platform/__init__.py..."
cat > platform/__init__.py << 'EOF'
"""Platform - Core implementation combining all services"""
EOF
echo "   ✓ Updated __init__.py"

# 6. List what remains
echo -e "\n6. Platform folder now contains:"
ls -la platform/ | grep -E "\.py$|\.txt$|\.md$" | grep -v __pycache__

echo -e "\n✅ Platform organization complete!"
echo -e "\nFiles moved to:"
echo "  - Security scripts → src/security-scanner/"
echo "  - test_components.py → tests/"
echo "  - run_demo_servers.py → demos/"
echo -e "\nPlatform folder now contains only core platform files:"
echo "  - extreme_mvp_frontier_events.py (main)"
echo "  - platform.py (base classes)"
echo "  - components.py (import helper)"
echo "  - requirements.txt"