# Week 4: Demo Preparation & Platform Finalization

## Overview
This week focuses on achieving demo-ready status with a polished, production-quality platform that demonstrates deep engineering expertise.

**Primary Goals:**
1. Complete Celery migration (fix the deque oversight)
2. Polish codebase and fix any quality issues
3. Prepare compelling demo scenarios
4. Create professional repository structure
5. Finalize documentation and slides
6. Ensure CI/CD is clean and working

**Demo Date Target:** End of Week 4

## Current Status (From Week 3)

### ✅ Completed
- Microservices architecture with Docker
- Storage service with multi-backend support
- React frontend with Monaco editor
- OpenAPI/TypeScript integration
- Wiki-style documentation system
- Nginx with HTTPS and security headers
- TypeScript linting configuration
- Celery integration (100% traffic, with Flower monitoring)
  - Priority queues implemented
  - Retry logic with exponential backoff
  - Task cancellation working
  - Zero-downtime migration strategy documented

### 🚧 In Progress
- Shared contracts implementation (partially done, TypeScript generator needs work)

### ✅ Completed (Week 4 Addition)
- **Multiple Worker Support**: Atomic executor allocation implemented with Redis Lua scripts
  - Multiple executors configured (executor-1, executor-2, executor-3)
  - Idempotent release mechanism prevents race conditions
  - See `docs/architecture/idempotent-executor-release.md`
- **Code Storage Fix**: Fixed issue where evaluation code wasn't being saved
  - Modified FlexibleStorageManager to include code field
  - Frontend ExecutionMonitor has collapsible code section ready
- **Priority Field**: Added to evaluation metadata (API changes made, requires rebuild)
- **Execution Image Field Task**: Created design document for tracking Docker execution environments
  - See `week-4-demo/add-execution-image-field.md`
- **API Testing Guide**: Created comprehensive testing documentation
  - See `docs/testing/api-testing-guide.md`
  - Includes proper JSON escaping examples, port mappings, and troubleshooting
- **ML Executor Image**: executor-ml image defined and built in docker-compose.yml
  - Executors configured to use `executor-ml:latest` for ML-enabled evaluations
  - Sets foundation for multiple execution environments with different capabilities
- **Docker Event Race Condition Fix**: Fixed issue where fast-failing containers showed empty logs
  - Modified event handler to always process die/stop events
  - Fixed log retrieval by combining stdout/stderr into single call
  - **Known limitation**: stdout and stderr are mixed together (acceptable for demo)
  - See `week-4-demo/docker-logs-issue.md` for full analysis
  - This will be properly resolved when migrating to Kubernetes

### ❌ Not Started (Deferred to Future)
- Authentication/authorization (will document the design only)
- Kubernetes deployment (Docker Compose is sufficient for demo)
- Comprehensive test suite (focus on key integration tests)

## Day 1 (Monday): Complete Celery Integration ✅

### Morning (4 hours): Finish Celery Setup ✅
- [x] Basic Celery infrastructure created
- [x] Fix docker-compose networking issue
- [x] Integrate celery_client.py into API service
  - [x] Add dual-write to microservices_gateway.py
  - [x] Add environment variables to docker-compose.yml
  - [x] Test end-to-end flow
- [x] Verify Flower dashboard working
- [x] Create comparison metrics script
  - [x] Submit same tasks to both systems
  - [x] Compare execution times
  - [x] Verify result consistency

### Afternoon (4 hours): Production Features ✅
- [x] Implement priority queues
  - [x] High priority queue for future "premium" users
  - [x] Normal queue for standard evaluations
  - [x] Low priority for batch operations
- [x] Add retry logic with exponential backoff
- [x] Implement task cancellation
- [x] Add Celery status endpoint to API
- [x] Update storage service to handle Celery task updates
- [x] Document the migration strategy

**Deliverables:**
- ✅ Working Celery integration with 50/50 traffic split
- ✅ Flower dashboard accessible at port 5555
- ✅ Documentation of zero-downtime migration approach
- ✅ Production-ready features: retry logic, task cancellation, DLQ, status endpoint

## Day 2 (Tuesday): Code Quality & Testing

### Morning (4 hours): Code Quality Sweep ✅
- [x] Run full linting across all services
  - [x] Python: `ruff check . --fix`
    - Started with 169 errors → 37 remaining (78% reduction)
    - **All core production services: 0 errors** ✅
    - See [Python Linting Status](../../docs/development/linting-cleanup-status.md)
  - [x] TypeScript: `npm run lint`
    - **0 errors** (build succeeds) ✅
    - 98 warnings remaining (non-blocking)
    - See [TypeScript ESLint Status](../../docs/development/typescript-eslint-status.md)
- [x] Fix all critical warnings
  - Fixed all Python errors in production services
  - Fixed all TypeScript type errors
- [x] Remove deprecated code ✅
  - [x] Removed worker-service/ directory (unused, referenced non-existent src/)
  - [x] Removed tests/legacy/ directory (referenced old src.core.components)
  - [x] Organized legacy/ directory with README explaining its reference purpose
  - [x] Added TODO comments to mark queue-service/queue-worker for Day 7 removal
  - [x] Marked traffic splitting code in API for removal after Celery migration
  - [x] Clean up legacy API files
- [x] Deferred renaming microservices_gateway.py → app.py to Week 5
  - [x] Documented in week-5-metr-future-work.md under Code Cleanup section
  - [x] Decision: Avoid breaking changes during demo prep
- [x] Update all service READMEs
  - [x] api-service README (created comprehensive new README)
  - [x] frontend README (already exists)
  - [x] storage-service README (created comprehensive new README)
  - [x] celery-worker README (updated with DLQ, retry, migration details)
  - [x] queue-service README (updated with 50/50 split context)
  - [x] queue-worker README (updated with migration timeline)
  - [x] shared/ README (created to explain contracts/types)
  - [x] tests/ README (created comprehensive testing guide)
- [x] Ensure consistent code style
- [x] **Implement idempotent executor release** ✅
  - [x] Fixed Celery link/link_error edge case where both callbacks could run
  - [x] Implemented Redis Lua script for atomic operations
  - [x] Added metrics tracking to detect double releases
  - [x] Created comprehensive documentation:
    - Technical solution: [Idempotent Executor Release](../../docs/architecture/idempotent-executor-release.md)
    - Journey narrative: [Celery Idempotency Journey](../../docs/narrative/celery-idempotency-journey.md)
    - Presentation: [Slide 30: Celery Idempotency](../../frontend/content/slides/30-celery-idempotency.md)

### Afternoon (4 hours): Critical Testing
- [x] Integration tests for core flows
  - [x] Submit evaluation → Celery → Executor → Storage (test_core_flows.py)
  - [x] Frontend → API → Storage retrieval (test_core_flows.py)
  - [x] Error handling paths (test_core_flows.py)
- [x] Load testing with multiple concurrent evaluations (test_load.py)
- [x] Test service restart resilience (test_resilience.py)
- [x] Document test results and performance metrics (docs/testing/performance-metrics.md)
- [ ] Validate fill in all numbers in docs/testing/performance-metrics.md (placeholders remain)
  - [ ] **Load Test Results**
    - [x] Run 5/10 load test and record results (100% success, 15.7s avg)
    - [x] Run 10/20 load test and record results (100% success, 73.2s avg)
    - [x] Run 20/50 load test and record results (100% success, 176.8s avg)
    - [x] Run 50/100 load test and record results (98% success, 185.6s avg)
    - [ ] Rerun 50/100 test with provisioning→completed fix (expect 100%)
    - [ ] Update performance table with all results
    - [ ] Add timing accuracy note about state machine limitations
  - [ ] **Resilience Test Results**
    - [ ] Run `pytest -m destructive tests/integration/test_resilience.py -v`
    - [ ] Record Queue Worker restart recovery time (expected: 5-10s)
    - [ ] Record Celery Worker failure recovery behavior
    - [ ] Record Storage Service outage handling results
    - [ ] Document network partition test results
    - [ ] Update resilience section with actual timings
  - [ ] **Error Handling Test Results**
    - [ ] Create and run invalid syntax test (submit `print(`)
    - [ ] Create and run infinite loop test (submit `while True: pass`)
    - [ ] Create and run memory exhaustion test (submit `x = [0] * 10**9`)
    - [ ] Create and run network attempt test (submit `import requests; requests.get(...)`)
    - [ ] Create and run container crash test (submit `import sys; sys.exit(1)`)
    - [ ] Document detection times and recovery behavior
    - [ ] Note timeout enforcement limitation (not fully implemented)
  - [ ] **Resource Usage Metrics**
    - [x] Collect idle resource usage with `docker stats`
    - [x] Collect load resource usage during test execution
    - [ ] Run sustained load test (60s) with resource monitoring
    - [ ] Capture peak CPU usage per service under stress
    - [ ] Capture peak memory usage per service under stress
    - [ ] Update resource consumption table with measured values
  - [ ] **Queue Performance Metrics**
    - [x] Record submission latency (0.024s - 0.161s measured)
    - [x] Record queue times (avg 10-52s depending on load)
    - [x] Record execution times (avg 0.8-1.2s for test workloads)
    - [ ] Measure Celery task acceptance time (<50ms expected)
    - [ ] Test 50/50 traffic split behavior (if still enabled)
    - [ ] Document queue latency under various loads
  - [ ] **Scaling Observations**
    - [ ] Document horizontal scaling potential for each service
    - [ ] Identify and document current bottlenecks
    - [ ] Test with different executor pool sizes (1, 3, 5)
    - [ ] Measure throughput vs executor count
  - [ ] **Test Automation Verification**
    - [ ] Verify all test commands in document work correctly
    - [ ] Update any outdated command examples
    - [ ] Ensure test output paths are correct
    - [ ] Add any missing test scenarios to run_tests.py
- [x] Create automated test script for demo (run_demo_tests.py)
- [x] Verify the above testing protocols perform and cover as expected/desired
- [x] Analyze and adapt legacy test code
  - [x] Review tests/legacy components for useful patterns
  - [x] Adapt tests/security_scanner for current architecture
  - [x] Document migration plan for valuable test cases (see tests/test-migration-plan.md)
- [x] Fix API input validation issues discovered by security tests ✅
  - [x] Reject oversized payloads (implemented 1MB code limit, 2MB total request limit)
  - [x] Validate language parameter (only accepts "python")
  - [x] Reject negative timeout values (minimum 1 second)
  - [x] Set maximum timeout limit (maximum 15 minutes/900 seconds)
  - [x] Document payload size limits and validation rules
  - [x] Added RequestSizeLimitMiddleware for HTTP-level protection
  - [x] Implemented Pydantic validators for field-level validation
  - [x] Fixed middleware to only apply to /api/ endpoints (avoiding Docker socket interference)
  - [x] Fixed middleware to return JSONResponse instead of raising HTTPException
  - [x] All 8 security validation tests now passing

**Deliverables:**
- Clean codebase passing all linters
- Core integration tests passing
- Performance metrics documented
- Legacy test analysis complete

## Day 3 (Wednesday): CI/CD & Infrastructure Polish

### Morning (4 hours): Fix CI/CD Pipeline ✅
- [x] Fix startup script and service dependencies
  - [x] Fixed health check issues (storage-service, queue-worker)
  - [x] Added Flower service for Celery monitoring
  - [x] Added separate Redis for Celery (isolation)
  - [x] Fixed migrate service to use storage-service image
  - [x] Improved startup script to wait for healthy services
  - [x] Fixed nginx dependency on Flower service
- [x] Fix OpenAPI generation workflow ✅
  - [x] Ensure spec generation works in CI (all 3 services)
  - [x] Update frontend to handle missing spec gracefully (safe-generate-types.js)
  - [x] Document the hybrid approach clearly (openapi-security-analysis.md)
  - [x] Fixed executor Docker client lazy loading
  - [x] Created shared generation script (DRY principle)
  - [x] Integrated with start-platform.sh
- [x] Clean up GitHub Actions ✅
  - [x] Fixed YAML syntax errors in workflow
  - [x] Ensured all services generate specs
  - [x] Docker build now works with fallback types
  - [x] Deleted validation_fixes.py (already applied)
- [ ] Add production deployment configuration
  - [ ] Update docker-compose.prod.yml if needed
  - [ ] Ensure clean startup sequence in production

### Afternoon (4 hours): Infrastructure Improvements ✅
- [x] Optimize Docker images
  - [x] Multi-stage builds for API and Celery services
  - [x] Optimized base image (removed venv complexity)
  - [x] Added comprehensive .dockerignore
  - [x] Result: ~30-40% size reduction
- [x] Add docker-compose production overrides
  - [x] Created docker-compose.prod.yml with:
    - [x] Memory and CPU resource limits
    - [x] Security hardening (read-only filesystems, no-new-privileges)
    - [x] Restart policies (always restart)
    - [x] Health check optimizations
    - [x] Log rotation settings
    - [x] Production-tuned PostgreSQL and Redis
- [x] Create one-command startup
  - [x] Created `./start-platform.sh` script
  - [x] Supports dev and prod modes
  - [x] Waits for critical services (postgres, redis)
  - [x] Runs database migrations
  - [x] Shows access URLs and helpful commands
  - [x] Optional browser opening with --no-browser flag

**Deliverables:**
- Working CI/CD pipeline
- Optimized Docker images
- One-command platform startup

## Day 4 (Thursday): Demo Scenarios & Content

### Morning (4 hours): Demo Scenarios
- [ ] Create compelling demo scripts
  1. **Basic Flow**: Submit code, see results
  2. **Concurrent Load**: 10+ evaluations at once
  3. **Error Handling**: Show graceful failures
  4. **Monitoring**: Flower dashboard tour
  5. **Storage Explorer**: Show distributed storage
  6. **Wiki Docs**: Navigate documentation
- [ ] Pre-populate demo data
  - [ ] Example evaluations
  - [ ] Various statuses
  - [ ] Performance metrics
- [ ] Test all demos end-to-end
- [ ] Create fallback recorded videos

### Afternoon (4 hours): Presentation Materials
- [ ] Create slide deck (15-20 slides)
  - [ ] Problem statement
  - [ ] Architecture overview
  - [ ] Key engineering decisions
  - [ ] Live demo placeholder slides
  - [ ] Performance metrics
  - [ ] Future roadmap
- [ ] Architecture diagrams
  - [ ] High-level system design
  - [ ] Request flow diagram
  - [ ] Celery migration strategy
- [ ] Update existing slides with Week 3-4 progress

**Deliverables:**
- 5-6 demo scenarios ready
- Professional slide deck
- Architecture diagrams
- Backup demo videos

## Day 5 (Friday): Repository & Documentation

### Morning (3 hours): Repository Structure
- [ ] Create clean repository layout
  ```
  /
  ├── README.md (compelling overview)
  ├── ARCHITECTURE.md
  ├── CONTRIBUTING.md
  ├── docs/
  │   ├── getting-started.md
  │   ├── api-reference.md
  │   └── deployment.md
  ├── services/
  │   ├── api/
  │   ├── frontend/
  │   ├── celery-worker/
  │   └── ...
  └── docker-compose.yml
  ```
- [ ] Write compelling README
  - [ ] Clear value proposition
  - [ ] Quick start (< 5 minutes)
  - [ ] Architecture overview
  - [ ] Key features
- [ ] Remove sensitive files
  - [ ] No internal URLs
  - [ ] No API keys
  - [ ] No personal information
- [ ] Add badges (build status, etc.)

### Afternoon (5 hours): Documentation Polish & Security Design
- [ ] Finalize ARCHITECTURE.md
  - [ ] System design decisions
  - [ ] Trade-offs made
  - [ ] Scaling considerations
  - [ ] Security model overview
- [ ] Create SECURITY.md (Design Only - 1 hour)
  - [ ] Authentication architecture (JWT flow diagram)
  - [ ] Authorization model (RBAC design)
  - [ ] API key management strategy
  - [ ] Rate limiting per user/tier
  - [ ] Security headers (already implemented)
  - [ ] Network isolation approach
  - [ ] Note: "Implementation planned for Phase 2"
- [ ] Create getting-started.md
  - [ ] Prerequisites
  - [ ] Installation steps
  - [ ] First evaluation
  - [ ] Troubleshooting
- [ ] API documentation
  - [ ] All endpoints
  - [ ] Request/response examples
  - [ ] Error codes
- [ ] Update wiki documentation index

**Deliverables:**
- Professional repository structure
- Comprehensive documentation
- Clean commit history
- Ready for public viewing

## Day 6 (Saturday): Final Testing & Polish

### Morning (3 hours): End-to-End Testing
- [ ] Fresh clone test
  ```bash
  git clone [repo]
  cd [repo]
  docker-compose up -d
  # Should work in < 5 minutes
  ```
- [ ] Test all demo scenarios again
- [ ] Verify all documentation links
- [ ] Check for any broken features
- [ ] Performance benchmarks

### Afternoon (3 hours): Final Polish
- [ ] Record demo videos
  - [ ] Full platform walkthrough (5 min)
  - [ ] Architecture explanation (3 min)
  - [ ] Individual feature demos
- [ ] Final code review
  - [x] No commented-out code ✅ Clean - no significant commented code found
  - [x] No TODOs in critical paths ⚠️ Some TODOs in storage stats (non-critical)
    - [ ] Storage Service: Several TODOs for implementing
    - [ ] stats/metrics (not critical for demo)
    - [ ] Frontend: Minor TODOs in monitoring components
    - [ ] Storage Manager: TODOs for Redis/S3 clients (but current implementation works)
  - [ ] Consistent formatting ❌ Needs formatting (88 Python, 68 TypeScript files)
- [ ] Update metrics and screenshots
- [ ] Practice demo presentation

**Deliverables:**
- Everything working from fresh clone
- Demo videos recorded
- Platform ready for presentation

## Day 7 (Sunday): Demo Day Preparation

### Morning (2 hours): Final Checks
- [ ] Test demo environment
- [ ] Ensure all services healthy
- [ ] Review presentation
- [ ] Prepare backup plans

### Afternoon: Demo/Submission
- [ ] Live demo or submission
- [ ] Be ready for questions
- [ ] Have architecture diagrams handy
- [ ] Show confidence in the platform

## Next Steps & Optimizations

### Build Performance with BuildKit
Enable Docker BuildKit for 30-50% faster builds:
```bash
# Add to .env or shell
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Then build with parallelism
docker-compose build --parallel
```

Benefits for our multi-service architecture:
- Parallel stage execution in multi-stage Dockerfiles
- Smarter layer caching across services
- Skip unused build stages automatically
- Better progress output during builds

### Other Future Optimizations
- [ ] Implement distributed tracing (OpenTelemetry)
- [ ] Add Prometheus metrics collection
- [ ] Set up log aggregation (ELK stack)
- [ ] Implement auto-scaling for executors
- [ ] Add GPU support for ML workloads
- [ ] Migrate to Kubernetes for production scale

### Nice to Have - End of Week 4
- [ ] **Investigate React Query invalidation patterns** - Current polling + cache invalidation causes request storms with many concurrent evaluations. See `docs/react-query-invalidation-patterns.md` for approaches.
- [ ] **Consider WebSockets/SSE** - Replace polling with real-time updates to eliminate cache invalidation complexity entirely
- [ ] **Improve batch submission** - Current implementation lacks rate limiting for large batches. See `docs/batch-submission-patterns.md` for better patterns using React Query
- [ ] **Fix type generation architecture** - Currently takes 45 minutes to modify a shared type due to indirect TypeScript generation through OpenAPI. Need direct YAML→TypeScript generation. See `docs/proposals/type-separation-architecture.md`
- [ ] **Update JavaScript/TypeScript generator to match Python capabilities** - Current JS generator only handles one hardcoded enum file. Should be updated to:
  - Auto-discover and process all YAML files
  - Generate interfaces/types (not just enums)
  - Handle cross-file references
  - Match the generic approach of the Python generator
  - See `docs/development/python-vs-js-generators.md` for detailed comparison

### Next Steps - Executor Capacity Management

- [ ] **Implement atomic executor allocation** - With multiple Celery workers, we need to handle race conditions when checking executor capacity. Current implementation uses optimistic concurrency. See `docs/architecture/executor-capacity-management.md` for the recommended approach:
  1. Let multiple workers race to claim executors
  2. Executor service returns 503 when at capacity
  3. Only set "provisioning" status after receiving 200 response
  4. Failed workers retry with exponential backoff
  
  This follows the "let the service be the source of truth" principle and avoids complex distributed locking.

## Success Metrics

By end of Week 4:

1. **Working Platform**
   - Celery fully integrated
   - All services communicating
   - Clean startup/shutdown
   - No critical bugs

2. **Professional Codebase**
   - Passing all linters
   - Well-documented
   - Consistent style
   - No major technical debt

3. **Demo Ready**
   - 5+ scenarios prepared
   - Backup videos recorded
   - Can handle questions
   - Shows platform depth

4. **Repository Quality**
   - Clean structure
   - Comprehensive docs
   - Quick start works
   - Professional appearance

## Risk Mitigation

1. **Celery Integration Issues**
   - Keep dual-write as fallback
   - Can demo with either system
   - Document as "migration in progress"

2. **Time Constraints**
   - Focus on demo-critical features
   - Document "future work" for missing pieces
   - Polish what exists vs. adding features

3. **Technical Issues**
   - Have backup demo environment
   - Record videos as fallback
   - Practice offline demos

## Daily Checklist

- [ ] Morning: Review plan, set priorities
- [ ] Test yesterday's work still functions
- [ ] Commit working code frequently
- [ ] Update documentation as you go
- [ ] End of day: Note progress, plan tomorrow

## Not Doing This Week

These are documented as "future enhancements":
- Authentication system (comprehensive design in SECURITY.md, implementation in Phase 2)
- Kubernetes deployment (Docker Compose sufficient for demo, k8s manifests as future work)
- 90% test coverage (focus on critical integration tests)
- Multi-tenant support (architecture supports it, document the design)

## Key Messages for Demo

1. **Production-Ready Architecture**
   - Microservices with clear boundaries
   - Distributed task processing with Celery
   - Multi-backend storage system
   - Real-time monitoring

2. **Engineering Excellence**
   - Zero-downtime migration strategy
   - Type-safe frontend/backend integration
   - Comprehensive error handling
   - Security-first design
   - **Idempotent operations for distributed reliability**

3. **Platform Maturity**
   - Wiki-style documentation
   - One-command deployment
   - Monitoring and observability
   - Clean, maintainable code
   - **Defensive programming for framework edge cases**

4. **Security Awareness**
   - "We've implemented security headers and rate limiting"
   - "Authentication is fully designed in SECURITY.md"
   - "The architecture supports multi-tenant isolation"
   - "Here's how JWT auth would integrate..." [show diagram]

5. **Distributed Systems Expertise**
   - "We discovered and handled Celery's edge cases with idempotent operations"
   - "Our executor pool uses atomic Redis operations to prevent race conditions"
   - "We implemented comprehensive metrics to detect and debug distributed issues"
   - "Task chaining solved resource allocation challenges elegantly"

## Demo Talking Points for Missing Features

When asked about authentication:
> "We prioritized core platform architecture for this demo. Authentication is fully designed in our SECURITY.md document, including JWT flows, RBAC model, and API key management. The API layer is built to accept authentication middleware - it would plug in here [show code]. We can walk through the design if you'd like."

When asked about Kubernetes:
> "We're using Docker Compose for this demo, but the architecture is Kubernetes-ready. Each service has health checks, follows 12-factor principles, and we've documented the k8s deployment strategy. Docker Compose gives us faster iteration during development."

Remember: It's better to have fewer features working perfectly than many features working poorly. Focus on polish and professionalism.

## Future Improvements & Technical Debt

### Monitoring & Observability
- **Flower Health Checks**: Currently using the `/healthcheck` endpoint (discovered in Flower 2.0+). Initially attempted complex auth-based health checks before finding this simpler solution. See `/docs/architecture/monitoring/flower-health-check-limitations.md` for full analysis.
- **Alternative to Flower**: Consider Prometheus + Grafana for production, as Flower lacks granular permissions and proper RBAC.

### Infrastructure
- **Health Check Standardization**: All services use different health check approaches (curl, httpx, urllib, nc). Should standardize on a single method.
- **Service Dependencies**: Some health checks could be more sophisticated (e.g., checking broker connectivity, not just port availability).

### Security
- **Secrets Management**: Currently using environment variables and docker-compose. Production should use proper secrets management (Vault, K8s secrets, AWS Secrets Manager).
- **Non-root Users**: Some containers still run as root. Should create dedicated users for each service.

### Code Quality
- **TypeScript Strictness**: Successfully enforced strict typing with no `any` types, but some `unknown` types remain at API boundaries (intentionally).
- **Python Type Hints**: Add mypy strict mode across all Python services.

### Performance
- **Connection Pooling**: Redis and PostgreSQL connections could benefit from proper pooling configuration.
- **Caching Layer**: No caching strategy implemented yet (Redis is available but underutilized).

### Developer Experience
- **Hot Reload**: Frontend has it, but Python services require container restart.
- **Debugging**: No remote debugging setup for containerized services.
- **Development Seeds**: No sample data or development fixtures.

### Distributed Systems Challenges
- **Celery Edge Cases**: Implemented idempotent executor release to handle rare cases where both link and link_error callbacks execute. This required Redis Lua scripts for atomicity. See [Celery Idempotency Journey](../narrative/celery-idempotency-journey.md) for the full story.
- **Task Chaining**: Used Celery task chaining to separate resource allocation from execution, avoiding retry limitations. See [Celery Task Chaining Solution](../architecture/celery-task-chaining-solution.md).
- **Framework Limitations**: Working with Celery taught us valuable lessons about defensive programming and the importance of idempotency in distributed systems.

These items are documented here rather than as TODOs in code to keep the codebase clean for demo purposes.