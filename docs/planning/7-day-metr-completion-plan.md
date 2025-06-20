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
- **Flask to FastAPI migration** ✨
- **React TypeScript frontend with professional UI** ✨
- **Real-time event streaming and monitoring** ✨
- **Kubernetes-style isolated storage per evaluation** ✨
- **Docker compose orchestration** ✨
- **Frontend-backend integration with proper CORS** ✨
- **PostgreSQL database integration** ✨
- **Storage abstraction with multiple backends** ✨
- **Output truncation for large results** ✨
- **Event-driven storage architecture** ✨
- **Docker path issues fixed** ✨

❌ **Remaining**:
- Frontend database visibility (evaluation history)
- Advanced queue system with Celery/Redis
- Kubernetes deployment manifests
- Production security hardening (rate limiting, etc)
- S3 integration for large output storage
- Clean public repository
- Polished presentation materials
- Comprehensive test suite

## Day 1: API Enhancement & Dockerization

### Morning (4 hours): RESTful API with OpenAPI ✅ COMPLETED!
- [x] RESTful API endpoints
  - [x] Evaluation endpoint (`/api/eval`) - async only now
  - [x] Status endpoints (`/api/status`, `/api/queue-status`)
  - [x] OpenAPI spec at `/api/openapi.yaml`
- [x] **Upgraded to FastAPI**
  - [x] Replaced Flask with FastAPI
  - [x] Removed eval-async (all evaluations are async)
  - [x] WebSocket support for real-time updates
  - [x] Auto-generated OpenAPI from code
  - [x] Interactive Swagger UI at `/docs`
  - [x] Proper error handling and validation
- [ ] **Future enhancements**:
  - [ ] Full CRUD operations for evaluations
  - [ ] API versioning (v1, v2)
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
- [x] Update deployment pipeline (next priority)
- [x] Bug fixing and reliability improvements

**Deliverables Achieved**: 
- ✅ Working API with OpenAPI docs at `/api/openapi.yaml`
- ✅ Platform running in Docker container
- ✅ Docker Compose for full local stack
- ✅ Docker-in-Docker execution with path translation

## Day 1.5: Container Deployment to AWS (4 hours) ✅ COMPLETED!

### Immediate Next Steps:
- [x] Push Docker image to Amazon ECR
  - [x] Create ECR repository via Terraform
  - [x] Configure GitHub Actions to build and push
  - [x] Tag images with git SHA and version
- [x] Update EC2 deployment
  - [x] Modify userdata to pull from ECR
  - [x] Update systemd service to use Docker
  - [x] Ensure Docker socket permissions
- [x] Update GitHub Actions workflow
  - [x] Add Docker build step
  - [x] Push to ECR on main branch
  - [x] Deploy new container to EC2
- [x] Test end-to-end deployment
  - [x] Push code change
  - [x] Verify container updates
  - [x] Confirm execution still works

**Why This Matters**: 
- Completes our containerization story
- Enables true CI/CD with immutable deployments
- Shows production-ready practices
- Makes deployment reproducible

## Day 2: React Dashboard & Real-time Monitoring ✅ COMPLETED!

### Morning (5 hours): React Frontend ✅ DONE
- [x] Created React app with TypeScript
  - [x] Set up in `/frontend` directory with Next.js 14
  - [x] TypeScript with ZERO type debt policy
  - [x] Tailwind CSS for styling
  - [x] Professional two-panel layout
- [x] Implemented full functionality:
  - [x] Code submission with syntax highlighting
  - [x] Real-time execution status updates
  - [x] Queue status monitoring
  - [x] Event stream display
  - [x] Active evaluations tracking
  - [x] Batch submission (5 evaluations)
- [x] Containerization:
  - [x] Multi-stage Dockerfile for React app
  - [x] Build-time API_URL configuration
  - [x] Added to docker-compose.yml
  - [x] Container networking configured
- [x] Frontend-backend integration:
  - [x] Removed inline HTML from Python
  - [x] CORS properly configured
  - [x] API proxy for development

### Afternoon (5 hours): Monitoring & Real-time Features ✅ PARTIAL
- [x] Real-time monitoring features:
  - [x] Live queue status updates (2s polling)
  - [x] Event stream with timestamps
  - [x] Platform health display
  - [x] Active evaluation tracking
- [x] Structured frontend monitoring:
  - [x] Color-coded status indicators
  - [x] Professional UI matching AdvancedHTMLFrontend
  - [x] Responsive design for mobile/desktop
- [ ] **Still TODO for production**:
  - [ ] Prometheus metrics integration
  - [ ] OpenTelemetry tracing
  - [ ] Grafana dashboards
  - [ ] Correlation IDs in logs

**Delivered**:
- ✅ React dashboard at port 3000 with real-time updates
- ✅ Platform status monitoring
- ✅ Event stream visualization
- ✅ Professional UI/UX

## Day 3: Advanced Queue System & Testing (9 hours)

### Morning (5 hours): Celery Integration
- [x] Fix deploy-docker.yml to use systemd service ✅
  - Created new deploy-compose.yml workflow
  - Systemd service installed via userdata
  - Clean deployment with minimal commands
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

## Day 5: Database Integration & Frontend Visibility (8 hours)

### Morning (4 hours): Database & Storage ✅ COMPLETED!
- [x] PostgreSQL integration
  - [x] SQLAlchemy models with proper schema
  - [x] Database migrations with Alembic
  - [x] Docker Compose PostgreSQL service
- [x] Storage abstraction layer
  - [x] FlexibleStorageManager with multiple backends
  - [x] File storage backend
  - [x] Database storage backend
  - [x] In-memory storage with caching
- [x] Output handling for large results
  - [x] Automatic truncation for outputs >1MB
  - [x] Preview storage (1KB) with metadata
  - [x] Fields ready for S3 integration (output_location)
- [x] Event-driven storage integration
  - [x] EVALUATION_QUEUED event handler
  - [x] EVALUATION_COMPLETED event handler
  - [x] Platform integration with storage retrieval

### Afternoon (4 hours): Frontend Database Visibility
- [ ] Frontend evaluation history
  - [ ] Evaluation History Page - List past evaluations from `/api/evaluations`
  - [ ] Evaluation Detail View - Show full details using `/api/eval-status/{id}`
  - [ ] Status Polling - For async evaluations, poll until complete
  - [ ] Real-time Updates - WebSocket connection for live status updates
- [ ] UI components for database features
  - [ ] Evaluation list with pagination
  - [ ] Search and filter capabilities
  - [ ] Output preview with truncation indicator
  - [ ] Download full output (when S3 is added)
- [ ] Enhanced monitoring
  - [ ] Database connection status
  - [ ] Storage usage metrics
  - [ ] Evaluation statistics dashboard

**Delivered Today**:
- ✅ Complete database integration with PostgreSQL
- ✅ Storage abstraction supporting multiple backends
- ✅ Output truncation for large results (>1MB)
- ✅ Event-driven architecture for loose coupling
- ✅ Platform retrieves full evaluation data from storage
- ✅ Test utilities for validation

## Day 5.5: Blue-Green Deployment Infrastructure ✅ COMPLETED!

### Morning (4 hours): Infrastructure Updates
- [x] Implement Terraform for_each for EC2 instances
  - [x] Update variables to support enabled_deployment_colors
  - [x] Modify EC2 resource to create multiple instances
  - [x] Update outputs to show all instance IPs
- [x] Add AWS Secrets Manager integration
  - [x] Generate secure database password
  - [x] Store in Secrets Manager
  - [x] Update IAM policies for access

### Afternoon (4 hours): Deployment Workflow
- [x] Create deploy-compose.yml workflow
  - [x] Build and push both backend and frontend to ECR
  - [x] Deployment color selection dropdown
  - [x] Retrieve DB password from Secrets Manager
  - [x] Deploy via SSM to selected color
- [x] Update infrastructure for docker-compose
  - [x] Systemd service via userdata
  - [x] Clean deployment process
  - [x] Both blue and green instances deployed

**Delivered**:
- ✅ True blue-green deployment capability
- ✅ Zero-downtime deployment ready
- ✅ Secure password management
- ✅ Both environments running simultaneously

## Day 6: Advanced Features & Frontend Polish (9 hours)

### Morning (4 hours): Complete Frontend Database Integration
- [ ] Implement evaluation history page
- [ ] Add async status polling
- [ ] Create evaluation detail views
- [ ] WebSocket integration for real-time updates

### Afternoon (5 hours): Advanced Execution Features
- [ ] Multi-language support ([see detailed design](../features/multi-language-execution.md))
  - Implement language detection
  - Add Node.js support as proof of concept
- [ ] S3 integration for large outputs
  - Store full output when > 1MB
  - Update output_location field
  - Add download endpoints
- [ ] Production operations
  - Monitoring alerts
  - Backup procedures
  - Cost optimization

## Day 7: Repository Preparation & Documentation (9 hours)

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

Current Progress vs Goals:

1. **Technical Excellence**
   - ✅ FastAPI with async support
   - ✅ Docker containerization with compose
   - ✅ Kubernetes-style isolation per evaluation
   - ✅ PostgreSQL with proper schema and migrations
   - ✅ Storage abstraction layer with multiple backends
   - ⏳ Production-ready platform with <100ms API latency (close)
   - ❌ Kubernetes-native deployment (Day 4)
   - ❌ 90%+ test coverage (Day 3)
   - ⏳ Security hardened (partial - have gVisor, need rate limiting)

2. **Platform Capabilities**
   - ✅ Real-time monitoring via React dashboard
   - ✅ Concurrent evaluation support (tested with 5)
   - ✅ Database persistence for evaluation history
   - ✅ Output truncation for large results (>1MB)
   - ⏳ Frontend database visibility (API ready, UI needed)
   - ⏳ 100+ concurrent evaluations (need Celery/Redis)
   - ❌ Multi-language support (Day 6)
   - ⏳ Horizontal scaling (Docker yes, K8s no)

3. **Deliverables**
   - ✅ Working platform with modern stack
   - ✅ Docker deployment ready
   - ✅ Database integration complete
   - ✅ Test utilities for validation
   - ❌ Clean public repository (Day 7)
   - ⏳ Comprehensive documentation (in progress)
   - ❌ Polished presentation (Day 7)
   - ✅ Live demo capability

4. **METR Alignment**
   - ✅ Demonstrates system design skills
   - ✅ Shows security-first mindset (gVisor, isolation)
   - ✅ Modern platform engineering (FastAPI, React, Docker, PostgreSQL)
   - ✅ Event-driven architecture for scalability
   - ✅ Ready for AI safety evaluation workloads

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

## Future Possibilities & Nice-to-Haves

Low-priority enhancements that could be tackled after core completion:

### Code Quality & Maintainability
- **Refactor nested replace() in Terraform**: The current nested `replace()` calls in `ec2.tf` for service file templating work but could be cleaner. Consider refactoring to use `templatefile()` directly on the service file for better readability and maintainability.
- **Remove container-awareness from execution engine**: The execution engine currently has logic to detect if it's running in a container and translate paths accordingly. This violates separation of concerns - the code shouldn't need to know about its deployment environment. Refactor to use environment variables for all paths and let the deployment layer (docker-compose, systemd) handle the mapping transparently.

### Additional Features
- **Multi-region deployment**: Extend Terraform to support multiple AWS regions
- ✅ **Blue-green deployments**: Implemented with for_each EC2 instances and deployment color selection
- **Observability stack**: Add Prometheus, Grafana, and distributed tracing
- **Cost optimization**: Spot instances, auto-scaling policies
- **Enhanced security**: Implement OPA policies, admission webhooks
- **Performance testing**: Load testing harness with Locust or K6
- **GitOps with ArgoCD**: Full declarative deployment pipeline
- **Service mesh**: Istio/Linkerd for advanced traffic management

### Developer Experience
- **Local development mode**: Simplified setup without cloud dependencies
- **Integration test suite**: Comprehensive end-to-end tests
- **API client libraries**: Python/TypeScript SDKs
- **CLI tool**: Command-line interface for platform management
- **Development containers**: Codespaces/DevContainer configuration

### Documentation
- **Video tutorials**: Recorded walkthroughs of key features
- **Architecture decision records (ADRs)**: Formal documentation of key choices
- **Runbooks**: Operational procedures for common tasks
- **Performance benchmarks**: Document system limits and optimization opportunities

These items are explicitly out of scope for the initial 7-day push but represent the natural evolution of the platform.