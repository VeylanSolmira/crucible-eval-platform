# Crucible Evaluation Platform (CEP)

A secure, scalable platform for AI model evaluation, designed with safety and extensibility at its core. Crucible provides organizations with the infrastructure needed to safely evaluate AI systems while maintaining strict security boundaries and comprehensive monitoring.

## Project Vision

The Crucible Evaluation Platform (CEP) is designed to:
- **Democratize AI safety evaluation** by providing a deployable platform
- **Enable distributed safety research** across multiple organizations
- **Maintain security standards** while being open and extensible
- **Lower barriers to entry** for AI safety evaluation work

This open-source platform enables decentralized AI safety evaluation, allowing multiple organizations to deploy and customize their own evaluation infrastructure while maintaining consistent security standards.

## Overview

Crucible provides a complete AI safety evaluation platform featuring:

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
crucible-eval-platform/
├── api/                    # FastAPI backend service
├── frontend/               # React TypeScript dashboard
├── dispatcher_service/     # Job dispatching service
├── celery_worker/          # Async task processing
├── cleanup_controller/     # Resource cleanup service
├── storage_service/        # File storage management
├── monitoring/             # Monitoring and metrics
├── nginx/                  # Web server configuration
├── k8s/                    # Kubernetes manifests
├── infrastructure/         # Terraform/OpenTofu IaC
├── scripts/                # Deployment and utility scripts
├── tests/                  # Comprehensive test suite
├── docs/                   # Documentation
└── evaluation-environments/ # Docker environments for evaluations
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

## Development Approach: Iterative Buildup

This project uses a unique "iterative buildup" approach that mirrors real architectural thinking, guided by the TRACE-AI decision framework.

### TRACE-AI Framework

We evaluate each technical decision using TRACE-AI:

- **T**ime to feedback - How quickly do we need user validation?
- **R**eversibility cost - How expensive is it to change later?
- **A**bstraction possibility - Can we hide this decision behind an interface?
- **C**ore vs peripheral - Is this central to our value proposition?
- **E**xpertise required - Do we have the skills to maintain it?
- **AI** **F**ungibility - How easily can AI tools help us migrate?

This framework helps us make pragmatic MVP decisions while avoiding architectural dead ends. See [mvp-technical-debt-framework.md](docs/mvp-technical-debt-framework.md) for detailed methodology.

### Extreme MVP Philosophy

We embrace "extreme MVP" - shipping the simplest possible implementation to learn quickly:

```bash
# Start with the extreme MVP (single file, zero dependencies!)
python evolution/extreme_mvp.py
# Then evolve based on real learnings - see evolution/ directory
```

### Level-Based Development

We develop the system in progressive levels, tagging each stage:

```bash
# View all levels
git tag -l "level*"

# Checkout a specific level
git checkout level3-workflow

# Return to latest
git checkout main
```

### Levels:
1. **level1-understanding**: Problem statement and core requirements
2. **level2-vocabulary**: Domain terminology and definitions  
3. **level3-workflow**: Basic system workflow (async, monitoring)
4. **level4-tools**: Technology selection using TRACE-AI framework
5. **level5-mvp**: Minimal working implementation
6. **level6-engine**: Core evaluation engine
7. **level7-integrations**: External integrations (Slack, Airtable)
8. **level8-monitoring**: Observability dashboard
9. **level9-security**: Production hardening
10. **level10-enterprise**: Multi-tenancy and scale

Each level applies TRACE-AI to make decisions appropriate to that stage of maturity.

### Working with Levels

During development:
```bash
# Complete work on a level
git add .
git commit -m "Level 3: Establish async workflow with monitoring"
git tag level3-workflow
```

For demos/presentation:
```bash
# Export a specific level for side-by-side comparison
git archive level3-workflow --prefix=demo/level3/ | tar -x

# Or simply checkout different levels during presentation
git checkout level2-vocabulary
```

### Handling Updates to Earlier Levels

If you discover issues in earlier levels:
1. **Document it**: Note in the current level that this issue exists
2. **Fix forward**: Fix in current code and note when it was discovered
3. **Optional**: Create versioned tags (`level3-v2`) if significant changes

This approach shows realistic architectural evolution!

## Development

### Prerequisites

- Docker Desktop or Docker Engine
- Python 3.11+
- Kubernetes cluster (Docker Desktop, Kind, or similar)
- kubectl configured to access your cluster
- Node.js 18+
- kubectl CLI
- Kubernetes (minikube/kind for local development)
- gVisor (optional but recommended) - See [gVisor Setup Guide](docs/gvisor-setup-guide.md)

### Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd crucible-eval-platform
   ```

2. Set up the local development environment:
   ```bash
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies (for linting, testing, OpenAPI generation)
   pip install -r requirements-dev.txt
   ```

3. Start the platform:
   ```bash
   # This script will:
   # - Check/create virtual environment and install dependencies
   # - Create Kind cluster if needed
   # - Build base Docker image
   # - Generate OpenAPI specs
   # - Start all services with Skaffold
   ./start-platform.sh --skip-tests --no-browser
   ```

4. Access the services:
   - Frontend: http://localhost:3000
   - API: http://localhost:8080
   - API Docs: http://localhost:8080/docs

### Development Commands

```bash
# Linting
ruff check .
mypy src/

# Testing
pytest tests/ -v

# OpenAPI generation (run after API changes)
./scripts/generate-all-openapi-specs.sh
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

## Infrastructure Deployment

The platform uses OpenTofu (open-source Terraform alternative) for infrastructure deployment, chosen for its state encryption capabilities - particularly important for adversarial AI testing environments.

```bash
# Install OpenTofu
brew install opentofu

# Deploy infrastructure
cd infrastructure/terraform
tofu init
tofu plan
tofu apply
```

See:
- [EC2 Deployment Guide](docs/ec2-deployment-guide.md) for detailed instructions
- [OpenTofu vs Terraform](docs/opentofu-vs-terraform.md) for why we chose OpenTofu

## Documentation

- [Architecture Overview](architecture.md) - System design and component details
- [Development Environment](DEVELOPMENT_ENVIRONMENT_CHECKLIST.md) - Setup guide
- [Docker Configuration](docker/README.md) - Container details
- [API Documentation](http://localhost:8000/docs) - Auto-generated OpenAPI docs (when running)
- [gVisor Setup Guide](docs/gvisor-setup-guide.md) - Production runtime configuration
- [Adversarial Testing Requirements](docs/adversarial-testing-requirements.md) - Security requirements for AI testing

## Security Considerations

This platform is designed with security as a primary concern:

- All evaluation workloads run in isolated containers
- **gVisor runtime** provides additional kernel-level isolation (see [gVisor Setup Guide](docs/gvisor-setup-guide.md))
- Network egress is completely disabled for evaluation containers
- Non-root user execution (nobody:nogroup)
- Read-only filesystems with minimal writable /tmp
- Resource limits enforced (CPU/memory)
- Comprehensive monitoring for anomalous behavior
- Emergency stop procedures for all evaluations

For production deployments evaluating untrusted AI models, gVisor is strongly recommended to provide defense-in-depth against container escape attempts.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with security patterns inspired by leading AI safety organizations
- Uses gVisor for enhanced container isolation
- Monitoring architecture based on cloud-native best practices