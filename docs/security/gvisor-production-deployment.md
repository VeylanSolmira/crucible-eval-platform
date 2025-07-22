# gVisor Production Deployment Guide

## Current State - Critical Issue ⚠️

As of July 16, 2025, our dispatcher service **hardcodes** the gVisor runtime requirement:

```python
# dispatcher_service/app.py - Line 171
runtime_class_name="gvisor",  # This will FAIL if gVisor isn't installed!
```

**This means production deployments will fail unless gVisor is properly installed on all nodes.**

## Why This Matters

1. **Security Requirement**: gVisor is critical for safely running untrusted AI model code
2. **Not Default**: No cloud provider includes gVisor by default (except GKE Sandbox)
3. **Node-Level Setup**: Requires installation and configuration on each Kubernetes node
4. **Current Code Has No Fallback**: Will crash when creating evaluation pods

## Production Deployment Options

### Option A: Google Kubernetes Engine (Recommended) ✅

GKE has built-in gVisor support via GKE Sandbox:

```bash
# Create cluster with gVisor enabled
gcloud container clusters create crucible-production \
  --zone us-central1-a \
  --enable-sandbox \
  --sandbox-type=gvisor \
  --num-nodes 3 \
  --machine-type n2-standard-4

# Deploy our manifests - will work immediately
kubectl apply -k k8s/overlays/production
```

**Pros**:
- Zero configuration needed
- Google maintains gVisor
- Production-tested at scale
- Automatic updates

**Cons**:
- Locked to GCP
- Slightly higher cost
- Some GKE-specific constraints

### Option B: Amazon EKS with Custom AMI 🔧

EKS requires custom setup:

```bash
# 1. Create custom AMI with gVisor
packer build eks-gvisor-ami.json

# 2. Create nodegroup with custom AMI
eksctl create nodegroup \
  --cluster crucible-production \
  --name gvisor-nodes \
  --node-ami ami-xxxxx \
  --nodes 3

# 3. Apply RuntimeClass
kubectl apply -f k8s/base/gvisor-runtimeclass.yaml

# 4. Deploy application
kubectl apply -k k8s/overlays/production
```

**Setup Script for AMI**:
```bash
#!/bin/bash
# Install gVisor on Amazon Linux 2
wget https://storage.googleapis.com/gvisor/releases/release/latest/x86_64/runsc
wget https://storage.googleapis.com/gvisor/releases/release/latest/x86_64/containerd-shim-runsc-v1
chmod +x runsc containerd-shim-runsc-v1
mv runsc containerd-shim-runsc-v1 /usr/local/bin/

# Configure containerd
cat >> /etc/containerd/config.toml <<EOF
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runsc]
  runtime_type = "io.containerd.runsc.v1"
EOF

systemctl restart containerd
```

**Pros**:
- Full control over configuration
- Can optimize for specific needs
- Works with existing AWS infrastructure

**Cons**:
- Complex setup and maintenance
- Must maintain custom AMIs
- Manual security updates

### Option C: Add Fallback Logic (Development Only) ⚠️

For development/testing environments where security isn't critical:

```python
# dispatcher_service/app.py - Modified version
def create_evaluation_job(request: ExecuteRequest):
    # Check if gVisor is available
    runtime_class = None
    try:
        v1 = client.CoreV1Api()
        v1.read_runtime_class("gvisor")
        runtime_class = "gvisor"
        logger.info("Using gVisor runtime for strong isolation")
    except client.exceptions.ApiException:
        logger.warning(
            "gVisor RuntimeClass not found - running with standard isolation. "
            "DO NOT USE IN PRODUCTION!"
        )
        # Could also reject the request here for production
        if os.getenv("REQUIRE_GVISOR", "false").lower() == "true":
            raise HTTPException(
                status_code=503,
                detail="gVisor runtime required but not available"
            )
    
    # ... rest of job creation
    spec=client.V1PodSpec(
        runtime_class_name=runtime_class,  # None is valid, uses default
        # ... rest of spec
    )
```

**Never use fallback in production** - it defeats the entire security model!

## Verification Steps

After deployment, verify gVisor is working:

```bash
# 1. Check RuntimeClass exists
kubectl get runtimeclass gvisor

# 2. Test evaluation pod
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: gvisor-test
  namespace: crucible
spec:
  runtimeClassName: gvisor
  containers:
  - name: test
    image: busybox
    command: ["uname", "-a"]
  restartPolicy: Never
EOF

# 3. Check output - should show gVisor kernel
kubectl logs gvisor-test
# Output: Linux gvisor 4.4.0 #1 SMP ... (gVisor version, not host kernel)

# 4. Clean up
kubectl delete pod gvisor-test
```

## Security Validation

Run security tests to ensure isolation:

```bash
# Run our filesystem isolation test
pytest tests/integration/test_filesystem_isolation.py

# Should now pass - gVisor blocks access to /etc/passwd
```

## Monitoring in Production

Add alerts for:

1. **Evaluation pods without gVisor**:
   ```yaml
   alert: EvaluationWithoutGvisor
   expr: |
     kube_pod_info{namespace="crucible",pod=~"eval-.*"}
     unless on(pod) 
     kube_pod_spec_runtime_class{runtime_class="gvisor"}
   annotations:
     summary: "Evaluation pod {{ $labels.pod }} running without gVisor"
     severity: critical
   ```

2. **RuntimeClass availability**:
   ```yaml
   alert: GvisorRuntimeClassMissing
   expr: |
     absent(kube_runtimeclass_info{runtimeclass="gvisor"})
   annotations:
     summary: "gVisor RuntimeClass not found in cluster"
     severity: critical
   ```

## Decision Matrix

| Environment | Requirement | Solution |
|------------|-------------|----------|
| Local Development | Optional | Kind without gVisor OK |
| Staging | Recommended | Add fallback + warnings |
| Production | **MANDATORY** | GKE or custom nodes |

## Next Steps

1. **Immediate**: Add environment detection to dispatcher
2. **Short-term**: Document GKE deployment process
3. **Medium-term**: Create Terraform modules for each cloud
4. **Long-term**: Consider Kata Containers as alternative

## References

- [gVisor Documentation](https://gvisor.dev/)
- [GKE Sandbox Guide](https://cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods)
- [EKS Custom AMI Guide](https://docs.aws.amazon.com/eks/latest/userguide/eks-custom-ami.html)
- [RuntimeClass Documentation](https://kubernetes.io/docs/concepts/containers/runtime-class/)