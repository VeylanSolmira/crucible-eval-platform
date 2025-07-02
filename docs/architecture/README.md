# Architecture Documentation

Welcome to the Crucible Platform architecture documentation. The documentation is organized into logical categories for easier navigation.

## 📁 Documentation Structure

### [Core Architecture](./core/)
Fundamental architecture documentation including platform overview, system evolution, and core design decisions.
- Platform architecture guide
- System evolution from monolith to microservices
- Architecture abstraction decisions

### [Microservices](./microservices/)
Event-driven architecture, service communication patterns, and microservice design.
- Event bus and event-driven patterns
- Service boundaries and modularization
- Queue worker architecture

### [Celery Integration](./celery/)
Everything related to Celery task queue integration and migration strategy.
- Migration from custom queue to Celery
- Task management and retry logic
- Monitoring with Flower

### [Docker & Containerization](./docker/)
Container security, networking, and deployment patterns.
- Docker socket proxy security
- Container networking strategies
- Non-root container patterns

### [Storage Architecture](./storage/)
Storage service design and data persistence patterns.
- Storage service API and patterns
- Event-driven storage updates
- Storage worker design

### [Security](./security/)
Security considerations and implementations.
- Secure code execution sandboxing
- Security model comparisons
- Pragmatic security decisions

### [Monitoring & Observability](./monitoring/)
Monitoring, logging, and real-time tracking.
- Unified monitoring strategy
- Real-time execution tracking
- Future observability plans

### [Design Patterns](./patterns/)
Common patterns, design decisions, and best practices.
- Architectural patterns (TRACE-AI)
- API design considerations
- Memory optimization strategies

### [Deployment & Infrastructure](./deployment/)
Deployment strategies, orchestration, and scaling.
- Kubernetes vs managed services
- Service discovery patterns
- Horizontal scaling strategies

## 🚀 Quick Start

1. **New to the project?** Start with [Core Architecture](./core/)
2. **Working on a service?** Check [Microservices](./microservices/)
3. **Deploying to production?** See [Deployment](./deployment/)
4. **Security concerns?** Review [Security](./security/)

## 📖 Key Documents

- [Platform Architecture](./core/PLATFORM_ARCHITECTURE.md) - Comprehensive architecture guide
- [System Evolution](./core/system-evolution.md) - How we got here
- [Celery Migration Strategy](./celery/celery-migration-strategy.md) - Current migration effort
- [Docker Socket Proxy Security](./docker/docker-socket-proxy-security.md) - Container security model

## 🔄 Architecture Evolution

The platform has evolved through several stages:
1. **Monolithic** - Single Python application
2. **Modular Monolith** - Separated concerns within monolith
3. **Microservices** - Event-driven service architecture
4. **Hybrid** - Celery for tasks, microservices for API

Each stage is documented with rationale for changes and lessons learned.