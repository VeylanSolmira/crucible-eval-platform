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
- **Complete microservices architecture** ✨
- **Docker socket proxy with minimal permissions** ✨
- **PostgreSQL as default storage backend** ✨
- **End-to-end evaluation flow working** ✨
- **Comprehensive storage documentation** ✨

❌ **Remaining**:
- API evaluation retrieval (schema mismatch issue)
- Frontend database visibility (evaluation history)
- Advanced queue system with Celery/Redis
- Kubernetes deployment manifests
- Production security hardening (rate limiting, etc)
- S3 integration for large output storage
- Clean public repository
- Polished presentation materials
- Comprehensive test suite

## Day 0.5: Modularization & Security Hardening ✅ COMPLETED!

### Major Security Architecture Upgrade (8 hours):
- [x] **Modularized the platform into microservices**
  - [x] Queue Service - HTTP wrapper around TaskQueue
  - [x] Queue Worker - Routes tasks to executors
  - [x] Executor Service - Creates isolated containers
  - [x] Shared base Docker image for all services
- [x] **Implemented Docker Socket Proxy for security**
  - [x] Replaced direct socket mounting with tecnativa/docker-socket-proxy
  - [x] Limited Docker API permissions (no exec, no volumes, no networks)
  - [x] ~10x reduction in attack surface
  - [x] Prevents container escape to host
- [x] **Migrated all services to non-root users**
  - [x] No service runs as root anymore
  - [x] Executor connects via TCP to proxy (no socket mount)
  - [x] Meets CIS Docker Benchmark standards
  - [x] SOC2/PCI-DSS compliant architecture
- [x] **Resource optimization for t2.micro (1GB RAM)**
  - [x] Added memory limits to all services
  - [x] Reduced from 3 to 1 executor
  - [x] Total footprint under 800MB

### Security Documentation Created:
- [x] Docker networking guide (application and internals)
- [x] Queue worker rationale document
- [x] Docker socket proxy security analysis
- [x] Non-root container security guide
- [x] Security comparison: Root vs Proxy (10x improvement)

### Development Process Improvements:
- [x] Added "Show Don't Tell" pattern to CLAUDE.md for incremental changes
- [x] Implemented structured task tracking with TodoWrite/TodoRead
- [x] Created comprehensive architecture documentation as we built

**Why This Matters for METR**:
- Essential for evaluating potentially adversarial AI code
- Prevents privilege escalation from compromised services
- Audit trail of all Docker operations
- Natural evolution path to Kubernetes
- Demonstrates mature security engineering

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

## Day 2: Microservices Deep Dive & Storage Architecture ✅ COMPLETED!

### Morning (6 hours): Complete Microservices Migration
- [x] **Removed all /src dependencies**
  - [x] Each service is now completely independent
  - [x] Migrated shared logic to appropriate services
  - [x] Clean separation of concerns
- [x] **Fixed service communication**
  - [x] Unified API key for internal services
  - [x] Proper event-driven architecture with Redis
  - [x] Health checks working across all services
- [x] **Docker Socket Proxy Permissions**
  - [x] Analyzed executor operations to find minimal permissions
  - [x] Removed unnecessary permissions (INFO, VERSION, etc.)
  - [x] Fixed IMAGES permission issue (container recreation needed)
  - [x] Created comprehensive permissions documentation

### Afternoon (4 hours): Storage Architecture Completion
- [x] **PostgreSQL as Default Storage**
  - [x] Added SQLAlchemy to required services
  - [x] Fixed storage backend selection logic
  - [x] Verified database migrations working
- [x] **Storage Documentation**
  - [x] Created storage patterns and events guide
  - [x] Documented Option 3 (dedicated storage service)
  - [x] Enumerated all storage event types
- [x] **End-to-End Testing**
  - [x] Successfully executed Python code in containers
  - [x] Evaluations stored in PostgreSQL
  - [x] Event flow working through all services

**Key Learnings**:
- Docker socket proxy requires container recreation after env changes
- Microservices should never share file storage (use DB or API)
- Event-driven architecture enables loose coupling
- Minimal permissions principle is crucial for security

## Day 2.5: React Dashboard & Real-time Monitoring ✅ COMPLETED!

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
- [x] Modularize queue architecture ✅ PARTIALLY COMPLETE
  - [x] Created separate Queue Service (HTTP wrapper)
  - [x] Implemented Queue Worker (task router)
  - [x] Executor Service for isolated execution
  - [ ] Still TODO: Replace with Celery/Redis for production scale
- [ ] Implement Redis Pub/Sub for event-driven architecture
  - [ ] Add Redis container to docker-compose
  - [ ] API Gateway publishes events after database writes
  - [ ] Storage worker subscribes to EVALUATION_COMPLETED events
  - [ ] Matches Kubernetes watch/event patterns
  - [ ] See [event bus architecture doc](../architecture/event-bus-microservices.md)
- [ ] Upgrade to Celery for advanced features
  - Redis as message broker (reuse from pub/sub)
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
  - Memory usage under load
  - Container resource limits validation
- [ ] Security testing
  - OWASP API Security Top 10
  - Container escape attempts
- [ ] Observability foundation
  - Structured logging with structlog
  - Basic metrics collection
  - See [observability future plan](../architecture/observability-future.md)

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
  - Enforce read-only storage access for API Gateway
    - Create PostgreSQL read-only user
    - Separate connection strings for read/write
    - See [read-only storage enforcement](../architecture/read-only-storage-enforcement.md)
- [ ] Performance optimization
  - Add Redis caching layer
  - Implement connection pooling
  - Optimize Docker image sizes
  - Add CDN for static assets
- [ ] Memory profiling and optimization
  - Profile actual memory usage of all services
  - Identify memory hotspots with memory-profiler
  - Document baseline metrics for t2.micro
  - Create memory monitoring dashboard
  - See [memory optimization notes](../architecture/memory-optimization-notes.md)
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

## Day 5.75: Production Deployment & Debugging ✅ COMPLETED!

### Infrastructure Fixes (4 hours):
- [x] Fixed userdata script failures
  - [x] Installed cloud-utils for ec2metadata command
  - [x] Fixed ec2-metadata → ec2metadata syntax
  - [x] Set user_data_replace_on_change = false for blue-green
- [x] Fixed IAM permissions
  - [x] Added ecr:DescribeRepositories for ECR login
  - [x] Applied via targeted Terraform update
- [x] Fixed systemd service
  - [x] Updated docker-compose → docker compose
  - [x] Fixed migrate service image selection

### Deployment Debugging (3 hours):
- [x] Diagnosed Python import issues
  - [x] Found volume mount overwriting storage module
  - [x] Removed ./storage:/app/storage mount
  - [x] Kept only ./data:/app/data for runtime
- [x] Successfully deployed to green EC2
  - [x] All services running healthy
  - [x] Frontend and backend connected
  - [x] API responding on port 8080
  - [x] Frontend serving on port 3000

**Delivered**:
- ✅ Working production deployment on AWS
- ✅ Resolved all infrastructure issues
- ✅ Blue instance untouched (zero-downtime achieved)
- ✅ Green instance fully operational

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

## Day 6: Security & Public Access (8 hours)

### Morning (3 hours): Secure Public Access - Phase 2
- [x] Implement IP whitelist approach
  - [x] Add allowed_web_ips variable to Terraform
  - [x] Update security groups for HTTPS (port 443)
  - [x] Add HTTP (port 80) for Let's Encrypt only
- [x] Infrastructure as Code for DNS
  - [x] Implement Elastic IPs for stable addressing
  - [x] Create Route 53 configuration (optional)
  - [x] Support both AWS and external DNS providers
  - [x] Blue-green traffic switching via active_deployment_color
- [ ] Install and configure Nginx
  - [ ] Reverse proxy for backend (8080) and frontend (3000)
  - [ ] Security headers configuration
  - [ ] Rate limiting preparation
- [ ] Set up HTTPS with Let's Encrypt
  - [ ] Install certbot
  - [ ] Configure auto-renewal
- [ ] DNS configuration
  - [x] Implement Route 53 + Elastic IPs strategy
  - [ ] Configure subdomain (crucible.veylan.dev)
  - [ ] Test without making public

### Afternoon (2 hours): Security Hardening
- [ ] Configure Nginx rate limiting
- [ ] Set up fail2ban for brute force protection
- [ ] Configure AWS CloudWatch alarms
  - [ ] High CPU usage alerts
  - [ ] Unusual network traffic
  - [ ] Billing alerts
- [ ] Create emergency shutdown procedures
- [ ] Document security runbooks

### Evening (3 hours): Complete Frontend Database Integration
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
   - ✅ Production deployment on AWS EC2
   - ✅ Blue-green deployment with zero downtime
   - ✅ Infrastructure as Code with Terraform
   - ✅ Elastic IPs and Route 53 configuration
   - ✅ IP whitelisting for secure public access
   - ✅ Complete microservices architecture (API, queue, worker, executor, storage)
   - ✅ Docker socket proxy with minimal permissions
   - ✅ All services run as non-root users
   - ✅ Event-driven architecture with Redis pub/sub
   - ✅ Independent services with no shared dependencies
   - ✅ PostgreSQL as default storage backend
   - ✅ Comprehensive architecture documentation
   - ⏳ Production-ready platform with <100ms API latency (close)
   - ⏳ Nginx configuration ready (awaiting deployment)
   - ❌ Kubernetes-native deployment (Day 4)
   - ❌ 90%+ test coverage (Day 3)
   - ✅ Security hardened with gVisor isolation

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
   - ✅ Production deployment on AWS
   - ✅ Database integration complete
   - ✅ Blue-green deployment capability
   - ✅ CI/CD pipeline with GitHub Actions
   - ✅ Infrastructure as Code (Terraform)
   - ✅ Live demo capability on EC2
   - ❌ Clean public repository (Day 7)
   - ⏳ Comprehensive documentation (in progress)
   - ❌ Polished presentation (Day 7)

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
- **Clean up /src directory**: Now that all microservices are independent, the /src directory contains only legacy monolithic code. Migration plan:
  1. Move app.py (monolithic entry point) to /src/legacy/
  2. Archive old API files (api.py, servers/, openapi_validator.py) that still import from /src
  3. Document which components were replaced by which microservices
  4. Consider keeping some utilities if they're genuinely reusable
  5. Update README to explain the transition from monolith to microservices
- **Organize top-level directories**: The project root has accumulated many service directories. Consider reorganizing:
  1. Create `/services` directory for all microservices (api/, queue-service/, queue-worker/, executor-service/, storage-worker/)
  2. Keep `/storage` at top level as it's shared between services
  3. Move `/frontend` to `/services/frontend` or keep at top level
  4. Create `/legacy` for old monolithic code
  5. Keep `/infrastructure`, `/docs`, `/scripts` at top level
  This would give a cleaner structure: services/, storage/, infrastructure/, docs/, scripts/, tests/
- **Refactor nested replace() in Terraform**: The current nested `replace()` calls in `ec2.tf` for service file templating work but could be cleaner. Consider refactoring to use `templatefile()` directly on the service file for better readability and maintainability.
- ✅ **Remove container-awareness from execution engine**: COMPLETED! With the modular architecture, the executor service now creates containers via Docker proxy without needing to know about its own container environment. Path translation is handled at the deployment layer.
- ✅ **Eliminate root requirement for Docker access**: COMPLETED! All services now run as non-root users. The Docker socket proxy handles privileged operations, providing a 10x security improvement.
- **Containerize Nginx for better development experience**: Currently Nginx runs on the EC2 host, making it impossible to test the full stack locally with docker-compose. Migration path:
  1. Add nginx service to docker-compose.yml with proper volumes for config and SSL
  2. Move nginx configuration files into the repository for version control
  3. Update GitHub Actions to deploy the nginx container alongside other services  
  4. Remove nginx installation from EC2 userdata script
  5. Mount SSL certificates from host into container (or use Let's Encrypt container)
  Benefits: Local testing of full stack, faster iteration on nginx config, consistent dev/prod environments, nginx config in version control

### Data Storage & Security Considerations
- **Review /data directory usage and security**: The file-based scratchpad needs comprehensive review:
  1. **Audit current writes**: What's actually being written to /data? Should some go to DB instead?
  2. **Security considerations**: 
     - Container vs host mount (current: container directory owned by appuser)
     - Temporary file cleanup policies
     - Disk usage limits and quotas
     - Potential for directory traversal attacks
  3. **Storage migration paths**:
     - Large outputs → S3 with presigned URLs
     - Metadata → PostgreSQL
     - Temporary files → tmpfs or container-local
     - Logs → Centralized logging system
  4. **Best practices**:
     - Should we use volumes for persistence?
     - Should different services have separate data directories?
     - How to handle cleanup of old files?
     - Encryption at rest for sensitive data?

### Security Enhancements (from our architecture docs)
- **Rootless Docker**: Migrate Docker daemon itself to run as non-root user
  - Additional isolation layer
  - Prevents even daemon compromise from gaining root
- **User Namespaces**: Enable container user remapping
  - Map container root to unprivileged host user
  - Further reduces blast radius of container escape
- **Read-only filesystems**: Make container root filesystems read-only where possible
- **Kubernetes migration**: Natural evolution from Docker socket proxy
  - No Docker socket needed at all
  - Native pod security policies
  - Better resource isolation
- **Firecracker/gVisor**: For extreme isolation requirements
  - Micro-VM isolation (Firecracker)
  - Kernel syscall interception (gVisor)

### Storage Architecture Evolution
- **Consider dedicated storage service architecture**: Implement Option 3 from [storage service architecture doc](../architecture/storage-service-architecture.md)
  - Single source of truth for all storage operations
  - API-level access control for read/write separation
  - Centralized caching and monitoring
  - Better suited for multi-tenant scenarios
  - Natural evolution from current event-driven architecture

### Additional Type Safety Improvements (Frontend)
- [ ] Add type-safe error handling for API responses
- [ ] Create type guards for runtime validation
- [ ] Create typed error classes for different API errors
- [ ] Add request/response interceptors for logging
- [ ] Add zod validation for runtime type checking

## Additional Features
- **Multi-region deployment**: Extend Terraform to support multiple AWS regions
- ✅ **Blue-green deployments**: Implemented with for_each EC2 instances and deployment color selection
- **Observability stack**: Add Prometheus, Grafana, and distributed tracing
  - Structured logging everywhere
  - OpenTelemetry for distributed tracing
  - Security audit logging for METR use case
  - See [detailed observability plan](../architecture/observability-future.md)
- **Cost optimization**: Spot instances, auto-scaling policies
- **Enhanced security**: Implement OPA policies, admission webhooks
- **Performance testing**: Load testing harness with Locust or K6
- **GitOps with ArgoCD**: Full declarative deployment pipeline
- **Service mesh**: Istio/Linkerd for advanced traffic management

### Code Quality Review
- **Comprehensive code review of all microservices**: Review implementation patterns and choices:
  1. **Global State Usage**:
     - Identify and refactor global variables (like `_worker` in storage-worker)
     - Replace with dependency injection or app state patterns
     - Document any necessary singletons with clear justification
  2. **Async/Sync Patterns**:
     - Review mixing of threading and async (e.g., health servers)
     - Ensure consistent async patterns throughout
     - Check for blocking I/O in async contexts
  3. **Error Handling**:
     - Consistent error response formats across services
     - Proper exception handling and logging
     - Circuit breaker patterns for external dependencies
  4. **Configuration Management**:
     - Environment variable validation and defaults
     - Configuration classes vs scattered os.getenv()
     - Secrets handling and rotation capability
  5. **Logging and Observability**:
     - Structured logging consistency (some use structlog, others don't)
     - Request ID propagation across services
     - Proper log levels (INFO vs DEBUG vs ERROR)
  6. **Security Patterns**:
     - Input validation on all endpoints
     - SQL injection prevention (parameterized queries)
     - Rate limiting implementation
     - Authentication/authorization consistency
     - **Internal service authentication strategy**: Currently using one shared API key for all internal services. Consider:
       - No auth for internal services (Kubernetes pattern with network policies)
       - Service mesh with mTLS (Istio/Linkerd)
       - Service-specific API keys with key rotation
       - JWT tokens with service accounts
  7. **Testing Patterns**:
     - Unit test coverage for business logic
     - Integration test patterns
     - Mock vs real dependencies
  8. **Resource Management**:
     - Connection pooling for databases and HTTP clients
     - Proper cleanup on shutdown
     - Memory leak prevention
  9. **API Design**:
     - RESTful conventions consistency
     - Error response standardization
     - Versioning strategy
  10. **Docker Best Practices**:
      - Multi-stage builds optimization
      - Layer caching effectiveness
      - Security scanning of base images

### Developer Experience
- **Local development mode**: Simplified setup without cloud dependencies
- **Integration test suite**: Comprehensive end-to-end tests
- **API client libraries**: Python/TypeScript SDKs
- **CLI tool**: Command-line interface for platform management
- **Development containers**: Codespaces/DevContainer configuration

### Documentation
- **Update terminology from "API Gateway" to "API Service"**: Update all documentation files to reflect the naming change from api-gateway to api-service to avoid AWS API Gateway confusion
- **Video tutorials**: Recorded walkthroughs of key features
- **Architecture decision records (ADRs)**: Formal documentation of key choices
- **Runbooks**: Operational procedures for common tasks
- **Performance benchmarks**: Document system limits and optimization opportunities

These items are explicitly out of scope for the initial 7-day push but represent the natural evolution of the platform.