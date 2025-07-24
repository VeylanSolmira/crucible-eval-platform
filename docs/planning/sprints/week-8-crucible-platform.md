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

### 2. Production Deployment Preparation

#### 2.1 Security Hardening
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

### 8. Monitoring Service & Event Architecture

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

### 10. Exit Code and Evaluation Status Architecture

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