# 7-Day METR Platform Completion Plan

## Overview
Building from our current state (working cloud deployment with Docker/gVisor execution), this plan focuses on:
1. Completing core platform features (Days 1-3)
2. Production hardening and Kubernetes (Days 4-5)
3. Creating public repository and polishing deliverables (Days 6-7)

Target: 6-10 hours per day, with clear deliverables that demonstrate platform engineering excellence.

## Current State (Updated)
✅ **Completed**:
- Modular Python platform with clean architecture
- Docker and gVisor execution engines
- AWS deployment with Terraform
- GitHub Actions CI/CD pipeline
- Fixed systemd/permissions issues
- Basic web interface with event-driven architecture
- **Platform containerization with Docker** ✨
- **Docker-in-Docker execution working** ✨
- **Path translation for volume mounts** ✨
- **OpenAPI specification and endpoints** ✨
- **RESTful API with proper routing** ✨
- **Pragmatic security decisions documented** ✨

❌ **Remaining**:
- React dashboard with real-time monitoring
- Advanced queue system with Celery/Redis
- Kubernetes deployment
- Production security hardening
- Performance optimization
- Clean public repository
- Polished presentation materials

## Day 1: API Enhancement & Dockerization

### Morning (4 hours): RESTful API with OpenAPI
**Partially Complete** - We have basic API with OpenAPI spec, but could enhance:
- [x] Basic RESTful API endpoints
  - [x] Evaluation endpoints (`/api/eval`, `/api/eval-async`)
  - [x] Status endpoints (`/api/status`, `/api/queue-status`)
  - [x] OpenAPI spec at `/api/openapi.yaml`
- [ ] **Still TODO**: Upgrade to FastAPI
  - [ ] Replace current basic HTTP server with FastAPI
  - [ ] Migrate eval-async to eval (as sync is deprecated)
  - [ ] Full CRUD operations for evaluations
  - [ ] Batch submission endpoints
  - [ ] WebSocket support for real-time updates
  - [ ] Auto-generated OpenAPI from code
  - [ ] Interactive Swagger UI at `/docs`
- [ ] Implement API versioning (v1, v2)
- [ ] Add authentication middleware (API keys)

### Afternoon (4 hours): Platform Dockerization ✅ COMPLETED!
- [x] Create multi-stage Dockerfile with pragmatic decisions
  - [x] Single container with all components
  - [x] Mount Docker socket for sibling containers
  - [x] Pragmatic root user with documentation
- [x] Docker Compose setup
  - [x] Platform container with socket mount
  - [x] Storage volume for persistence
  - [x] Environment configuration with HOST_PWD
  - [x] Path translation for Docker-in-Docker
- [x] Test sibling container execution - Working!
- [ ] Update deployment pipeline (next priority)

**Deliverables Achieved**: 
- ✅ Working API with OpenAPI docs at `/api/openapi.yaml`
- ✅ Platform running in Docker container
- ✅ Docker Compose for full local stack
- ✅ Docker-in-Docker execution with path translation

## Day 1.5: Container Deployment to AWS (4 hours) 🚀 NEXT PRIORITY

### Immediate Next Steps:
- [ ] Push Docker image to Amazon ECR
  - [ ] Create ECR repository via Terraform
  - [ ] Configure GitHub Actions to build and push
  - [ ] Tag images with git SHA and version
- [ ] Update EC2 deployment
  - [ ] Modify userdata to pull from ECR
  - [ ] Update systemd service to use Docker
  - [ ] Ensure Docker socket permissions
- [ ] Update GitHub Actions workflow
  - [ ] Add Docker build step
  - [ ] Push to ECR on main branch
  - [ ] Deploy new container to EC2
- [ ] Test end-to-end deployment
  - [ ] Push code change
  - [ ] Verify container updates
  - [ ] Confirm execution still works

**Why This Matters**: 
- Completes our containerization story
- Enables true CI/CD with immutable deployments
- Shows production-ready practices
- Makes deployment reproducible

## Day 2: React Dashboard & Real-time Monitoring (10 hours)

### Morning (5 hours): React Frontend
- [ ] Create React app with TypeScript
  - Modern tooling (Vite, ESLint, Prettier)
  - Tailwind CSS for styling
  - Component library (shadcn/ui or MUI)
- [ ] Core components:
  - Evaluation submission form with code editor (Monaco)
  - Real-time evaluation status grid
  - Execution timeline visualization
  - Resource usage graphs
- [ ] WebSocket integration for live updates
- [ ] Dark mode support

### Afternoon (5 hours): Monitoring & Observability
- [ ] Integrate Prometheus metrics
  - Execution count/duration
  - Queue depth
  - Resource usage
  - Error rates
- [ ] Add OpenTelemetry tracing
  - Trace evaluation lifecycle
  - Identify bottlenecks
- [ ] Create Grafana dashboards
  - Platform health overview
  - Execution analytics
  - Security events
- [ ] Add structured logging with correlation IDs

**Deliverables**:
- React dashboard at port 3000
- Prometheus metrics at `/metrics`
- Grafana dashboards showing platform health
- End-to-end request tracing

## Day 3: Advanced Queue System & Testing (9 hours)

### Morning (5 hours): Celery Integration
- [ ] Replace basic queue with Celery
  - Redis as message broker
  - Separate worker processes
  - Priority queues (high/normal/low)
  - Task routing by engine type
- [ ] Implement advanced features:
  - Task retry with exponential backoff
  - Dead letter queue for failed tasks
  - Scheduled/delayed execution
  - Task cancellation
- [ ] Add Flower for queue monitoring
- [ ] Horizontal scaling demos (multiple workers)

### Afternoon (4 hours): Comprehensive Testing
- [ ] Unit tests with pytest
  - 90% code coverage target
  - Mocking for external dependencies
- [ ] Integration tests
  - API endpoint testing
  - Queue processing tests
  - Docker engine tests
- [ ] End-to-end tests with Playwright
  - User workflow testing
  - WebSocket functionality
- [ ] Load testing with Locust
  - Find performance limits
  - Identify bottlenecks
- [ ] Security testing
  - OWASP API Security Top 10
  - Container escape attempts

**Deliverables**:
- Celery-powered queue system
- Flower dashboard
- 90% test coverage
- Load test results showing >100 concurrent evaluations

## Day 4: Kubernetes & Production Hardening (10 hours)

### Morning (5 hours): Kubernetes Deployment
- [ ] Create Kubernetes manifests
  - Deployments for API, workers, frontend
  - Services and Ingress
  - ConfigMaps and Secrets
  - HorizontalPodAutoscaler
- [ ] Implement security policies
  - NetworkPolicies for isolation
  - PodSecurityPolicies
  - RBAC configuration
  - Admission webhooks for validation
- [ ] Add Helm chart for easy deployment
- [ ] Setup for different environments (dev/staging/prod)

### Afternoon (5 hours): Security & Performance
- [ ] Security hardening
  - Implement rate limiting
  - Add request signing/validation
  - Enable audit logging
  - Secrets management with Vault/Sealed Secrets
  - Container image scanning
- [ ] Performance optimization
  - Add Redis caching layer
  - Implement connection pooling
  - Optimize Docker image sizes
  - Add CDN for static assets
- [ ] Implement circuit breakers
- [ ] Add chaos engineering tests (Litmus)

**Deliverables**:
- Complete K8s manifests in `/k8s` directory
- Helm chart in `/helm`
- Security scan reports
- Performance benchmarks showing <100ms API response times

## Day 5: Advanced Features & Production Readiness (8 hours)

### Morning (4 hours): Advanced Execution Features
- [ ] Multi-language support ([see detailed design](../features/multi-language-execution.md))
  - Implement language detection
  - Add Node.js support as proof of concept
  - Document architecture for Go, Rust, etc.
- [ ] GPU support for ML workloads
  - NVIDIA Docker integration
  - GPU resource scheduling
  - Usage monitoring
- [ ] Distributed execution
  - Split large evaluations
  - Map-reduce pattern support
- [ ] Evaluation artifacts storage (S3)

### Afternoon (4 hours): Production Operations
- [ ] Implement blue-green deployment
- [ ] Add database migrations (Alembic)
- [ ] Backup and restore procedures
- [ ] Monitoring alerts (PagerDuty integration)
- [ ] Runbook documentation
- [ ] SLO/SLA definitions
- [ ] Cost optimization
  - Spot instance support
  - Auto-scaling policies
  - Resource waste detection

**Deliverables**:
- Multi-language execution demo
- GPU-enabled evaluation example
- Complete ops runbook
- Cost analysis showing <$100/month for moderate load

## Day 6: Repository Preparation & Documentation (9 hours)

### Morning (5 hours): Clean Public Repository
- [ ] Create new public repository structure
  ```
  metr-task-standard-platform/
  ├── README.md (compelling project overview)
  ├── docs/
  │   ├── architecture.md
  │   ├── getting-started.md
  │   ├── api-reference.md
  │   └── deployment.md
  ├── examples/
  │   ├── basic-evaluation/
  │   ├── batch-processing/
  │   └── ml-workload/
  ├── platform/
  │   └── (clean source code)
  └── infrastructure/
      ├── docker/
      ├── kubernetes/
      └── terraform/
  ```
- [ ] Cherry-pick clean commits
  - Initial platform architecture
  - Core execution engines
  - API implementation
  - Frontend dashboard
  - Infrastructure as code
- [ ] Remove sensitive content
  - Interview prep files
  - Internal notes
  - AWS account specifics
- [ ] Add proper licensing (MIT)

### Afternoon (4 hours): Documentation Polish
- [ ] Write compelling README
  - Problem statement
  - Architecture diagram
  - Quick start guide
  - Feature highlights
  - Performance metrics
- [ ] Create architecture documentation
  - System design decisions
  - Security model
  - Scaling approach
- [ ] Add code examples
  - Python SDK usage
  - REST API examples
  - WebSocket integration
- [ ] Create demo videos/GIFs

**Deliverables**:
- Clean public repository
- Professional documentation
- Working quickstart in <5 minutes

## Day 7: Presentation Materials & Demo Preparation (8 hours)

### Morning (4 hours): Slide Deck Creation
- [ ] Refine presentation narrative
  - Problem → Solution → Implementation → Results
  - Focus on METR's needs
  - Highlight engineering decisions
- [ ] Create technical deep-dive slides
  - Architecture diagrams
  - Security model
  - Performance benchmarks
  - Scaling demonstration
- [ ] Add demo screenshots/videos
- [ ] Prepare speaker notes

### Afternoon (4 hours): Demo Environment & Practice
- [ ] Setup demo environment
  - Pre-loaded with example evaluations
  - Monitoring dashboards ready
  - Load generation scripts
- [ ] Create demo script
  - Basic evaluation flow
  - Real-time monitoring
  - Scaling demonstration
  - Security features
  - Chaos engineering demo
- [ ] Record backup demo video
- [ ] Practice presentation (30 min)
- [ ] Prepare Q&A responses

**Deliverables**:
- Polished slide deck (20-30 slides)
- Live demo environment
- Backup demo video
- Q&A preparation document

## Success Metrics

By the end of Day 7, we should have:

1. **Technical Excellence**
   - ✓ Production-ready platform with <100ms API latency
   - ✓ Kubernetes-native deployment
   - ✓ 90%+ test coverage
   - ✓ Security hardened (OWASP compliant)

2. **Platform Capabilities**
   - ✓ 100+ concurrent evaluations
   - ✓ Multi-language support
   - ✓ Real-time monitoring
   - ✓ Horizontal scaling

3. **Deliverables**
   - ✓ Clean public repository
   - ✓ Comprehensive documentation
   - ✓ Polished presentation
   - ✓ Live demo

4. **METR Alignment**
   - ✓ Demonstrates large-scale system design
   - ✓ Shows security-first mindset
   - ✓ Exhibits platform engineering best practices
   - ✓ Ready for AI safety evaluation workloads

## Risk Mitigation

- **Time Crunch**: Focus on core features first, advanced features can be simulated
- **Technical Blockers**: Have fallback options (e.g., k3s if full K8s is too complex)
- **Demo Failures**: Record everything, have backup videos
- **Scope Creep**: Stick to the plan, document "future work" instead of implementing

## Daily Checklist

Each day:
- [ ] Morning standup (self-reflection on goals)
- [ ] Code/feature implementation
- [ ] Documentation updates
- [ ] Git commits with clear messages
- [ ] End-of-day progress review
- [ ] Next day preparation

Remember: This is a portfolio piece that demonstrates platform engineering excellence for AI safety infrastructure. Quality > Quantity.