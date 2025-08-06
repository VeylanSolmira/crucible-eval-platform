# Wiki Topics Analysis - Crucible Documentation

This document contains a comprehensive analysis of topics found across all Crucible documentation for wiki implementation.

## Documentation Overview

- **Total Files Scanned**: 204 markdown files
- **Directories**: `/docs`, `/frontend/docs`, `/infrastructure`
- **Existing Wiki Links**: 10+ already in use

## Core Topics by Category

### 1. Platform Core Concepts

| Topic                | Frequency | Description                                  |
| -------------------- | --------- | -------------------------------------------- |
| Crucible             | High      | The evaluation platform name                 |
| Crucible             | High      | Secure AI Model Evaluation Platform          |
| Evaluation/Evaluator | High      | Core functionality for running tests         |
| Executor Service     | High      | Service that runs evaluations                |
| Storage Service      | Medium    | Handles file/data persistence                |
| Monitoring Service   | Medium    | Real-time evaluation tracking                |
| Queue Worker         | Medium    | Job processing system                        |

### 2. Security & Isolation

| Topic               | Frequency | Description                       |
| ------------------- | --------- | --------------------------------- |
| Container Isolation | Very High | Security through containerization |
| gVisor/runsc        | High      | Userspace kernel for isolation    |
| Threat Model        | High      | Security risk assessment          |
| Adversarial Testing | High      | Testing against malicious models  |
| Defense in Depth    | Medium    | Multiple security layers          |
| Zero Trust          | Medium    | Security principle                |
| Container Escape    | Medium    | Security vulnerability type       |
| Network Isolation   | High      | No internet for evaluations       |
| Sandboxing          | High      | Isolated execution environments   |
| Non-root Execution  | Medium    | Security best practice            |

### 3. Infrastructure & Cloud

| Topic              | Frequency | Description                   |
| ------------------ | --------- | ----------------------------- |
| Docker             | Very High | Primary containerization      |
| Docker Compose     | High      | Multi-container orchestration |
| AWS                | High      | Primary cloud provider        |
| EC2                | High      | Current deployment target     |
| Kubernetes/K8s     | High      | Future orchestration platform |
| Terraform/OpenTofu | Medium    | Infrastructure as Code        |
| S3                 | Medium    | Object storage                |
| IAM                | Medium    | Identity management           |
| SQS                | Medium    | Message queuing service       |
| VPC/Subnets        | Medium    | Network isolation             |
| Security Groups    | Medium    | AWS firewall rules            |

### 4. Architecture Patterns

| Topic                     | Frequency | Description                   |
| ------------------------- | --------- | ----------------------------- |
| Microservices             | High      | Service-oriented architecture |
| Event-Driven Architecture | High      | Async communication pattern   |
| Queue/Worker Pattern      | Medium    | Job processing pattern        |
| API Gateway               | Medium    | Request routing               |
| Service Discovery         | Low       | Dynamic service location      |
| Real-time Updates         | Medium    | WebSocket/SSE streaming       |
| Pub/Sub                   | Medium    | Messaging pattern             |

### 5. Development Stack

| Topic      | Frequency | Description          |
| ---------- | --------- | -------------------- |
| Python     | High      | Backend language     |
| TypeScript | High      | Frontend language    |
| React      | High      | UI framework         |
| Next.js    | High      | React framework      |
| FastAPI    | High      | Python web framework |
| OpenAPI    | Medium    | API specification    |
| Redis      | Medium    | Cache/message broker |
| PostgreSQL | Medium    | Primary database     |
| Alembic    | Low       | Database migrations  |

### 6. Development Practices

| Topic                | Frequency | Description                       |
| -------------------- | --------- | --------------------------------- |
| CI/CD                | Medium    | Continuous integration/deployment |
| Type Safety          | High      | TypeScript/Python typing          |
| API-First Design     | Medium    | OpenAPI specification             |
| Testing Philosophy   | Medium    | Test-driven development           |
| Documentation-Driven | Medium    | Comprehensive docs                |
| Code Generation      | Medium    | OpenAPI to TypeScript             |

### 7. Monitoring & Observability

| Topic         | Frequency | Description           |
| ------------- | --------- | --------------------- |
| Monitoring    | High      | Real-time tracking    |
| Logging       | High      | Audit trails          |
| Metrics       | Medium    | Performance tracking  |
| Health Checks | Medium    | Service availability  |
| OpenTelemetry | Low       | Future observability  |
| Prometheus    | Low       | Metrics collection    |
| Grafana       | Low       | Metrics visualization |

### 8. AI Safety Specific

| Topic                  | Frequency | Description          |
| ---------------------- | --------- | -------------------- |
| AI Safety              | High      | Core mission         |
| Model Evaluation       | High      | Primary purpose      |
| Transformative AI      | Medium    | AI with major impact |
| Capability Evaluation  | Medium    | Testing AI abilities |
| Autonomous Replication | Medium    | Key risk to prevent  |
| Deceptive Alignment    | Low       | AI safety concern    |

## Existing Wiki Links Found

The following wiki-style links are already in use:

- `[[Container Isolation]]`
- `[[gVisor Setup]]`
- `[[Threat Model]]`
- `[[Docker Security]]`
- `[[Network Policies]]`
- `[[Resource Management]]`
- `[[Monitoring and Alerting]]`
- `[[Adversarial Testing]]`
- `[[Kubernetes Security]]`

## Common Themes

1. **Security-First Architecture** - Every decision considers security
2. **Isolation Layers** - Multiple levels of containment
3. **Scalable Microservices** - Modular, distributed design
4. **Real-time Monitoring** - Continuous observation
5. **Cloud Native** - Built for AWS deployment
6. **Type Safety** - Strong typing throughout
7. **Event-Driven** - Asynchronous communication
8. **Infrastructure as Code** - Reproducible deployments
9. **AI Safety Focus** - Purpose-built for dangerous AI
10. **Progressive Enhancement** - MVP to production evolution

## Auto-Link Priority List

### Tier 1 (Auto-link always)

- Crucible
- Crucible
- Docker
- Kubernetes / K8s
- gVisor / runsc
- Container Isolation
- AWS / EC2
- FastAPI
- Next.js
- TypeScript

### Tier 2 (Context-dependent)

- Evaluation / Evaluator
- Executor Service
- Monitoring
- Security
- Microservices
- Redis
- Python
- React
- Terraform

### Tier 3 (Manual linking preferred)

- API Gateway
- Queue Worker
- Storage Service
- WebSocket
- PostgreSQL
- Alembic
- OpenAPI
- CI/CD

## Recommendations

1. **Create Topic Hub Pages** for Tier 1 topics
2. **Build Glossary** with brief definitions and links
3. **Auto-link Detection** for high-frequency terms
4. **Security Documentation Graph** - visualize security doc relationships
5. **Learning Paths** - guided tours through documentation
6. **Cross-Reference Matrix** - which docs reference which topics

## Next Steps

1. Implement auto-linking for Tier 1 topics
2. Create glossary template
3. Build topic detection system
4. Generate topic hub pages
5. Visualize documentation relationships
