#!/bin/bash
# Clean up execution engine structure

echo "🧹 Cleaning up execution engine structure"
echo "========================================"

cd src/execution-engine

# 1. Remove the broken engines subfolder
if [ -d "engines" ]; then
    echo "Removing broken engines/ subfolder..."
    rm -rf engines/
    echo "  ✓ Removed engines/ subfolder"
fi

# 2. Add a comment to execution.py about future modularization
echo "Adding modularization note to execution.py..."
cat > execution_header.py << 'EOF'
"""
Execution engines for code evaluation.
These can evolve into full sandboxing services.

NOTE: Currently monolithic by design. See docs/architecture/when-to-modularize.md
for criteria on when to split into separate modules.

TODO: Consider modularizing when:
- Adding 5th engine type (e.g., Firecracker)
- Any engine exceeds 200 lines
- Need engine-specific dependencies
"""
EOF

# Combine header with rest of file (skip first 4 lines)
tail -n +5 execution.py > execution_temp.py
cat execution_header.py execution_temp.py > execution.py
rm execution_header.py execution_temp.py

# 3. Fix the import (if needed)
echo "Fixing imports..."
if grep -q "from \.base import TestableComponent" execution.py; then
    sed -i.bak 's/from \.base import TestableComponent/from ..shared.base import TestableComponent/' execution.py
    rm execution.py.bak
    echo "  ✓ Fixed TestableComponent import"
fi

echo ""
echo "✅ Execution engine cleanup complete!"
echo ""
echo "Summary:"
echo "  - Removed broken engines/ subfolder"
echo "  - Added modularization documentation reference"
echo "  - Fixed imports if needed"
echo ""
echo "The execution engines remain in execution.py with a note about future modularization."