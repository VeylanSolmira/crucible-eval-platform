#!/bin/bash
# Update each service's requirements.txt based on actual needs

echo "📦 Updating service requirements based on actual usage"
echo "===================================================="

# Execution Engine - needs Docker interaction
echo "1. Execution Engine"
cat > src/execution-engine/requirements.txt << 'EOF'
# Execution engine - runs code in isolated environments
# No web framework needed if used as a library
# Add these only if running as standalone service:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
EOF

# Event Bus - just Python, no external deps for basic version
echo "2. Event Bus"
cat > src/event-bus/requirements.txt << 'EOF'
# Event bus - coordinates events between components
# Basic implementation uses only Python stdlib
# Add these for WebSocket support:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
# websockets==12.0
EOF

# Monitoring - needs prometheus client
echo "3. Monitoring"
cat > src/monitoring/requirements.txt << 'EOF'
# Monitoring - collects and exports metrics
prometheus-client==0.19.0
# Add these only if running as standalone service:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
EOF

# Queue - just Python for in-memory version
echo "4. Queue"
cat > src/queue/requirements.txt << 'EOF'
# Queue - manages task queue
# Basic in-memory implementation uses only Python stdlib
# For production, consider:
# celery==5.3.4
# redis==5.0.1
# Add these only if running as standalone service:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
EOF

# Storage - just Python for filesystem version
echo "5. Storage"
cat > src/storage/requirements.txt << 'EOF'
# Storage - handles persistent storage
# Basic filesystem implementation uses only Python stdlib
# For cloud storage:
# boto3==1.29.7  # For S3
# Add these only if running as standalone service:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
EOF

# Web Frontend - needs web framework
echo "6. Web Frontend"
cat > src/web-frontend/requirements.txt << 'EOF'
# Web frontend - serves UI
# For Flask support:
# flask==3.0.0
# For FastAPI support:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
# For basic HTTP server, no deps needed (uses Python stdlib)
EOF

# Security Scanner - needs component imports
echo "7. Security Scanner"
cat > src/security-scanner/requirements.txt << 'EOF'
# Security scanner - runs security tests
# Needs access to execution engines
# No additional requirements if importing from platform
# Add these only if running as standalone service:
# fastapi==0.104.1
# uvicorn[standard]==0.24.0
EOF

# Platform (monolithic) - needs everything
echo "8. Platform (Monolithic)"
cat > src/platform/requirements.txt << 'EOF'
# Platform - monolithic version with all components

# Core web framework (choose one)
# For basic operation:
# (no requirements - uses Python stdlib HTTP server)

# For Flask support:
# flask==3.0.0

# For FastAPI support:
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Optional features:
# prometheus-client==0.19.0  # For monitoring
# openapi-core==0.18.2  # For OpenAPI validation
# pydantic==2.5.0  # For data validation (required by FastAPI)

# For production deployments:
# gunicorn==21.2.0
# python-multipart==0.0.6  # For file uploads
EOF

# Lambda - needs AWS SDK
echo "9. Lambda"
cat > src/lambda/requirements.txt << 'EOF'
# Lambda functions - AWS serverless
boto3==1.29.7
# Note: boto3 is provided by Lambda runtime, but good for local testing
EOF

# API Gateway (in future-services)
echo "10. API Gateway (Future)"
cat > src/future-services/api-gateway/requirements.txt << 'EOF'
# API Gateway - RESTful API service
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
# For OpenAPI support:
# openapi-core==0.18.2
# For authentication:
# python-jose[cryptography]==3.3.0
# passlib[bcrypt]==1.7.4
EOF

echo ""
echo "✅ Requirements updated!"
echo ""
echo "📋 Summary:"
echo "- Most services don't need web frameworks if used as libraries"
echo "- Web frameworks only needed when running as standalone services"
echo "- Platform (monolithic) needs the most dependencies"
echo "- Many services can run with just Python stdlib"
echo ""
echo "💡 To install for monolithic platform:"
echo "   cd src/platform && pip install -r requirements.txt"