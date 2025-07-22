# Kubernetes Python Client Migration

## Overview
The test orchestrator currently uses `subprocess.run()` to execute kubectl commands. This document analyzes why migrating to the Kubernetes Python client would be beneficial and outlines the approach.

## Current Implementation Issues

### Security Concerns
- **Command injection risk**: While currently safe due to controlled inputs, subprocess commands can be vulnerable if inputs aren't properly validated
- **Shell execution**: Although we avoid `shell=True`, the pattern of shelling out to commands is inherently less secure than API calls
- **No input validation**: Commands are constructed with minimal validation of parameters

### Reliability Issues
- **Output parsing**: Relies on parsing JSON from kubectl output, which can be fragile
- **Version dependencies**: Different kubectl versions may have different output formats
- **Race conditions**: We discovered timing issues when checking job status (had to add `kubectl wait`)
- **Error handling**: Limited to checking return codes rather than structured exceptions

### Maintenance Concerns
- **String manipulation**: Building commands as strings is error-prone
- **No type safety**: Everything is strings and dictionaries
- **Limited debugging**: Hard to debug when commands fail

## Benefits of Kubernetes Python Client

### Type Safety and Structure
```python
# Current approach
result = subprocess.run(["kubectl", "get", "job", job_name, "-n", namespace, "-o", "json"], 
                       capture_output=True, text=True)
if result.returncode == 0:
    job_data = json.loads(result.stdout)
    succeeded = job_data.get("status", {}).get("succeeded", 0)

# Python client approach
from kubernetes import client
batch_v1 = client.BatchV1Api()
job = batch_v1.read_namespaced_job(name=job_name, namespace=namespace)
succeeded = job.status.succeeded or 0
```

### Better Error Handling
```python
# Current approach
if result.returncode != 0:
    print(f"Failed: {result.stderr}")
    return 1

# Python client approach
try:
    job = batch_v1.read_namespaced_job(name=job_name, namespace=namespace)
except client.exceptions.ApiException as e:
    if e.status == 404:
        print(f"Job {job_name} not found")
    else:
        print(f"API error: {e.reason}")
```

### Real-time Watching
```python
# Current approach - polling with kubectl wait
subprocess.run(["kubectl", "wait", "--for=condition=complete", f"job/{job_name}", 
                "-n", namespace, "--timeout=30s"])

# Python client approach - event-based watching
from kubernetes import watch
w = watch.Watch()
for event in w.stream(batch_v1.list_namespaced_job, 
                     namespace=namespace,
                     field_selector=f"metadata.name={job_name}",
                     timeout_seconds=30):
    job = event['object']
    if job.status.succeeded:
        print(f"Job {job_name} completed successfully")
        w.stop()
        return 0
    elif job.status.failed:
        print(f"Job {job_name} failed")
        w.stop()
        return 1
```

## Migration Approach

### Phase 1: Setup and Authentication
1. Add kubernetes Python package to requirements
2. Implement config loading (works with existing kubeconfig)
3. Create client initialization with proper error handling

### Phase 2: Core Functions
1. Replace job creation (`kubectl apply`)
2. Replace job status checking (`kubectl get`)
3. Replace job waiting (`kubectl wait`)
4. Replace log streaming (`kubectl logs`)

### Phase 3: Advanced Features
1. Implement proper watch APIs for real-time updates
2. Add retry logic with exponential backoff
3. Improve error messages with structured exceptions

### Phase 4: Cleanup
1. Remove all subprocess.run calls
2. Remove JSON parsing logic
3. Add comprehensive error handling

## Example Implementation

```python
class KubernetesTestOrchestrator:
    def __init__(self):
        # Load config from default location (~/.kube/config) or in-cluster
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()
    
    def submit_job(self, job_manifest: dict) -> str:
        """Submit a job using the API instead of kubectl apply."""
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(**job_manifest["metadata"]),
            spec=client.V1JobSpec(**job_manifest["spec"])
        )
        
        created = self.batch_v1.create_namespaced_job(
            namespace=self.namespace,
            body=job
        )
        return created.metadata.name
    
    def monitor_job(self, job_name: str) -> int:
        """Monitor job using watch API instead of kubectl logs + wait."""
        # Stream logs
        w = watch.Watch()
        for event in w.stream(self.core_v1.list_namespaced_pod,
                             namespace=self.namespace,
                             label_selector=f"job-name={job_name}"):
            pod = event['object']
            if pod.status.phase == "Running":
                # Stream logs from the pod
                logs = self.core_v1.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=self.namespace,
                    follow=True,
                    _preload_content=False
                )
                for line in logs:
                    print(line.decode('utf-8'), end='')
                w.stop()
                break
        
        # Wait for job completion
        for event in w.stream(self.batch_v1.list_namespaced_job,
                             namespace=self.namespace,
                             field_selector=f"metadata.name={job_name}",
                             timeout_seconds=300):
            job = event['object']
            if job.status.succeeded:
                return 0
            elif job.status.failed:
                return 1
```

## Considerations

### Pros
- **Security**: No subprocess/shell execution risks
- **Reliability**: Direct API communication, structured responses
- **Type safety**: Real Python objects with attributes
- **Error handling**: Proper exceptions with meaningful messages
- **Performance**: Connection pooling, efficient streaming
- **Features**: Access to watch APIs, field selectors, etc.

### Cons
- **Complexity**: Slightly more complex initial setup
- **Dependencies**: Additional package requirement
- **Learning curve**: Need to understand Kubernetes API objects
- **Debugging**: May need to understand Kubernetes API internals

## Recommendation
The migration to Kubernetes Python client is strongly recommended for:
1. Enhanced security (no subprocess risks)
2. Better reliability (no output parsing)
3. Improved maintainability (type safety, better errors)
4. Access to advanced features (watching, streaming)

The investment in migration will pay off in reduced debugging time and improved robustness.