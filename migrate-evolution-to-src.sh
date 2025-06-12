#!/bin/bash
# Migration script: evolution → src
# This script renames the evolution folder to src and updates all references

set -e

echo "🔄 Migrating evolution/ to src/"
echo "================================"

# Check if we're in the right directory
if [ ! -d "evolution" ]; then
    echo "❌ Error: evolution/ directory not found"
    echo "   Please run this script from the metr-eval-platform root directory"
    exit 1
fi

if [ -d "src" ]; then
    echo "❌ Error: src/ directory already exists"
    echo "   Please remove or rename it first"
    exit 1
fi

# Step 1: Rename the directory
echo "📁 Renaming evolution/ to src/..."
mv evolution src

# Step 2: Update all file references
echo "📝 Updating file references..."

# Update systemd files
if [ -d "infrastructure/systemd" ]; then
    echo "  - Updating systemd service files..."
    find infrastructure/systemd -type f -name "*.service" -o -name "*.sh" -o -name "*.md" | while read file; do
        sed -i.bak 's|/evolution/|/src/|g' "$file"
        sed -i.bak 's|/evolution$|/src|g' "$file"
        rm "${file}.bak"
    done
fi

# Update terraform files
if [ -d "infrastructure/terraform" ]; then
    echo "  - Updating terraform files..."
    find infrastructure/terraform -type f -name "*.tf" -o -name "*.sh" | while read file; do
        sed -i.bak 's|evolution/|src/|g' "$file"
        rm "${file}.bak"
    done
fi

# Update documentation
echo "  - Updating documentation..."
find docs -type f -name "*.md" | while read file; do
    sed -i.bak 's|/evolution/|/src/|g' "$file"
    sed -i.bak 's|evolution/|src/|g' "$file"
    rm "${file}.bak"
done

# Update Python imports in src
echo "  - Updating Python imports..."
find src -type f -name "*.py" | while read file; do
    # Update any absolute imports that might reference evolution
    sed -i.bak 's|from evolution\.|from src.|g' "$file"
    sed -i.bak 's|import evolution\.|import src.|g' "$file"
    rm "${file}.bak"
done

# Update deployment scripts
echo "  - Updating deployment scripts..."
for file in src/*.sh; do
    if [ -f "$file" ]; then
        sed -i.bak 's|evolution|src|g' "$file"
        rm "${file}.bak"
    fi
done

# Step 3: Create EC2 update script
echo "📜 Creating EC2 update script..."
cat > update-ec2-paths.sh << 'EOF'
#!/bin/bash
# Run this on the EC2 instance to update paths

echo "🔄 Updating paths on EC2 instance"

# Check if evolution exists
if [ ! -d "$HOME/evolution" ]; then
    echo "✅ No evolution/ directory found, nothing to migrate"
    exit 0
fi

# Stop the service if running
if systemctl is-active --quiet evaluation-platform; then
    echo "🛑 Stopping evaluation-platform service..."
    sudo systemctl stop evaluation-platform
fi

# Rename directory
echo "📁 Renaming evolution/ to src/..."
mv "$HOME/evolution" "$HOME/src"

# Update systemd service
if [ -f /etc/systemd/system/evaluation-platform.service ]; then
    echo "🔧 Updating systemd service..."
    sudo sed -i 's|/evolution/|/src/|g' /etc/systemd/system/evaluation-platform.service
    sudo sed -i 's|/evolution$|/src|g' /etc/systemd/system/evaluation-platform.service
    sudo systemctl daemon-reload
fi

# Update any local scripts
if [ -d "$HOME/src" ]; then
    find "$HOME/src" -type f -name "*.sh" | while read file; do
        sed -i 's|evolution|src|g' "$file"
    done
fi

# Restart service if it was running
if [ -f /etc/systemd/system/evaluation-platform.service ]; then
    echo "🚀 Starting evaluation-platform service..."
    sudo systemctl start evaluation-platform
    sudo systemctl status evaluation-platform --no-pager
fi

echo "✅ EC2 update complete!"
EOF

chmod +x update-ec2-paths.sh

# Step 4: Update .gitignore if needed
if [ -f ".gitignore" ]; then
    echo "  - Updating .gitignore..."
    sed -i.bak 's|evolution/|src/|g' .gitignore
    rm .gitignore.bak
fi

# Step 5: Summary
echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Summary of changes:"
echo "  - Renamed evolution/ → src/"
echo "  - Updated all file references"
echo "  - Created update-ec2-paths.sh for server updates"
echo ""
echo "🚀 Next steps:"
echo "  1. Review the changes: git status"
echo "  2. Commit the changes: git add . && git commit -m 'Refactor: rename evolution to src'"
echo "  3. Update EC2 instance: scp update-ec2-paths.sh ubuntu@44.246.137.198:~/"
echo "                         ssh ubuntu@44.246.137.198 ./update-ec2-paths.sh"
echo ""
echo "⚠️  Note: You may need to update any local environment variables or IDE configurations"