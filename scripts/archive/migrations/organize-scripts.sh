#!/bin/bash
# Organize migration scripts into proper folders

echo "📁 Organizing scripts"
echo "===================="

# Create scripts/migrations folder
echo "Creating scripts/migrations folder..."
mkdir -p scripts/migrations
echo "✓ Created scripts/migrations/"

# Identify scripts to keep at root
echo -e "\nScripts to keep at project root:"
echo "  - setup-venv.sh (environment setup)"
echo "  - organize-scripts.sh (this script)"

# Move migration/cleanup scripts
echo -e "\nMoving migration scripts..."
migration_scripts=(
    "migrate-evolution-to-src.sh"
    "migrate-to-services.sh"
    "move-evolution-properly.sh"
    "move-evolution-tree.sh"
    "fix-migration.sh"
    "rename-reference-folder.sh"
    "rename-main-py-files.sh"
    "cleanup-execution-engine.sh"
    "cleanup-monitoring.sh"
    "cleanup-queue.sh"
    "cleanup-shared.sh"
    "cleanup-storage.sh"
    "cleanup-web-frontend.sh"
    "reorganize-security-scanner.sh"
    "analyze-shared-issues.sh"
    "fix-shared-issues.sh"
    "fix-shared-simple.sh"
    "update-dockerfiles-placeholder.sh"
    "update-service-requirements.sh"
)

for script in "${migration_scripts[@]}"; do
    if [ -f "$script" ]; then
        mv "$script" scripts/migrations/
        echo "  ✓ Moved $script"
    fi
done

# Move documentation organization scripts
echo -e "\nMoving documentation scripts..."
mkdir -p scripts/docs
doc_scripts=(
    "organize-docs.sh"
    "reorganize_docs.sh"
    "reorganize-src-docs.sh"
    "create-security-docs.sh"
)

for script in "${doc_scripts[@]}"; do
    if [ -f "$script" ]; then
        mv "$script" scripts/docs/
        echo "  ✓ Moved $script"
    fi
done

# Create README for scripts folder
echo -e "\nCreating scripts documentation..."
cat > scripts/README.md << 'EOF'
# Scripts

Utility scripts for the Crucible platform.

## Directory Structure

### `/migrations`
Scripts used for code reorganization and migration. These were used during the platform restructuring and can be deleted once the migration is stable.

### `/docs`
Scripts for documentation organization and generation.

### `/deployment` (future)
Deployment and infrastructure scripts.

## Root Level Scripts

Only essential, frequently-used scripts should remain at the project root:
- `setup-venv.sh` - Python virtual environment setup

## Usage

Most scripts are one-time use for migrations. Review before running.
EOF

echo "✓ Created scripts/README.md"

# Create a summary of what was moved
echo -e "\n📋 Summary:"
echo "  - Moved ${#migration_scripts[@]} migration scripts to scripts/migrations/"
echo "  - Moved ${#doc_scripts[@]} documentation scripts to scripts/docs/"
echo "  - Kept setup-venv.sh at root (essential setup)"
echo "  - Created scripts/README.md"

echo -e "\n✅ Script organization complete!"
echo -e "\nNext step: Review scripts/migrations/ and delete any that are no longer needed."