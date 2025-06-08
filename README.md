# METR Evaluation Platform

> ⚠️ **PRIVATE REPOSITORY** - Contains sensitive interview preparation materials. See [SECURITY.md](SECURITY.md) before making any visibility changes.

A demonstration platform showcasing secure AI model evaluation infrastructure, designed with safety and scalability in mind.

## Overview

This project demonstrates platform engineering skills relevant to AI safety evaluation infrastructure, including:

- **Secure containerized evaluation environments** using Kubernetes and gVisor
- **Real-time monitoring dashboard** with React/TypeScript frontend
- **High-performance async API** with FastAPI backend
- **Comprehensive security architecture** with defense-in-depth approach
- **Scalable orchestration system** for managing evaluation workloads

## Architecture

See [architecture.md](architecture.md) for detailed system design, including:
- Component interaction diagrams
- Security boundaries and isolation
- Scaling strategies
- Technology choices and trade-offs

## Project Structure

```
metr-eval-platform/
├── frontend/          # React TypeScript dashboard
├── src/              # Python backend services
│   ├── api/          # FastAPI gateway
│   ├── evaluator/    # Evaluation orchestration
│   └── monitor/      # Safety monitoring
├── k8s/              # Kubernetes manifests
├── scripts/          # Deployment and utility scripts
├── tests/            # Comprehensive test suite
└── docs/             # Additional documentation
```

## Key Features

### Security & Isolation
- Container runtime security with gVisor
- Network policies for complete isolation
- Resource limits and quotas
- Comprehensive audit logging

### Monitoring & Observability
- Real-time evaluation progress tracking
- Resource utilization dashboards
- Safety alert system
- Distributed tracing with OpenTelemetry

### Scalability
- Horizontal pod autoscaling
- Queue-based job distribution
- Multi-region deployment ready
- Efficient caching strategies

## Development

### Prerequisites

- Docker Desktop or Docker Engine
- Kubernetes (minikube/kind for local development)
- Python 3.11+
- Node.js 18+
- kubectl CLI

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd metr-eval-platform
   ```

2. Set up the development environment:
   ```bash
   # Backend
   cd src
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt

   # Frontend
   cd ../frontend
   npm install
   ```

3. Run locally:
   ```bash
   # Start backend
   cd src
   uvicorn api.main:app --reload

   # Start frontend (new terminal)
   cd frontend
   npm start
   ```

See [DEVELOPMENT_ENVIRONMENT_CHECKLIST.md](DEVELOPMENT_ENVIRONMENT_CHECKLIST.md) for detailed setup instructions.

## Testing

```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Integration tests
pytest tests/integration/ -v
```

## Documentation

- [Architecture Overview](architecture.md) - System design and component details
- [Development Environment](DEVELOPMENT_ENVIRONMENT_CHECKLIST.md) - Setup guide
- [Docker Configuration](docker/README.md) - Container details
- [API Documentation](http://localhost:8000/docs) - Auto-generated OpenAPI docs (when running)

## Security Considerations

This platform is designed with security as a primary concern:

- All evaluation workloads run in isolated containers
- Network egress is strictly controlled
- Comprehensive monitoring for anomalous behavior
- Emergency stop procedures for all evaluations

## License

Copyright (c) 2024. All rights reserved.

---

**Note**: This is a demonstration project for showcasing platform engineering skills. For production use, additional security hardening and compliance measures would be required.