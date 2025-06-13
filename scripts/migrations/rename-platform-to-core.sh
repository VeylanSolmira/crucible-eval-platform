#!/bin/bash
# Rename platform folder to core to avoid conflicts and better reflect its purpose

echo "🔄 Renaming platform/ to core/"
echo "=============================="

cd src

# 1. Rename the folder
echo "1. Renaming folder..."
if [ -d "platform" ]; then
    mv platform core
    echo "   ✓ Renamed platform/ → core/"
else
    echo "   ❌ platform/ folder not found"
    exit 1
fi

# 2. Update imports in extreme_mvp_frontier_events.py
echo -e "\n2. Updating imports in extreme_mvp_frontier_events.py..."
# The import is already relative, so no change needed there

# 3. Update imports in components.py
echo -e "\n3. Updating components.py imports..."
# Update the fallback import that was looking for 'platform' module
sed -i.bak 's/from platform import/from crucible_core import/' core/components.py 2>/dev/null || true
rm -f core/components.py.bak

# 4. Update imports in core/platform.py (the base classes file)
echo -e "\n4. Checking core/platform.py imports..."
# No changes needed - it uses relative imports

# 5. Update __main__.py
echo -e "\n5. Updating __main__.py..."
# Already uses relative imports, no change needed

# 6. Update test files that might import from platform
echo -e "\n6. Updating test imports..."
if [ -f "../tests/test_components.py" ]; then
    sed -i.bak "s|'src', 'platform'|'src', 'core'|g" ../tests/test_components.py
    sed -i.bak "s|src\.platform|src.core|g" ../tests/test_components.py
    rm -f ../tests/test_components.py.bak
    echo "   ✓ Updated test_components.py"
fi

# 7. Update deployment scripts
echo -e "\n7. Updating deployment scripts..."
for script in core/scripts/*.sh; do
    if [ -f "$script" ]; then
        sed -i.bak 's|/platform/|/core/|g' "$script"
        sed -i.bak 's|platform/|core/|g' "$script"
        rm -f "$script.bak"
    fi
done
echo "   ✓ Updated deployment scripts"

# 8. Update docker-compose.yml.example
echo -e "\n8. Updating docker-compose.yml.example..."
if [ -f "docker-compose.yml.example" ]; then
    sed -i.bak 's|# Note: This is a template|# Note: The monolithic core is in src/core/|' docker-compose.yml.example
    rm -f docker-compose.yml.example.bak
    echo "   ✓ Updated docker-compose.yml.example"
fi

# 9. Update README files
echo -e "\n9. Updating documentation..."

# Update src/README.md
sed -i.bak 's|- `platform/`|- `core/`|g' README.md
sed -i.bak 's|cd platform|cd core|g' README.md
sed -i.bak 's|from the `platform/`|from the `core/`|g' README.md
rm -f README.md.bak
echo "   ✓ Updated src/README.md"

# Update project-level files that might reference platform
cd ..
if [ -f "pyproject.toml" ]; then
    sed -i.bak 's|src\.platform\.|src.core.|g' pyproject.toml
    rm -f pyproject.toml.bak
    echo "   ✓ Updated pyproject.toml"
fi

if [ -f "README_RUNNING.md" ]; then
    sed -i.bak 's|src\.platform|src.core|g' README_RUNNING.md
    sed -i.bak 's|inside `src/platform/`|inside `src/core/`|g' README_RUNNING.md
    sed -i.bak 's|Our `platform` folder|Our `core` folder|g' README_RUNNING.md
    rm -f README_RUNNING.md.bak
    echo "   ✓ Updated README_RUNNING.md"
fi

# 10. Create a note explaining the rename
echo -e "\n10. Creating migration note..."
cat > src/core/RENAME_NOTE.md << 'EOF'
# Core Module (formerly platform)

This folder was renamed from `platform/` to `core/` to:

1. **Avoid naming conflicts** with Python's built-in `platform` module
2. **Better reflect its purpose** as the transitional monolithic core
3. **Indicate it's temporary** - code here will migrate to service folders

## What's in core/

- `extreme_mvp_frontier_events.py` - Main entry point
- `platform.py` - Base classes (EvaluationPlatform, etc.)
- `components.py` - Import helper for all services

## Running

From project root:
```bash
python -m src.core.extreme_mvp_frontier_events
# or
python -m src.core
```

## Future

As we complete the microservices migration, code will move from here to the appropriate service folders.
EOF
echo "   ✓ Created RENAME_NOTE.md"

echo -e "\n✅ Rename complete!"
echo -e "\nChanges made:"
echo "  - platform/ → core/"
echo "  - Updated all import references"
echo "  - Updated documentation"
echo "  - No Python built-in conflicts!"
echo -e "\nTo run:"
echo "  cd $(pwd)"
echo "  python -m src.core.extreme_mvp_frontier_events --help"