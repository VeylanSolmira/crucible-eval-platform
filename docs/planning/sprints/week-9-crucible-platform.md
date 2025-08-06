# Week 9: gVisor Implementation & Platform Hardening
**Dates**: August 3 - August 9, 2025  
**Focus**: Complete gVisor integration via DaemonSet and improve platform reliability
**Goal**: Achieve secure code execution and address technical debt

## Planned Tasks 📋

### 1. gVisor DaemonSet Implementation

#### 1.1 Revert to Standard EKS AMI
- [ ] Update Terraform to use standard EKS-optimized AMI
  - [ ] Remove custom AMI ID from launch template
  - [ ] Set ami_type back to "AL2_x86_64"
  - [ ] Remove custom user data
- [ ] Delete existing gVisor node group
- [ ] Deploy new node group with standard configuration

#### 1.2 Create gVisor DaemonSet
- [ ] Design privileged DaemonSet for gVisor installation
  - [ ] Use official gVisor container image or create custom
  - [ ] Mount host filesystem for binary installation
  - [ ] Access containerd socket for config updates
- [ ] Implement installation script
  - [ ] Check if gVisor already installed
  - [ ] Download and verify gVisor binaries
  - [ ] Backup original containerd config
  - [ ] Modify containerd configuration
  - [ ] Restart containerd service
  - [ ] Verify runtime availability
- [ ] Add proper security controls
  - [ ] Use specific ServiceAccount with minimal permissions
  - [ ] Add node selector for controlled rollout
  - [ ] Implement health checks and status reporting

#### 1.3 Testing and Validation
- [ ] Deploy DaemonSet to dev environment
- [ ] Verify gVisor installation on all nodes
- [ ] Test pod creation with gVisor runtime
- [ ] Run actual evaluation with gVisor
- [ ] Document rollback procedure

### 2. Complete gVisor Integration

#### 2.1 Update Dispatcher for gVisor
- [ ] Re-enable gVisor requirement in dispatcher
  - [ ] Remove DISABLE_GVISOR flag
  - [ ] Update job specifications to use gVisor runtime
- [ ] Add runtime class validation
  - [ ] Check if gVisor RuntimeClass exists
  - [ ] Fallback behavior if not available
- [ ] Update resource calculations for gVisor overhead

#### 2.2 Create gVisor-Specific Executor Images
- [ ] Validate existing executor images work with gVisor
- [ ] Document any gVisor-specific limitations
- [ ] Update executor documentation

#### 2.3 Security Validation
- [ ] Test network isolation with gVisor
- [ ] Verify filesystem isolation
- [ ] Validate resource limits enforcement
- [ ] Document security boundaries

### 3. Platform Reliability Improvements

#### 3.1 Fix Exit Code Tracking (from Week 8)
- [ ] Implement structured output for evaluations
  - [ ] Define JSON schema for evaluation results
  - [ ] Update executors to write status files
  - [ ] Modify storage worker to parse structured output
- [ ] Remove reliance on exit codes
  - [ ] Use Kubernetes job status as primary signal
  - [ ] Parse logs for secondary validation
  - [ ] Handle edge cases (OOM, timeout, etc.)
- [ ] Update evaluation status logic
  - [ ] Clear status definitions and transitions
  - [ ] Proper handling of incomplete information

#### 3.2 Improve Log Shipping Reliability
- [ ] Implement proper log shipping coordination
  - [ ] Add Fluent Bit buffer configuration
  - [ ] Implement completion markers
  - [ ] Event-driven cleanup instead of time-based
- [ ] Ensure logs are captured before pod deletion
  - [ ] Modify cleanup controller to check log status
  - [ ] Add retry logic for failed log shipping
  - [ ] Monitor log shipping metrics

### 4. Long-term gVisor AMI Solution

#### 4.1 Design Post-Bootstrap Configuration
- [ ] Create systemd service for gVisor configuration
  - [ ] Runs after kubelet.service
  - [ ] Idempotent configuration script
  - [ ] Proper error handling and logging
- [ ] Update AMI build process
  - [ ] Include systemd service in custom AMI
  - [ ] Add configuration verification
  - [ ] Test with multiple EKS versions

#### 4.2 Document Custom AMI Process
- [ ] Create comprehensive AMI build guide
- [ ] Document testing procedures
- [ ] Establish AMI update cadence
- [ ] Create rollback procedures

### 5. Technical Debt Reduction

#### 5.1 Fix Celery Worker Readiness Probe
- [ ] Replace broken `celery inspect ping` exec probe
  - [ ] Add HTTP health endpoints (/healthz and /readyz)
  - [ ] Run small FastAPI server alongside celery worker
  - [ ] Update Kubernetes deployment to use HTTP probes
  - [ ] Follow pattern from storage_worker implementation

#### 5.2 Fix GitHub Actions Health Check Warning
- [ ] Investigate "Health check failed (non-critical)" warning in deploy workflow
  - [ ] Workflow uses curl to check health endpoint inside pod
  - [ ] Celery worker image doesn't have curl installed
  - [ ] Either add curl to base image or skip curl check for certain services
  - [ ] Warning is spurious - pod is actually healthy (1/1 Ready)

#### 5.3 Remove Inter-Service Health Checks (from Week 8)
- [ ] Audit remaining services for health check anti-patterns
  - [ ] Storage service
  - [ ] Storage worker
  - [ ] Dispatcher
  - [ ] Frontend
- [ ] Implement proper failure handling patterns
  - [ ] Try/catch with retries
  - [ ] Circuit breakers where appropriate
  - [ ] Graceful degradation
- [ ] Update monitoring and alerting

#### 5.2 Standardize Logging Infrastructure
- [ ] Replace print statements with proper logging
  - [ ] API service
  - [ ] Dispatcher service
  - [ ] Storage worker
  - [ ] Test infrastructure
- [ ] Implement structured logging
  - [ ] JSON format for production
  - [ ] Include trace IDs
  - [ ] Proper log levels

### 6. Testing Infrastructure

#### 6.1 Implement Adaptive Timeout Testing
- [ ] Create sophisticated timeout validation for tests
  - [ ] Consider cluster load when asserting on execution times
  - [ ] Account for pod scheduling delays and preemption
  - [ ] Implement load-aware timeout assertions
  - [ ] Add cluster resource metrics to test context
- [ ] Update test_evaluation_timeout to be less brittle
  - [ ] Remove hard-coded 15-second limit
  - [ ] Base expectations on actual cluster conditions
  - [ ] Consider retry attempts in timing calculations

#### 6.2 gVisor-Specific Tests
- [ ] Create test suite for gVisor functionality
  - [ ] Runtime isolation tests
  - [ ] Performance benchmarks
  - [ ] Security boundary tests
- [ ] Add gVisor to CI/CD pipeline
  - [ ] Validate all executors work with gVisor
  - [ ] Run security tests
  - [ ] Performance regression tests

#### 6.3 Chaos Testing for gVisor
- [ ] Test gVisor runtime failures
  - [ ] DaemonSet pod deletion
  - [ ] Containerd restart during evaluation
  - [ ] Node replacement scenarios
- [ ] Document failure modes and recovery

## Success Criteria 🎯

1. **gVisor Operational**
   - All evaluation pods run with gVisor runtime
   - No performance degradation > 20%
   - Security boundaries validated

2. **Platform Stability**
   - Exit code tracking fixed
   - Log shipping reliability > 99.9%
   - Health checks follow best practices

3. **Documentation Complete**
   - gVisor runbook created
   - AMI build process documented
   - Security boundaries documented

## Dependencies & Blockers 🚧

- gVisor DaemonSet requires careful security review
- Custom AMI process needs iteration time
- Log shipping changes may affect existing monitoring

## Notes 📝

- DaemonSet approach is tactical; custom AMI is strategic
- Consider using Bottlerocket OS in future (has better runtime support)
- gVisor adds ~50-100ms overhead per container start

## Completed Tasks ✅

### Monitoring Service Architecture Design
- [x] Identified fundamental design flaws in dispatcher log fetching
  - Dispatcher was trying to fetch logs when Kubernetes job completed
  - Created race conditions between job completion and pod cleanup
  - Made evaluation success dependent on log availability
  - Violated single responsibility principle

#### Key Issues Discovered:
1. **Double Race Condition**
   - Race between Job completion and Pod cleanup by cleanup controller
   - Race between Pod deletion and Loki log ingestion by Fluent Bit
   - Dispatcher interpreted "no logs in Loki yet" as "evaluation failed"

2. **Architectural Smell**
   - Logs are already handled by Fluent Bit → Loki pipeline
   - Dispatcher duplicating log collection responsibility
   - Bundling logs with completion events created unnecessary coupling

3. **Fix Implemented**
   - Removed exit code checking from log retrieval
   - Trust Kubernetes job status as source of truth
   - Made logs best-effort in completion events
   - Job succeeded = evaluation succeeded, regardless of log availability

### Monitoring Service Proposal
Based on the issues discovered, the monitoring service should:
- Own all log aggregation and retrieval
- Query Loki asynchronously after events
- Provide unified log API for all services
- Handle log shipping coordination with Fluent Bit
- Monitor log pipeline health

This separation would eliminate the race conditions and properly separate concerns.

## Additional Tasks (Time Permitting)

### Network Policy Implementation

#### Phase 1: Fix Current NetworkPolicies (Priority: High)
- [ ] Update evaluation pod NetworkPolicy to allow essential traffic
  - [ ] Add DNS egress rules (UDP/TCP port 53 to kube-dns)
  - [ ] Add Fluent Bit logging egress (TCP port 24224)
  - [ ] Add storage service egress for results (TCP port 8082)
  - [ ] Reference: [Evaluation Pod Network Requirements](../../networking/evaluation-pod-network-requirements.md)
- [ ] Update platform services NetworkPolicy
  - [ ] Add Redis access (port 6379)
  - [ ] Add Postgres access (port 5432)
  - [ ] Add inter-service communication rules
  - [ ] Reference: [NetworkPolicy Best Practices](../../networking/network-policy-best-practices.md)
- [ ] Test updated policies in dev environment
  - [ ] Verify DNS resolution works
  - [ ] Verify logs are collected
  - [ ] Verify results are stored
  - [ ] Verify all services can communicate

#### Phase 2: AWS VPC CNI Configuration (Priority: High)
- [ ] Verify ENABLE_NETWORK_POLICY environment variable is set correctly
  - [ ] Update Terraform to include null_resource workaround
  - [ ] Add automated verification in CI/CD
  - [ ] Reference: [AWS VPC CNI NetworkPolicy Setup](../../networking/aws-vpc-cni-network-policy-setup.md)
- [ ] Implement PolicyEndpoint monitoring
  - [ ] Add checks for PolicyEndpoint creation
  - [ ] Monitor eBPF program loading
  - [ ] Create alerts for NetworkPolicy failures

#### Phase 3: Evaluate CNI Alternatives (Priority: Medium)
- [ ] Research Calico integration with EKS
  - [ ] Test Calico alongside VPC CNI in dev cluster
  - [ ] Measure performance impact
  - [ ] Document installation process
  - [ ] Reference: [CNI Comparison](../../networking/cni-comparison.md)
- [ ] Evaluate Cilium as alternative
  - [ ] Test eBPF-based network policies
  - [ ] Assess L7 policy capabilities
  - [ ] Compare resource usage

#### Phase 4: Implement Full Network Isolation (Priority: Low)
- [ ] If internet blocking required, implement Calico
  - [ ] Create migration plan from VPC CNI
  - [ ] Test with evaluation workloads
  - [ ] Update NetworkPolicies for full isolation
- [ ] Consider alternative isolation methods
  - [ ] gVisor for network isolation
  - [ ] Security Groups for Pods
  - [ ] iptables in init containers
  - [ ] Reference: [Network Isolation Alternatives](../../networking/network-isolation-alternatives.md)

#### Phase 5: Testing and Validation
- [ ] Fix race condition in network isolation test
  - [ ] Add retry logic for Job pods
  - [ ] Implement wait for PolicyEndpoint sync
  - [ ] Update test to handle VPC CNI limitations
- [ ] Re-enable `test_network_isolation` in CI/CD
  - [ ] Update test to check internal traffic only (for VPC CNI)
  - [ ] Add separate test for external traffic (if using Calico)
- [ ] Create comprehensive network policy test suite
  - [ ] Test each service's allowed connections
  - [ ] Test blocked connections
  - [ ] Performance impact testing

#### Files to Update:
- `/k8s/base/security/network-policies-basic.yaml` - Fix egress rules
- `/k8s/base/kustomization.yaml` - Re-enable after fixing
- `/infrastructure/terraform/eks-vpc-cni.tf` - Add workaround
- `/tests/e2e/test_network_isolation.py` - Remove skip, add retry logic

## Links & Resources 🔗

- [gVisor Installation Analysis](../../deployment/gvisor-eks-analysis.md)
- [gVisor Documentation](https://gvisor.dev/docs/)
- [EKS Custom AMI Guide](https://docs.aws.amazon.com/eks/latest/userguide/eks-custom-ami.html)
- [Kubernetes DaemonSet Best Practices](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [Event Architecture Documentation](../../architecture/events.md)