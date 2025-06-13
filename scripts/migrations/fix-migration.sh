#!/bin/bash
# Fix migration - properly move components to their service directories

set -e

echo "🔧 Fixing migration - moving components to proper services"
echo "========================================================"

# Remove the incorrectly copied components from platform
rm -rf src/platform/components src/platform/security_scenarios

# Move execution engine components
echo "📦 Moving execution engine components..."
if [ -f "evolution/components/execution.py" ]; then
    cp evolution/components/execution.py src/execution-engine/engines/base.py
    
    # Extract engine classes from execution.py
    python3 << 'EOF'
import re

# Read the execution.py file
with open('evolution/components/execution.py', 'r') as f:
    content = f.read()

# Extract SubprocessEngine class
subprocess_match = re.search(r'(class SubprocessEngine.*?)(?=class|\Z)', content, re.DOTALL)
if subprocess_match:
    with open('src/execution-engine/engines/subprocess.py', 'w') as f:
        f.write('"""Subprocess execution engine"""\n')
        f.write('from .base import ExecutionEngine\n\n')
        f.write(subprocess_match.group(1))

# Extract DockerEngine class
docker_match = re.search(r'(class DockerEngine.*?)(?=class|\Z)', content, re.DOTALL)
if docker_match:
    with open('src/execution-engine/engines/docker.py', 'w') as f:
        f.write('"""Docker execution engine"""\n')
        f.write('from .base import ExecutionEngine\n')
        f.write('import subprocess\n')
        f.write('import tempfile\n')
        f.write('import os\n')
        f.write('import json\n')
        f.write('from typing import Dict, Any\n\n')
        f.write(docker_match.group(1))

# Extract GVisorEngine class
gvisor_match = re.search(r'(class GVisorEngine.*?)(?=class|\Z)', content, re.DOTALL)
if gvisor_match:
    with open('src/execution-engine/engines/gvisor.py', 'w') as f:
        f.write('"""gVisor execution engine"""\n')
        f.write('from .docker import DockerEngine\n')
        f.write('import platform\n')
        f.write('from typing import Dict, Any\n\n')
        f.write(gvisor_match.group(1))
EOF
fi

# Move API components
echo "📦 Moving API components..."
if [ -f "evolution/components/api.py" ]; then
    cp evolution/components/api.py src/api-gateway/handlers/base.py
fi

# Move monitoring components
echo "📦 Moving monitoring components..."
if [ -f "evolution/components/monitoring.py" ]; then
    cp evolution/components/monitoring.py src/monitoring/collectors/base.py
fi

# Move storage components
echo "📦 Moving storage components..."
if [ -f "evolution/components/storage.py" ]; then
    cp evolution/components/storage.py src/storage/backends/base.py
fi

# Move queue components
echo "📦 Moving queue components..."
if [ -f "evolution/components/queue.py" ]; then
    cp evolution/components/queue.py src/queue/handlers/base.py
fi

# Move web frontend components
echo "📦 Moving web frontend components..."
if [ -f "evolution/components/web_frontend.py" ]; then
    cp evolution/components/web_frontend.py src/web-frontend/base.py
fi

# Move event bus components
echo "📦 Moving event bus components..."
if [ -f "evolution/components/events.py" ]; then
    cp evolution/components/events.py src/event-bus/handlers/base.py
    # Also create the Dockerfile and main.py for event-bus
    cat > src/event-bus/Dockerfile << 'EOFD'
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
EOFD
fi

# Move shared components
echo "📦 Moving shared components..."
if [ -f "evolution/components/base.py" ]; then
    cp evolution/components/base.py src/shared/utils/base_component.py
fi

if [ -f "evolution/components/platform.py" ]; then
    cp evolution/components/platform.py src/shared/utils/platform.py
fi

# Move security scenarios
echo "📦 Moving security scenarios..."
if [ -d "evolution/security_scenarios" ]; then
    cp -r evolution/security_scenarios/* src/security-scanner/scenarios/
fi

# Move OpenAPI validator to shared
if [ -f "evolution/components/openapi_validator.py" ]; then
    cp evolution/components/openapi_validator.py src/shared/utils/openapi_validator.py
fi

# Create __init__.py files for all packages
echo "📦 Creating __init__.py files..."
for dir in src/*/; do
    if [ -d "$dir" ] && [ "$dir" != "src/k8s/" ]; then
        touch "$dir/__init__.py"
    fi
done

# For the platform monolith, we'll create a components symlink
echo "🔗 Creating symlink for platform monolith..."
cd src/platform
ln -sf ../execution-engine/engines engines
ln -sf ../api-gateway/handlers api_handlers
ln -sf ../monitoring/collectors monitoring
ln -sf ../storage/backends storage
ln -sf ../queue/handlers queue
ln -sf ../web-frontend web_frontend
ln -sf ../event-bus/handlers event_bus
ln -sf ../security-scanner/scenarios security_scenarios
ln -sf ../shared shared

# Create a components module that imports from all services
cat > components.py << 'EOF'
"""
Components module for monolithic platform
Imports from all service directories to maintain backward compatibility
"""

# Execution engines
from engines.subprocess import SubprocessEngine
from engines.docker import DockerEngine
from engines.gvisor import GVisorEngine

# Monitoring
from monitoring.base import AdvancedMonitor

# Queue
from queue.base import TaskQueue

# Storage
from storage.base import FileStorage, InMemoryStorage

# Platform
from shared.utils.platform import QueuedEvaluationPlatform

# API
from api_handlers.base import create_api_service, create_api_handler

# Web Frontend
from web_frontend.base import (
    create_frontend,
    FrontendConfig,
    SimpleHTTPFrontend,
    AdvancedHTMLFrontend,
    FlaskFrontend,
    FastAPIFrontend,
    ReactFrontend
)

# Event Bus
from event_bus.base import EventBus

# OpenAPI Validator
try:
    from shared.utils.openapi_validator import OpenAPIValidator
except ImportError:
    OpenAPIValidator = None

__all__ = [
    'SubprocessEngine',
    'DockerEngine', 
    'GVisorEngine',
    'AdvancedMonitor',
    'TaskQueue',
    'FileStorage',
    'InMemoryStorage',
    'QueuedEvaluationPlatform',
    'create_api_service',
    'create_api_handler',
    'create_frontend',
    'FrontendConfig',
    'SimpleHTTPFrontend',
    'AdvancedHTMLFrontend',
    'FlaskFrontend',
    'FastAPIFrontend',
    'ReactFrontend',
    'EventBus',
    'OpenAPIValidator'
]
EOF

cd ../..

echo "✅ Migration fixed!"
echo ""
echo "📋 Summary:"
echo "  - Components properly distributed to service directories"
echo "  - Platform directory has symlinks for monolithic operation"
echo "  - Each service has its core components"
echo ""
echo "🚀 Next steps:"
echo "  1. Test monolithic: cd src/platform && python extreme_mvp_frontier_events.py --help"
echo "  2. Test services: cd src && docker-compose up"
echo "  3. Remove evolution directory: rm -rf evolution"