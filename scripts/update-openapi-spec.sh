#!/bin/bash
# Update OpenAPI specification from FastAPI app

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "🔄 Updating OpenAPI specification..."

cd "$PROJECT_ROOT"

# Run the export script
python api/scripts/export-openapi-spec.py

echo "
✅ OpenAPI spec updated!

Next steps:
1. Review the changes to api/openapi.yaml
2. Regenerate frontend types: cd frontend && npm run generate-types
3. Commit both the spec and generated types
"