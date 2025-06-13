#!/bin/bash
# Properly move all files from evolution/ to their correct locations

set -e

echo "🚚 Moving all files from evolution/ to proper locations"
echo "====================================================="

# Check if evolution directory exists
if [ ! -d "evolution" ]; then
    echo "❌ Error: evolution/ directory not found"
    exit 1
fi

# 1. Move components to their service directories
echo "📦 Moving component files to service directories..."

# Execution engine
if [ -f "evolution/components/execution.py" ]; then
    echo "  - Moving execution.py to execution-engine service"
    mv evolution/components/execution.py src/execution-engine/execution.py
fi

# API
if [ -f "evolution/components/api.py" ]; then
    echo "  - Moving api.py to api-gateway service"
    mv evolution/components/api.py src/api-gateway/api.py
fi

# Monitoring
if [ -f "evolution/components/monitoring.py" ]; then
    echo "  - Moving monitoring.py to monitoring service"
    mv evolution/components/monitoring.py src/monitoring/monitoring.py
fi

# Storage
if [ -f "evolution/components/storage.py" ]; then
    echo "  - Moving storage.py to storage service"
    mv evolution/components/storage.py src/storage/storage.py
fi

# Queue
if [ -f "evolution/components/queue.py" ]; then
    echo "  - Moving queue.py to queue service"
    mv evolution/components/queue.py src/queue/queue.py
fi

# Web Frontend
if [ -f "evolution/components/web_frontend.py" ]; then
    echo "  - Moving web_frontend.py to web-frontend service"
    mv evolution/components/web_frontend.py src/web-frontend/web_frontend.py
fi

# Event Bus
if [ -f "evolution/components/events.py" ]; then
    echo "  - Moving events.py to event-bus service"
    mv evolution/components/events.py src/event-bus/events.py
fi

# Platform
if [ -f "evolution/components/platform.py" ]; then
    echo "  - Moving platform.py to shared"
    mv evolution/components/platform.py src/shared/platform.py
fi

# Base component
if [ -f "evolution/components/base.py" ]; then
    echo "  - Moving base.py to shared"
    mv evolution/components/base.py src/shared/base.py
fi

# OpenAPI validator
if [ -f "evolution/components/openapi_validator.py" ]; then
    echo "  - Moving openapi_validator.py to shared"
    mv evolution/components/openapi_validator.py src/shared/openapi_validator.py
fi

# Components __init__.py
if [ -f "evolution/components/__init__.py" ]; then
    echo "  - Moving components __init__.py to shared"
    mv evolution/components/__init__.py src/shared/components_init.py
fi

# 2. Move security scenarios
echo "📦 Moving security scenarios..."
if [ -d "evolution/security_scenarios" ]; then
    mv evolution/security_scenarios/* src/security-scanner/scenarios/
    rmdir evolution/security_scenarios
fi

# 3. Move main platform files
echo "📦 Moving main platform files..."
mv evolution/extreme_mvp_frontier_events.py src/platform/
mv evolution/run_demo_servers.py src/platform/ 2>/dev/null || true
mv evolution/run_security_demo.py src/platform/ 2>/dev/null || true
mv evolution/safe_security_check.py src/platform/ 2>/dev/null || true
mv evolution/test_components.py src/platform/ 2>/dev/null || true

# 4. Move reference implementations
echo "📦 Moving reference implementations..."
if [ -d "evolution/reference" ]; then
    mkdir -p src/reference
    mv evolution/reference/* src/reference/
    rmdir evolution/reference
fi

# 5. Move documentation from evolution/docs
echo "📦 Moving evolution documentation..."
if [ -d "evolution/docs" ]; then
    mkdir -p docs/evolution
    mv evolution/docs/* docs/evolution/
    rmdir evolution/docs
fi

# 6. Move other evolution files
echo "📦 Moving remaining evolution files..."
mv evolution/*.md docs/evolution/ 2>/dev/null || true
mv evolution/*.sh src/platform/scripts/ 2>/dev/null || true
mkdir -p src/platform/scripts
mv evolution/package_for_deployment.sh src/platform/scripts/ 2>/dev/null || true
mv evolution/quick_deploy.sh src/platform/scripts/ 2>/dev/null || true

# 7. Move test results and reports
echo "📦 Moving test results and reports..."
mkdir -p src/security-scanner/results
mv evolution/CONTAINER_SECURITY_REPORT.md src/security-scanner/results/ 2>/dev/null || true
mv evolution/security_test_results.json src/security-scanner/results/ 2>/dev/null || true
mv evolution/SAFE_SECURITY_CHECK.md src/security-scanner/results/ 2>/dev/null || true
mv evolution/safe_security_check.json src/security-scanner/results/ 2>/dev/null || true

# 8. Clean up components directory if empty
if [ -d "evolution/components" ]; then
    rmdir evolution/components 2>/dev/null || true
fi

# 9. Check if evolution is empty and can be removed
if [ -z "$(ls -A evolution 2>/dev/null)" ]; then
    echo "✅ Removing empty evolution directory"
    rmdir evolution
else
    echo "⚠️  Some files remain in evolution/:"
    ls -la evolution/
fi

# 10. Create proper imports for platform directory
echo "📦 Creating import structure for platform..."
cat > src/platform/components.py << 'EOF'
"""
Components module for platform - imports from service directories
This allows the monolithic platform to work with the distributed components
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import from sibling directories
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from service directories
from execution_engine.execution import SubprocessEngine, DockerEngine, GVisorEngine, ExecutionEngine
from monitoring.monitoring import AdvancedMonitor, MonitoringService
from queue.queue import TaskQueue, QueueService
from storage.storage import FileStorage, InMemoryStorage, StorageService
from api_gateway.api import create_api_service, create_api_handler, APIService, APIHandler
from web_frontend.web_frontend import (
    create_frontend, FrontendConfig, FrontendType,
    SimpleHTTPFrontend, AdvancedHTMLFrontend, 
    FlaskFrontend, FastAPIFrontend, ReactFrontend,
    WebFrontendService
)
from event_bus.events import EventBus, EventTypes
from shared.platform import QueuedEvaluationPlatform, EvaluationPlatform
from shared.openapi_validator import OpenAPIValidator

# For backward compatibility
def create_openapi_validated_api(*args, **kwargs):
    """Backward compatibility wrapper"""
    if OpenAPIValidator:
        return create_api_service(*args, **kwargs)
    return create_api_service(*args, **kwargs)

__all__ = [
    'SubprocessEngine', 'DockerEngine', 'GVisorEngine', 'ExecutionEngine',
    'AdvancedMonitor', 'MonitoringService',
    'TaskQueue', 'QueueService',
    'FileStorage', 'InMemoryStorage', 'StorageService',
    'create_api_service', 'create_api_handler', 'APIService', 'APIHandler',
    'create_frontend', 'FrontendConfig', 'FrontendType',
    'SimpleHTTPFrontend', 'AdvancedHTMLFrontend',
    'FlaskFrontend', 'FastAPIFrontend', 'ReactFrontend',
    'WebFrontendService',
    'EventBus', 'EventTypes',
    'QueuedEvaluationPlatform', 'EvaluationPlatform',
    'OpenAPIValidator',
    'create_openapi_validated_api'
]
EOF

# 11. Update imports in extreme_mvp_frontier_events.py
echo "📦 Updating imports in main platform file..."
sed -i.bak 's|from shared.utils import|from components import|g' src/platform/extreme_mvp_frontier_events.py
rm src/platform/extreme_mvp_frontier_events.py.bak

echo ""
echo "✅ Migration complete!"
echo ""
echo "📋 Summary:"
echo "  - All component files moved to their respective service directories"
echo "  - Reference implementations moved to src/reference/"
echo "  - Evolution docs moved to docs/evolution/"
echo "  - Security test results moved to src/security-scanner/results/"
echo "  - Platform scripts moved to src/platform/scripts/"
echo "  - Created proper import structure for monolithic platform"
echo ""
echo "📂 New structure:"
echo "  src/"
echo "  ├── execution-engine/     (execution.py)"
echo "  ├── api-gateway/         (api.py)"
echo "  ├── monitoring/          (monitoring.py)"
echo "  ├── storage/             (storage.py)"
echo "  ├── queue/               (queue.py)"
echo "  ├── web-frontend/        (web_frontend.py)"
echo "  ├── event-bus/           (events.py)"
echo "  ├── security-scanner/    (scenarios/)"
echo "  ├── platform/            (monolithic version)"
echo "  ├── reference/           (all reference implementations)"
echo "  └── shared/              (base classes and utilities)"
echo ""
echo "🧪 Test with:"
echo "  cd src/platform && python extreme_mvp_frontier_events.py --help"