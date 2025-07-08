# Kubernetes Evaluation Architecture Tasks

## Tasks Not Automatically Handled by Kubernetes

While Kubernetes handles many aspects of container lifecycle management, several evaluation-specific requirements need custom implementation:

### 1. Log Aggregation and Persistence

**The Challenge**: Kubernetes doesn't aggregate or persist logs by default. Pods are ephemeral and their logs disappear when deleted.

**Tasks**:
- [ ] Implement log streaming from pods to persistent storage
- [ ] Handle multi-line logs (Python tracebacks)
- [ ] Separate stdout/stderr streams
- [ ] Store logs before pod garbage collection

```python
# Example implementation needed
async def stream_pod_logs(eval_id: str):
    """Stream logs to persistent storage before pod deletion"""
    v1 = client.CoreV1Api()
    
    # Stream logs from pod
    logs = v1.read_namespaced_pod_log(
        name=f"eval-{eval_id}",
        namespace="evaluations",
        follow=True,
        _preload_content=False
    )
    
    # Store in Redis/S3/Database before pod is deleted
    async for line in logs:
        await store_log_line(eval_id, line)
```

### 2. Result Extraction Pattern

**The Challenge**: Kubernetes tells you a Job completed, but not what the output was.

**Tasks**:
- [ ] Design result extraction workflow
- [ ] Handle pod name discovery (Job → Pod mapping)
- [ ] Extract exit codes from Job status
- [ ] Implement retry logic for transient failures

```python
# Need to implement
async def extract_job_results(job_name: str):
    """Get results after job completion"""
    # Find pod created by job
    pods = v1.list_namespaced_pod(
        namespace="evaluations",
        label_selector=f"job-name={job_name}"
    )
    
    if not pods.items:
        raise PodNotFoundError()
        
    pod_name = pods.items[0].metadata.name
    
    # Race to get logs before garbage collection
    try:
        logs = v1.read_namespaced_pod_log(pod_name, "evaluations")
    except ApiException as e:
        if e.status == 404:
            # Pod already deleted!
            return get_logs_from_storage(job_name)
```

### 3. Resource Quota Management

**The Challenge**: Need to manage evaluation resource allocation across the cluster.

**Tasks**:
- [ ] Implement per-user resource quotas
- [ ] Design priority classes for evaluations
- [ ] Handle quota exhaustion gracefully
- [ ] Monitor resource usage patterns

```yaml
# Need to create
apiVersion: v1
kind: ResourceQuota
metadata:
  name: evaluation-quota
spec:
  hard:
    requests.cpu: "100"
    requests.memory: "100Gi"
    count/jobs.batch: "50"  # Max concurrent evaluations
```

### 4. Security Isolation

**The Challenge**: Kubernetes provides some isolation, but evaluations need additional security.

**Tasks**:
- [ ] Implement PodSecurityPolicies or Pod Security Standards
- [ ] Design network policies for evaluation pods
- [ ] Set up seccomp/AppArmor profiles
- [ ] Configure runtime security (gVisor/Kata)

### 5. Evaluation Controller Implementation

**The Challenge**: Need custom controller to manage evaluation lifecycle.

**Tasks**:
- [ ] Implement EvaluationJob CRD (Custom Resource Definition)
- [ ] Build controller with proper reconciliation loop
- [ ] Handle edge cases (orphaned jobs, partial failures)
- [ ] Implement proper leader election for HA

```go
// Controller pseudocode
func (r *EvaluationReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    // Get EvaluationJob resource
    evalJob := &v1.EvaluationJob{}
    if err := r.Get(ctx, req.NamespacedName, evalJob); err != nil {
        return ctrl.Result{}, err
    }
    
    // Check if Job exists
    job := &batchv1.Job{}
    err := r.Get(ctx, types.NamespacedName{
        Name: evalJob.Status.JobName,
        Namespace: evalJob.Namespace,
    }, job)
    
    if err != nil && errors.IsNotFound(err) {
        // Create Job
        return r.createJob(ctx, evalJob)
    }
    
    // Update status based on Job
    return r.updateStatus(ctx, evalJob, job)
}
```

### 6. Distributed Tracing

**The Challenge**: In Kubernetes, evaluation requests flow through multiple components.

**Tasks**:
- [ ] Implement OpenTelemetry instrumentation
- [ ] Add trace context propagation
- [ ] Design trace sampling strategy
- [ ] Set up trace storage and visualization

### 7. Cost Attribution

**The Challenge**: Need to track resource usage per evaluation for cost management.

**Tasks**:
- [ ] Implement pod labels for cost tracking
- [ ] Integrate with cluster cost monitoring
- [ ] Design chargeback/showback reports
- [ ] Handle spot instance usage

### 8. Evaluation Artifacts

**The Challenge**: Some evaluations may produce files/artifacts beyond logs.

**Tasks**:
- [ ] Design artifact extraction from pods
- [ ] Implement temporary volume management
- [ ] Handle large artifact uploads
- [ ] Set up artifact retention policies

### 9. Webhook Handlers

**The Challenge**: Need to notify external systems of evaluation status.

**Tasks**:
- [ ] Implement admission webhooks for validation
- [ ] Design mutation webhooks for defaults
- [ ] Create conversion webhooks for CRD versions
- [ ] Handle webhook failures gracefully

### 10. Multi-Cluster Considerations

**The Challenge**: May need to run evaluations across multiple clusters.

**Tasks**:
- [ ] Design cluster selection strategy
- [ ] Implement cross-cluster job scheduling
- [ ] Handle cluster-specific resource limits
- [ ] Set up cross-cluster monitoring

## Migration Specific Tasks

### From Docker to Kubernetes

- [ ] Map Docker security opts to Pod Security Standards
- [ ] Convert container resource limits to K8s format
- [ ] Migrate from Docker events to K8s watch API
- [ ] Update networking from bridge to K8s CNI

### Backward Compatibility

- [ ] Support both Docker and K8s executors during migration
- [ ] Implement feature flags for gradual rollout
- [ ] Design rollback strategy
- [ ] Maintain API compatibility