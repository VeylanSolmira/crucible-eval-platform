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