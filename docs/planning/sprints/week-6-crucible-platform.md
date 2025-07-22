# Week 6: Kubernetes Migration & Executor Evolution

## Sprint Overview
**Dates**: July 13-19, 2025  
**Focus**: Complete Kubernetes migration, implement dispatcher pattern, and plan Phase 3 executor architecture
**Goal**: Production-ready Kubernetes deployment with modern executor architecture

## Completed This Week ✅

### 1. Docker Compose to Kubernetes Migration
- [x] Migrated all services from docker-compose.yml to K8s manifests
- [x] Created StatefulSet for PostgreSQL with persistent storage
- [x] Implemented separate Redis deployments (main and Celery)
- [x] Built complete K8s overlay system for local development
- [x] Documented migration in KUBERNETES_MIGRATION_GUIDE.md

### 2. Executor Architecture Evolution
- [x] Analyzed executor patterns (static pool → Jobs → dispatcher)
- [x] Decided on stateless dispatcher service pattern
- [x] Documented decision in DISPATCHER_ARCHITECTURE_DECISION.md
- [x] Implemented dispatcher service with K8s Job creation
- [x] Removed Docker proxy dependency

### 3. Local Development Setup
- [x] Created Kind-compatible overlay with proper image handling
- [x] Fixed storage limitations (RWO vs RWX)
- [x] Implemented replica scaling for resource efficiency
- [x] Created LOCAL_DEPLOYMENT.md guide

### 4. Initial Kubernetes Deployment - Fixes Applied Round 2
- [x] Fixed dispatcher Redis connection resilience
  - [x] Implemented ResilientRedisClient with retry logic
  - [x] Fixed startup issue where Redis unavailability caused permanent failure
  - [x] Refactored from global redis_client to dependency injection pattern
- [x] Fixed dispatcher executor image detection
  - [x] Updated logic to detect SHA-tagged images from Skaffold
  - [x] Fixed NoneType errors when node images aren't populated
  - [x] Changed from looking for "sha256:" prefix to detecting hex SHA tags
- [x] Fixed RBAC permissions for dispatcher
  - [x] Added node read permissions for local development
  - [x] Used JSON patch format to add permissions without replacing existing rules
  - [x] Verified dispatcher can now query node images successfully
- [x] Fixed Redis state management tests
  - [x] Tests now pass with event-driven architecture working correctly
  - [x] Evaluations properly tracked in Redis with state transitions
  - [x] Dispatcher successfully finds and uses Skaffold's SHA-tagged executor images

## Next Sprint Tasks 🚀

### 1. Phase 3: Advanced Executor Patterns

#### 1.1 Warm Pool Implementation
- [ ] Design warm pool architecture
  - [ ] Define pool manager service
  - [ ] Implement pre-warmed container lifecycle
  - [ ] Create pool sizing algorithm
- [ ] Build pool management
  - [ ] Health checking for warm containers
  - [ ] Automatic pool replenishment
  - [ ] Graceful draining on shutdown
- [ ] Performance optimization
  - [ ] Sub-second cold starts
  - [ ] Connection pooling for K8s API
  - [ ] Request batching

#### 1.2 Heterogeneous Executor Types
- [ ] Define executor classes
  - [ ] CPU-only executors (t3.micro equivalent)
  - [ ] GPU-enabled executors
  - [ ] High-memory executors
  - [ ] Network-enabled executors (for specific tests)
- [ ] Implement routing logic
  - [ ] Tag-based routing in dispatcher
  - [ ] Resource requirement detection
  - [ ] Fallback strategies
- [ ] Cost optimization
  - [ ] Spot instance support
  - [ ] Automatic right-sizing
  - [ ] Usage tracking per type

#### 1.3 Frontend Selection of Evaluation Environments
- [ ] Update Dispatcher Service API
  - [ ] Add `executor_image` field to `ExecuteRequest` model in `dispatcher_service/app.py`
  - [ ] Default to `executor-ml:latest` for backward compatibility
  - [ ] Validate requested image exists before creating job
  - [ ] Use requested image when creating Kubernetes job container
- [ ] Update API Gateway
  - [ ] Pass `executor_image` from frontend through to dispatcher service
  - [ ] Add to evaluation request schema
- [ ] Update Frontend
  - [ ] Add dropdown/selector for available evaluation environments
  - [ ] Options from `/evaluation-environments/`:
    - `executor-ml` - Standard ML environment with PyTorch, TensorFlow
    - `executor-gpu` - GPU-enabled environment (future)
    - `executor-sandbox` - High-security sandboxed environment (future)
    - `executor-minimal` - Lightweight Python-only environment (future)
  - [ ] Store selection in evaluation submission
- [ ] Create Additional Evaluation Environments
  - [ ] Build out images in `/evaluation-environments/`:
    - [ ] `executor-gpu/` - Add CUDA support
    - [ ] `executor-sandbox/` - Add gVisor or similar isolation
    - [ ] `executor-minimal/` - Stripped down for basic Python
  - [ ] Update `skaffold.yaml` to build all environments
- [ ] Update Documentation
  - [ ] Document available environments and their capabilities
  - [ ] Add security implications of each environment
  - [ ] Provide guidance on which environment to use

**Note**: Currently hardcoded in `dispatcher_service/app.py` line 27: `EXECUTOR_IMAGE = os.getenv("EXECUTOR_IMAGE", "executor-ml:latest")`

#### 1.4 Scale-to-Zero Architecture
- [ ] Implement KEDA integration
  - [ ] Install KEDA operator
  - [ ] Create ScaledObject for dispatcher
  - [ ] Define scaling metrics
- [ ] Queue-based autoscaling
  - [ ] Monitor Celery queue depth
  - [ ] Scale dispatcher based on pending evaluations
  - [ ] Implement cooldown periods
- [ ] Cost tracking
  - [ ] Zero-cost when idle
  - [ ] Fast scale-up on demand
  - [ ] Predictive scaling based on patterns

**📚 Documentation**: See [Dispatcher Autoscaling Guide](../../DISPATCHER_SCALING_GUIDE.md) for detailed implementation approaches and recommendations.

### 2. Production Readiness

#### 2.1 Type Safety and Interface Contracts
- [ ] Create shared types between services
  - [ ] Define TypeScript-style interfaces for dispatcher API
    - [ ] ExecuteRequest/Response types
    - [ ] JobStatus response types
    - [ ] Logs response types
  - [ ] Create Python shared types package
    - [ ] Pydantic models for request/response validation
    - [ ] Share between dispatcher and celery worker
    - [ ] Ensure type consistency across services
  - [ ] Generate OpenAPI spec for dispatcher service
    - [ ] Add OpenAPI documentation to dispatcher endpoints
    - [ ] Create export script similar to other services
    - [ ] Include in CI/CD OpenAPI generation workflow

#### 2.2 Observability
- [ ] Implement comprehensive monitoring
  - [ ] Prometheus metrics for dispatcher
  - [ ] Grafana dashboards for evaluation metrics
  - [ ] Distributed tracing with OpenTelemetry
- [ ] Alerting
  - [ ] Job failure rates
  - [ ] Resource exhaustion
  - [ ] Security anomalies

#### 2.2 Security Hardening
- [ ] Network policies
  - [ ] Restrict dispatcher ingress to Celery only
  - [ ] Isolate evaluation Jobs completely
  - [ ] Implement egress controls
- [ ] Pod Security Standards
  - [ ] Enforce restricted security context
  - [ ] Implement admission controllers
  - [ ] Regular security scanning

#### 2.3 Disaster Recovery
- [ ] Backup strategies
  - [ ] Automated PostgreSQL backups
  - [ ] Job history archival
  - [ ] Configuration backup
- [ ] Multi-region considerations
  - [ ] Cross-region replication
  - [ ] Failover procedures
  - [ ] Data locality compliance

### 3. Testing & Validation

#### 3.1 Test Classification for K8s Migration
- [x] Add pytest markers for test classification
  - [x] Define blackbox, whitebox, and graybox markers in conftest.py
  - [x] Create TEST_CLASSIFICATION.md documenting all tests
  - [x] Build add_test_markers.py script for automated marking

**📚 Reference**: See [Testing Taxonomy: Black Box, White Box, and Grey Box](../../testing/testing-taxonomy.md) for detailed explanation of testing philosophies and the spectrum from black box to white box testing.

**🏗️ Architecture Analysis**: See [Kubernetes Test Architecture Analysis](../../testing/kubernetes-test-architecture-analysis.md) for a comprehensive analysis of our Kubernetes-native testing approach, including pros/cons and architectural trade-offs.

**Purpose**: This testing taxonomy document should guide our future test development. We should aim to develop tests using the various categories described there, particularly:
- **Informed Black Box Testing** for API and integration tests that leverage our knowledge while maintaining loose coupling
- **Grey Box Testing** for performance and behavior tests that verify emergent properties without coupling to implementation
- **Strategic White Box Testing** only where deep implementation testing provides clear value

This approach will help us maintain more resilient tests that survive implementation changes while still providing comprehensive coverage.
- [ ] Apply markers to all test files
  - [ ] Run `python tests/add_test_markers.py --apply`
  - [ ] Verify black box tests still pass in K8s environment
  - [ ] Identify white box tests that need rewriting
- [ ] Update white box tests for Kubernetes
  - [ ] Replace Docker-specific tests with K8s equivalents
  - [ ] Update service discovery for K8s DNS
  - [ ] Fix file paths for K8s persistent volumes

#### 3.2 Load Testing
- [ ] Create load testing framework
  - [ ] Simulate 1000+ concurrent evaluations
  - [ ] Test dispatcher scaling
  - [ ] Measure end-to-end latency
- [ ] Chaos engineering
  - [ ] Node failures
  - [ ] Network partitions
  - [ ] Resource exhaustion

#### 3.3 Integration Testing
- [ ] Full stack K8s tests
  - [ ] API → Celery → Dispatcher → Job flow
  - [ ] Error handling paths
  - [ ] Timeout scenarios
- [ ] Migration validation
  - [ ] Compare Docker Compose vs K8s behavior
  - [ ] Performance benchmarks
  - [ ] Resource utilization analysis

### 4. Event-Based Status Updates

#### 4.1 Replace Polling with Kubernetes Informers
- [ ] Implement Kubernetes watch/informer pattern
  - [ ] Create informer in dispatcher service for Job status changes
  - [ ] Use field selectors to watch specific evaluation Jobs
  - [ ] Handle reconnection and missed events gracefully
- [ ] Publish events on Job state transitions
  - [ ] Emit Redis events when Jobs transition states (Pending → Running → Succeeded/Failed)
  - [ ] Include all relevant metadata (timestamps, exit codes, resource usage)
  - [ ] Ensure events are published exactly once per transition
- [ ] Update Celery worker to consume events
  - [ ] Subscribe to Job state change events from Redis
  - [ ] Remove or reduce polling frequency (keep as fallback only)
  - [ ] Handle out-of-order events appropriately
- [ ] Performance improvements
  - [ ] Measure latency reduction (target: <1s vs current 10s polling)
  - [ ] Reduce unnecessary API calls to Kubernetes
  - [ ] Lower CPU usage in Celery workers

#### 4.2 Implement Event Publishing from Evaluations
- [ ] Create event wrapper for executor images
  - [ ] Implement `event_wrapper.py` with Redis integration
  - [ ] Update executor Dockerfiles to include wrapper
  - [ ] Pass evaluation ID and Redis URL as environment variables
- [ ] Update dispatcher service
  - [ ] Pass `USER_CODE` as environment variable to Jobs
  - [ ] Configure Redis connection details in Job spec
  - [ ] Add evaluation ID to Job metadata/labels
- [ ] Modify Celery worker
  - [ ] Subscribe to Redis evaluation events
  - [ ] Update status on event receipt
  - [ ] Keep polling as fallback (reduced frequency)
- [ ] Enable real-time progress updates
  - [ ] Publish evaluation start event when code begins executing
  - [ ] Stream output chunks as they're produced
  - [ ] Send completion event with final results
- [ ] Test event flow end-to-end
  - [ ] Verify events published from Jobs
  - [ ] Confirm Celery receives and processes events
  - [ ] Monitor latency improvements

**📚 Documentation**: See [Event-Based Status Updates Architecture](../../architecture/event-based-status-updates.md) for implementation details and design rationale.

**Benefits of Event-Driven Architecture**:
- **Reduced Latency**: Near-instant status updates vs 10-second polling intervals
- **Lower Resource Usage**: No constant polling of Kubernetes API
- **Better User Experience**: Real-time feedback on evaluation progress
- **Scalability**: Event streams handle high load better than polling
- **Future-Proof**: Enables features like live output streaming, progress bars, etc.

### 5. Development Environment Improvements

#### 5.1 Investigate Kubernetes Code Sync Issues
- [x] Test Skaffold cache busting with CACHEBUST build arg
  - [x] Implemented in default profile with {{.TIMESTAMP}}
  - [x] Disabled cacheFrom for reliable builds
  - [x] Forces new deployments on every build
- [x] Fix multi-stage Docker builds for proper sync support
  - [x] Updated all services to use proper strip directives
  - [x] Changed dispatcher context from `dispatcher-service` to `.`
  - [x] Sync now works correctly with updated Dockerfiles
- [x] Implement container restart hooks after sync
  - [x] Test kill signal approach - pkill not available in containers
  - [x] Explore graceful restart options - uvicorn doesn't support SIGHUP without gunicorn
  - [x] Create fallback procedures - documented removal of hooks as best approach
- [ ] Benchmark alternative solutions
  - [ ] Volume mounts for local Kind/Minikube
  - [ ] Compare sync reliability across methods
  - [ ] Document pros/cons of each approach
- [x] Create developer runbook
  - [x] Documented in kubernetes-code-sync-solutions.md
  - [x] Cache busting is automatic with CACHEBUST={{.TIMESTAMP}}
  - [x] Uvicorn --reload handles file sync automatically
  - [x] No manual restart needed

**📚 Reference**: See [Kubernetes Code Sync Solutions](../../development/kubernetes-code-sync-solutions.md) for detailed analysis including uvicorn reload behavior

- [x] Remove sync hooks from Skaffold config
  - [x] Hooks are failing due to missing pkill command
  - [x] Uvicorn doesn't support SIGHUP reload without gunicorn
  - [x] File sync is working without the hooks

- [x] Add --reload flag to uvicorn services for local development
  - [x] Created uvicorn-reload-patch.yaml in k8s/overlays/local
  - [x] Applied to api-service, storage-service, and dispatcher
  - [x] Enables automatic reloading when files are synced
  - [x] Only affects local development, not production

#### 5.2 Debug Kubernetes API JSON Output Issue
- [x] Identify root cause of dict repr in test output
  - [x] Manual YAML jobs produce correct JSON
  - [x] Jobs created via Kubernetes Python API produce dict repr
  - [x] Confirmed with test_k8s_api_job.py test
- [ ] Test different command formats to fix output
  - [ ] Shell wrapper approach (/bin/sh -c)
  - [ ] Direct command without variables
  - [ ] File-based output to bypass stdout
  - [ ] Command escaping variations
- [ ] Apply fix to dispatcher service
  - [ ] Update job creation command format
  - [ ] Ensure all tests pass with proper JSON
  - [ ] Document the solution

**📚 Reference**: See [Kubernetes API JSON Output Issue](../../debugging/kubernetes-api-json-output-issue.md) for investigation details

### 6. Documentation & Training

#### 6.1 Kubernetes Skills Development
- [ ] Practice kubectl commands
  - [ ] Basic operations: get, describe, logs, exec
  - [ ] Resource management: apply, delete, edit
  - [ ] Debugging: port-forward, cp, top
  - [ ] Advanced: jsonpath queries, custom columns
- [ ] Learn Kubernetes DNS and service discovery
  - [ ] Understand ClusterIP vs NodePort vs LoadBalancer
  - [ ] Practice service-to-service communication
  - [ ] Debug DNS resolution issues
  - [ ] Understand headless services for StatefulSets

#### 6.2 Operational Runbooks
- [ ] Deployment procedures
- [ ] Troubleshooting guides
- [ ] Scaling playbooks
- [ ] Incident response

#### 6.3 Architecture Documentation
- [ ] Update system diagrams
- [ ] Document decision rationale
- [ ] Create onboarding guides
- [ ] Record architecture decision records (ADRs)

## Technical Decisions Made

### Dispatcher Pattern
- **Decision**: Separate stateless dispatcher service over sidecar
- **Rationale**: Better security isolation, independent scaling, cleaner architecture
- **Trade-off**: Additional network hop (~50ms) vs significant flexibility gains

### No More Docker-in-Docker
- **Decision**: Pure Kubernetes Jobs instead of Docker containers
- **Rationale**: Better resource management, native K8s monitoring, improved security
- **Trade-off**: Can't use Docker Compose locally for full testing

### Phase 3 Architecture Vision
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────┐
│     API     │
└──────┬──────┘
       │
┌──────▼──────┐     ┌─────────────┐
│   Celery    │────▶│ Dispatcher  │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Decision   │
                    │   Engine    │
                    └──────┬──────┘
                           │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐ ┌────────▼──────┐ ┌───────▼──────┐
│  Warm Pool   │ │ GPU Executors │ │   K8s Jobs   │
│  (fast start)│ │  (ML tasks)   │ │  (standard)  │
└──────────────┘ └───────────────┘ └──────────────┘
```

## Risks & Mitigations

### Risk: Warm Pool Complexity
- **Impact**: Increased operational overhead
- **Mitigation**: Start with simple pool, iterate based on metrics

### Risk: Cost Overruns with GPU Executors
- **Impact**: Unexpectedly high cloud bills
- **Mitigation**: Implement hard quotas, cost alerts, automatic shutdown

### Risk: Migration Disruption
- **Impact**: Evaluation downtime during cutover
- **Mitigation**: Blue-green deployment, gradual traffic shift

## Success Metrics

1. **Performance**
   - Evaluation start latency < 2s (warm pool)
   - Dispatcher availability > 99.9%
   - Zero dropped evaluations

2. **Cost**
   - 50% reduction in idle resource costs
   - < $0.01 per evaluation
   - Zero cost when idle (scale-to-zero)

3. **Security**
   - Zero container escapes
   - All pods pass security policies
   - Complete audit trail

## Next Week Preview

**Week 7 Focus**: Production deployment and monitoring
- Deploy to staging environment
- Implement full observability stack
- Begin load testing
- Create operational documentation

## Lessons Learned

1. **Kubernetes Native is Better**: Moving away from Docker-in-Docker simplified everything
2. **Stateless Services Scale**: Dispatcher pattern enables horizontal scaling
3. **Overlays Are Powerful**: Kustomize overlays made local/prod differences manageable
4. **Security First**: Each component with minimal permissions improves overall security

### 7. Security Tasks

#### 7.1 Secure Output Parsing for Kubernetes Jobs
- [ ] Implement secure parsing of Kubernetes job outputs
  - [ ] Replace current approach with YAML-based job creation
  - [ ] Or implement streaming API with `_preload_content=False`
  - [ ] Add resource limits for parsing operations
  - [ ] Consider structured output protocols
- [ ] Address parser differential attacks
  - [ ] Standardize on single parsing method
  - [ ] Add validation for ambiguous inputs
  - [ ] Implement timeout and size limits

**📚 Reference**: See [Kubernetes Output Parsing Security Analysis](../../security/kubernetes-output-parsing-security.md)

#### 7.2 Adversarial Output Storage Security
- [ ] Review log storage security implications
  - [ ] Implement size limits at storage layer
  - [ ] Add character validation before storage
  - [ ] Consider separate storage for adversarial outputs
- [ ] Protect log aggregation systems
  - [ ] Configure parser limits in Fluentd/Elasticsearch
  - [ ] Implement circuit breakers for malformed logs
  - [ ] Add monitoring for suspicious patterns
- [ ] Harden log viewing interfaces
  - [ ] Add resource limits to kubectl logs operations
  - [ ] Implement safe preview modes for large outputs
  - [ ] Add warnings for potentially malicious content

**📚 Reference**: See [Kubernetes Output Parsing Security Analysis](../../security/kubernetes-output-parsing-security.md#log-storage-risk-analysis)

### 8. Comprehensive Network Isolation

#### 8.1 Implement Zero-Trust Network Architecture
- [ ] Create default deny NetworkPolicy for entire namespace
  - [ ] Block all ingress/egress by default
  - [ ] Allow only DNS lookups for service discovery
  - [ ] Document security model clearly
- [ ] Create individual NetworkPolicies for each service
  - [ ] API service: needs ingress from ingress controller
  - [ ] Storage service: needs ingress from API, egress to Redis
  - [ ] Celery worker: needs egress to storage/dispatcher
  - [ ] Dispatcher: needs Kubernetes API access
  - [ ] PostgreSQL/Redis: only from specific services
- [ ] Handle image pulling in production
  - [ ] Set up private container registry
  - [ ] Pre-pull images to nodes
  - [ ] Or use ImagePullPolicy: IfNotPresent with pre-cached images
  - [ ] Document deployment process

#### 8.2 Test Network Isolation Thoroughly
- [ ] Create test suite for NetworkPolicies
  - [ ] Test that denied pods cannot access network
  - [ ] Test that allowed services can communicate
  - [ ] Test DNS resolution works for all pods
  - [ ] Test that new pods without labels are blocked
- [ ] Verify CNI plugin support
  - [ ] Check if Kind supports NetworkPolicies
  - [ ] Install Calico or other CNI if needed
  - [ ] Test in production-like environment
- [ ] Create monitoring for policy violations
  - [ ] Log dropped packets
  - [ ] Alert on unexpected connection attempts
  - [ ] Regular audit of network flows

**📚 Documentation**: Create comprehensive network security guide covering:
- Zero-trust principles
- NetworkPolicy best practices
- Testing procedures
- Troubleshooting guide

### 9. Kubernetes API Output Investigation

#### 9.1 Deep Investigation of JSON Output Bug
- [ ] Research Kubernetes Python client source code
  - [ ] Trace how commands are serialized and sent to API
  - [ ] Identify where output transformation occurs
  - [ ] Check for related issues in kubernetes-client/python repo
- [ ] Test with different Kubernetes versions
  - [ ] Test with older K8s API versions
  - [ ] Test with different Python client versions
  - [ ] Verify if issue exists in other language clients
- [ ] Explore alternative approaches
  - [ ] Test with exec API instead of logs API
  - [ ] Try streaming logs with follow=True
  - [ ] Investigate _preload_content=False for raw responses

#### 9.2 Permanent Fix Implementation
- [ ] Evaluate potential solutions
  - [ ] Patch at dispatcher level to detect and fix output
  - [ ] Implement custom log retrieval mechanism
  - [ ] Consider switching to exec for output capture
  - [ ] Explore using sidecar container for output handling
- [ ] Test solution thoroughly
  - [ ] Ensure no performance impact
  - [ ] Verify works with all output types
  - [ ] Test with large outputs
- [ ] Update platform accordingly
  - [ ] Remove workarounds from tests
  - [ ] Update documentation
  - [ ] Deprecate evaluation_utils workaround

**📚 References**: 
- [Kubernetes JSON Output Issue](../../known-issues/kubernetes-json-output.md) - Current workarounds and user guidance
- [Debugging JSON Output Issue](../../debugging/debugging-json-output-issue.md) - Full investigation notes and findings
- [YAML Job Creation Approach](../../debugging/yaml-job-creation-approach.md) - Alternative implementation approach

### 10. gVisor Runtime Implementation

#### 10.1 Fix Production Deployment Blocker
- [ ] Add runtime detection to dispatcher service
  - [ ] Check if gVisor RuntimeClass exists before using it
  - [ ] Add REQUIRE_GVISOR environment variable for production
  - [ ] Log warnings when falling back to standard runtime
  - [ ] Reject requests in production without gVisor
- [ ] Create deployment-specific configurations
  - [ ] Development: Allow fallback with warnings
  - [ ] Staging: Prefer gVisor but allow fallback
  - [ ] Production: Require gVisor or fail

#### 10.2 Cloud Provider Deployment Guides
- [ ] Document GKE Sandbox deployment
  - [ ] Create Terraform module for GKE with gVisor
  - [ ] Add to CI/CD deployment pipeline
  - [ ] Test full platform on GKE Sandbox
- [ ] Document EKS custom AMI approach
  - [ ] Create Packer template for gVisor AMI
  - [ ] Document nodegroup configuration
  - [ ] Add monitoring for gVisor availability
- [ ] Create local development guide
  - [ ] Colima setup for macOS developers
  - [ ] Linux VM setup instructions
  - [ ] Kind cluster with gVisor support

#### 10.3 Security Validation
- [ ] Update filesystem isolation tests
  - [ ] Add tests for gVisor-specific isolation
  - [ ] Verify /etc/passwd is not readable
  - [ ] Test kernel isolation via /proc
- [ ] Add integration tests for RuntimeClass
  - [ ] Verify evaluation pods use gVisor
  - [ ] Test fallback behavior
  - [ ] Ensure production requirements enforced
- [ ] Create security benchmarks
  - [ ] Compare isolation with/without gVisor
  - [ ] Document attack surface reduction
  - [ ] Performance impact measurements

**📚 Documentation**: See [gVisor Production Deployment Guide](../../security/gvisor-production-deployment.md) for critical production requirements and deployment options.

**⚠️ CRITICAL**: Current code will FAIL in production without gVisor installed. This must be fixed before any production deployment.

### 11. Secure Timeout and Grace Period Implementation

#### 11.1 Implement Signal Handling in Executor
- [ ] Add SIGTERM handler to executor Python code
  - [ ] Gracefully interrupt running evaluations
  - [ ] Clean up temporary files and child processes
  - [ ] Flush audit logs before termination
  - [ ] Exit cleanly within 1 second
- [ ] Test signal handling with different timeout scenarios
  - [ ] Verify cleanup completes successfully
  - [ ] Ensure no orphaned processes
  - [ ] Validate audit log completeness

#### 11.2 Risk-Based Grace Period System
- [ ] Add risk_level field to evaluation requests
  - [ ] Define risk levels: low, medium, high, critical
  - [ ] Pass risk level through to dispatcher
  - [ ] Default to "high" for unknown sources
- [ ] Implement dynamic grace period calculation
  - [ ] Low risk: 30s grace period
  - [ ] Medium risk: 10s grace period  
  - [ ] High risk: 5s grace period
  - [ ] Critical risk: 2s grace period
- [ ] Add configuration overrides for specific use cases

#### 11.3 Grace Period Security Monitoring
- [ ] Implement shutdown behavior monitoring
  - [ ] Detect network activity during grace period
  - [ ] Monitor process spawning attempts
  - [ ] Track file system modifications
  - [ ] Log suspicious termination behavior
- [ ] Add immediate termination triggers
  - [ ] Data exfiltration attempts
  - [ ] Fork bomb detection
  - [ ] Excessive resource consumption
  - [ ] Network scanning activity
- [ ] Create security alerts for abnormal shutdown patterns

#### 11.4 Application-Level Timeout Implementation  
- [ ] Add Python-level timeout handling in executor
  - [ ] Use signal.alarm() for backup timeout
  - [ ] Implement subprocess timeout management
  - [ ] Ensure timeout fires before Kubernetes deadline
- [ ] Create timeout wrapper for user code
  - [ ] Isolate user code in subprocess
  - [ ] Monitor subprocess resource usage
  - [ ] Clean termination of subprocess tree
- [ ] Test timeout accuracy and reliability

#### 11.5 Comprehensive Audit Logging
- [ ] Implement SecurityAuditLogger class
  - [ ] Log all timeout events with full context
  - [ ] Track cleanup success/failure
  - [ ] Record resource state at termination
  - [ ] Ensure logs are flushed even during SIGKILL
- [ ] Add audit log aggregation and analysis
  - [ ] Identify patterns in timeout behavior
  - [ ] Detect potential security incidents
  - [ ] Generate security metrics

**📚 Documentation**: See [Kubernetes Timeout and Grace Period Security](../../security/kubernetes-timeout-and-grace-period-security.md) for detailed security analysis and implementation guidelines.

**⚠️ SECURITY**: Current implementation uses a fixed 1-second grace period. This is too aggressive for production use and needs to be replaced with risk-based dynamic grace periods.

### 11. Test Runner Pod Scaling and Performance

#### 11.1 Test Runner Architecture Considerations
- [ ] Evaluate scaling approaches for test runner pods
  - [ ] Current: Kubernetes Jobs (ephemeral, auto-cleanup)
  - [ ] HPA doesn't support Jobs - need alternative approaches
  - [ ] KEDA can scale Jobs based on queue metrics
  - [ ] Pre-warmed pod pools for instant test execution
- [ ] Design parallel test execution improvements
  - [ ] Current `--parallel` flag creates multiple Jobs
  - [ ] Consider test sharding strategies
  - [ ] Implement test result aggregation service
  - [ ] Add progress tracking for long-running test suites

#### 11.2 Scaling Options for Test Infrastructure
- [ ] KEDA-based Job scaling
  - [ ] Monitor test queue depth (if using queue)
  - [ ] Scale based on pending test suites
  - [ ] Configure scaling policies and limits
- [ ] Pre-warmed test runner pools
  - [ ] Keep N test runners ready for instant use
  - [ ] Similar to executor warm pools but for tests
  - [ ] Trade-off: Resource cost vs start latency
- [ ] Test runner as Deployment + HPA
  - [ ] Convert from Jobs to long-running pods
  - [ ] Use work queue pattern
  - [ ] Enable HPA based on CPU/memory metrics
  - [ ] Requires significant architecture changes

#### 11.3 Test Infrastructure Improvements
- [ ] Fix current test execution errors
  - [ ] Debug import errors in unit tests
  - [ ] Ensure test dependencies are properly installed
  - [ ] Fix module path issues in container
- [ ] Optimize test image size and build time
  - [ ] Multi-stage builds for smaller images
  - [ ] Cache test dependencies
  - [ ] Minimize test runner startup time
- [ ] Implement test result caching
  - [ ] Cache results for unchanged code
  - [ ] Distributed cache for team sharing
  - [ ] Invalidation strategies

**📚 Note**: Test runner pods are separate from evaluation pods and have different requirements:
- **Test runners**: Need kubectl access, can have network access, run our tests
- **Evaluation pods**: Strict isolation, no network, run user code

**Trade-offs**:
- Jobs: Simple, auto-cleanup, but no HPA support
- Deployments: HPA support, but need work queue architecture
- KEDA: Best of both worlds but adds complexity
- Pre-warming: Fast starts but costs resources when idle

### 12. Container Security Scanning with Docker Scout

#### 12.1 Initial Security Assessment
- [ ] Scan all container images with Docker Scout
  - [ ] Run `docker scout quickview` on all images
  - [ ] Document critical vulnerabilities (CVSS 7.0+)
  - [ ] Create priority list for remediation
  - [ ] Generate SBOMs for compliance tracking
- [ ] Fix critical vulnerabilities in base image
  - [ ] Update h11 to 0.16.0+ (fixes CVSS 9.1 HTTP smuggling)
  - [ ] Update FastAPI to 0.115.5+
  - [ ] Update Uvicorn to 0.32.1+
  - [ ] Update Starlette to 0.40.0+
  - [ ] Rebuild all dependent images

#### 12.2 Automated Vulnerability Scanning
- [ ] Integrate Docker Scout into CI/CD pipeline
  - [ ] Add scout-action to GitHub Actions workflow
  - [ ] Configure to fail on critical vulnerabilities
  - [ ] Generate vulnerability reports as artifacts
  - [ ] Create issues for new vulnerabilities
- [ ] Set up scheduled scans
  - [ ] Weekly scan of all production images
  - [ ] Daily scan of base images
  - [ ] Monthly dependency update PRs
  - [ ] Quarterly security review meetings

#### 12.3 Security Policy and Procedures
- [ ] Define vulnerability response SLA
  - [ ] Critical (CVSS 9.0+): Fix within 24 hours
  - [ ] High (CVSS 7.0-8.9): Fix within 1 week
  - [ ] Medium (CVSS 4.0-6.9): Fix within 1 month
  - [ ] Low: Track and fix in regular updates
- [ ] Create security runbooks
  - [ ] How to run Docker Scout scans
  - [ ] How to interpret CVSS scores
  - [ ] How to update dependencies safely
  - [ ] How to handle zero-day vulnerabilities
- [ ] Implement security gates
  - [ ] Pre-commit hooks for local scanning
  - [ ] PR checks for vulnerability scans
  - [ ] Production deployment gates
  - [ ] Regular security audits

**📚 Documentation**: See [Docker Scout Vulnerability Analysis](../../security/docker-scout-vulnerability-analysis.md) for detailed scan results and remediation strategies.

**🔧 Quick Start**: Run `./scripts/security-scan.sh` to scan all images for vulnerabilities.

**⚠️ CRITICAL**: Current base image has 2 critical vulnerabilities (CVSS 9.1) that allow HTTP request smuggling. These must be fixed immediately.

### 13. Health Check Audit and Implementation

#### 13.1 Health Check Audit
- [ ] Audit ALL service health checks for placeholder implementations
  - [ ] Celery worker health_check() - Currently just returns {"status": "healthy"}
  - [ ] API service `/health` endpoint
  - [ ] Storage service health check endpoint
  - [ ] Storage worker health check
  - [ ] Dispatcher service health check
  - [ ] Frontend health check (if any)
- [ ] Document current state of each health check
  - [ ] What it claims to check vs what it actually checks
  - [ ] Critical dependencies that should be verified
  - [ ] Performance impact of proper checks

#### 13.2 Implement Real Health Checks
- [ ] Define health check standards across platform
  - [ ] Fast health check (<100ms) for load balancers
  - [ ] Detailed health check for monitoring systems
  - [ ] Consistent response format across services
- [ ] Celery worker health check improvements
  - [ ] Check Redis broker connectivity (PING)
  - [ ] Check Redis result backend connectivity
  - [ ] Verify worker can accept tasks
  - [ ] Include worker stats (tasks processed, queue depth)
- [ ] Service-specific health checks
  - [ ] API: Database connection, Redis cache
  - [ ] Storage: Database connection, file system access
  - [ ] Dispatcher: Kubernetes API access, permissions
- [ ] Consider two-tier approach
  - [ ] `/health` or `/healthz` - Basic liveness (is process running)
  - [ ] `/ready` or `/readyz` - Readiness (can serve requests)
  - [ ] `/health/detailed` - Comprehensive status for debugging

#### 13.3 Health Check Best Practices
- [ ] Implement timeouts on all external checks
- [ ] Cache results for frequently called endpoints
- [ ] Return appropriate HTTP status codes
  - [ ] 200: Everything healthy
  - [ ] 503: Service unavailable
  - [ ] Include details in response body
- [ ] Add structured logging for health check failures
- [ ] Create alerts based on health check failures

**🔥 Discovery**: During Celery test debugging, found that `health_check()` function doesn't actually check health - it's a placeholder that always returns success regardless of system state.

### 14. HTTP Status Code Audit and Standardization

#### 14.1 HTTP Status Code Audit
- [ ] Audit all API endpoints for incorrect HTTP status codes
  - [ ] Storage service POST /evaluations returns 200 instead of 201 Created
  - [ ] Check all POST endpoints that create resources
  - [ ] Check all PUT/PATCH endpoints for proper 200 vs 204
  - [ ] Check DELETE endpoints for proper 204 No Content
  - [ ] Verify error responses use appropriate 4xx/5xx codes
- [ ] Document current vs expected status codes for each endpoint

#### 14.2 Implement Correct HTTP Status Codes
- [ ] POST endpoints that create resources should return 201 Created
  - [ ] Include Location header when applicable
  - [ ] Return created resource in response body
- [ ] PUT endpoints should return:
  - [ ] 200 OK when returning updated resource
  - [ ] 204 No Content when not returning body
- [ ] DELETE endpoints should return 204 No Content
- [ ] PATCH endpoints should follow PUT conventions
- [ ] Ensure consistent error response format

#### 14.3 Update Tests and Documentation
- [ ] Update all tests to expect correct status codes
- [ ] Update OpenAPI specifications
- [ ] Update API documentation
- [ ] Add integration tests that verify status codes

**🔥 Discovery**: During Celery test debugging, found storage service returns 200 OK instead of 201 Created when creating evaluations. This violates HTTP semantics and makes tests confusing.

### 15. Update Celery Integration Tests for Kubernetes

#### 15.1 Test Architecture Updates Needed
- [ ] Update test_celery_integration.py for Kubernetes architecture
  - [ ] Replace localhost URLs with k8s_test_config
  - [ ] Remove executor pool checks (no longer applicable)
  - [ ] Update for async job model instead of sync execution
  - [ ] Remove executor allocation/release tests
- [ ] Decide on test scope
  - [ ] Keep as full e2e tests (API → Celery → K8s → Storage)
  - [ ] Or split into focused integration tests
  - [ ] Consider if these duplicate other e2e tests

#### 15.2 Specific Test Updates
- [ ] test_single_evaluation - Update for async K8s jobs
- [ ] test_concurrent_evaluations - Focus on K8s job concurrency limits
- [ ] test_executor_shortage - Convert to test K8s resource limits
- [ ] test_task_cancellation - Test K8s job cancellation
- [ ] test_high_load - Test K8s cluster scaling behavior

#### 15.3 Implementation Approach
- [ ] Keep tests skipped via check_services() fixture until rewrite
- [ ] Consider creating new K8s-specific integration tests
- [ ] Ensure no overlap with existing e2e tests

**Note**: These tests are currently skipped because they check for services at localhost URLs. The skip is intentional until we can properly rewrite them for Kubernetes.

## Resources & References

- [Kubernetes Jobs Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [KEDA - Kubernetes Event Driven Autoscaling](https://keda.sh/)
- [Kustomize Best Practices](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [gVisor Production Deployment Guide](../../security/gvisor-production-deployment.md)
- [Docker Scout Documentation](https://docs.docker.com/scout/)
- [CVSS Calculator](https://www.first.org/cvss/calculator/3.1)