#!/bin/bash
# Move EVOLUTION_TREE.md to docs and add reference

echo "📄 Moving EVOLUTION_TREE.md to docs"
echo "==================================="

# Move the file
echo "Moving EVOLUTION_TREE.md to docs/extreme-mvp/..."
mv src/mvp-evolution/EVOLUTION_TREE.md docs/extreme-mvp/evolution-tree.md
echo "✓ Moved to docs/extreme-mvp/evolution-tree.md"

# Add a reference in the mvp-evolution folder
echo "Adding reference in mvp-evolution/..."
cat > src/mvp-evolution/EVOLUTION_TREE_MOVED.md << 'EOF'
# Evolution Tree

The evolution tree documentation has been moved to maintain all documentation in the `/docs` folder.

See: [Evolution Tree](../../docs/extreme-mvp/evolution-tree.md)

This file remains as a pointer for anyone looking in the code directory.
EOF
echo "✓ Added reference pointer"

# Update the mvp-evolution README to mention the new location
echo "Updating mvp-evolution/README.md..."
sed -i.bak 's|See \[EVOLUTION_TREE.md\](EVOLUTION_TREE.md)|See [Evolution Tree](../../docs/extreme-mvp/evolution-tree.md)|' src/mvp-evolution/README.md
rm -f src/mvp-evolution/README.md.bak
echo "✓ Updated README reference"

echo ""
echo "✅ Migration complete!"
echo ""
echo "Evolution tree now at: docs/extreme-mvp/evolution-tree.md"
echo "Reference pointer left at: src/mvp-evolution/EVOLUTION_TREE_MOVED.md"