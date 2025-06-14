#!/bin/bash
# Clean up api folder and fix imports

echo "🧹 Cleaning up api folder"
echo "========================"

cd src/api

# 1. Remove duplicate handler files
echo "1. Removing duplicate handler files..."
rm -rf handlers/
echo "   ✓ Removed handlers/ folder (contained duplicates)"

# 2. Handle empty routes folder
echo -e "\n2. Handling routes folder..."
if [ -z "$(ls -A routes 2>/dev/null)" ]; then
    echo "   Adding README to explain routes folder purpose..."
    cat > routes/README.md << 'EOF'
# API Routes

This folder is reserved for route definitions when the API grows.

## Future Structure

```
routes/
├── evaluation.py    # Evaluation endpoints
├── monitoring.py    # Monitoring/metrics endpoints
├── admin.py        # Admin endpoints
└── health.py       # Health check endpoints
```

## Example Route Module

```python
from typing import List
from ..api import APIHandler, APIRequest, APIResponse

class EvaluationRoutes:
    def __init__(self, handler: APIHandler):
        self.handler = handler
    
    def get_routes(self) -> List[tuple]:
        return [
            ('POST', '/evaluate', self.handle_evaluate),
            ('GET', '/evaluate/{eval_id}', self.get_evaluation),
            ('GET', '/evaluations', self.list_evaluations),
        ]
    
    async def handle_evaluate(self, request: APIRequest) -> APIResponse:
        return await self.handler.handle_request(request)
```

Currently, all routes are defined in the main api.py file.
EOF
    echo "   ✓ Added routes/README.md"
fi

# 3. Move openapi_validator.py from shared to api
echo -e "\n3. Moving openapi_validator.py to api folder..."
if [ -f "../shared/openapi_validator.py" ]; then
    mv ../shared/openapi_validator.py .
    echo "   ✓ Moved openapi_validator.py to api/"
    
    # Fix imports in openapi_validator.py
    echo "   Fixing imports in openapi_validator.py..."
    sed -i.bak 's|from \.base import TestableComponent|from ..shared.base import TestableComponent|' openapi_validator.py
    sed -i.bak 's|from \.api import|from .api import|' openapi_validator.py
    rm -f openapi_validator.py.bak
    echo "   ✓ Fixed imports"
fi

# 4. Update shared/__init__.py to remove openapi_validator import
echo -e "\n4. Updating shared/__init__.py..."
cat > ../shared/__init__.py << 'EOF'
"""Shared components and utilities used across all services"""

from .base import TestableComponent

# Optional imports for future microservices
try:
    from .service_registry import ServiceRegistry
except ImportError:
    ServiceRegistry = None

__all__ = [
    'TestableComponent',
    'ServiceRegistry'
]
EOF
echo "   ✓ Updated shared/__init__.py"

# 5. Update api/__init__.py to export everything
echo -e "\n5. Updating api/__init__.py..."
cat > __init__.py << 'EOF'
"""API module - handles evaluation requests and responses"""

from .api import (
    APIService,
    APIHandler,
    APIRequest,
    APIResponse,
    HTTPMethod,
    create_api_service,
    create_api_handler
)

# OpenAPI validation is optional
try:
    from .openapi_validator import OpenAPIValidator
except ImportError:
    OpenAPIValidator = None

__all__ = [
    'APIService',
    'APIHandler',
    'APIRequest',
    'APIResponse',
    'HTTPMethod',
    'create_api_service',
    'create_api_handler',
    'OpenAPIValidator'
]
EOF
echo "   ✓ Updated __init__.py"

# 6. Update core/components.py to import from new location
echo -e "\n6. Updating core/components.py imports..."
cd ../core
sed -i.bak 's|from future_services\.api_gateway\.api import|from api.api import|' components.py
rm -f components.py.bak

# Also update the OpenAPIValidator import
sed -i.bak 's|from shared\.openapi_validator import OpenAPIValidator|from api.openapi_validator import OpenAPIValidator|' components.py
rm -f components.py.bak
echo "   ✓ Updated imports in components.py"

echo -e "\n✅ API folder cleanup complete!"
echo -e "\nSummary:"
echo "  - Removed duplicate handlers/"
echo "  - Added documentation to routes/"
echo "  - Moved openapi_validator.py to api/ (where it belongs)"
echo "  - Updated all imports"
echo -e "\nThe api folder now contains:"
echo "  - api.py (main implementation)"
echo "  - openapi_validator.py (API validation)"
echo "  - routes/ (future route definitions)"