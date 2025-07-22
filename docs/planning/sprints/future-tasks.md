# Week 5 - METR Platform Future Work

## Overview
This document tracks all future work items for the METR platform after the MVP demo. Items are organized by priority and dependencies.

## Library and Package Management

### Evaluation Environment Library Decisions
- [ ] Define standard library sets for each executor type
  - [ ] **executor-minimal**: Core Python only (no external packages)
    - Standard library modules only
    - Smallest possible image size (~50MB)
    - For basic Python evaluation tasks
  - [ ] **executor-base**: Common data science packages
    - numpy, pandas, matplotlib
    - requests, beautifulsoup4
    - Standard ML data processing
    - Target size: ~300MB
  - [ ] **executor-ml**: Full ML/AI environment  
    - Current: numpy, torch, requests
    - Missing: pandas, matplotlib, scipy, sklearn, tensorflow
    - Consider: transformers, huggingface_hub, openai
    - Balance size vs functionality (~1-2GB)
  - [ ] **executor-gpu**: GPU-enabled ML environment
    - All executor-ml packages
    - CUDA-enabled versions
    - GPU-specific libraries (cupy, rapids)
    - Size: 4GB+

### Library Security Review
- [ ] Security audit all included packages
  - [ ] Check for known vulnerabilities (safety, pip-audit)
  - [ ] Review package permissions and capabilities
  - [ ] Establish update cadence for security patches
- [ ] Create allowlist/blocklist system
  - [ ] Define criteria for package inclusion
  - [ ] Document security implications of each package
  - [ ] Create approval process for new packages
- [ ] Network isolation considerations
  - [ ] Which packages require network access
  - [ ] How to handle packages that phone home
  - [ ] SSL certificate bundle management

### Package Version Management
- [ ] Establish version pinning strategy
  - [ ] Lock files for reproducibility
  - [ ] Regular update schedule
  - [ ] Compatibility testing between packages
- [ ] Create package documentation
  - [ ] Available packages per environment
  - [ ] Version information
  - [ ] Usage examples and limitations
- [ ] User communication
  - [ ] How to request new packages
  - [ ] Update notifications
  - [ ] Migration guides for breaking changes

**Current Status**: Test shows numpy, torch, requests available; pandas, matplotlib, scipy, sklearn, tensorflow missing from executor-ml

## Post-Kubernetes Migration Tasks

### Multi-Executor Image Architecture
- [ ] Design multi-executor architecture with specialized images
  - [ ] Create `executor-base` image (150MB) for simple Python tasks
  - [ ] Create `executor-ml-light` image (500MB) with ONNX Runtime
  - [ ] Create `executor-ml-full` image (1.3GB) with PyTorch for training
  - [ ] Create `executor-gpu` image (4GB+) with CUDA support
- [ ] Implement Celery routing logic based on evaluation requirements
- [ ] Add `executor_type` field to evaluation request schema
- [ ] Update API validation to enforce executor type selection
- [ ] Deploy multiple executor services with different resource limits
- [ ] Document migration path from single-image to multi-image architecture

### Kubernetes Infrastructure Improvements
- [ ] Implement Horizontal Pod Autoscaling for executor pools
- [ ] Configure Pod Security Policies for enhanced isolation
- [ ] Set up Network Policies for zero-trust networking
- [ ] Add Persistent Volume Claims for model caching
- [ ] Consider Service Mesh (Istio/Linkerd) for observability

### Kubernetes Architecture Exploration
- [ ] Explore putting each service on its own t2.micro
  - [ ] Analyze cost implications of distributed deployment
  - [ ] Document architectural benefits and drawbacks
  - [ ] Compare with container-per-node vs multi-container approaches
  - [ ] Consider this partially for architectural experience
  - [ ] Create cost comparison spreadsheet

### Production Kubernetes Manifests (From 5-day-metr Day 4)
- [ ] Create comprehensive K8s configurations to show production thinking
  - [ ] Network policies for isolation
    - [ ] Deny all default
    - [ ] Explicit ingress/egress rules
    - [ ] Pod-to-pod communication rules
  - [ ] Pod security policies
    - [ ] Read-only root filesystem
    - [ ] Non-root user enforcement
    - [ ] Capability dropping
    - [ ] Seccomp profiles
  - [ ] Resource quotas and limits
    - [ ] Namespace quotas
    - [ ] LimitRanges
    - [ ] PodDisruptionBudgets
  - [ ] RBAC configuration
    - [ ] Service accounts
    - [ ] Role bindings
    - [ ] Least privilege access

### Kubernetes Integration Testing (Post-Migration)
- [ ] Create `test_k8s_deployment.py` test suite
  - [ ] Test pod creation and lifecycle
  - [ ] Verify service discovery works correctly
  - [ ] Test horizontal pod autoscaling under load
  - [ ] Verify resource limits and quotas enforcement
- [ ] Test Kubernetes-specific features
  - [ ] Namespace isolation for multi-tenancy
  - [ ] Persistent volume claims for model storage
  - [ ] Network policies for security
  - [ ] Pod security policies enforcement
  - [ ] ConfigMap and Secret management
- [ ] Add chaos testing
  - [ ] Pod failure injection
  - [ ] Network partition simulation
  - [ ] Resource exhaustion scenarios
- [ ] Performance testing in K8s
  - [ ] Measure pod startup times
  - [ ] Test scaling response times
  - [ ] Verify load balancing effectiveness
- [ ] Create K8s-specific test fixtures
  - [ ] kubectl command wrappers
  - [ ] Namespace setup/teardown
  - [ ] Test data volume provisioning

### GitOps with ArgoCD (From week-3-metr)
- [ ] ArgoCD installation and configuration
- [ ] Application definitions for all services
- [ ] Automated sync policies
- [ ] Rollback procedures
- [ ] Multi-environment promotion workflows
- [ ] GitOps best practices documentation

## Testing Infrastructure Improvements

### Queue Status Integration
- [ ] Implement `wait_for_queue_empty()` helper function in test utilities
- [ ] Update all integration tests to use queue status polling instead of sleep
- [ ] Add queue metrics to test output for debugging
- [ ] Create test helper for waiting on specific evaluation states
- [ ] Document new testing patterns in test README

### Concurrency Testing
- [ ] Create `test_executor_concurrency.py` test suite
  - [ ] Test parallel execution with configured executor count
  - [ ] Verify no serialization bottlenecks
  - [ ] Test queue handling under concurrent load
  - [ ] Add performance regression tests
- [ ] Create test to verify expected concurrency exists or establish baseline
  - [ ] Test should check if we have documented expected concurrency levels
  - [ ] If not documented, run baseline test to measure actual concurrency
  - [ ] Create configuration file with expected concurrency metrics
  - [ ] Future tests should validate against these expectations
- [ ] Add concurrency metrics to platform monitoring
- [ ] Document expected vs actual concurrency behavior

### Test Suite - Next Level
- [ ] Bring tests to next level:
  - [ ] Assess what "next level" precisely means
  - [ ] Define key unit tests for each component
  - [ ] Define key integration tests
  - [ ] Set percentage coverage targets
  - [ ] Document what comes after achieving current targets

### End-to-End UI Testing
- [ ] Create automated UI test framework
  - [ ] Choose testing framework (Playwright, Cypress, Selenium)
  - [ ] Set up test infrastructure for browser automation
  - [ ] Create page object models for main UI components
- [ ] Implement core UI test scenarios
  - [ ] Code submission through Monaco editor
  - [ ] Real-time status updates via WebSocket/polling
  - [ ] Error display and formatting
  - [ ] Code editor features (syntax highlighting, auto-completion)
  - [ ] Execution configuration changes
  - [ ] History/results viewing
- [ ] Add visual regression testing
  - [ ] Capture baseline screenshots
  - [ ] Detect unintended UI changes
- [ ] Integrate with CI/CD pipeline
  - [ ] Run on pull requests
  - [ ] Generate test reports with screenshots
- [ ] Document UI testing patterns and best practices

## Docker Event Race Condition

### Immediate Fixes (Week 4 - COMPLETED)
- [x] Fix event handler to always process die/stop events
- [x] Add fallback to retrieve container from Docker API
- [x] Update log retrieval to use single combined call
- [x] Document stdout/stderr separation limitations
- [x] Create integration tests for fast-failing containers

### Long-term Improvements (Post-K8s)
- [ ] Implement proper stdout/stderr separation using Kubernetes logging
- [ ] Add structured logging with JSON output
- [ ] Implement log streaming for real-time output
- [ ] Add log retention policies and rotation
- [ ] Consider using Fluentd/Fluent Bit for log aggregation

## Evaluation Timeout Enforcement

### Current Issue
- [ ] Implement strict timeout enforcement for evaluations
  - Timeout parameter is accepted but not strictly enforced
  - Containers can run longer than specified timeout
  - Should forcibly stop/kill container when timeout is exceeded
  - Return status="timeout" or status="failed" with appropriate error

### Implementation Tasks
- [ ] Update executor service to monitor container runtime
- [ ] Implement container kill on timeout exceeded
- [ ] Add grace period configuration (cleanup time)
- [ ] Ensure partial output is captured before kill
- [ ] Update integration tests (re-enable `test_evaluation_timeout`)
- [ ] Document timeout behavior in API docs

## Security Enhancements

### Safety Test Suite & Attack Scenarios (From 5-day-metr)
- [ ] Create comprehensive safety demonstration suite
  - [ ] Network escape attempts (should fail with "Connection refused")
  - [ ] Resource exhaustion tests (CPU/memory limits enforced)
  - [ ] File system probing (show read-only restrictions)
  - [ ] Capabilities hiding detection via monitoring
- [ ] Build concrete attack scenario evaluations
  - [ ] Data exfiltration attempts (blocked by network=none)
  - [ ] Fork bomb / resource exhaustion (killed by cgroup limits)
  - [ ] Container escape attempts (blocked by gVisor syscall filtering)
  - [ ] Kernel exploitation attempts (isolated by gVisor)
  - [ ] Side-channel attacks (timing, cache)
- [ ] Document each attack with:
  - [ ] Attack description and potential impact
  - [ ] Defense layer that stops it
  - [ ] Actual output showing the failure
  - [ ] Monitoring alerts generated

### Container Isolation
- [ ] Evaluate gVisor for enhanced container isolation
- [ ] Implement Seccomp profiles for system call filtering
- [ ] Add AppArmor/SELinux policies for mandatory access control
- [ ] Configure read-only root filesystems where possible
- [ ] Implement container image signing and verification

### Network Security
- [ ] Implement egress filtering for evaluation containers
- [ ] Add mTLS between services
- [ ] Configure WAF rules for API Gateway
- [ ] Implement rate limiting per user/evaluation
- [ ] Add DDoS protection strategies

### Nginx Production Enhancements (From week-3-metr)
- [ ] Custom error pages for rate limiting
- [ ] Wildcard certificate support in ACME setup
- [ ] Production test for rate limit effectiveness

### Private Subnet Architecture (From 5-day-metr Day 4)
- [ ] Migrate to production-grade networking
  - [ ] Deploy VPC with public/private subnets
  - [ ] Configure NAT Gateway for controlled egress
  - [ ] Remove public IPs from compute instances
  - [ ] Implement bastion host or SSM endpoints
- [ ] Deploy Session Manager infrastructure
  - [ ] Copy session-manager-setup.tf.example to active
  - [ ] Configure IAM roles for SSM access
  - [ ] Enable CloudTrail audit logging
  - [ ] Document access procedures
- [ ] Security benefits to highlight
  - [ ] Zero network attack surface (no SSH)
  - [ ] Complete audit trail via CloudTrail
  - [ ] No public IPs or SSH keys to manage
  - [ ] Demonstrates defense in depth

### ML Model Security (Download vs Evaluation Separation)
- [ ] Implement physically separate model download pipeline
- [ ] Create secure model cache in S3
- [ ] VPC endpoint for model access (no internet)
- [ ] Model validation and scanning service
- [ ] See detailed design: [ml-model-security-considerations.md](/docs/architecture/ml-model-security-considerations.md)

## Performance Optimizations

### Performance Testing & Benchmarks (From 5-day-metr)
- [ ] Create comprehensive performance test suite
  - [ ] Load test with 10, 50, 100 concurrent evaluations
  - [ ] Measure throughput (evaluations/second)
  - [ ] Document scaling limits and bottlenecks
  - [ ] Test queue overflow behavior
  - [ ] Measure resource usage under load
- [ ] Create automated performance regression tests
  - [ ] Baseline performance metrics
  - [ ] Alert on performance degradation
  - [ ] Track metrics over time
- [ ] Document performance characteristics
  - [ ] Cold start times
  - [ ] Evaluation latency distribution
  - [ ] Resource usage patterns
  - [ ] Scaling recommendations

### Image Size Reduction
- [ ] Analyze dependency tree and remove unused packages
- [ ] Implement multi-stage builds more aggressively
- [ ] Use distroless base images where possible
- [ ] Implement lazy loading for ML libraries
- [ ] Create dependency caching layer

### Cold Start Optimization
- [ ] Pre-warm executor containers
- [ ] Implement container checkpointing (CRIU)
- [ ] Use init containers for common setup tasks
- [ ] Optimize Python import times
- [ ] Consider using GraalVM for Python (when stable)

## Monitoring and Observability

### CloudWatch Integration (From 5-day-metr Day 2)
- [ ] Add custom CloudWatch metrics for evaluation status
- [ ] Implement log aggregation across all services
- [ ] Create basic alerting for:
  - [ ] Evaluation failures above threshold
  - [ ] Resource exhaustion
  - [ ] Security violations detected
  - [ ] Queue depth warnings
- [ ] Add systemd service for auto-start of platform
  - [ ] Create evaluation-platform.service
  - [ ] Enable automatic restart on failure
  - [ ] Configure proper dependencies

### Monitoring Dashboard (From 5-day-metr Day 2)
- [ ] Create comprehensive monitoring dashboard
  - [ ] Current evaluation status overview
  - [ ] Real-time resource usage graphs
  - [ ] Safety violation alerts and history
  - [ ] Queue depth and throughput metrics
  - [ ] Container health status
- [ ] Add historical trend analysis
- [ ] Export capability for metrics

### Mobile Alerting System
- [ ] Explore mobile phone alerting options
  - [ ] Research AWS SNS SMS/push notifications
  - [ ] Evaluate PagerDuty integration for on-call
  - [ ] Consider Twilio for custom alerting logic
  - [ ] Test mobile app solutions (AWS, Datadog, etc.)
- [ ] Design alert severity hierarchy
  - [ ] Critical: Security breaches, system down
  - [ ] High: Multiple evaluation failures, resource exhaustion
  - [ ] Medium: Performance degradation, queue backlog
  - [ ] Low: Informational updates
- [ ] Implement cognitive load management
  - [ ] Alert fatigue prevention strategies
  - [ ] Time-based alert suppression (quiet hours)
  - [ ] Alert deduplication and grouping
  - [ ] Escalation policies
- [ ] Create alert routing rules
  - [ ] Critical → immediate SMS/call
  - [ ] High → push notification
  - [ ] Medium → email digest
  - [ ] Low → dashboard only
- [ ] Document on-call procedures
  - [ ] Response time SLAs per severity
  - [ ] Runbooks for each alert type
  - [ ] Escalation paths
  - [ ] Post-incident review process
- [ ] Work/Life Balance Considerations
  - [ ] Define sustainable on-call rotation schedules
  - [ ] Implement "follow the sun" support model
  - [ ] Create clear boundaries for after-hours response
  - [ ] Compensation/time-off policies for on-call duty
  - [ ] Mental health support for incident responders
- [ ] Psychology of Software Ownership
  - [ ] Document "you build it, you run it" philosophy
  - [ ] Create ownership culture guidelines
  - [ ] Balance autonomy with shared responsibility
  - [ ] Define team vs individual accountability
  - [ ] Address alert fatigue and burnout prevention
- [ ] METR-Specific Considerations
  - [ ] AI safety criticality vs sustainable operations
  - [ ] Risk assessment for different evaluation types
  - [ ] Clear escalation for potential safety issues
  - [ ] Balance security paranoia with operational sanity
  - [ ] Document when to wake someone up vs wait

### Real-Time Resource Monitoring (From week-3-metr)
- [ ] CPU and memory usage graphs (live display)
  - Note: These have been broken for a while, historical display would be valuable
- [ ] Kill execution button for running evaluations

### Metrics Collection
- [ ] Add Prometheus metrics for all services
- [ ] Create Grafana dashboards for key metrics
- [ ] Implement custom metrics for evaluation performance
- [ ] Add business metrics (evaluations/hour, success rate)
- [ ] Set up alerting rules for SLO violations

### Distributed Tracing
- [ ] Implement OpenTelemetry instrumentation
- [ ] Add trace context propagation across services
- [ ] Create trace analysis dashboards
- [ ] Add performance profiling integration
- [ ] Document trace debugging workflows

## Developer Experience

### Local Development
- [ ] Create lightweight dev containers
- [ ] Implement hot-reload for all services
- [ ] Add VS Code devcontainer configuration
- [ ] Create make targets for common operations
- [ ] Improve local Kubernetes setup (kind/minikube)

### Documentation (Enhanced from 5-day-metr)
- [ ] Update README with clear setup instructions
  - [ ] Prerequisites and system requirements
  - [ ] Step-by-step local development setup
  - [ ] Production deployment guide
  - [ ] Troubleshooting common issues
- [ ] Document architecture decisions with TRACE-AI rationale
  - [ ] Why Docker over alternatives
  - [ ] Why microservices architecture
  - [ ] Security design philosophy
  - [ ] Performance trade-offs
- [ ] Create comprehensive security architecture deep-dive
  - [ ] Threat model documentation
  - [ ] Defense layers explanation
  - [ ] Security testing procedures
  - [ ] Incident response plan
- [ ] Create architecture decision records (ADRs)
- [ ] Add API client SDKs (Python, TypeScript)
- [ ] Create video walkthroughs of key features
- [ ] Add troubleshooting guides
- [ ] Create onboarding checklist for new developers

### Advanced Frontend Debugging Features (From week-3-metr)
- [ ] Note: Evaluate how much we value these debugging features
- [ ] URL Parameter Debug Mode - Enable debug logging via `?debug=true`
- [ ] Temporary log level override - Allow support staff to enable debug logs without code changes
- [ ] Session-based debug mode - Remember debug preference for troubleshooting sessions
- [ ] Debug info overlay - Show connection status, API latency, queue depth in corner
- [ ] See frontend logger implementation at `/frontend/src/utils/logger.ts`

### Code Quality (From 5-day-metr Day 5)
- [ ] Remove all debug code and console.logs
- [ ] Add meaningful comments to complex logic
- [ ] Ensure consistent code style across all services
- [ ] Run linters and fix all warnings
  - [ ] Python: ruff, mypy, black
  - [ ] TypeScript: eslint, prettier
  - [ ] Dockerfiles: hadolint
- [ ] Add pre-commit hooks for code quality
- [ ] Document code conventions and style guide

### Final Code Polish (From week-4-demo)
- [ ] Remove TODOs in storage service stats/metrics (non-critical)
- [ ] Consistent code formatting needed:
  - [ ] 88 Python files need formatting
  - [ ] 68 TypeScript files need formatting
- [ ] Final code review for production readiness
- [ ] Ensure no commented-out code in critical paths
- [ ] Verify all critical features have proper error handling

### CI/CD Optimizations
- [ ] Add Python dependency caching to GitHub Actions workflows
  - [ ] Cache pip dependencies in generate-openapi-spec.yml
  - [ ] Use actions/setup-python cache option for faster builds
  - [ ] Cache between workflow runs to reduce install time from ~80s to ~5s
  - [ ] Apply same caching strategy to deploy-compose.yml if needed

### CI/CD Pipeline for Base Image (From week-3-metr)
- [ ] Build crucible-base in GitHub Actions
- [ ] Push to container registry (ECR/DockerHub)
- [ ] Tag with git SHA and version
- [ ] Update service Dockerfiles to use registry image
- [ ] **Security**: Automated scanning of all images

## Platform Features

### Frontend Evaluation History (From 7-day-metr Day 5)
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

### Exit Code Documentation Links
- [ ] Make exit codes in the UI clickable to provide instant help
  - [ ] Update `RunningEvaluations.tsx` - Exit code badge display
  - [ ] Update `ExecutionMonitor.tsx` - Exit status card  
  - [ ] On click show modal/tooltip with info from `/docs/reference/exit-codes.md`
  - [ ] Example: Click "Exit: 137" → Shows "Memory Limit Exceeded (OOM)"
  - [ ] Benefits: Self-service debugging, reduced support questions
  - [ ] Priority: Medium, Effort: Small (2-4 hours)

### Monaco Editor Enhancements (From week-3-metr)
- [ ] Verify pre-submission syntax validation is implemented
- [ ] Link errors to editor line numbers
- [ ] Common error explanations for frequent errors
- [ ] Auto-save to localStorage
- [ ] Recent submissions history
- [ ] Memory limit selector (256MB - 2GB)
- [ ] Python version selector

### Evaluation Enhancements
- [ ] Add support for multi-file evaluations
- [ ] Implement evaluation templates/presets
- [ ] Add collaborative features (sharing, comments)
- [ ] Create evaluation history and versioning
- [ ] Add support for custom base images

### User Management
- [ ] Implement proper authentication (OAuth2/OIDC)
- [ ] Add role-based access control (RBAC)
- [ ] Create user quotas and limits
- [ ] Add audit logging for all actions
- [ ] Implement API key management

## Internal Service Authentication Strategy (From 7-day-metr Section 8)

### Current State
- Currently using one shared API key for all internal services
- Simple but not ideal for production environments

### Authentication Strategy Options
- [ ] **No auth for internal services** (Kubernetes pattern with network policies)
  - Rely on network isolation and Kubernetes NetworkPolicies
  - Services trust each other within the cluster
  - External access controlled at ingress
  - Common pattern in Kubernetes environments
  
- [ ] **Service mesh with mTLS** (Istio/Linkerd)
  - Automatic mutual TLS between services
  - Service identity verification
  - Zero-trust networking
  - Observability and traffic management included
  
- [ ] **Service-specific API keys with key rotation**
  - Each service gets unique API key
  - Implement key rotation mechanism
  - Store keys in Kubernetes secrets
  - More complex but granular control
  
- [ ] **JWT tokens with service accounts**
  - Services authenticate with JWT tokens
  - Token expiration and refresh
  - Can integrate with existing auth system
  - Standard OAuth2/OIDC patterns

### Implementation Considerations
- [ ] Evaluate based on security requirements
- [ ] Consider operational complexity
- [ ] Plan migration from current shared key
- [ ] Document chosen approach thoroughly
- [ ] Create runbooks for key rotation (if applicable)

## Code Cleanup and Refactoring

### API Service Naming
- [ ] Rename `microservices_gateway.py` to `app.py` for consistency
  - Current name is verbose and doesn't follow Python service conventions
  - All other services use `app.py` as their main file
  - Would align with standard FastAPI project structure
  - Update imports in Dockerfile and any references
  - Consider during next major refactor to avoid breaking changes

### Python Module Naming Convention
- [ ] Rename hyphenated directories to Python-compatible module names
  - [ ] `storage-service` → `storage_service`
  - [ ] `executor-service` → `executor_service`
  - [ ] `celery-worker` → `celery_worker`
  - [ ] `storage-worker` → `storage_worker`
  - [ ] `load-tests` → `load_tests`
  - [ ] `github-integration` → `github_integration`
  - [ ] Update all Docker Compose files for new paths
  - [ ] Update Dockerfiles and COPY commands
  - [ ] Update GitHub Actions workflows
  - [ ] Update shell scripts (start-platform.sh, etc.)
  - [ ] Fix all Python imports to use clean module paths
  - [ ] Remove sys.path hacks from export scripts
  - [ ] See detailed migration plan: [rename-hyphenated-directories.md](/docs/planning/week-5-tasks/rename-hyphenated-directories.md)

### Other Cleanup Tasks
- [ ] Standardize error response formats across all services
- [ ] Consolidate duplicate configuration constants
- [ ] Remove deprecated endpoints after migration period
- [ ] Refactor global Redis clients to use app.state or dependency injection
- [ ] Fix OpenAPI export in read-only containers (serve via endpoint only)
- [ ] Fix startup 503 errors with proper readiness checks

### Shared Contracts Implementation (From week-3-metr)
- [ ] Inspect if there's anything left on the migration status for shared contracts
- [ ] Create `/shared/` directory structure:
  - [ ] `/types/` - OpenAPI schemas for shared types
  - [ ] `/constants/` - Security limits, event channels
  - [ ] `/docker/` - Shared base images
  - [ ] `/generated/` - Language-specific generated code
- [ ] Complete migration strategy to fix status value inconsistencies
- [ ] Ensure type safety across service boundaries

### Storage Backend Improvements (From week-3-metr)
- [ ] Verify if we still need or want these improvements (evaluate value)
- [ ] Add efficient count_evaluations method to all storage backends
- [ ] FileStorage: Use os.listdir() or glob for efficient counting
- [ ] MemoryStorage: Use len() for O(1) count
- [ ] Ensure all backends implement count_evaluations(status: Optional[str] = None)

### React Query Improvements (From week-4-demo)
- [ ] Investigate React Query invalidation patterns
  - Current polling + cache invalidation causes request storms
  - See `docs/react-query-invalidation-patterns.md` for approaches
- [ ] Consider WebSockets/SSE for real-time updates
  - Replace polling to eliminate cache invalidation complexity
- [ ] Improve batch submission
  - Current implementation lacks rate limiting for large batches
  - See `docs/batch-submission-patterns.md` for better patterns

### Type Generation Architecture Fix (From week-4-demo)
- [ ] Fix type generation architecture
  - Currently takes 45 minutes to modify a shared type
  - Need direct YAML→TypeScript generation
  - See `docs/proposals/type-separation-architecture.md`
- [ ] Update JavaScript/TypeScript generator to match Python capabilities:
  - [ ] Auto-discover and process all YAML files
  - [ ] Generate interfaces/types (not just enums)
  - [ ] Handle cross-file references
  - [ ] Match the generic approach of the Python generator
  - [ ] See `docs/development/python-vs-js-generators.md` for comparison

## Deferred Items (Intentionally Postponed)

### Until Kubernetes Migration
- [ ] ~~Dynamic image selection~~ (security risk)
- [ ] ~~Complex resource allocation~~ (K8s handles better)
- [ ] ~~Multi-tenancy isolation~~ (needs K8s namespaces)
- [ ] ~~Image registry integration~~ (K8s native support)

### Until Production Requirements Clear
- [ ] ~~High availability setup~~ (needs SLA definition)
- [ ] ~~Disaster recovery plan~~ (needs RTO/RPO targets)
- [ ] ~~Compliance certifications~~ (needs regulatory context)
- [ ] ~~Cost optimization~~ (needs usage patterns)

## Evaluation State Management

### Immediate Fix - State Machine Implementation
- [x] Implement state machine approach for evaluation status updates
  - [x] Define terminal states (completed, failed, cancelled)
  - [x] Add validation to prevent transitions from terminal states
  - [x] Log and ignore invalid state transitions
  - [ ] Add tests for out-of-order event scenarios
  - [x] Document state transition rules

### Executor Event Ordering Fix (High Priority)
- [ ] Rerun 50/100 load test to verify provisioning→completed fix
  - [ ] Run: `source venv/bin/activate && MONITOR_MODE=redis python tests/integration/test_load.py 50 100 600`
  - [ ] Verify 100% success rate (no stuck evaluations)
  - [ ] Update performance-metrics.md with results
- [ ] Implement robust event ordering in executor service
  - [ ] Design and implement event queue with sequence numbers
  - [ ] Ensure events are published in correct order (provisioning → running → completed)
  - [ ] Add retry logic for rejected state transitions
  - [ ] Monitor and log edge cases (e.g., provisioning → completed)
  - [ ] See detailed analysis: [executor-event-ordering.md](/docs/architecture/executor-event-ordering.md)
- [ ] Add integration tests for fast-execution race conditions
  - [ ] Test evaluations that complete in < 100ms
  - [ ] Test high concurrency scenarios
  - [ ] Verify no evaluations get stuck in non-terminal states

### State Machine Adoption Across Services
- [ ] Update storage-service to use state machine validation
  - [ ] PUT `/evaluations/{id}` endpoint should validate transitions
  - [ ] Consider making validation mandatory vs optional
- [ ] Update API service to use state machine
  - [ ] Evaluation creation and updates
  - [ ] Consider client-side validation helpers
- [ ] Update Celery worker to use state machine
  - [ ] Task status updates should respect state rules
  - [ ] Handle retry scenarios properly
- [ ] Add state machine validation to executor service
  - [ ] Validate before publishing status events
  - [ ] Prevent invalid event publication at source

### Platform Monitoring Infrastructure
- [ ] Create unified evaluation lifecycle monitoring
  - [ ] Design consolidated event stream with guaranteed ordering
  - [ ] Add state machine-aware monitoring API endpoint
  - [ ] Implement WebSocket endpoint for real-time validated state changes
  - [ ] Create evaluation lifecycle hooks for testing/monitoring
- [ ] Refactor test_load.py after monitoring infrastructure
  - [ ] Remove workaround of checking Redis then verifying against DB
  - [ ] Use platform's unified monitoring hooks instead
  - [ ] Simplify to single source of truth for evaluation status
  - [ ] Consider creating a test utilities library for common patterns

### Future Architecture - Workflow Orchestration
- [ ] Evaluate workflow orchestration platforms
  - [ ] POC with Temporal for complex evaluation workflows
  - [ ] Compare with current Celery implementation
  - [ ] Design migration strategy from Celery to Temporal
  - [ ] Document benefits for long-running evaluations
- [ ] Implement Kubernetes-native evaluation management
  - [ ] Design Evaluation CRDs (Custom Resource Definitions)
  - [ ] Build Kubernetes operator for evaluation lifecycle
  - [ ] Use Kubernetes events for state tracking
  - [ ] Integrate with service mesh for observability
- [ ] Add event sourcing for critical audit trails
  - [ ] Design event store schema
  - [ ] Implement append-only event log
  - [ ] Build event replay capabilities
  - [ ] Add cryptographic signatures for non-repudiation

### Related Documentation
- See [Evaluation State Management Architecture](/docs/architecture/evaluation-state-management.md) for detailed analysis

## Demo & Presentation Materials

### Performance Metrics Documentation Completion (From week-4-demo)
- [ ] Complete all placeholders in performance-metrics.md:
  - [ ] Rerun 50/100 load test with provisioning→completed fix (expect 100% success)
  - [ ] Run resilience tests and record actual recovery times:
    - [ ] Queue Worker restart recovery time (expected: 5-10s)
    - [ ] Celery Worker failure recovery behavior
    - [ ] Storage Service outage handling results
    - [ ] Network partition test results
  - [ ] Run error handling tests:
    - [ ] Invalid syntax test (submit `print(`)
    - [ ] Infinite loop test (submit `while True: pass`)
    - [ ] Memory exhaustion test (submit `x = [0] * 10**9`)
    - [ ] Network attempt test (submit `import requests; requests.get(...)`)
    - [ ] Container crash test (submit `import sys; sys.exit(1)`)
  - [ ] Resource monitoring under stress:
    - [ ] Run sustained load test (60s) with resource monitoring
    - [ ] Capture peak CPU usage per service
    - [ ] Capture peak memory usage per service
  - [ ] Scaling tests:
    - [ ] Test with different executor pool sizes (1, 3, 5)
    - [ ] Measure throughput vs executor count
    - [ ] Document horizontal scaling potential

### Future Demo Enhancements
- [ ] Create fallback recorded videos for each scenario
- [ ] Automated demo suite advanced features:
  - [ ] Script all demo scenarios for reproducibility
  - [ ] Create demo runner that executes scenarios in sequence
  - [ ] Add timing and transitions between demos
  - [ ] Include error recovery if demo fails
  - [ ] Generate performance metrics from demo runs
  - [ ] Create both interactive and fully automated modes
  - [ ] Ensure suite is not too expansive but covers key features
  - [ ] Document how to run demo suite for presentations
- [ ] Demo video advanced production:
  - [ ] Introduction to the security challenges of AI evaluation
  - [ ] Show real-time monitoring and status updates
  - [ ] Demonstrate safety features (failed attack attempts)
  - [ ] Architecture overview with diagrams
  - [ ] Performance under load demonstration
  - [ ] "Hello World" evaluation success
  - [ ] Resource exhaustion handling
  - [ ] Network isolation verification
  - [ ] ML model evaluation (when working)
  - [ ] Concurrent evaluation handling
  - [ ] Polish demo environment for consistency
- [ ] Polish demo environment:
  - [ ] Pre-populate with interesting evaluations
  - [ ] Ensure consistent performance
  - [ ] Test all features before recording
- [ ] Professional demo production:
  - [ ] Edited videos with transitions
  - [ ] Voice-over narration
  - [ ] Multiple scenario compilations

### Interview Preparation Package (From 5-day-metr)
- [ ] Create comprehensive `INTERVIEW_NOTES.md`
  - [ ] Key architectural decisions and rationale
  - [ ] Trade-offs made and alternatives considered
  - [ ] Security design philosophy
  - [ ] Performance characteristics and limits
  - [ ] Future improvements roadmap
- [ ] Prepare answers to likely questions
  - [ ] "Why did you choose X over Y?"
  - [ ] "How would you handle scale to 1000x?"
  - [ ] "What security threats concern you most?"
  - [ ] "How would you extend this for LLM evaluation?"
  - [ ] "What would you do differently with more time?"
- [ ] Create talking points document
  - [ ] Platform's unique security features
  - [ ] Production-ready aspects
  - [ ] Monitoring and observability story
  - [ ] Evolution from MVP to current state
  - [ ] Kubernetes migration benefits

### Interview Prep Schedule and Protocols
- [ ] Revisit interview questions and create study schedule
- [ ] Develop different protocols to hone platform knowledge:
  - [ ] Daily architecture review sessions
  - [ ] Mock interview scenarios
  - [ ] Deep-dive sessions on specific components
  - [ ] Practice explaining complex features simply
- [ ] Create flashcards for key concepts
- [ ] Schedule practice sessions with timers
- [ ] Document weak areas for focused study

### Presentation Materials & Slides (From 7-day-metr Section 10)
- [ ] Refine presentation narrative
  - [ ] Problem → Solution → Implementation → Results flow
  - [ ] Focus on METR's specific needs
  - [ ] Highlight key engineering decisions
- [ ] Create technical deep-dive slides
  - [ ] Architecture diagrams with clear annotations
  - [ ] Security model visualization
  - [ ] Performance benchmarks and metrics
  - [ ] Scaling demonstration with real data
- [ ] Add demo screenshots/videos
  - [ ] Capture key user workflows
  - [ ] Show monitoring dashboards in action
  - [ ] Demonstrate security features
- [ ] Prepare comprehensive speaker notes
  - [ ] Key points for each slide
  - [ ] Anticipated questions and answers
  - [ ] Time allocations per section
- [ ] Create polished slide deck (20-30 slides)
  - [ ] Executive summary (2-3 slides)
  - [ ] Problem space and challenges (3-4 slides)
  - [ ] Solution architecture (5-6 slides)
  - [ ] Implementation details (4-5 slides)
  - [ ] Security deep dive (3-4 slides)
  - [ ] Performance and scaling (2-3 slides)
  - [ ] Future roadmap (2-3 slides)
  - [ ] Q&A preparation slides

### Demo Preparation Materials (From week-3-metr)
- [ ] One-page architecture summary
- [ ] Performance benchmark report
- [ ] Security assessment summary
- [ ] Cost analysis document
- [ ] Dedicated demo instance setup
- [ ] Cover letter preparation

### Fresh Clone Testing (From week-4-demo)
- [ ] Test platform works from fresh clone in < 5 minutes:
  ```bash
  git clone [repo]
  cd [repo]
  docker-compose up -d
  # Should work in < 5 minutes
  ```
- [ ] Verify all documentation links work
- [ ] Check for any broken features
- [ ] Test quick start guide accuracy
- [ ] Ensure all demo scenarios work from fresh install

## Wiki Knowledge Graph - Advanced Features (From week-3-metr)

### Week 2: AI Safety Integration
- [ ] Security concept ontology
- [ ] Cross-project linking (AI Safety Compiler)
- [ ] Learning path generation

### Week 3: Visualization
- [ ] Interactive knowledge graph with react-force-graph
- [ ] Graph-based navigation
- [ ] Concept relationship mapping

### Wiki Documentation Visibility
- [ ] Ensure every document in /docs is visible in the app
  - [ ] Audit all documentation files
  - [ ] Add missing documents to wiki index
  - [ ] Verify navigation works for all docs
  - [ ] Test deep linking to specific sections

## Slides System Security (From week-3-metr)
- [ ] Remove dangerouslySetInnerHTML from slides system
- [ ] Ensure all markdown rendering is XSS-safe

## Slides Polish and Inspection
- [ ] Polish all presentation slides
  - [ ] Review content for accuracy
  - [ ] Ensure consistent formatting
  - [ ] Check all diagrams and images
  - [ ] Verify code examples are up-to-date
- [ ] Inspect slides for demo readiness
  - [ ] Test all interactive elements
  - [ ] Ensure smooth navigation
  - [ ] Verify mobile responsiveness

## Public Repository Preparation (From week-3-metr)

### Repository Structure
- [ ] Create clean public repository structure
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

### Repository Cleanup
- [ ] Clean commit history
  - [ ] Squash development commits
  - [ ] Clear commit messages
    - [ ] Add co-authors appropriately
- [ ] Security audit
  - [ ] Remove all secrets
  - [ ] Remove internal URLs
  - [ ] Remove personal information
  - [ ] Add security policy

### Community Files
- [ ] Code of conduct
- [ ] Contributing guidelines
- [ ] Issue templates
- [ ] Pull request template

### Documentation Completion (From week-4-demo)

## Monitoring & Observability Improvements (From week-4-demo)

### Alternative Monitoring Solutions
- [ ] Evaluate alternatives to Flower
  - Flower lacks granular permissions and proper RBAC
  - Consider Prometheus + Grafana for production
  - Document migration path from Flower
- [ ] Health check standardization
  - All services use different approaches (curl, httpx, urllib, nc)
  - Standardize on single method across services
- [ ] Service dependency checks
  - Make health checks more sophisticated
  - Check broker connectivity, not just port availability

### Performance Optimization
- [ ] Connection pooling configuration
  - Redis connections need proper pooling
  - PostgreSQL connections need pooling
- [ ] Implement caching strategy
  - Redis is available but underutilized
  - Design caching layer for common queries

## Developer Experience Enhancements (From week-4-demo)

### Development Environment
- [ ] Hot reload for Python services
  - Frontend has it, Python services require restart
  - Investigate watchdog or similar solutions
- [ ] Remote debugging setup
  - Configure debugpy for containerized services
  - Document VS Code remote debugging
- [ ] Development seeds/fixtures
  - Create sample data for development
  - Add database seeding scripts

## Security Improvements (From week-4-demo)

### Production Security
- [ ] Secrets management strategy
  - Current: Environment variables in docker-compose
  - Options: Vault, K8s secrets, AWS Secrets Manager
  - Document migration path
- [ ] Non-root users for all containers
  - Some containers still run as root
  - Create dedicated users per service
- [ ] Python type hints enforcement
  - Implement mypy strict mode across all services
  - Add to CI/CD pipeline

## Notes
- Items marked with ~~strikethrough~~ are intentionally deferred
- Tasks are roughly ordered by priority within each section
- Dependencies between tasks should be considered when planning sprints
- This list will evolve based on user feedback and production requirements