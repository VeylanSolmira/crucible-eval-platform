# Week 3 METR Platform Completion Plan

## Overview
Building on our current working platform with OpenAPI/TypeScript integration, this plan focuses on:
1. Production hardening and security (Days 1-2)
2. Advanced features and scaling (Days 3-4)
3. Testing and observability (Day 5)
4. Repository preparation and presentation (Days 6-7)

Target: 6-10 hours per day, focusing on production-ready features that demonstrate platform maturity.

## Critical Issues to Address First

### OpenAPI Schema Synchronization
**Status**: RESOLVED - Implemented hybrid static/CI approach
**Issue**: The static `api/openapi.yaml` doesn't match the actual API implementation
**Resolution**: 
- Manually updated openapi.yaml to include missing `language` and `engine` fields
- Created `generate-openapi-spec.yml` GitHub Action for CI/CD
- Removed failing auto-export from API startup
- Added scripts for local updates

**Current Implementation**:
1. **Local Development**: 
   - Run `scripts/update-openapi-spec.sh` when API changes
   - Or use `python api/scripts/export-openapi-spec.py`
   - Commit updated spec files
2. **CI/CD Pipeline**:
   - GitHub Action auto-generates spec when Python files change
   - Creates artifact for use in deployments
   - Deploy workflow uses fresh artifact if available
3. **Docker Builds**:
   - Frontend generates types at build time from static spec
   - API runs with read-only filesystem (security best practice)

**Completed items**:
- ✅ Removed auto-export from API startup (was failing due to read-only FS)
- ✅ Created GitHub Action `generate-openapi-spec.yml`
- ✅ Updated deploy workflow to use artifacts
- ✅ Created local update script
- ✅ Fixed frontend Docker build with proper OpenAPI fields

**Future Considerations**:
- [ ] Evaluate dynamic generation patterns for development - see [OpenAPI Dynamic Generation Patterns](../architecture/openapi-dynamic-generation-patterns.md)
- [ ] Consider dedicated spec service for rapid API development phases
- [ ] Add automated tests to validate spec matches API
- [ ] Monitor if manual updates become a bottleneck

**Related Documentation**:
- [OpenAPI Dynamic Generation Patterns](../architecture/openapi-dynamic-generation-patterns.md)

### React Query Migration
**Status**: COMPLETED ✅
**Issue**: Custom polling solution was replaced with React Query, initially causing 90-second delays
**Resolution**: 
- Successfully migrated to React Query for better state management
- Identified caching and status mismatch issues
- Discovered the need for shared contracts across services

**Key Learnings**:
1. **Performance Issue**: Hello World went from 3s to 90s due to:
   - React Query caching stale data
   - Status string mismatches between services ("pending" vs "queued")
   - Multiple service hops in microservices architecture
2. **Root Cause**: No shared contract for status values across distributed services
3. **Solution**: Implementing shared contracts pattern (in progress)

### Shared Contracts Implementation
**Status**: IN PROGRESS 🚧
**Issue**: Distributed services using inconsistent status values and event schemas
**Solution**: Creating shared contracts for core domain concepts

**Why This Matters**:
- In a monolith, status values were implicitly consistent
- In microservices, each service had its own definitions
- React Query migration exposed this hidden coupling
- Without shared contracts, we're debugging string mismatches in production

**Implementation**:
1. **Shared Structure** (`/shared/`):
   - `/types/` - OpenAPI schemas for shared types
   - `/constants/` - Security limits, event channels
   - `/docker/` - Shared base images
   - `/generated/` - Language-specific generated code

2. **Core Contracts Identified**:
   - ✅ `EvaluationStatus` enum (queued, running, completed, failed)
   - ✅ Event schemas for inter-service communication
   - ✅ Security-critical resource limits
   - ✅ Redis pub/sub channel names

3. **Migration Strategy**:
   - Start with API service (highest impact)
   - Export OpenAPI spec with enums
   - Regenerate frontend types
   - Propagate to other services

**This demonstrates**:
- Understanding of distributed systems challenges
- Proactive architectural improvements
- Type safety across service boundaries
- Production-ready thinking
- [Frontend Type Generation Guide](../../frontend/docs/handling-generated-types.md)
- [OpenAPI Integration](../implementation/OPENAPI_INTEGRATION.md)
- GitHub Actions: `.github/workflows/generate-openapi-spec.yml`
- Local script: `scripts/update-openapi-spec.sh`

## Current State
✅ **Completed in Weeks 1-2**:
- Complete microservices architecture with Docker
- PostgreSQL database with migrations
- React TypeScript frontend with real-time updates
- OpenAPI/TypeScript integration with build-time type safety
- Blue-green deployment on AWS
- Docker socket proxy for security
- Event-driven architecture with Redis
- Storage service with multi-backend support
- Service isolation with storage-only database writes
- Redis pending status check (202 vs 404)
- OpenAPI integration for all FastAPI services
- READMEs for all microservices

❌ **Remaining from 7-day plan**:
- Frontend evaluation history and statistics
- Celery/Redis for advanced queueing
- Kubernetes deployment
- Authentication & authorization system
- Comprehensive testing suite
- Public repository and presentation

## Day 1: Frontend for AI Safety Researchers

### Recent Accomplishments ✅
- [x] Implemented researcher-focused frontend at `/researcher`
  - [x] Monaco Editor with Python syntax highlighting
  - [x] Real-time execution monitoring
  - [x] Error display with stack traces
  - [x] Code templates and examples
- [x] Enhanced error handling
  - [x] Smart API client with rate limit handling
  - [x] Proper error boundaries
  - [x] TypeScript strict mode compliance
- [x] Security improvements
  - [x] Frontend ES2020 standardization (avoiding need for polyfills)
  - [x] Created polyfill security analysis and best practices guide
  - [x] Content Security Policy headers in Nginx
  - [x] Comprehensive security documentation

### Morning (4 hours): Professional Code Editor ✅ MOSTLY COMPLETED
- [x] Replace textarea with Monaco Editor (VS Code's editor)
  - [x] Python syntax highlighting and auto-indentation
  - [x] Code templates dropdown (hello world, network, file I/O examples)
  - [ ] Auto-save to localStorage
  - [ ] Recent submissions history
- [x] Add execution configuration
  - [x] Timeout selector (30s default, configurable in API)
  - [ ] Memory limit selector (256MB - 2GB)
  - [ ] Python version selector
  - [ ] Pre-submission syntax validation

### Afternoon (4 hours): Real-Time Monitoring ✅ PARTIALLY COMPLETED
- [x] Live execution dashboard
  - [x] Real-time stdout/stderr streaming (via polling)
  - [ ] CPU and memory usage graphs (live)
  - [x] Elapsed time counter
  - [ ] Kill execution button
- [x] Enhanced error display
  - [x] Stack traces with code context
  - [ ] Link errors to editor line numbers
  - [ ] Common error explanations
  - [x] Environment info for debugging

**Deliverables**:
- Monaco-based code editor with Python support
- Real-time execution monitoring with resource graphs
- Professional error handling and debugging tools
- Researcher-friendly UI that rivals Jupyter notebooks

## Day 2: Security Hardening & Production Features

### Morning (4 hours): Nginx & HTTPS Setup ✅ COMPLETED
- [x] Containerize Nginx
  - [x] Create Nginx Docker image with Alpine base
  - [x] Add to docker-compose.yml with proper service dependencies
  - [x] Volume mount for SSL certificates from host
  - [x] Health checks and logging configuration
- [x] Configure security headers
  - [x] Content Security Policy (CSP)
  - [x] X-Frame-Options: DENY
  - [x] X-Content-Type-Options: nosniff
  - [x] Strict-Transport-Security with includeSubDomains
  - [x] Referrer-Policy and XSS-Protection
- [x] Implement rate limiting
  - [x] Per-IP rate limits (general: 30r/s, api: 10r/s)
  - [x] Separate zones for auth (2r/s) and expensive ops (1r/s)
  - [x] Connection limits per IP
  - [x] 429 status codes for rate limit exceeded
- [x] SSL Certificate Strategy
  - [x] Host fetches from SSM Parameter Store
  - [x] Container mounts host certificates (read-only)
  - [x] Fail-fast in production mode
  - [x] Self-signed fallback for local development
  - [x] Tested successfully in local Docker environment
- [ ] Minor future enhancements:
  - [ ] Custom error pages for rate limiting (nice-to-have)
  - [ ] Wildcard certificate support in ACME setup
  - [ ] Monitor rate limit effectiveness in production

### Afternoon (4 hours): Authentication & Authorization
> **Note**: Before removing IP whitelisting, see [Security Requirements Before Removing IP Whitelisting](../security/platform-access-strategy.md#security-requirements-before-removing-ip-whitelisting) for the minimum security measures that must be in place.

- [ ] Implement API key authentication
  - [ ] API key generation and storage
  - [ ] Key rotation mechanism
  - [ ] Rate limiting per API key
  - [ ] Usage tracking and analytics
- [ ] Add JWT authentication for web users
  - [ ] Login/logout endpoints
  - [ ] Refresh token mechanism
  - [ ] Session management
  - [ ] Password reset flow (future)
- [ ] Implement RBAC (Role-Based Access Control)
  - [ ] Define roles (admin, user, viewer)
  - [ ] Permission system for different operations
  - [ ] Resource-level permissions
  - [ ] Audit logging for all actions
- [ ] Add tenant isolation
  - [ ] Multi-tenant data model
  - [ ] Tenant-specific quotas
  - [ ] Cross-tenant security validation

**Deliverables**:
- ✅ Nginx running in container with HTTPS
  - Containerized with Alpine base image
  - SSL certificates fetched from SSM by host, mounted read-only
  - Rate limiting configured (4 zones with different limits)
  - Security headers implemented
  - Production mode with fail-fast on missing certificates
  - Port 8000 secured for dev-only access
- Complete authentication system (pending)
- RBAC with audit logging (pending)
- Multi-tenant support (pending)

## Day 3: Celery Integration & Advanced Queueing

### Morning (5 hours): Celery Setup
- [ ] Replace simple queue with Celery
  - [ ] Install and configure Celery with Redis
  - [ ] Create task definitions for evaluations
  - [ ] Implement task routing
  - [ ] Add Flower for monitoring
- [ ] Implement priority queues
  - [ ] High priority for authenticated users
  - [ ] Normal priority for anonymous
  - [ ] Low priority for batch operations
  - [ ] Configurable queue weights
- [ ] Add advanced task features
  - [ ] Task chaining for multi-step evaluations
  - [ ] Task groups for batch processing
  - [ ] Scheduled tasks (cron-like)
  - [ ] Task result backend configuration
- [ ] Implement retry mechanisms
  - [ ] Exponential backoff with jitter
  - [ ] Max retry limits
  - [ ] Dead letter queue for failed tasks
  - [ ] Failure notifications

### Afternoon (4 hours): Distributed Task Processing
- [ ] Horizontal scaling setup
  - [ ] Multiple Celery workers
  - [ ] Worker specialization by task type
  - [ ] Auto-scaling based on queue depth
  - [ ] Worker health monitoring
- [ ] Task lifecycle management
  - [ ] Task cancellation/revocation
  - [ ] Task progress reporting
  - [ ] Long-running task handling
  - [ ] Graceful shutdown procedures
- [ ] Resource management
  - [ ] CPU/memory limits per task
  - [ ] Concurrent task limits
  - [ ] Resource reservation system
  - [ ] Fair scheduling algorithm
- [ ] Advanced monitoring
  - [ ] Queue depth metrics
  - [ ] Task execution time histograms
  - [ ] Worker utilization metrics
  - [ ] SLA monitoring and alerts

**Deliverables**:
- Celery replacing simple queue
- Flower dashboard for queue monitoring
- Horizontal scaling demonstration
- Advanced task lifecycle management

## Day 4: Storage Service & Kubernetes Deployment

### Morning (3 hours): Storage Service Implementation ✅ COMPLETED
- [x] Create dedicated storage service
  - [x] Design RESTful API for storage operations
  - [x] Move database access from API service to storage service
  - [x] Implement storage backends abstraction (FlexibleStorageManager)
  - [x] Add caching layer for frequently accessed data (Redis/Memory)
- [x] Storage service endpoints
  - [x] GET /evaluations/{id} - Retrieve evaluation
  - [x] POST /evaluations - Create evaluation
  - [x] PUT /evaluations/{id} - Update evaluation
  - [x] GET /evaluations - List evaluations with pagination
  - [x] GET /statistics - Aggregated statistics
  - [x] GET /storage-info - Storage configuration details
  - [x] GET /health - Health check endpoint
- [x] Implement storage patterns
  - [x] Repository pattern for data access (StorageService base class)
  - [x] Multiple backend support (Database, File, S3, Redis)
  - [x] Automatic large output handling (>100KB to file storage)
  - [x] Result pagination with limit/offset ✅ FULLY IMPLEMENTED
    - GET /evaluations?limit=100&offset=0
    - Supports filtering by status, language, and since date
    - Returns has_more flag for pagination UI
- [x] Add storage service features
  - [x] Bulk operations for efficiency ✅ FULLY IMPLEMENTED
    - POST /evaluations/bulk accepts array of evaluations
    - Returns detailed results with success/error for each item
    - Used for batch submissions
  - [x] Event tracking infrastructure (API exists but not integrated)
  - [x] Soft deletes with recovery (status="deleted")
  - [x] OpenAPI integration with YAML/JSON export
  - [x] Comprehensive error handling and logging

**Additional Completed Features**:
- [x] Storage-worker updated to use storage service API
- [x] API gateway refactored to proxy to storage service
- [x] Redis pending check with 202 Accepted status
- [x] Service READMEs created for all microservices
- [x] Legacy API files moved to /api/legacy folder

### Afternoon (2 hours): Kubernetes Manifests
- [ ] Create base Kubernetes resources
  - [ ] Deployments for all services
  - [ ] Services for internal communication
  - [ ] ConfigMaps for configuration
  - [ ] Secrets for sensitive data
- [ ] Implement security policies
  - [ ] NetworkPolicies for micro-segmentation
  - [ ] PodSecurityPolicies (or Pod Security Standards)
  - [ ] RBAC for service accounts
  - [ ] Admission controllers configuration
- [ ] Add ingress and load balancing
  - [ ] Ingress controller (nginx-ingress)
  - [ ] TLS termination at ingress
  - [ ] Path-based routing rules
  - [ ] Backend service health checks
- [ ] Resource management
  - [ ] Resource requests and limits
  - [ ] Horizontal Pod Autoscaling (HPA)
  - [ ] Vertical Pod Autoscaling (VPA)
  - [ ] Pod Disruption Budgets (PDB)

### Late Afternoon (2 hours): Helm Charts & GitOps
- [ ] Create Helm charts
  - [ ] Chart for platform services
  - [ ] Configurable values.yaml
  - [ ] Environment-specific overrides
  - [ ] Helm hooks for migrations
- [ ] Implement GitOps workflow
  - [ ] ArgoCD installation and config
  - [ ] Application definitions
  - [ ] Automated sync policies
  - [ ] Rollback procedures
- [ ] CI/CD pipeline for base image
  - [ ] Build crucible-base in GitHub Actions
  - [ ] Push to container registry (ECR/DockerHub)
  - [ ] Tag with git SHA and version
  - [ ] Update service Dockerfiles to use registry image
  - [ ] Automated security scanning of base image
- [ ] Multi-environment support
  - [ ] Dev/staging/prod namespaces
  - [ ] Environment-specific configs
  - [ ] Promotion workflows
  - [ ] Feature flag integration
- [ ] Observability integration
  - [ ] Prometheus ServiceMonitors
  - [ ] Grafana dashboards
  - [ ] Log aggregation setup
  - [ ] Distributed tracing config

**Deliverables**:
- Dedicated storage service with clean API
- Complete Kubernetes manifests
- Helm charts for easy deployment
- GitOps with ArgoCD
- Multi-environment setup

## Day 5: Testing & Observability

### Morning (5 hours): Comprehensive Testing
- [ ] Unit test coverage
  - [ ] Achieve 90% code coverage
  - [ ] Test all business logic
  - [ ] Mock external dependencies
  - [ ] Property-based testing where applicable
- [ ] Integration testing
  - [ ] API contract testing
  - [ ] Database integration tests
  - [ ] Message queue integration tests
  - [ ] Service-to-service communication tests
- [ ] End-to-end testing
  - [ ] Playwright for UI testing
  - [ ] User journey tests
  - [ ] Cross-browser testing
  - [ ] Mobile responsiveness tests
- [ ] Performance testing
  - [ ] Load testing with K6/Locust
  - [ ] Stress testing to find limits
  - [ ] Spike testing for sudden load
  - [ ] Soak testing for memory leaks

### Afternoon (4 hours): Observability Stack
- [ ] Metrics collection
  - [ ] Prometheus setup
  - [ ] Custom application metrics
  - [ ] Infrastructure metrics
  - [ ] Business metrics
- [ ] Logging pipeline
  - [ ] Structured logging everywhere
  - [ ] Log aggregation with Loki/ELK
  - [ ] Log correlation with trace IDs
  - [ ] Log retention policies
- [ ] Distributed tracing
  - [ ] OpenTelemetry integration
  - [ ] Trace sampling strategies
  - [ ] Performance bottleneck identification
  - [ ] Cross-service trace correlation
- [ ] Alerting and SLOs
  - [ ] Define Service Level Objectives
  - [ ] Alert routing with AlertManager
  - [ ] On-call procedures
  - [ ] Runbook automation

**Deliverables**:
- 90% test coverage with CI integration
- Full observability stack deployed
- SLOs defined and monitored
- Runbooks for common issues

## Day 6: Repository Preparation & Documentation

### Morning (5 hours): Clean Public Repository
- [ ] Create new public repository structure
  ```
  metr-task-standard-platform/
  ├── README.md (compelling overview)
  ├── ARCHITECTURE.md
  ├── SECURITY.md
  ├── CONTRIBUTING.md
  ├── docs/
  │   ├── getting-started/
  │   ├── deployment/
  │   ├── api-reference/
  │   └── development/
  ├── platform/
  │   ├── services/
  │   ├── frontend/
  │   └── shared/
  ├── infrastructure/
  │   ├── docker/
  │   ├── kubernetes/
  │   ├── terraform/
  │   └── helm/
  ├── examples/
  │   ├── quickstart/
  │   ├── advanced/
  │   └── integrations/
  └── .github/
      ├── workflows/
      └── ISSUE_TEMPLATE/
  ```
- [ ] Clean commit history
  - [ ] Squash development commits
  - [ ] Clear commit messages
  - [ ] Remove sensitive information
  - [ ] Add co-authors appropriately
- [ ] Security audit
  - [ ] Remove all secrets
  - [ ] Remove internal URLs
  - [ ] Remove personal information
  - [ ] Add security policy
- [ ] Add community files
  - [ ] Code of conduct
  - [ ] Contributing guidelines
  - [ ] Issue templates
  - [ ] Pull request template

### Afternoon (4 hours): Professional Documentation
- [ ] Write compelling README
  - [ ] Clear problem statement
  - [ ] Architecture overview diagram
  - [ ] Quick start (< 5 minutes)
  - [ ] Feature showcase
  - [ ] Performance metrics
  - [ ] Use case examples
- [ ] Create comprehensive docs
  - [ ] Installation guide
  - [ ] Configuration reference
  - [ ] API documentation
  - [ ] Deployment guides
  - [ ] Troubleshooting guide
  - [ ] FAQ section
- [ ] Add visual assets
  - [ ] Architecture diagrams
  - [ ] Sequence diagrams
  - [ ] Screenshots/GIFs
  - [ ] Demo videos
- [ ] Developer documentation
  - [ ] Development setup
  - [ ] Testing guide
  - [ ] Release process
  - [ ] Code style guide
  - [x] Documentation system (see [migration plan](../development/docs-migration-plan.md)) ✅ COMPLETED
    - [ ] Content audit - review README files for inclusion/exclusion
    - [ ] Decide on slides integration approach (unified markdown renderer)
    - [x] Implement smart filtering for valuable content
    - [x] Created comprehensive docs route at `/docs`
  - [x] **Wiki Knowledge Graph** (HIGH PRIORITY - see [detailed plan](../development/wiki-knowledge-graph.md)) ✅ CORE FEATURES COMPLETED
    - [x] Week 1: Core wiki features ✅ COMPLETED
      - [x] Cross-reference system ([[Page]] syntax) with remark-wiki-link
      - [x] Backlinks ("Referenced by" sections) with real-time processing
      - [x] Topic extraction and auto-generated topic pages
      - [x] Created wiki-topics-analysis.md with 191 files analyzed
      - [x] Implemented TopicDetector for automatic link suggestions
      - [x] Created auto-link-docs.js script (580+ link opportunities)
      - [x] Generated missing links report (555 missing, 180 orphaned)
      - [x] Created docs/index.md as central hub with wiki links
    - [ ] Week 2: AI Safety integration (PENDING)
      - [ ] Security concept ontology
      - [ ] Cross-project linking (AI Safety Compiler)
      - [ ] Learning path generation
    - [ ] Week 3: Visualization (PENDING)
      - [ ] Interactive knowledge graph (react-force-graph added)
      - [ ] Graph-based navigation
      - [ ] Concept relationship mapping
- [ ] Security improvements
  - [ ] Remove dangerouslySetInnerHTML from slides system
  - [ ] Ensure all markdown rendering is XSS-safe

**Deliverables**:
- Clean public repository
- Professional documentation
- Quick start guide
- Visual assets

## Day 7: Presentation & Demo Preparation

### Morning (4 hours): Presentation Materials
- [ ] Create slide deck (20-30 slides)
  - [ ] Problem statement and motivation
  - [ ] Solution architecture
  - [ ] Technical deep dives
  - [ ] Security model
  - [ ] Performance metrics
  - [ ] Future roadmap
- [ ] Prepare demo scenarios
  - [ ] Basic evaluation flow
  - [ ] Concurrent execution demo
  - [ ] Scaling demonstration
  - [ ] Security features
  - [ ] Monitoring dashboards
  - [ ] Failure handling
- [ ] Create supporting materials
  - [ ] One-page architecture summary
  - [ ] Performance benchmark report
  - [ ] Security assessment summary
  - [ ] Cost analysis
- [ ] Practice and polish
  - [ ] Time the presentation
  - [ ] Prepare speaker notes
  - [ ] Anticipate questions
  - [ ] Create backup slides

### Afternoon (4 hours): Final Preparations
- [ ] Demo environment setup
  - [ ] Dedicated demo instance
  - [ ] Pre-loaded with examples
  - [ ] All features enabled
  - [ ] Monitoring visible
- [ ] Record demo videos
  - [ ] Full platform walkthrough
  - [ ] Individual feature demos
  - [ ] Architecture explanation
  - [ ] Deployment process
- [ ] Final testing
  - [ ] Test all demo scenarios
  - [ ] Verify documentation links
  - [ ] Check repository access
  - [ ] Validate quick start
- [ ] Submission preparation
  - [ ] Final repository review
  - [ ] Documentation check
  - [ ] Update submission form
  - [ ] Prepare cover letter

**Deliverables**:
- Polished slide deck
- Live demo environment
- Recorded demo videos
- Ready for submission

## Additional Tasks to Consider

### Storage Backend Improvements
- [ ] Add efficient count_evaluations method to all storage backends
  - [ ] FileStorage: Use os.listdir() or glob to count JSON files efficiently
  - [ ] MemoryStorage: Use len(self.evaluations) for O(1) count
  - [ ] Ensure all backends implement count_evaluations(status: Optional[str] = None)
  - [ ] This enables proper pagination counts without fetching all records

### Frontend Improvements
- [ ] Implement React Query to replace custom polling logic (DISCUSSED BUT NOT IMPLEMENTED)
  - Replace manual polling in page.tsx with React Query
  - Automatic retry with exponential backoff
  - Request deduplication and caching
  - Better error handling and loading states
  - See discussion about smart polling vs React Query/SWR
  - Current implementation uses custom polling with 202 status handling

### Type Generation Improvements
- [ ] Option B for type generation: Generate from live API during Docker build
  - Start API service in build container
  - Generate types from actual running API
  - More complex but guarantees accuracy
  - See `frontend/docs/handling-generated-types.md` for details
- [ ] Resolve build order dependency issue
  - Currently frontend build requires `api/openapi.yaml` to exist
  - Options: Generate during API build, commit baseline spec, or make frontend build resilient
  - Important for CI/CD pipelines with fresh clones

### Event Tracking & Audit Trail Completion
- [ ] Implement automatic event tracking for state changes
  - Add event publishing in storage-worker when status changes
  - Track queued → running → completed transitions
  - Include metadata like worker_id, execution_time, etc.
- [ ] Integrate microservices with event API
  - Queue-worker to publish "evaluation_started" events
  - Executor to publish "execution_progress" events
  - Storage-worker to call storage service event API
- [ ] Add event history display to frontend
  - Create timeline component showing all events
  - Add to evaluation details view
  - Include filtering by event type
  - Show event metadata in expandable rows

### Soft Delete Enhancements
- [ ] Add undelete/restore endpoint
  - POST /evaluations/{eval_id}/restore
  - Clear deleted_at timestamp
  - Set status back to previous state
- [ ] Filter deleted evaluations from listings
  - Add query parameter ?include_deleted=false (default)
  - Update storage service list endpoint
  - Add "Show deleted" toggle in frontend
- [ ] Implement automatic cleanup policy
  - Configurable retention period (e.g., 30 days)
  - Background job to hard delete old soft-deleted records
  - Add "permanent_delete" permission check

### Technical Debt
- [ ] Refactor global Redis clients to use app.state or dependency injection
- [ ] Fix OpenAPI export in read-only containers (serve via endpoint only)
- [ ] Build crucible-base image in CI/CD pipeline
- [x] Address deprecated datetime.utcnow() usage
- [ ] Fix startup 503 errors with proper readiness checks
- [x] **Address Build Warnings and Linting Issues** ✅ COMPLETED
  - [x] Set up TypeScript ESLint with strict type checking
  - [x] Created comprehensive .eslintrc.json configuration
  - [x] Fixed critical errors blocking build:
    - Replaced `<a>` tags with Next.js `<Link>` components
    - Fixed unescaped apostrophes in JSX
    - Changed `let` to `const` where appropriate
    - Added proper type imports
  - [x] Configured VS Code integration for real-time error detection
  - [x] Created lint-staged and prettier configurations
  - [x] Added `lint:all` script for combined linting and type checking
  - [x] Relaxed rules to warnings to enable build while maintaining code quality guidance
  - [x] Build now completes successfully with ~200 warnings to address over time
- [ ] Convert shared imports to proper Python package
  - See [Shared Python Package Proposal](../architecture/shared-python-package-proposal.md)
  - Current approach uses PYTHONPATH which only works in Docker
  - Would improve local development and testing experience
- [ ] Create separate enums for different lifecycle concerns
  - **EvaluationStatus**: Overall evaluation lifecycle (queued, running, completed, failed)
  - **ExecutionResult**: Container execution outcomes (completed, failed, timeout, killed, memory_exceeded)
  - **LifecycleState**: Entity lifecycle (active, deleted, archived, suspended)
  - This would provide better type safety and clearer domain modeling
  - Currently mixing concerns (e.g., "deleted" doesn't fit with execution statuses)
- [ ] Advanced Frontend Debugging Features
  - **URL Parameter Debug Mode**: Enable debug logging via `?debug=true` parameter
  - **Temporary log level override**: Allow support staff to enable debug logs without code changes
  - **Session-based debug mode**: Remember debug preference for troubleshooting sessions
  - **Debug info overlay**: Show connection status, API latency, queue depth in corner
  - See frontend logger implementation at `/frontend/src/utils/logger.ts`

## Success Metrics

By the end of Week 3, we should have:

1. **Production-Ready Platform**
   - Complete authentication and authorization
   - HTTPS with proper security headers
   - Celery-based distributed task processing
   - Kubernetes deployment ready
   - 90% test coverage

2. **Professional Repository**
   - Clean, well-documented code
   - Comprehensive documentation
   - Quick start in < 5 minutes
   - Active CI/CD pipelines
   - Security and contributing guidelines

3. **Compelling Presentation**
   - Clear value proposition
   - Technical depth demonstration
   - Live demo capability
   - Performance metrics
   - Future vision

4. **METR Alignment**
   - Demonstrates production engineering skills
   - Shows security-first mindset
   - Scalable architecture for AI workloads
   - Ready for adversarial code execution
   - Professional delivery

## Risk Mitigation

- **Complexity**: Focus on depth over breadth - better to have fewer features working perfectly
- **Time management**: Use timeboxing - move on if stuck
- **Demo failures**: Always have recorded backups
- **Scope creep**: Refer back to this plan daily

## Daily Routine

- Morning: Check plan, set daily goals
- Work blocks: 2-hour focused sessions
- Breaks: 15 minutes between blocks
- End of day: Update progress, prepare next day
- Documentation: Update as you go, not at the end