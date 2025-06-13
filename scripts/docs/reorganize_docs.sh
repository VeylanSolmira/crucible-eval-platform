#!/bin/bash

# Script to reorganize documentation files
# This script moves docs to their appropriate categories and renames the evolution folder

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base directory
DOCS_DIR="/Users/infinitespire/ai_dev/applications/metr-eval-platform/docs"

echo -e "${BLUE}Starting documentation reorganization...${NC}"
echo

# Create new directories if they don't exist
echo -e "${GREEN}Creating new directory structure...${NC}"
mkdir -p "$DOCS_DIR/knowledge"
mkdir -p "$DOCS_DIR/architecture"

# Move general knowledge guides to docs/knowledge/
echo -e "${YELLOW}Moving general knowledge guides to docs/knowledge/${NC}"
mv "$DOCS_DIR/evolution/factory-functions-pattern.md" "$DOCS_DIR/knowledge/" 2>/dev/null && echo "  ✓ Moved factory-functions-pattern.md"
mv "$DOCS_DIR/evolution/monkey-patching-guide.md" "$DOCS_DIR/knowledge/" 2>/dev/null && echo "  ✓ Moved monkey-patching-guide.md"
mv "$DOCS_DIR/evolution/python-typing-guide.md" "$DOCS_DIR/knowledge/" 2>/dev/null && echo "  ✓ Moved python-typing-guide.md"
mv "$DOCS_DIR/evolution/mvp-model-testing-guide.md" "$DOCS_DIR/knowledge/" 2>/dev/null && echo "  ✓ Moved mvp-model-testing-guide.md"

# Move architecture/security docs to docs/architecture/
echo
echo -e "${YELLOW}Moving architecture and security docs to docs/architecture/${NC}"
mv "$DOCS_DIR/evolution/PLATFORM_ARCHITECTURE.md" "$DOCS_DIR/architecture/" 2>/dev/null && echo "  ✓ Moved PLATFORM_ARCHITECTURE.md"
mv "$DOCS_DIR/evolution/CONTAINER_SECURITY_REPORT.md" "$DOCS_DIR/architecture/" 2>/dev/null && echo "  ✓ Moved CONTAINER_SECURITY_REPORT.md"

# Rename evolution folder to extreme-mvp
echo
echo -e "${YELLOW}Renaming evolution/ to extreme-mvp/${NC}"
mv "$DOCS_DIR/evolution" "$DOCS_DIR/extreme-mvp" 2>/dev/null && echo "  ✓ Renamed evolution/ to extreme-mvp/"

# Create summary README in docs/ if it doesn't exist
echo
echo -e "${GREEN}Creating documentation overview...${NC}"
cat > "$DOCS_DIR/README.md" << 'EOF'
# METR Evaluation Platform Documentation

## Directory Structure

### `/extreme-mvp/`
Contains documentation specific to the extreme MVP implementation approach:
- Evolution of the platform from simple to modular
- Implementation updates and summaries
- Real-time updates strategy
- Frontend refactoring details

### `/knowledge/`
General knowledge guides and best practices:
- **factory-functions-pattern.md** - Design pattern for interface abstraction
- **monkey-patching-guide.md** - Python dynamic modification techniques
- **python-typing-guide.md** - Modern Python type hints and static typing
- **mvp-model-testing-guide.md** - Guide for testing language models on various platforms

### `/architecture/`
Platform architecture and security documentation:
- **PLATFORM_ARCHITECTURE.md** - Understanding the platform components and structure
- **CONTAINER_SECURITY_REPORT.md** - Security assessment of execution engines

### `/deployment/`
Deployment guides and instructions (existing)

### `/api/`
API documentation and specifications (if exists)

## Quick Links

- [Platform Architecture Overview](architecture/PLATFORM_ARCHITECTURE.md)
- [MVP Evolution Story](extreme-mvp/README.md)
- [Python Best Practices](knowledge/python-typing-guide.md)
- [Security Report](architecture/CONTAINER_SECURITY_REPORT.md)
EOF

echo "  ✓ Created docs/README.md"

# Final summary
echo
echo -e "${BLUE}Documentation reorganization complete!${NC}"
echo
echo "Summary of changes:"
echo "  • Created docs/knowledge/ for general guides"
echo "  • Created docs/architecture/ for platform architecture docs"
echo "  • Moved 4 files to knowledge/"
echo "  • Moved 2 files to architecture/"
echo "  • Renamed evolution/ to extreme-mvp/"
echo "  • Created docs/README.md overview"
echo
echo -e "${GREEN}The documentation is now better organized by category.${NC}"

# List final structure
echo
echo "New structure:"
tree "$DOCS_DIR" -L 2 -d 2>/dev/null || {
    echo "docs/"
    echo "├── api/ (if exists)"
    echo "├── architecture/"
    echo "├── deployment/"
    echo "├── extreme-mvp/"
    echo "└── knowledge/"
}