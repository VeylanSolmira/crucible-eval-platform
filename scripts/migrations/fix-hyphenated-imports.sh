#!/bin/bash
# Fix hyphenated directory names for Python imports

echo "🔧 Fixing hyphenated directory names"
echo "==================================="

cd src

# Rename directories from hyphens to underscores
echo "Renaming directories to be Python-importable..."

# 1. execution-engine → execution_engine
if [ -d "execution-engine" ]; then
    mv execution-engine execution_engine
    echo "✓ Renamed execution-engine → execution_engine"
fi

# 2. event-bus → event_bus
if [ -d "event-bus" ]; then
    mv event-bus event_bus
    echo "✓ Renamed event-bus → event_bus"
fi

# 3. web-frontend → web_frontend
if [ -d "web-frontend" ]; then
    mv web-frontend web_frontend
    echo "✓ Renamed web-frontend → web_frontend"
fi

# 4. security-scanner → security_scanner
if [ -d "security-scanner" ]; then
    mv security-scanner security_scanner
    echo "✓ Renamed security-scanner → security_scanner"
fi

# 5. future-services → future_services
if [ -d "future-services" ]; then
    mv future-services future_services
    echo "✓ Renamed future-services → future_services"
    
    # Also rename api-gateway inside
    if [ -d "future_services/api-gateway" ]; then
        mv future_services/api-gateway future_services/api_gateway
        echo "✓ Renamed api-gateway → api_gateway"
    fi
fi

# Update docker-compose.yml.example to reflect new names
echo -e "\nUpdating docker-compose.yml.example..."
if [ -f "docker-compose.yml.example" ]; then
    sed -i.bak 's|./execution-engine|./execution_engine|g' docker-compose.yml.example
    sed -i.bak 's|./event-bus|./event_bus|g' docker-compose.yml.example
    sed -i.bak 's|./web-frontend|./web_frontend|g' docker-compose.yml.example
    sed -i.bak 's|./security-scanner|./security_scanner|g' docker-compose.yml.example
    sed -i.bak 's|./future-services/api-gateway|./future_services/api_gateway|g' docker-compose.yml.example
    rm -f docker-compose.yml.example.bak
    echo "✓ Updated docker-compose.yml.example"
fi

# Update README.md
echo -e "\nUpdating src/README.md..."
sed -i.bak 's|execution-engine/|execution_engine/|g' README.md
sed -i.bak 's|event-bus/|event_bus/|g' README.md
sed -i.bak 's|security-scanner/|security_scanner/|g' README.md
sed -i.bak 's|web-frontend/|web_frontend/|g' README.md
sed -i.bak 's|future-services/|future_services/|g' README.md
sed -i.bak 's|mvp-evolution/|mvp_evolution/|g' README.md
rm -f README.md.bak
echo "✓ Updated README.md"

# Update any shell scripts that might reference old names
echo -e "\nUpdating references in platform/scripts/..."
if [ -d "platform/scripts" ]; then
    for script in platform/scripts/*.sh; do
        if [ -f "$script" ]; then
            sed -i.bak 's|execution-engine|execution_engine|g' "$script"
            sed -i.bak 's|event-bus|event_bus|g' "$script"
            sed -i.bak 's|web-frontend|web_frontend|g' "$script"
            sed -i.bak 's|security-scanner|security_scanner|g' "$script"
            rm -f "$script.bak"
        fi
    done
    echo "✓ Updated shell scripts"
fi

# Bonus: Also rename mvp-evolution for consistency
if [ -d "mvp-evolution" ]; then
    mv mvp-evolution mvp_evolution
    echo "✓ Renamed mvp-evolution → mvp_evolution"
fi

echo -e "\n✅ Directory renaming complete!"
echo -e "\nAll directories now use underscores for Python compatibility:"
echo "  - execution_engine/"
echo "  - event_bus/"
echo "  - web_frontend/"
echo "  - security_scanner/"
echo "  - future_services/"
echo "  - mvp_evolution/"
echo -e "\nThe imports in components.py will now work correctly!"