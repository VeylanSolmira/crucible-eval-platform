#!/bin/bash
# Rename platform.py to core.py for consistency

echo "📝 Renaming platform.py to core.py"
echo "================================="

cd src/core

# 1. Rename the file
echo "1. Renaming file..."
if [ -f "platform.py" ]; then
    mv platform.py core.py
    echo "   ✓ Renamed platform.py → core.py"
else
    echo "   ❌ platform.py not found"
    exit 1
fi

# 2. Update imports in components.py
echo -e "\n2. Updating components.py..."
sed -i.bak 's/from \.platform import/from .core import/' components.py
rm -f components.py.bak
echo "   ✓ Updated import in components.py"

# 3. Update any other references in the core folder
echo -e "\n3. Checking for other references..."
grep -l "import platform" *.py 2>/dev/null | while read file; do
    echo "   - Checking $file"
done

# 4. Update the rename note
echo -e "\n4. Updating documentation..."
sed -i.bak 's/platform\.py - Base classes/core.py - Base classes/' RENAME_NOTE.md
rm -f RENAME_NOTE.md.bak
echo "   ✓ Updated RENAME_NOTE.md"

echo -e "\n✅ Rename complete!"
echo -e "\nThe core module structure is now consistent:"
echo "  src/core/           (folder)"
echo "  ├── core.py         (base classes)"
echo "  ├── extreme_mvp_frontier_events.py"
echo "  └── components.py"