#!/bin/bash
# Rename reference folder to better indicate its purpose

echo "📁 Renaming reference folder"
echo "==========================="

cd src

# Consider different naming options
echo "Naming options considered:"
echo "  - extreme-mvp-progression (descriptive but long)"
echo "  - mvp-evolution (shorter, clear)"
echo "  - evolution-history (generic but clear)"
echo "  - mvp-history (concise)"
echo ""
echo "Chosen: mvp-evolution (clear and concise)"
echo ""

# Rename the folder
if [ -d "reference" ]; then
    mv reference mvp-evolution
    echo "✓ Renamed reference/ to mvp-evolution/"
else
    echo "❌ reference/ folder not found"
    exit 1
fi

# Update any imports that might reference it
echo "Checking for imports..."
grep -r "from reference" . --include="*.py" 2>/dev/null || echo "  No imports found from reference folder"
grep -r "import reference" . --include="*.py" 2>/dev/null || echo "  No direct imports of reference module"

# Update the platform's components.py if it mentions reference
if [ -f "platform/components.py" ]; then
    sed -i.bak 's|reference/|mvp-evolution/|g' platform/components.py 2>/dev/null && echo "  Updated platform/components.py" || echo "  No reference paths in components.py"
    rm -f platform/components.py.bak
fi

# Update the src/README.md
if [ -f "README.md" ]; then
    sed -i.bak 's|- `reference/` - Historical implementations|- `mvp-evolution/` - Historical implementation progression|' README.md
    rm -f README.md.bak
    echo "✓ Updated src/README.md"
fi

echo ""
echo "✅ Renaming complete!"
echo ""
echo "The folder is now: src/mvp-evolution/"
echo "This clearly indicates it contains the MVP's evolution history."