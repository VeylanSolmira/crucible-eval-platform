#!/bin/bash
# Move app.py to project root as the main entry point

echo "📦 Moving app.py to project root"
echo "==============================="

cd /Users/infinitespire/ai_dev/applications/metr-eval-platform

# 1. Move app.py to project root
echo "1. Moving app.py to project root..."
if [ -f "src/core/app.py" ]; then
    mv src/core/app.py app.py
    echo "   ✓ Moved app.py to project root"
else
    echo "   ❌ src/core/app.py not found"
    exit 1
fi

# 2. Fix imports in app.py
echo -e "\n2. Fixing imports in app.py..."
# Change from relative imports to absolute imports
sed -i.bak 's/from \.components import/from src.core.components import/' app.py
rm -f app.py.bak
echo "   ✓ Fixed imports"

# 3. Update or create __main__.py at project root
echo -e "\n3. Creating project-level __main__.py..."
cat > __main__.py << 'EOF'
"""
Main entry point for the Crucible Evaluation Platform.
Allows running as: python -m crucible
"""

from app import main

if __name__ == "__main__":
    main()
EOF
echo "   ✓ Created __main__.py"

# 4. Update pyproject.toml
echo -e "\n4. Updating pyproject.toml..."
sed -i.bak 's/src\.core\.app:main/app:main/' pyproject.toml
rm -f pyproject.toml.bak
echo "   ✓ Updated pyproject.toml"

# 5. Remove old __main__.py from core
echo -e "\n5. Cleaning up old entry points..."
rm -f src/core/__main__.py
echo "   ✓ Removed src/core/__main__.py"

# 6. Update documentation
echo -e "\n6. Updating documentation..."
cat > RUN.md << 'EOF'
# Running the Crucible Evaluation Platform

The platform is a Python application with `app.py` as the main entry point.

## Quick Start

From the project root:

```bash
# Direct execution
python app.py --help

# As a module
python -m app

# If installed with pip
crucible --help
```

## Options

- `--engine [subprocess|docker|gvisor]` - Choose execution engine
- `--port PORT` - Web server port (default: 8080)
- `--test` - Run component tests
- `--unsafe` - Allow subprocess engine (dangerous!)

## Project Structure

```
crucible-evaluation-platform/
├── app.py              # Main entry point
├── src/                # Source code
│   ├── core/          # Core platform classes
│   ├── api/           # API component
│   ├── execution_engine/  # Execution engines
│   └── ...            # Other components
├── tests/             # Test files
├── docs/              # Documentation
└── pyproject.toml     # Python package configuration
```

This is a standard Python application structure where:
- `app.py` at the root is the main executable
- `src/` contains all the library code
- The application can be run directly or installed as a package
EOF
echo "   ✓ Created RUN.md"

# 7. Update README_RUNNING.md
echo -e "\n7. Updating README_RUNNING.md..."
sed -i.bak 's|python -m src\.core\.extreme_mvp_frontier_events|python app.py|g' README_RUNNING.md
sed -i.bak 's|python -m src\.core|python -m app|g' README_RUNNING.md
rm -f README_RUNNING.md.bak
echo "   ✓ Updated README_RUNNING.md"

echo -e "\n✅ App.py moved to project root!"
echo -e "\nThe project now has a standard Python application structure:"
echo "  - app.py at root: Main entry point"
echo "  - src/: Library code"
echo "  - Standard execution: python app.py"
echo -e "\nTo run:"
echo "  cd $(pwd)"
echo "  python app.py --help"