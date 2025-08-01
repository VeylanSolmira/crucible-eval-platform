# Week 8: Message Queue Enhancements & Production Readiness
**Dates**: July 27 - August 2, 2025  
**Focus**: RabbitMQ migration planning and production deployment preparation
**Goal**: Plan for true priority queuing and finalize production readiness

## Planned Tasks 📋

### 1. RabbitMQ Migration Planning

#### 1.1 Research & Design
- [ ] Evaluate RabbitMQ benefits vs operational complexity
  - [ ] True priority queue support (x-max-priority)
  - [ ] Message durability guarantees
  - [ ] Dead letter exchange handling
  - [ ] Delayed message plugins
- [ ] Design migration strategy
  - [ ] Parallel Redis/RabbitMQ operation during transition
  - [ ] Zero-downtime migration approach
  - [ ] Rollback procedures
- [ ] Document architecture decision
  - [ ] See [Celery Broker Comparison](../../architecture/celery-redis-vs-rabbitmq.md)

#### 1.2 RabbitMQ Setup
- [ ] Create RabbitMQ Kubernetes manifests
  - [ ] StatefulSet for persistence
  - [ ] Service definitions
  - [ ] ConfigMap for configuration
  - [ ] PersistentVolumeClaims
- [ ] Configure high availability
  - [ ] Multi-node cluster setup
  - [ ] Mirrored queues
  - [ ] Proper resource limits
- [ ] Security configuration
  - [ ] TLS between nodes
  - [ ] User authentication
  - [ ] Network policies

#### 1.3 Celery Configuration Updates
- [ ] Update celeryconfig.py for RabbitMQ
  - [ ] Priority queue configuration with x-max-priority
  - [ ] Exchange and routing setup
  - [ ] Dead letter handling
- [ ] Modify task definitions
  - [ ] Add priority levels (0-10) to tasks
  - [ ] Configure task routing rules
- [ ] Update celery_client.py
  - [ ] Enable priority parameter functionality
  - [ ] Add routing key support

### 2. Test Infrastructure Consolidation

#### 2.1 Wait Function Consolidation
- [ ] Consolidate duplicate wait_for_evaluation functions across test suite
  - [ ] Integration tests have multiple custom implementations:
    - `test_priority_queue.py` - Returns (status, duration) tuple
    - `test_evaluation_job_imports.py` - Takes api_session/api_base_url params
    - `test_docker_event_diagnostics.py` - Uses AdaptiveWaiter
    - `test_resource_cleanup_example.py` - Class method implementation
  - [ ] Chaos tests (`test_pod_resilience.py`) - 120s timeout for resilience testing
  - [ ] Consider creating a unified wait utility that supports:
    - Different return types (full result vs status/duration tuple)
    - Session/URL parameters for cluster-internal tests
    - Configurable timeouts and polling intervals
    - Optional adaptive waiting for load scenarios
- [ ] Document when to use simple vs adaptive waiting
  - Simple: Unit tests, single evaluation tests
  - Adaptive: E2E tests, load tests, parallel test execution

### 3. Production Deployment Preparation

#### 3.1 Security Hardening
- [ ] Complete gVisor integration verification
  - [ ] Test all evaluation scenarios with gVisor
  - [ ] Performance benchmarking
  - [ ] Security boundary testing
- [ ] Network policy refinements
  - [ ] Tighten egress rules
  - [ ] Add Calico/Cilium advanced policies
- [ ] Secret management
  - [ ] Integrate with AWS Secrets Manager
  - [ ] Rotate all credentials
  - [ ] Remove hardcoded values

#### 2.2 Monitoring & Observability
- [ ] Prometheus metrics
  - [ ] Celery queue depths
  - [ ] Task processing times
  - [ ] Priority queue effectiveness
- [ ] Grafana dashboards
  - [ ] Queue visualization
  - [ ] Worker performance
  - [ ] Priority distribution
- [ ] Alert rules
  - [ ] Queue backup thresholds
  - [ ] Worker failures
  - [ ] Priority starvation

#### 2.3 Performance Optimization
- [ ] Load testing with priority queues
  - [ ] Verify high-priority task latency
  - [ ] Test queue saturation scenarios
  - [ ] Measure priority effectiveness
- [ ] Resource tuning
  - [ ] Worker concurrency optimization
  - [ ] Memory limits adjustment
  - [ ] CPU request/limit ratios

### 3. Testing Infrastructure

#### 3.1 Priority Queue Testing
- [ ] Update e2e tests for RabbitMQ
  - [ ] Modify test_priority_queue_e2e.py for true priority
  - [ ] Add tests for priority levels (0-10)
  - [ ] Test priority starvation scenarios
- [ ] Integration tests
  - [ ] RabbitMQ failover testing
  - [ ] Message persistence verification
  - [ ] Priority ordering validation

#### 3.2 Chaos Engineering
- [ ] RabbitMQ failure scenarios
  - [ ] Node failures
  - [ ] Network partitions
  - [ ] Disk pressure
- [ ] Recovery testing
  - [ ] Message recovery after crash
  - [ ] Queue reconstruction
  - [ ] Priority preservation
- [ ] Kubernetes chaos testing
  - [ ] Implement kubectl-based chaos tests - see [Kubernetes Chaos Testing Guide](../../testing/kubernetes-chaos-testing.md)
  - [ ] Pod deletion scenarios
  - [ ] Service scaling disruptions
  - [ ] Evaluation completion verification

### 4. Network Isolation Testing Infrastructure

#### 4.1 Handle Kind CNI Limitations
- [ ] Add pytest markers for network-dependent tests
  - [ ] Create `@pytest.mark.network_isolation` marker
  - [ ] Add environment detection for CNI capabilities
  - [ ] Skip tests when NetworkPolicy not enforced
- [ ] Create environment detection utility
  - [ ] Check if CNI supports NetworkPolicy (kindnet doesn't)
  - [ ] Check if gVisor is available (not on macOS)
  - [ ] Set appropriate test skip conditions
- [ ] Update test configuration
  - [ ] Add `--skip-network-isolation` flag for local development
  - [ ] Document in test README
  - [ ] Add clear skip reasons in test output

#### 4.2 CI/CD Network Testing
- [ ] Configure CI environment with proper CNI
  - [ ] Use Kind with Calico in GitHub Actions
  - [ ] Ensure all network tests run in CI
  - [ ] Separate test report for network tests
- [ ] Add network test status badge to README
  - [ ] Show which tests are environment-dependent
  - [ ] Link to documentation about limitations

#### 4.3 Developer Experience
- [ ] Create `make test-with-calico` target
  - [ ] Spins up Calico-enabled cluster (warning: +600MB RAM)
  - [ ] Runs full test suite including network tests
  - [ ] Option to restore original cluster after
- [ ] Add resource usage warnings
  - [ ] Warn when switching to Calico/Cilium CNI
  - [ ] Show memory impact before proceeding
- [ ] Improve test output
  - [ ] Summary showing why tests were skipped
  - [ ] Suggest how to run skipped tests

#### References
- [Network Isolation Limitations in Development](../../development/network-isolation-limitations.md)
- [CNI Resource Usage Comparison](../../development/cni-resource-comparison.md)

### 5. Event Channel Architecture

#### 5.1 Evaluation Timeout Event Channel
- [ ] Investigate adding dedicated `evaluation:timeout` event channel
  - [ ] Current state: Timeouts handled as failed evaluations with timeout reason
  - [ ] Benefits of separate channel:
    - Clear distinction between failures and timeouts in logs
    - Different handling logic if needed (e.g., different retry policies)  
    - Better metrics/monitoring (timeouts vs actual failures)
  - [ ] Implementation considerations:
    - Storage worker subscribes to `evaluation:timeout` channel
    - Update evaluation status to "timeout" (if separate status exists)
    - Clean up Redis state same as failed/completed events
    - Dispatcher/runner publishes to this channel on job timeout
- [ ] Update event documentation
  - [ ] Document all event channels and their purposes
  - [ ] Create event flow diagrams
  - [ ] Define event payload schemas

### 6. Advanced Testing Infrastructure

#### 6.1 Reconsider Unit Test Execution Strategy
- [ ] Evaluate current approach of running all tests in-cluster
  - [ ] Current state: All tests (unit, integration, e2e) run via test orchestrator in Kubernetes
  - [ ] Traditional approach: Unit tests run locally, only integration/e2e in cluster
  - [ ] Trade-offs to consider:
    - **Complexity**: Setting up local test execution vs maintaining single infrastructure
    - **Speed**: Local unit tests (~1s) vs in-cluster (~30-60s per test run)
    - **Developer Experience**: Instant feedback vs consistent environment
    - **Debugging**: Local debugging vs pod logs
  - [ ] See [Unit Test Philosophy](../../testing/unit-test-philosophy.md) for detailed analysis
- [ ] Investigate hybrid approach options
  - [ ] Support both local and in-cluster execution for unit tests
  - [ ] Use test markers to indicate cluster requirements
  - [ ] Provide make targets for different test modes
- [ ] Update test documentation
  - [ ] Document when to use each test execution method
  - [ ] Provide clear examples for developers
  - [ ] Update CI/CD pipelines if changes are made

## Success Criteria 🎯

1. **RabbitMQ Design Complete**
   - Clear migration plan documented
   - Risk assessment completed
   - Go/no-go decision made

2. **Production Ready**
   - All security controls in place
   - Monitoring dashboards operational
   - Runbooks documented

3. **Performance Validated**
   - Priority queues reduce high-priority latency by >50%
   - System handles 100+ concurrent evaluations
   - <5s latency for high-priority tasks

4. **Network Testing Infrastructure**
   - Developers can run tests locally without +600MB overhead
   - Network isolation tests run in CI/CD
   - Clear documentation on environment limitations
   - Easy path for developers needing full network testing

## Dependencies & Blockers 🚧

- RabbitMQ expertise may require training
- Production AWS environment access needed
- Load testing infrastructure required

## Notes 📝

- Consider staying with Redis if current round-robin approach is sufficient
- RabbitMQ adds operational complexity - ensure team is ready
- Priority queuing may not be worth the migration effort if current system meets SLAs

## Links & Resources 🔗

- [Celery Broker Comparison](../../architecture/celery-redis-vs-rabbitmq.md)
- [RabbitMQ Best Practices](https://www.rabbitmq.com/best-practices.html)
- [Celery Priority Queue Docs](https://docs.celeryproject.org/en/stable/userguide/routing.html#priority)

### 6. Advanced Testing Infrastructure

#### 6.1 Load Testing
- [ ] Create dedicated load test suite
  - [ ] Separate from integration tests (tests/load/)
  - [ ] Throughput tests (max evaluations/second)
  - [ ] Resource exhaustion tests
  - [ ] Burst load recovery tests
  - [ ] Queue depth monitoring
- [ ] Implement adaptive timeout strategies
  - [ ] Resource-aware timeout calculation
  - [ ] Progress-based dynamic timeouts
  - [ ] Performance calibration for different clusters
  - [x] See [Adaptive Timeout Strategies](../../testing/adaptive-timeout-strategies.md) (documentation only)
- [ ] Performance benchmarking
  - [ ] Baseline metrics collection
  - [ ] Regression detection
  - [ ] Multi-cluster comparison

#### 6.2 Resource Cleanup System
- [x] Implement test resource cleanup infrastructure
  - [x] Create KubernetesResourceManager for tracking resources
  - [x] Add cleanup levels (none, pods, all)
  - [x] Integrate with test coordinator via --resource-cleanup flag
  - [x] Preserve logs while cleaning pods
  - [x] Add pytest fixtures and decorators
  - [x] Create [Resource Cleanup Documentation](../../testing/resource-cleanup.md)
- [x] Test cleanup patterns
  - [x] Fixture-based cleanup (resource_manager)
  - [x] Decorator-based cleanup (@with_resource_cleanup)
  - [x] Context manager cleanup (managed_test_resources)
  - [x] Example tests in test_resource_cleanup_example.py
- [x] Integration with test orchestrator
  - [x] Add --resource-cleanup flag to test_orchestrator.py
  - [x] Pass through to coordinator and pytest
  - [x] Configure cleanup behavior per test suite
- [ ] Future: Automatic cleanup without test modifications
  - [ ] See [Automatic Cleanup Strategies](../../testing/automatic-cleanup-strategies.md) for advanced approaches
  - [ ] Consider implementing time-based or label-based auto-cleanup

#### 6.3 Replace All Test Waits with Adaptive Waiting
- [ ] Audit all test files for hardcoded timeouts and simple polling
  - [ ] Integration tests: Check for direct time.sleep() or simple wait loops
  - [ ] E2E tests: Ensure all use adaptive waiting for cluster load resilience
  - [ ] Performance tests: Update to handle variable load conditions
  - [ ] Chaos tests: Already use longer timeouts but could benefit from adaptive approach
- [ ] Update remaining tests to use adaptive waiting
  - [ ] Replace manual polling loops with wait_for_completion(use_adaptive=True)
  - [ ] Convert hardcoded timeouts to use AdaptiveWaiter
  - [ ] Ensure tests pass under significant cluster load (e.g., 100+ concurrent evaluations)
- [ ] Document adaptive waiting patterns
  - [ ] When to use simple vs adaptive waiting
  - [ ] How to configure timeouts for different test scenarios
  - [ ] Best practices for load-resilient tests
- [ ] Consider making adaptive waiting the default
  - [ ] Update wait_for_completion to use adaptive by default
  - [ ] Add use_simple=True parameter for tests that need deterministic timing
  - [ ] Update test documentation accordingly

### 7. Code Quality & Technical Debt

#### 7.1 Clean Up sys.path Manipulations
- [ ] Remove all sys.path.insert/append hacks from codebase
  - [ ] Current offenders (25+ files):
    - api/microservices_gateway.py
    - api/models.py
    - storage_worker/app.py
    - storage/backends/database.py
    - Various test files
    - Script files
  - [ ] Replace with proper solutions:
    - Set PYTHONPATH in scripts/environments where needed
    - Use relative imports for modules
    - Consider making project installable with setup.py
  - [ ] Update documentation for running scripts
  - [ ] Test all affected components after cleanup

### 8. EKS AL2 to AL2023 Migration [URGENT - Deadline: Nov 26, 2025]

#### 8.1 Migration Planning
- [ ] Review [EKS AL2 to AL2023 Migration Guide](../../infrastructure/eks-al2-to-al2023-migration.md)
- [ ] Test AL2023 AMI in development environment
  - [ ] Create parallel node group with AL2023_x86_64
  - [ ] Test all workloads on new nodes
  - [ ] Verify gVisor DaemonSet compatibility
  - [ ] Check for any custom script issues

#### 8.2 Migration Execution
- [ ] Development environment migration (Early August 2025)
  - [ ] Update terraform ami_type to AL2023_x86_64
  - [ ] Apply blue-green node group migration
  - [ ] Monitor for issues for 1 week
- [ ] Staging environment migration (Late August 2025)
  - [ ] Repeat process for staging
  - [ ] Run full test suite
  - [ ] Performance comparison
- [ ] Production migration (September 2025)
  - [ ] Schedule maintenance window
  - [ ] Execute migration with rollback plan ready
  - [ ] Post-migration validation

#### 8.3 Post-Migration Tasks
- [ ] Update all documentation references
- [ ] Performance benchmarking comparison
- [ ] Security audit of new nodes
- [ ] Remove AL2 deprecation warnings from code

### 9. Monitoring Service & Event Architecture

#### 8.1 Create Dedicated Monitoring Service
- [ ] Extract job monitoring from dispatcher into dedicated service
  - [ ] Create new `monitoring-service` directory structure
  - [ ] Move `watch_job_events_sync` and `process_job_event` from dispatcher
  - [ ] Set up FastAPI application with health/readiness endpoints
  - [ ] Create Dockerfile and Kubernetes manifests
  - [ ] Update Skaffold configuration
- [ ] Implement high availability
  - [ ] Leader election using Kubernetes lease API
  - [ ] Deploy with 2+ replicas
  - [ ] Test failover scenarios
  - [ ] Document HA operations
- [ ] Add comprehensive metrics
  - [ ] Prometheus integration
  - [ ] Job monitoring metrics
  - [ ] Event processing latency
  - [ ] Create Grafana dashboard

#### 7.2 Migration Strategy
- [ ] Phased rollout plan
  - [ ] Deploy alongside dispatcher monitoring initially
  - [ ] Add feature flag `USE_MONITORING_SERVICE`
  - [ ] Test with subset of jobs first
  - [ ] Full migration after validation
  - [ ] Remove monitoring code from dispatcher
- [ ] Maintain backward compatibility
  - [ ] Keep same Redis event format
  - [ ] Support rollback procedures
  - [ ] Document migration steps

#### 7.3 Documentation
- [ ] Update [Job Monitoring Architecture](../../architecture/job-monitoring-architecture.md)
- [ ] Create operations runbook
- [ ] Document metrics and alerts
- [ ] Update system architecture diagrams

**Rationale**: Extracting monitoring to a dedicated service removes the coupling between dispatcher lifetime and job monitoring, improving reliability and scalability. This completes the event-driven architecture vision.

### 9. Storage Service Investigation & Improvements

#### 9.1 Fix Storage Service Logging Inconsistency
- [ ] Investigate conflicting log messages in storage service startup
  - [ ] Current issue: FlexibleStorageManager prints "Using file storage as primary" but storage service shows "Primary backend: database"
  - [ ] Root cause: FlexibleStorageManager prints messages during initialization that may be misleading
  - [ ] The actual logic is correct: When `prefer_database=true` and DATABASE_URL is configured, database is primary and file is fallback
  - [ ] Fix options:
    - Remove print statements from FlexibleStorageManager
    - Convert to proper logging with accurate messages
    - Ensure messages reflect actual configuration outcome
- [ ] Update logging to be clear and consistent
  - [ ] Show primary backend selection reason
  - [ ] Show fallback backend if configured
  - [ ] Log cache enablement status

#### 9.2 Re-evaluate Storage Architecture
- [ ] Review current storage backend options and their usage
  - [ ] **Database (PostgreSQL)**: Currently primary when configured
    - Structured queries and filtering
    - Good for metadata and status tracking
    - Limited by connection pool size
  - [ ] **File Storage**: Currently fallback, stores large outputs
    - Good for large evaluation outputs (>1MB)
    - Simple and reliable
    - No query capabilities
  - [ ] **Redis**: Currently only used for transient state
    - Running evaluations tracking
    - Real-time event publishing
    - Not used for permanent storage
  - [ ] **S3**: Mentioned but not implemented
    - Long-term archival
    - Cost-effective for large outputs
    - High latency for retrieval
- [ ] Consider improvements
  - [ ] Implement S3 backend for long-term storage
  - [ ] Add Redis as a permanent storage option (with persistence)
  - [ ] Improve large file handling (currently just truncates)
  - [ ] Add storage migration utilities
- [ ] Document storage strategy
  - [ ] When to use each backend
  - [ ] Data lifecycle policies
  - [ ] Backup and recovery procedures

#### 9.3 Storage Performance Optimization
- [ ] Add storage metrics collection
  - [ ] Backend-specific latencies
  - [ ] Cache hit rates
  - [ ] Storage size tracking
- [ ] Implement missing features
  - [ ] Large file externalization to S3
  - [ ] Automatic data archival
  - [ ] Storage backend health checks
- [ ] Create storage management tools
  - [ ] Migration between backends
  - [ ] Cleanup utilities
  - [ ] Storage usage reports

**Rationale**: The storage service is critical infrastructure that needs clear logging, proper documentation, and potential architectural improvements to handle different data types and lifecycle requirements effectively.

### 10. GitHub Actions to EKS Deployment Security

#### 10.1 Implement Secure CI/CD Access
- [ ] **Configure EKS aws-auth for GitHub Actions** ✅
  - [x] Added GitHub Actions IAM role to aws-auth ConfigMap
  - [x] Granted system:masters permissions (consider reducing for production)
  - [ ] Create Terraform resource to manage aws-auth ConfigMap
- [ ] **Document deployment strategies** ✅
  - [x] Created comprehensive guide at `docs/deployment/github-actions-eks-access.md`
  - [x] Analyzed 5 different approaches with pros/cons
  - [x] Recommended SSM-based approach for short-term
  - [x] Recommended ArgoCD for long-term
- [ ] **Implement production-ready solution**
  - [ ] Set up SSM-based deployment for immediate use
  - [ ] Create restricted RBAC role instead of system:masters
  - [ ] Plan ArgoCD migration for Q2

**Rationale**: GitHub Actions needs secure access to deploy to EKS. IP allowlisting is impractical due to 5000+ dynamic ranges. Using IAM roles with aws-auth provides secure, manageable access without exposing the cluster to the internet.

### 11. Logging Infrastructure Standardization

#### 10.1 Add Proper Logging to All Python Services
- [ ] Replace print statements with proper logging across all services
  - [ ] **API Service** (api/)
    - [ ] FastAPI request/response logging
    - [ ] Error handling with proper log levels
    - [ ] Structured logging for metrics
  - [ ] **Dispatcher Service** (dispatcher/)
    - [ ] Job submission logging
    - [ ] Resource allocation decisions
    - [ ] Error tracking with context
  - [ ] **Storage Worker** (storage_worker/)
    - [ ] Event processing logs
    - [ ] Storage operation tracking
    - [ ] Performance metrics logging
  - [ ] **Test Infrastructure** (tests/)
    - [ ] Test execution logging
    - [ ] Resource cleanup operations
    - [ ] Performance timing logs
- [ ] Standardize logging configuration
  - [ ] Create shared logging config module
  - [ ] Use consistent format across services
  - [ ] Include service name, timestamp, level
  - [ ] Support structured JSON logging for production
- [ ] Configure log levels appropriately
  - [ ] DEBUG: Detailed diagnostic info
  - [ ] INFO: General operational messages
  - [ ] WARNING: Handled errors and fallbacks
  - [ ] ERROR: Failures requiring attention
  - [ ] CRITICAL: System-threatening issues
- [ ] Test output improvements
  - [ ] Ensure logs don't interfere with pytest output
  - [ ] Configure pytest to capture logs appropriately
  - [ ] Show logs only for failed tests

#### 10.2 Logging Best Practices Documentation
- [ ] Create logging guidelines document
  - [ ] When to use each log level
  - [ ] What information to include
  - [ ] Performance considerations
  - [ ] Security (no secrets in logs)
- [ ] Add logging examples
  - [ ] Service startup/shutdown
  - [ ] Request handling
  - [ ] Error scenarios
  - [ ] Performance tracking
- [ ] Integration with monitoring
  - [ ] Log aggregation patterns
  - [ ] Metrics extraction from logs
  - [ ] Alert configuration

**Rationale**: Proper logging is essential for production debugging, monitoring, and maintaining clean test output. The current mix of print statements makes debugging harder and clutters test results.

### 11. Queue Optimization and Resource-Aware Scheduling

#### 11.1 Implement Task Peeking or Resource Checking
- [ ] Investigate queue optimization strategies
  - [ ] Option 1: Redis-based task peeking
    - Peek at queue without dequeuing
    - Check resource requirements before pulling task
    - Maintain queue visibility
  - [ ] Option 2: Capacity pre-flight endpoint
    - Add `/capacity/check` endpoint to dispatcher
    - Workers check before dequeuing
    - Include resource requirements in check
  - [ ] Option 3: Resource-based queue routing
    - Multiple queues by resource size (small/medium/large)
    - Workers pull from appropriate queue based on capacity
- [ ] Evaluate trade-offs
  - [ ] Complexity vs benefit analysis
  - [ ] Impact on queue visibility/monitoring
  - [ ] Celery compatibility considerations
- [ ] Implement chosen solution
  - [ ] Start with simple dequeue/requeue pattern
  - [ ] Add optimizations based on production metrics

#### 11.2 Improve Retry Strategy for Resource Constraints
- [x] Update Celery retry configuration
  - [x] Unlimited retries for resource constraints
  - [x] Exponential backoff with jitter
  - [x] Longer retry windows (hours not minutes)
  - [x] Distinguish resource constraints from real failures
- [x] Add cluster capacity visibility
  - [x] Expose available resources via API (`/capacity/check`)
  - [x] Help tasks make informed retry decisions
  - [ ] Consider queue depth in capacity calculations

#### 11.3 Add Resource Requirements to Evaluation API
- [ ] Extend evaluation request model
  - [ ] Add `memory_limit` field (e.g., "512Mi", "1Gi", "2Gi")
  - [ ] Add `cpu_limit` field (e.g., "500m", "1", "2")
  - [ ] Set sensible defaults and maximum limits
  - [ ] Validate resource requests against cluster capacity
- [ ] Update task signatures
  - [ ] Pass resource requirements through Celery tasks
  - [ ] Update dispatcher calls to use requested resources
- [ ] Implement resource-based routing
  - [ ] Small tasks (≤256Mi) to lightweight queue
  - [ ] Large tasks (≥1Gi) to heavyweight queue
  - [ ] Prevent small tasks from being blocked by large ones
- [ ] Update capacity check logic
  - [ ] Check capacity before dequeuing based on actual requirements
  - [ ] More accurate queue wait time estimates
- [ ] Add resource usage to billing/tracking
  - [ ] Track actual resource consumption per evaluation
  - [ ] Enable usage-based pricing models

**Rationale**: Under load, tasks may need to wait hours for resources. The current 3-retry limit is insufficient. Smart queueing and capacity awareness can reduce wasted work and improve throughput. Resource requirements should be first-class citizens in the API to enable proper scheduling and capacity planning.

### 12. Resource Requirements and Default Strategy

#### 12.1 Analyze Resource Requirements Patterns
- [ ] Profile different evaluation workloads
  - [ ] Simple print/calculation tasks (minimal resources)
  - [ ] Data processing tasks (memory intensive)
  - [ ] Compute-heavy tasks (CPU intensive)
  - [ ] Long-running tasks (timeout considerations)
- [ ] Collect metrics on actual resource usage
  - [ ] Memory high-water marks
  - [ ] CPU utilization patterns
  - [ ] Correlation with code complexity/size
- [ ] Document findings and patterns

#### 12.2 Design Default Resource Strategy
- [ ] Consider multiple approaches:
  - [ ] **Static defaults**: Simple but may waste resources
  - [ ] **Tiered defaults**: Based on code size/complexity heuristics
  - [ ] **Historical data**: Learn from past evaluations
  - [ ] **User profiles**: Different defaults per user/organization
  - [ ] **Dynamic adjustment**: Start small, scale up if needed
- [ ] Cost implications analysis
  - [ ] Resource waste from over-provisioning
  - [ ] Failure costs from under-provisioning
  - [ ] Retry overhead costs
- [ ] Performance implications
  - [ ] Queue wait times with different resource allocations
  - [ ] Success rates with different limits
  - [ ] Time to first result

#### 12.3 Implementation Considerations
- [ ] API design decisions
  - [ ] Keep fields optional with server-side defaults
  - [ ] Allow override for power users
  - [ ] Consider resource "profiles" (small/medium/large)
  - [ ] Version the API for future changes
- [ ] Migration strategy
  - [ ] How to update defaults without breaking existing clients
  - [ ] A/B testing different default strategies
  - [ ] Gradual rollout approach
- [ ] Monitoring and alerting
  - [ ] Track resource utilization efficiency
  - [ ] Alert on consistent under/over-provisioning
  - [ ] Dashboard for resource usage patterns

#### 12.4 Documentation and Communication
- [ ] Document default resource allocations clearly
  - [ ] In API documentation
  - [ ] In error messages when limits hit
  - [ ] In billing/usage documentation
- [ ] Provide guidance for users
  - [ ] When to override defaults
  - [ ] How to estimate resource needs
  - [ ] Best practices for efficient code

**Rationale**: Proper resource defaults are critical for system efficiency and user experience. Rushing to add arbitrary defaults now would lock us into values that are hard to change later. This needs careful analysis of actual workload patterns, cost considerations, and user needs. The system should be smart about resource allocation while remaining simple for users who don't want to think about infrastructure details.

### 13. Exit Code and Evaluation Status Architecture

#### 10.1 Fix Exit Code Tracking Issues
- [ ] Address fundamental exit code tracking problems
  - [ ] Current issue: Race condition between Kubernetes job status and container exit codes
  - [ ] When job.status.succeeded=true, container might not be terminated yet
  - [ ] Can't get exit code from deleted pods (logs from Loki have no exit code)
  - [ ] Python exceptions (like 1/0) exit with code 1 but Kubernetes marks job as "succeeded"
- [ ] Improve exit code retrieval
  - [ ] Wait for container termination before processing job success
  - [ ] Consider pod phase AND container state together
  - [ ] Handle the None exit code case properly (don't default to 0 or 1)
- [ ] Re-architect evaluation status determination
  - [ ] Current: Relies on exit codes to determine success/failure
  - [ ] Problem: Exit codes are unreliable and hard to get consistently
  - [ ] Consider alternatives:
    - Parse logs for success/failure indicators
    - Have evaluations explicitly report status
    - Use structured output format with status field

#### 10.2 Cleanup Controller Coordination
- [ ] Address log shipping race condition
  - [ ] Current: 10-second grace period before deleting pods
  - [ ] Problem: Arbitrary delay, not event-driven
  - [ ] Consider:
    - Event-based coordination (cleanup controller waits for "logs shipped" signal)
    - Fluent Bit completion markers
    - Sidecar pattern for log shipping confirmation
- [ ] Improve Fluent Bit reliability
  - [ ] Current: DaemonSet reads from /var/log/containers/*.log
  - [ ] Problem: Files deleted when pods are deleted
  - [ ] Consider:
    - Log streaming directly from containers
    - Buffer logs in persistent volume temporarily
    - Ensure Fluent Bit processes logs before deletion

#### 10.3 Evaluation Result Architecture
- [ ] Design proper evaluation result reporting
  - [ ] Move away from exit code reliance
  - [ ] Options:
    - Structured JSON output with explicit status field
    - Separate status reporting API endpoint
    - Status file written to shared volume
- [ ] Handle edge cases properly
  - [ ] Container OOM kills
  - [ ] Timeouts
  - [ ] Network failures
  - [ ] Partial outputs
- [ ] Document evaluation lifecycle
  - [ ] All possible states and transitions
  - [ ] How status is determined at each stage
  - [ ] What happens when information is incomplete

**Rationale**: The current system's reliance on exit codes for determining evaluation success/failure is fundamentally flawed due to Kubernetes' async nature and the complexity of tracking exit codes through multiple layers (job -> pod -> container). A more robust architecture is needed that doesn't depend on race conditions and unreliable signals.

### 14. Resource Validation and Quota Management

#### 14.1 Implement Three-Tier Resource Validation
- [ ] **API-Level Validation** (Immediate rejection for impossible requests)
  - [ ] Add cluster capacity validation to dispatcher `/execute` endpoint
  - [ ] Check against maximum possible capacity (with scaling)
  - [ ] Validate against node-level constraints (largest instance type)
  - [ ] Return clear 400 errors with actionable messages
  - [ ] See [Resource Validation Patterns](../../testing/resource-validation-patterns.md)
  - [ ] **Note**: Current implementation validates synchronously through Celery → Dispatcher chain, 
        adding 50-500ms latency. Consider moving validation to API level with cached limits 
        for better performance at scale
- [ ] **Admission Controller** (Future: Policy-based validation)
  - [ ] Research ValidatingAdmissionWebhook for dynamic policies
  - [ ] Design user quota system
  - [ ] Priority-based admission during resource pressure
  - [ ] Document admission control strategy
- [ ] **Scheduler-Level** (Queue with bounded timeout)
  - [ ] Keep current activeDeadlineSeconds approach
  - [ ] Consider adding scheduling timeout annotations
  - [ ] Monitor unschedulable pod metrics

#### 14.2 Improve Resource Feedback Loop
- [ ] Enhance capacity checking endpoint
  - [ ] Add queue depth to capacity calculations
  - [ ] Estimate wait times based on current load
  - [ ] Expose per-node capacity information
  - [ ] Add "why rejected" detailed explanations
- [ ] Update error messages and documentation
  - [ ] Provide maximum allowed values in errors
  - [ ] Suggest alternative resource configurations
  - [ ] Link to resource limit documentation
  - [ ] Add examples of valid requests

#### 14.3 Testing Resource Validation
- [ ] Update test expectations
  - [ ] Fix test_quota_error_handling to expect 400 errors
  - [ ] Test immediate rejection of impossible requests
  - [ ] Test queueing of possible but unavailable requests
  - [ ] Verify error message quality
- [ ] Add performance tests for validation
  - [ ] Measure validation overhead
  - [ ] Test under high submission rates
  - [ ] Verify no race conditions

**Rationale**: Fast validation at the API level provides immediate feedback for impossible requests while allowing the scheduler flexibility to handle possible requests. This balances user experience with system efficiency and follows industry best practices from systems like Databricks, AWS Batch, and HPC schedulers.

### 15. EKS Infrastructure Improvements

#### 15.1 Permanent Fix for AZ Volume Affinity Issues 
- [ ] **HIGH PRIORITY** - Implement solution to prevent volume affinity conflicts during node replacements
  - [ ] Option 1: Create separate node groups per AZ
    ```hcl
    resource "aws_eks_node_group" "workers_az_a" {
      subnet_ids = ["subnet-in-us-west-2a"]
      # Ensures nodes in us-west-2a for volumes
    }
    resource "aws_eks_node_group" "workers_az_b" {
      subnet_ids = ["subnet-in-us-west-2b"]
      # Ensures nodes in us-west-2b for volumes
    }
    ```
  - [ ] Option 2: Implement pod topology spread constraints
    ```yaml
    topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
    ```
  - [ ] Option 3: Migrate to EFS for cross-AZ storage
    - Works across all AZs
    - Good for read-heavy workloads
    - No affinity issues
  - [ ] Option 4: Implement data replication
    - PostgreSQL streaming replication
    - Redis Cluster mode
    - Loki HA mode
- [ ] Document chosen solution and implementation plan
- [ ] Test solution with node replacements/upgrades
- [ ] Update runbooks for handling volume issues

**Background**: EBS volumes are AZ-specific. When nodes get replaced (upgrades, scaling, failures), new nodes may launch in different AZs, making existing volumes unmountable. This causes downtime and potential data loss.

#### 15.2 Complete EKS Upgrade Path to 1.32
- [ ] **HIGH PRIORITY** - Continue upgrading from 1.29 → 1.32
  - [ ] Phase 1: Upgrade 1.29 → 1.30
    - [ ] Update control plane
    - [ ] Check add-on compatibility
    - [ ] Update node groups
    - [ ] Update Terraform eks-minimal.tf
    - [ ] Test applications
  - [ ] Phase 2: Upgrade 1.30 → 1.31
    - [ ] Update control plane
    - [ ] Check add-on compatibility
    - [ ] Update node groups
    - [ ] Update Terraform
    - [ ] Test applications
  - [ ] Phase 3: Upgrade 1.31 → 1.32
    - [ ] Update control plane
    - [ ] Check add-on compatibility
    - [ ] Update node groups
    - [ ] Update Terraform
    - [ ] Test applications
- [ ] Update kubectl to 1.32
- [ ] Review and update deprecated APIs
- [ ] Performance testing on 1.32
- [ ] Document any breaking changes

**Rationale**: Staying on 1.28 incurs extended support charges ($0.10/hour). Version 1.32 is the latest stable version with the longest support window. Each version must be upgraded sequentially due to Kubernetes compatibility requirements.

### 16. Implement Proper Health Check Pattern Across All Services

#### 16.1 Standardize Health Check Endpoints
- [ ] **HIGH PRIORITY** - Implement healthz/readyz pattern for all services
  - [ ] Create standard health check interface/pattern
    ```python
    # /healthz - Liveness: Is the process alive?
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}
    
    # /readyz - Readiness: Can I serve my purpose?
    @app.get("/readyz") 
    async def readyz():
        # Check only critical deps (e.g., can I connect to my database?)
        # NOT: Is every downstream service perfect?
        
    # /health - Full status for monitoring
    @app.get("/health")
    async def health():
        # Comprehensive check for dashboards/debugging
    ```
- [ ] Update all service deployments to use correct probes
  - [ ] API Service ✓ (completed)
  - [ ] Storage Service - Remove database check from liveness
  - [ ] Storage Worker - Separate Redis availability from liveness  
  - [ ] Dispatcher - Don't fail liveness on K8s API issues
  - [ ] Celery Worker - Handle broker reconnection gracefully
  - [ ] Frontend - Simple Next.js server check
- [ ] Set appropriate timeouts
  - [ ] Liveness: 1-2 second timeout (just HTTP response)
  - [ ] Readiness: 2-3 second timeout (critical checks only)
  - [ ] No health check should make external API calls

#### 16.2 Fix Cascading Failure Patterns
- [ ] Audit current health check dependencies
  - [ ] Map out which services check which dependencies
  - [ ] Identify circular health check dependencies
  - [ ] Remove unnecessary coupling
- [ ] Implement circuit breakers where appropriate
  - [ ] Services should degrade gracefully, not restart
  - [ ] Return partial results when possible
  - [ ] Use async health checks that don't block requests

#### 16.3 Documentation and Monitoring
- [ ] Create health check best practices guide
  - [ ] When to use each endpoint type
  - [ ] What should/shouldn't be in health checks
  - [ ] Anti-patterns to avoid
- [ ] Update monitoring dashboards
  - [ ] Separate liveness/readiness metrics
  - [ ] Track false positive restarts
  - [ ] Alert on cascading failures

**Rationale**: The current health check implementation causes cascading failures when any service has a temporary issue. Services are restarting unnecessarily because they're checking external dependencies in their liveness probes. This violates Kubernetes best practices and reduces system reliability. Proper health checks should be fast, focused, and independent.

### 17. Optimize OpenAPI Generation to Prevent Unnecessary Rebuilds

#### 17.1 Implement Content-Based Comparison
- [ ] Update OpenAPI generation scripts to avoid unnecessary file writes
  - [ ] Modify `api/scripts/export-openapi-spec.py` to compare content before writing
  - [ ] Modify `storage_service/scripts/export-openapi-spec.py` similarly
  - [ ] Use consistent formatting (sort_keys=True) for deterministic output
  - [ ] Add hash comparison or direct content comparison
- [ ] Test that unchanged APIs don't trigger frontend rebuilds
  - [ ] Verify timestamps are preserved when content is identical
  - [ ] Ensure Docker layer caching works correctly
  - [ ] Measure build time improvements

#### 17.2 Improve Build Pipeline Efficiency
- [ ] Optimize Docker layer ordering for better caching
  - [ ] Copy OpenAPI specs before source code in frontend Dockerfile
  - [ ] Structure layers to maximize cache reuse
- [ ] Consider implementing checksum files for explicit change tracking
  - [ ] Generate `.sha256` files alongside OpenAPI specs
  - [ ] Update frontend build to check checksums before regenerating types

#### 17.3 Documentation and Long-term Improvements
- [ ] Document the new behavior in developer guides
- [ ] Consider adopting content-aware build tools (Turbo, Nx) for future
- [ ] Evaluate moving OpenAPI generation out of build pipeline entirely

**Reference**: See [OpenAPI Generation Optimization](../../development/openapi-generation-optimization.md) for detailed analysis and implementation options.

**Rationale**: Currently, any change to the API service triggers a complete frontend rebuild because OpenAPI spec files are regenerated with new timestamps, even when the API contract hasn't changed. This causes unnecessary build time, Docker layer invalidation, and CI/CD pipeline delays. Implementing content-based comparison will significantly improve developer experience and reduce build times.

### 18. Remove Inter-Service Health Checks (HIGH PRIORITY)

#### 18.1 Audit All Services for Health Check Anti-patterns
- [ ] **API Service** - COMPLETED ✅
  - [x] Removed background health check loop
  - [x] Removed service_health tracking dictionary
  - [x] Updated endpoints to handle failures gracefully
  - [x] Let Kubernetes manage health via probes
- [ ] **Storage Service**
  - [ ] Check for health checks of Redis/Postgres
  - [ ] Remove any background health monitoring
  - [ ] Update endpoints to handle database failures gracefully
- [ ] **Storage Worker**
  - [ ] Check for health checks of storage service
  - [ ] Remove pre-flight health checks
  - [ ] Handle storage service failures at call time
- [ ] **Dispatcher Service**
  - [ ] Check for health checks of Kubernetes API
  - [ ] Remove any service availability checks
  - [ ] Handle API failures gracefully with retries
- [ ] **Celery Worker**
  - [ ] Check for health checks of Redis/storage
  - [ ] Remove broker health monitoring
  - [ ] Let Celery handle connection failures
- [ ] **Frontend**
  - [ ] Should not proactively check backend health
  - [ ] Handle API failures gracefully in UI

#### 18.2 Implement Proper Failure Handling Patterns
- [ ] Replace pre-checking with try/catch patterns
  ```python
  # BAD - Pre-checking health
  if not service_health["storage"]:
      raise HTTPException(503, "Storage unavailable")
  
  # GOOD - Try the call and handle failure
  try:
      response = await storage_client.post(...)
  except httpx.HTTPError as e:
      logger.error(f"Storage call failed: {e}")
      # Retry with backoff, circuit break, or return 503
      raise HTTPException(503, f"Storage error: {str(e)}")
  ```
- [ ] Add proper retry logic where appropriate
  - [ ] Use exponential backoff for transient failures
  - [ ] Set reasonable timeout values
  - [ ] Distinguish between retryable and non-retryable errors
- [ ] Implement circuit breakers for repeated failures
  - [ ] Prevent cascading failures
  - [ ] Allow services to recover gracefully
  - [ ] Return cached or degraded responses when possible

#### 18.3 Update Health Check Endpoints
- [ ] Ensure each service only reports its OWN health
  - [ ] `/healthz` - Simple liveness check (can the process respond?)
  - [ ] `/readyz` - Readiness check (can the service handle requests?)
  - [ ] `/health` - Detailed health for monitoring (not for K8s probes)
- [ ] Remove all external dependency checks from health endpoints
- [ ] Keep health checks fast and lightweight (<1 second)

#### 18.4 Documentation and Monitoring
- [ ] Document the new health check philosophy
  - [ ] Each service is responsible only for itself
  - [ ] Kubernetes manages service dependencies
  - [ ] Failures are handled at call sites
- [ ] Update monitoring to track actual failures
  - [ ] Monitor real request failures, not pre-emptive checks
  - [ ] Track retry success rates
  - [ ] Alert on sustained failures, not transient issues

**Background**: The current architecture has services checking the health of their dependencies in background loops. This creates several problems:
1. **False negatives**: Transient network issues mark services as "unhealthy" even when they're fine
2. **Circular dependencies**: Services checking each other can create deadlocks
3. **Additional failure modes**: The health checks themselves become a source of failures
4. **Fighting Kubernetes**: This pattern works against K8s's built-in health management

**Benefits of Removal**:
- Services become self-healing automatically
- No more false positives from network hiccups  
- Simpler code without background tasks and shared state
- Better alignment with cloud-native patterns
- Improved system resilience

**Example**: The API service had a background health check that would timeout in EKS after ~10 seconds, marking storage as unhealthy and causing the entire API to return 503 errors even though storage was actually working fine. Removing this check immediately fixed the issue.

### 19. Service Level Objectives (SLOs) and Monitoring

#### 19.1 Define Core Service SLOs
- [ ] **API Service SLOs**
  - [ ] Availability: 99.5% uptime (allows ~3.6 hours downtime/month)
  - [ ] Latency: 95% of requests < 500ms, 99% < 1s
  - [ ] Error rate: < 1% 5xx errors
  - [ ] Health check response time: < 100ms
- [ ] **Evaluation Execution SLOs**
  - [ ] Success rate: > 95% for valid submissions
  - [ ] Time to start: 95% within 30s of submission
  - [ ] Completion time: 95% within expected timeout + 10%
  - [ ] Result retrieval: 99% retrievable within 5s of completion
- [ ] **Storage Service SLOs**
  - [ ] Availability: 99.9% for reads, 99.5% for writes
  - [ ] Latency: 95% of reads < 100ms, writes < 200ms
  - [ ] Data durability: 99.999% (five 9s)
  - [ ] Large file handling: Support up to 100MB outputs

#### 19.2 Implement SLO Monitoring
- [ ] Create Prometheus recording rules for SLIs
  - [ ] Request rate, error rate, duration metrics
  - [ ] Availability calculations over sliding windows
  - [ ] Queue depth and processing time percentiles
- [ ] Build Grafana dashboards for SLO tracking
  - [ ] Real-time SLO status dashboard
  - [ ] Historical SLO compliance trends
  - [ ] Error budget burn rate visualization
  - [ ] Service dependency mapping
- [ ] Configure AlertManager for SLO violations
  - [ ] Alert when error budget consumption accelerates
  - [ ] Differentiate between warning and critical thresholds
  - [ ] Route alerts based on severity and service

#### 19.3 Error Budget and Policy
- [ ] Define error budget policies
  - [ ] What happens when error budget is exhausted
  - [ ] How to prioritize reliability work vs features
  - [ ] Incident response procedures
- [ ] Create SLO review process
  - [ ] Monthly SLO compliance review
  - [ ] Quarterly SLO target adjustment
  - [ ] Post-incident SLO impact analysis

#### 19.4 Documentation and Communication
- [ ] Document SLOs in service README files
- [ ] Create user-facing status page showing SLO compliance
- [ ] Define internal vs external SLOs
- [ ] Establish SLO reporting cadence

**Rationale**: SLOs provide objective measures of service reliability and help balance feature development with operational excellence. They enable data-driven decisions about when to focus on reliability vs new features and provide clear expectations for users.

---

### 20. gVisor Security Hardening

#### 20.1 Strict Enforcement
- [x] **Remove permissive environment variables**
  - [x] Remove GVISOR_AVAILABLE and REQUIRE_GVISOR
  - [x] Make gVisor mandatory except for local macOS development
  - [x] Fail fast if gVisor unavailable (except local)

#### 20.2 Simplified Deployment
- [x] **Remove node labeling complexity**
  - [x] Remove nodeSelector from RuntimeClass
  - [x] DaemonSet installs on all nodes
  - [x] No manual labeling required

#### 20.3 ConfigMap-based Configuration
- [x] **Replace brittle awk approach**
  - [x] Create containerd config ConfigMap
  - [x] Simple file copy instead of text manipulation
  - [x] More maintainable and reliable

**Rationale**: High-security platforms require mandatory isolation. Making gVisor required by default (with only local dev exception) ensures production security while maintaining developer productivity.

---

### 21. Deployment Automation (GitHub Actions CD)

#### 21.1 Quick Improvements (Immediate)
- [ ] **Create single-service deploy script**
  - [ ] Build specific service with git SHA tag
  - [ ] Update kustomization.yaml for that service
  - [ ] Apply changes to cluster
  - [ ] Document usage in README

#### 21.2 GitHub Actions CD Pipeline
- [ ] **Create deployment workflow**
  - [ ] Trigger on merge to main
  - [ ] Path-based triggers for each service
  - [ ] Build and push to ECR
  - [ ] Update image in deployment
  - [ ] Apply to dev environment

#### 21.3 Deployment Safety
- [ ] **Add deployment checks**
  - [ ] Wait for rollout completion
  - [ ] Basic smoke tests
  - [ ] Rollback on failure
  - [ ] Slack/email notifications

#### 21.4 Multi-environment Support
- [ ] **Environment-specific workflows**
  - [ ] Dev auto-deploy on merge
  - [ ] Staging with approval gate
  - [ ] Production manual trigger
  - [ ] Environment-specific secrets

**Rationale**: Automating deployments reduces errors and speeds up iteration. GitHub Actions provides good automation without additional infrastructure overhead, making it ideal for our current single-node setup.

**Documentation**: See [Deployment Strategies Guide](../../deployment/deployment-strategies.md) for detailed analysis of options from manual to full GitOps.

---

### 22. Zero-Downtime NAT Instance Implementation

**Priority:** High  
**Effort:** 3-4 days  
**Documentation:** [NAT Instance Architecture Decision](../../architectural-decisions/nat-instance-vs-nat-gateway.md)

#### Overview
Enhance the current NAT instance implementation to achieve zero downtime during updates by implementing a dual-instance solution with health checks and automatic failover.

#### Justification
While our current implementation with `create_before_destroy` lifecycle provides reasonable uptime (30-second interruption), a zero-downtime solution would demonstrate advanced AWS networking skills and high-availability design patterns valuable for AI safety evaluation infrastructure.

#### Current State
- Single NAT instance with Elastic IP
- ~30 second downtime during instance replacement
- Manual intervention required for failures
- Cost: ~$3.80/month

#### Target State
- Dual NAT instances (primary/standby)
- Automatic health checks every 30 seconds
- Zero-downtime failover
- Automated rolling updates
- Cost: ~$7.60/month (still 83% cheaper than NAT Gateway)

#### Implementation Steps

**Phase 1: Infrastructure Setup**
- [ ] Create standby NAT instance in different AZ
- [ ] Set up secondary Elastic IP
- [ ] Configure route table update mechanism
- [ ] Document failover procedures

**Phase 2: Health Check System**
- [ ] Create Lambda function for health checks
- [ ] Implement TCP/HTTP health probes
- [ ] Add CloudWatch metrics for tracking
- [ ] Set up SNS notifications for failures

**Phase 3: Failover Logic**
- [ ] Implement route table update logic
- [ ] Add connection draining logic
- [ ] Test failover scenarios
- [ ] Document recovery procedures

**Phase 4: Rolling Update System**
- [ ] Create update orchestration logic
- [ ] Implement pre-update health verification
- [ ] Add rollback capabilities
- [ ] Create operational playbook for updates

#### Success Metrics
- Failover time < 5 seconds
- Zero dropped connections
- 99.9% uptime over 30 days
- Successful automated updates

**Rationale**: This enhancement demonstrates high-availability design skills, cost-conscious engineering, AWS Lambda and automation expertise, understanding of network architecture, and production-ready thinking.

---

### 23. GitHub Actions Test Suite Improvements

**Priority:** Medium  
**Effort:** 2-4 hours  
**Impact:** Faster CI/CD, better developer experience

#### Overview
Optimize the test-suite.yml workflow for performance and reliability, especially for the 872MB test-runner image.

#### Tasks

**23.1 Add Job Timeout**
- [ ] Add `timeout-minutes: 30` to prevent hanging jobs
- [ ] Prevents runaway jobs from consuming Actions minutes
- [ ] 30 minutes should be sufficient for most test suites

**23.2 Implement Concurrency Control**
- [ ] Add concurrency group to cancel old runs on new pushes
```yaml
concurrency:
  group: test-${{ github.ref }}
  cancel-in-progress: true
```
- [ ] Saves CI resources when pushing multiple commits
- [ ] Ensures only latest code is tested

**23.3 Add Docker Layer Caching**
- [ ] Set up Docker Buildx for layer caching
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
```
- [ ] Can significantly speed up image builds
- [ ] Especially helpful for the 872MB test-runner image

**23.4 Add Test Result Reporting**
- [ ] Integrate test reporter action for better visibility
- [ ] Options:
  - dorny/test-reporter@v1 for JUnit XML reports
  - EnricoMi/publish-unit-test-result-action@v2
- [ ] Provides inline PR comments with test failures

**23.5 Parallel Test Suite Execution**
- [ ] Consider splitting test suites into parallel jobs
- [ ] Example structure:
  - job: unit-tests
  - job: integration-tests  
  - job: security-tests
- [ ] Faster feedback, especially for large test suites

**23.6 Optimize Image Size**
- [ ] Investigate reducing the 872MB test-runner image
- [ ] Multi-stage builds to exclude build dependencies
- [ ] Use slim base images where possible
- [ ] Remove unnecessary test fixtures from image

**Rationale**: These optimizations will improve CI/CD performance, reduce build times, and provide better feedback to developers. The 872MB image size is a particular bottleneck for upload speeds.

---

### 24. GitHub Actions Workflow Improvements

**Priority:** Low  
**Effort:** 2-3 hours  
**Impact:** Cleaner, more maintainable CI/CD workflows

#### Overview
Optimize terraform.yml workflow to reduce code duplication and improve maintainability.

#### Current State
- terraform.tfvars creation duplicated in 3 places (Plan, Apply, Destroy jobs)
- Each job runs on isolated VMs requiring separate file creation
- Maintenance overhead when updating variables

#### Improvement Options

**24.1 Composite Action Approach (Recommended)**
- [ ] Create `.github/actions/setup-terraform/action.yml`
```yaml
name: Setup Terraform
description: Creates terraform.tfvars from GitHub variables
runs:
  using: composite
  steps:
    - name: Create terraform.tfvars
      shell: bash
      run: |
        cd infrastructure/terraform
        cat > terraform.tfvars <<EOF
        domain_name = "${{ inputs.domain_name }}"
        email = "${{ inputs.email }}"
        create_route53_zone = ${{ inputs.create_route53_zone }}
        kubernetes_load_balancer_ip = "${{ inputs.kubernetes_lb_ip }}"
        aws_profile = "${{ inputs.aws_profile }}"
        EOF
```
- [ ] Benefits:
  - Single source of truth for tfvars creation
  - Reusable across workflows
  - Version controlled with repo
  - Can add other setup steps (tool installation, etc.)

**24.2 Shared Artifact Approach**
- [ ] Create setup job that uploads tfvars as artifact
- [ ] Download in each subsequent job
- [ ] Pros: True single execution
- [ ] Cons: Adds complexity, slower due to upload/download

**24.3 Reusable Workflow**
- [ ] Extract common setup into `.github/workflows/terraform-setup.yml`
- [ ] Call from main workflow
- [ ] More complex than composite action for this use case

#### Implementation Plan
1. Start with composite action (Option 1)
2. Test in development branch
3. Gradually add more common setup tasks
4. Document usage for team

**Rationale**: While the current duplication works, implementing a composite action will improve maintainability and provide a foundation for standardizing other common CI/CD tasks. This demonstrates infrastructure-as-code best practices and GitHub Actions expertise.