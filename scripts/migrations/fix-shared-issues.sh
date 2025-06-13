#!/bin/bash
# Fix identified issues in shared folder

echo "🔧 Fixing shared folder issues"
echo "============================="

cd src/shared

# 1. Remove outdated components_init.py
echo "1. Removing outdated components_init.py..."
rm -f components_init.py
echo "   ✓ Removed components_init.py"

# 2. Add header to service_registry.py explaining it's for future use
echo "2. Updating service_registry.py with future use note..."
cat > service_registry_temp.py << 'EOF'
"""
Service Registry - Maintains service endpoints for microservices architecture

NOTE: This is for FUTURE use when the platform is split into microservices.
Currently, the platform runs as a monolith and doesn't use these endpoints.
The ports match those in docker-compose.yml.example.

When migrating to microservices, this could be enhanced with:
- Service discovery (Consul, etcd)
- Health checking
- Load balancing
- Dynamic registration
"""

SERVICES = {
    'execution-engine': 'http://localhost:8001',
    'api-gateway': 'http://localhost:8000',
    'monitoring': 'http://localhost:8002',
    'storage': 'http://localhost:8003',
    'queue': 'http://localhost:8004',
    'web-frontend': 'http://localhost:8080',
    'event-bus': 'http://localhost:8005',
    'security-scanner': 'http://localhost:8006',
}

def get_service_url(service_name: str) -> str:
    """Get service URL by name"""
    return SERVICES.get(service_name, 'http://localhost:8000')

# Future enhancement example:
class ServiceRegistry:
    """Dynamic service registry for production use"""
    def register(self, name: str, url: str, health_check: str = None):
        """Register a service with optional health check endpoint"""
        pass
    
    def discover(self, name: str) -> str:
        """Discover a healthy service instance"""
        pass
    
    def health_check_all(self):
        """Check health of all registered services"""
        pass
EOF
mv service_registry_temp.py service_registry.py
echo "   ✓ Added documentation header"

# 3. Rename platform.py to evaluation_platform.py to avoid confusion
echo "3. Renaming platform.py to avoid confusion with platform/ folder..."
mv platform.py evaluation_platform.py
echo "   ✓ Renamed to evaluation_platform.py"

# 4. Update __init__.py to reflect the rename
echo "4. Updating __init__.py imports..."
sed -i.bak 's/from \.platform import/from .evaluation_platform import/' __init__.py
rm -f __init__.py.bak
echo "   ✓ Updated imports"

# 5. Update any internal imports in the renamed file
echo "5. Checking evaluation_platform.py for self-references..."
sed -i.bak 's/from \.platform import/from .evaluation_platform import/' evaluation_platform.py 2>/dev/null || true
rm -f evaluation_platform.py.bak

# 6. Create a migration note
echo "6. Creating migration note..."
cat > PLATFORM_RENAME_NOTE.md << 'EOF'
# Platform Module Rename

The file `platform.py` has been renamed to `evaluation_platform.py` to avoid confusion with the `platform/` directory.

## Import Changes Required

If you get import errors, update:
```python
# Old
from shared.platform import EvaluationPlatform, QueuedEvaluationPlatform

# New
from shared.evaluation_platform import EvaluationPlatform, QueuedEvaluationPlatform
```

This affects files that import from shared, primarily in the platform/ directory.
EOF
echo "   ✓ Created migration note"

echo ""
echo "✅ Shared folder fixes complete!"
echo ""
echo "Summary:"
echo "  1. Removed outdated components_init.py"
echo "  2. Added documentation to service_registry.py"
echo "  3. Renamed platform.py → evaluation_platform.py"
echo "  4. Updated imports in __init__.py"
echo "  5. Created migration note"
echo ""
echo "⚠️  IMPORTANT: You may need to update imports in platform/components.py"
echo "   Check for: from shared.platform import ..."
echo "   Change to: from shared.evaluation_platform import ..."