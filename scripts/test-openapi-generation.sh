#!/bin/bash
# Test script for OpenAPI generation across all services

set -e

echo "🧪 Testing OpenAPI generation for all services..."
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python is available
if ! command_exists python3 && ! command_exists python; then
    echo -e "${RED}❌ Python not found. Please install Python 3.x${NC}"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD=$(command_exists python3 && echo "python3" || echo "python")

# Test API service
echo -e "\n📄 Testing API service OpenAPI generation..."
if [ -f "api/scripts/export-openapi-spec.py" ]; then
    cd api
    if $PYTHON_CMD scripts/export-openapi-spec.py; then
        echo -e "${GREEN}✅ API service spec generated successfully${NC}"
        if [ -f "openapi.yaml" ] && [ -f "openapi.json" ]; then
            echo -e "${GREEN}   - openapi.yaml exists${NC}"
            echo -e "${GREEN}   - openapi.json exists${NC}"
        else
            echo -e "${RED}❌ API spec files not created${NC}"
        fi
    else
        echo -e "${RED}❌ API service spec generation failed${NC}"
        echo -e "${YELLOW}   Check if dependencies are installed: pip install -r requirements.txt${NC}"
    fi
    cd ..
else
    echo -e "${RED}❌ API export script not found${NC}"
fi

# Test Storage service
echo -e "\n📄 Testing Storage service OpenAPI generation..."
if [ -f "storage-service/scripts/export-openapi-spec.py" ]; then
    cd storage-service
    if $PYTHON_CMD scripts/export-openapi-spec.py; then
        echo -e "${GREEN}✅ Storage service spec generated successfully${NC}"
        if [ -f "openapi.yaml" ] && [ -f "openapi.json" ]; then
            echo -e "${GREEN}   - openapi.yaml exists${NC}"
            echo -e "${GREEN}   - openapi.json exists${NC}"
        else
            echo -e "${RED}❌ Storage spec files not created${NC}"
        fi
    else
        echo -e "${RED}❌ Storage service spec generation failed${NC}"
        echo -e "${YELLOW}   Check if dependencies are installed: pip install -r requirements.txt${NC}"
    fi
    cd ..
else
    echo -e "${RED}❌ Storage export script not found${NC}"
fi

# Test Executor service
echo -e "\n📄 Testing Executor service OpenAPI generation..."
if [ -f "executor-service/scripts/export-openapi-spec.py" ]; then
    cd executor-service
    if $PYTHON_CMD scripts/export-openapi-spec.py; then
        echo -e "${GREEN}✅ Executor service spec generated successfully${NC}"
        if [ -f "openapi.yaml" ] && [ -f "openapi.json" ]; then
            echo -e "${GREEN}   - openapi.yaml exists${NC}"
            echo -e "${GREEN}   - openapi.json exists${NC}"
        else
            echo -e "${RED}❌ Executor spec files not created${NC}"
        fi
    else
        echo -e "${RED}❌ Executor service spec generation failed${NC}"
        echo -e "${YELLOW}   Check if dependencies are installed: pip install -r requirements.txt${NC}"
    fi
    cd ..
else
    echo -e "${RED}❌ Executor export script not found${NC}"
fi

# Summary
echo -e "\n================================================"
echo -e "📊 Summary of OpenAPI spec files:"
echo -e "================================================"

for service in api storage-service executor-service; do
    if [ -f "$service/openapi.yaml" ]; then
        echo -e "${GREEN}✅ $service/openapi.yaml${NC}"
    else
        echo -e "${RED}❌ $service/openapi.yaml${NC}"
    fi
done

echo -e "\n💡 Next steps:"
echo "1. If any generation failed, install dependencies:"
echo "   pip install -r api/requirements.txt"
echo "   pip install -r storage-service/requirements.txt"
echo "   pip install -r executor-service/requirements.txt"
echo ""
echo "2. Test the frontend type generation:"
echo "   cd frontend && npm run generate-types"
echo ""
echo "3. Run the GitHub Actions workflow locally (requires act):"
echo "   act -W .github/workflows/generate-openapi-spec.yml"