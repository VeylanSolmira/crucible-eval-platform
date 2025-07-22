# Smoke Tests for Kubernetes Cluster Access

## Purpose

These minimal smoke tests verify cluster readiness BEFORE attempting to run the main test suite. They run from **outside** the cluster and check that we can:

1. **Connect to the cluster** - kubectl works
2. **Access our namespace** - namespace exists and is active  
3. **Find required services** - all services are deployed
4. **Execute jobs** - can create and run K8s jobs
5. **Reach the API** - API gateway is accessible

## Philosophy

The smoke tests follow the principle of "fail fast" - if we can't do these basic operations from outside the cluster, there's no point trying to run the full test suite inside the cluster.

## Running the Smoke Tests

```bash
# From project root
python tests/smoke/run_smoke_tests.py

# Or with pytest directly
pytest tests/smoke/test_cluster_access.py -v

# With a specific namespace
K8S_NAMESPACE=my-namespace pytest tests/smoke/test_cluster_access.py -v
```

## What Happens Next?

If smoke tests **PASS** ✅:
- The cluster is ready for the main test suite
- You can run tests inside the cluster as Kubernetes Jobs
- All services are reachable and healthy

If smoke tests **FAIL** ❌:
- Check kubectl configuration: `kubectl config current-context`
- Verify namespace exists: `kubectl get ns`
- Check pod status: `kubectl get pods -n crucible`
- Review service endpoints: `kubectl get endpoints -n crucible`

## Test Details

### 1. Kubectl Connectivity
```python
def test_kubectl_connectivity():
    # Verifies: kubectl version --short
    # Ensures: Can talk to Kubernetes API server
```

### 2. Namespace Access
```python
def test_namespace_exists():
    # Verifies: kubectl get namespace <name>
    # Ensures: Namespace exists and is Active
```

### 3. Service Discovery
```python
def test_required_services():
    # Verifies: All required services exist
    # Checks: Service endpoints have addresses
    # Services: api, celery-redis, postgres, etc.
```

### 4. Job Execution
```python
def test_simple_job_execution():
    # Creates: Simple busybox job
    # Waits: For completion
    # Verifies: Logs contain expected output
```

### 5. API Health
```python
def test_api_accessible():
    # Tries: Direct access (LoadBalancer/Ingress)
    # Falls back: Port-forward if needed
    # Verifies: /health returns healthy
```

## Design Decisions

**Why run from outside the cluster?**
- If we can't access the cluster from outside, we can't deploy test jobs
- These tests verify our deployment pipeline will work
- They're fast and don't require building/pushing test images

**Why not just use port-forwards for everything?**
- Port-forwards are a workaround, not the ideal
- In production/CI, tests should run inside the cluster
- Smoke tests verify we CAN run jobs, then main tests run AS jobs

**Why separate from main test suite?**
- Clear separation of concerns
- Fast feedback loop
- Can run without test dependencies installed