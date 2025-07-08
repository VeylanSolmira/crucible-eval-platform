#!/bin/bash
# Shared script to generate OpenAPI specs for all services
# Used by both GitHub Actions and local development

set -e

echo "Generating OpenAPI specs for all services..."

# Services that need OpenAPI spec generation
SERVICES=(api storage-service executor-service)

# Track if all succeeded
all_success=true

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Determine which Python to use
if [ -n "$VIRTUAL_ENV" ]; then
    # Virtual environment is activated
    PYTHON_CMD="python"
    echo "Using Python from virtual environment: $VIRTUAL_ENV"
elif [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
    # Virtual environment exists but not activated
    PYTHON_CMD="$PROJECT_ROOT/venv/bin/python"
    echo "Using Python from $PROJECT_ROOT/venv/bin/python"
else
    # Fall back to system Python
    PYTHON_CMD="python"
    echo "Using system Python"
fi

for service in "${SERVICES[@]}"; do
    echo "📄 Generating $service spec..."
    
    # Check if export script exists
    if [ ! -f "$service/scripts/export-openapi-spec.py" ]; then
        echo "⚠️  No export script found for $service"
        continue
    fi
    
    # Generate the spec by running from the service directory
    # This allows 'from app import app' to work naturally
    # Include project root in PYTHONPATH for shared modules
    if (cd "$service" && PYTHONPATH=".:$PROJECT_ROOT" $PYTHON_CMD scripts/export-openapi-spec.py); then
        echo "✅ $service spec generated"
    else
        echo "❌ Failed to generate $service spec"
        all_success=false
    fi
done

if [ "$all_success" = true ]; then
    echo "✅ All OpenAPI specs generated successfully"
    exit 0
else
    echo "⚠️  Some specs failed to generate"
    exit 1
fi