#!/bin/bash
# Reorganize platform folder and fix imports

echo "🔧 Reorganizing platform folder"
echo "=============================="

cd src

# 1. Move platform.py from shared to platform
echo "1. Moving platform.py from shared/ to platform/..."
if [ -f "shared/platform.py" ]; then
    mv shared/platform.py platform/
    echo "   ✓ Moved platform.py to platform folder"
else
    echo "   ❌ shared/platform.py not found"
fi

# 2. Update shared/__init__.py to remove platform import
echo -e "\n2. Updating shared/__init__.py..."
cat > shared/__init__.py << 'EOF'
"""Shared components and utilities used across all services"""

from .base import TestableComponent
from .openapi_validator import OpenAPIValidator

# Optional imports for future microservices
try:
    from .service_registry import ServiceRegistry
except ImportError:
    ServiceRegistry = None

__all__ = [
    'TestableComponent',
    'OpenAPIValidator',
    'ServiceRegistry'
]
EOF
echo "   ✓ Updated shared/__init__.py"

# 3. Update components.py with better import structure
echo -e "\n3. Updating components.py with proper imports..."
cat > platform/components.py << 'EOF'
"""
Components import helper for the platform

This module provides a clean import interface for all platform components,
handling the path setup and providing a single place to manage imports.
This is a common pattern in Python projects (similar to Django's shortcuts).
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import from sibling directories
sys.path.insert(0, str(Path(__file__).parent.parent))

# Core platform classes (now local)
from .platform import EvaluationPlatform, QueuedEvaluationPlatform

# Execution engines
from execution_engine.execution import (
    ExecutionEngine,
    SubprocessEngine,
    DockerEngine,
    GVisorEngine
)

# Monitoring
from monitoring.monitoring import (
    MonitoringService,
    AdvancedMonitor
)

# Queue
from queue.queue import (
    TaskQueue
)

# Storage
from storage.storage import (
    StorageService,
    FileStorage,
    InMemoryStorage
)

# Event Bus
from event_bus.events import (
    EventBus,
    EventTypes
)

# Web Frontend
from web_frontend.web_frontend import (
    create_frontend,
    FrontendConfig,
    FrontendType,
    SimpleHTTPFrontend,
    AdvancedHTMLFrontend,
    FlaskFrontend,
    FastAPIFrontend,
    ReactFrontend
)

# Shared utilities
from shared.base import TestableComponent
from shared.openapi_validator import OpenAPIValidator

# API components (from future-services for now)
try:
    from future_services.api_gateway.api import (
        create_api_service,
        create_api_handler
    )
except ImportError:
    # Fallback for API components
    def create_api_service(*args, **kwargs):
        raise NotImplementedError("API Gateway not available")
    
    def create_api_handler(*args, **kwargs):
        raise NotImplementedError("API Gateway not available")

# Re-export everything
__all__ = [
    # Platform
    'EvaluationPlatform',
    'QueuedEvaluationPlatform',
    'TestableComponent',
    # Execution
    'ExecutionEngine',
    'SubprocessEngine',
    'DockerEngine',
    'GVisorEngine',
    # Monitoring
    'MonitoringService',
    'AdvancedMonitor',
    # Queue
    'TaskQueue',
    # Storage
    'StorageService',
    'FileStorage',
    'InMemoryStorage',
    # Events
    'EventBus',
    'EventTypes',
    # Frontend
    'create_frontend',
    'FrontendConfig',
    'FrontendType',
    'SimpleHTTPFrontend',
    'AdvancedHTMLFrontend',
    'FlaskFrontend',
    'FastAPIFrontend',
    'ReactFrontend',
    # API
    'create_api_service',
    'create_api_handler',
    # Utilities
    'OpenAPIValidator',
]
EOF
echo "   ✓ Updated components.py"

# 4. Update extreme_mvp_frontier_events.py imports if needed
echo -e "\n4. Checking extreme_mvp_frontier_events.py imports..."
if grep -q "from components import" platform/extreme_mvp_frontier_events.py; then
    echo "   ℹ️  extreme_mvp_frontier_events.py already uses components import (good!)"
else
    echo "   ⚠️  You may need to update imports in extreme_mvp_frontier_events.py"
fi

# 5. Update platform.py imports to work in new location
echo -e "\n5. Fixing imports in platform.py..."
if [ -f "platform/platform.py" ]; then
    # Fix the import from shared.base
    sed -i.bak 's/from \.base import TestableComponent/from ..shared.base import TestableComponent/' platform/platform.py
    rm -f platform/platform.py.bak
    echo "   ✓ Fixed imports in platform.py"
fi

echo -e "\n✅ Platform reorganization complete!"
echo -e "\nSummary:"
echo "  - Moved platform.py from shared/ to platform/"
echo "  - Updated components.py as import helper (common pattern)"
echo "  - Fixed import paths throughout"
echo -e "\nThe import helper pattern in components.py:"
echo "  - Provides clean imports: 'from components import ...'"
echo "  - Single place to manage paths"
echo "  - Handles optional dependencies"
echo "  - Common in frameworks like Django, Flask, FastAPI"