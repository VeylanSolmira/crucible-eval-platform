# METR Production Architecture: Container-Based Evaluation Platform

## Why Kubernetes for METR

METR's core mission of evaluating potentially dangerous AI systems requires:
- **Extreme isolation**: Running untrusted code safely
- **Scale**: Parallel evaluation of multiple models
- **Resource management**: GPU scheduling, memory limits
- **Audit trails**: Who ran what, when, and what happened
- **Reproducibility**: Exact same environment every time

Kubernetes provides all of this out of the box.

## Likely METR Production Architecture

```yaml
# Simplified view of METR's likely k8s architecture
┌─────────────────────────────────────────────────────────────┐
│                        EKS Cluster                           │
│                                                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  Control Plane  │  │  Evaluation Pods │  │ Monitoring │ │
│  │  - API Server   │  │  - gVisor/kata   │  │ - Prometh. │ │
│  │  - Scheduler    │  │  - Isolated      │  │ - Grafana  │ │
│  │  - Web Frontend │  │  - Time-limited  │  │ - Falco    │ │
│  └─────────────────┘  └──────────────────┘  └────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Node Groups (Auto-scaling)                │    │
│  │  - CPU Nodes (t3.large)                             │    │
│  │  - GPU Nodes (g4dn.xlarge) - for model evaluation  │    │
│  │  - Spot Instances for cost optimization            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Key Components for METR Use Case

### 1. Container Runtime Security
```yaml
# Pod with gVisor runtime for untrusted code
apiVersion: v1
kind: Pod
metadata:
  name: evaluation-pod
  annotations:
    io.kubernetes.cri-o.TrustedSandbox: "false"
    io.kubernetes.cri-o.SandboxRuntime: "runsc"  # gVisor
spec:
  runtimeClassName: gvisor  # Critical for METR
  securityContext:
    runAsNonRoot: true
    readOnlyRootFilesystem: true
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL
```

### 2. Network Isolation
```yaml
# NetworkPolicy to prevent model exfiltration
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: evaluation-isolation
spec:
  podSelector:
    matchLabels:
      app: evaluation-pod
  policyTypes:
  - Ingress
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: result-collector
    ports:
    - protocol: TCP
      port: 8080
  # No other egress allowed - prevents model self-exfiltration
```

### 3. Resource Limits & Quotas
```yaml
# ResourceQuota for evaluation namespace
apiVersion: v1
kind: ResourceQuota
metadata:
  name: evaluation-quota
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    requests.nvidia.com/gpu: "4"
    persistentvolumeclaims: "10"
    pods: "50"
```

### 4. Job-Based Evaluations
```yaml
# Evaluation as a Kubernetes Job
apiVersion: batch/v1
kind: Job
metadata:
  name: eval-gpt4-safety
spec:
  ttlSecondsAfterFinished: 3600  # Auto-cleanup
  activeDeadlineSeconds: 7200     # 2-hour timeout
  template:
    spec:
      runtimeClassName: gvisor
      containers:
      - name: evaluator
        image: metr/evaluation-runtime:v1.2.3
        env:
        - name: MODEL_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: model-credentials
              key: endpoint
        - name: EVALUATION_ID
          value: "eval-123456"
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
          limits:
            memory: "32Gi"
            cpu: "8"
            nvidia.com/gpu: "1"
        volumeMounts:
        - name: eval-code
          mountPath: /evaluation
          readOnly: true
      volumes:
      - name: eval-code
        configMap:
          name: evaluation-code-gpt4
      restartPolicy: OnFailure
```

## Container Build Pipeline

```dockerfile
# Multi-stage Dockerfile for evaluation runtime
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

# Security: Run as non-root
RUN useradd -m -u 1000 evaluator

# Copy only necessary files
COPY --from=builder /root/.local /home/evaluator/.local
COPY --chown=evaluator:evaluator src/ /app/

# Security: Read-only filesystem compatibility
RUN mkdir -p /tmp/evaluation && chown evaluator:evaluator /tmp/evaluation

USER evaluator
WORKDIR /app

ENV PATH=/home/evaluator/.local/bin:$PATH
ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "crucible.evaluation.runner"]
```

## GitOps Deployment Flow

```yaml
# ArgoCD Application for continuous deployment
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: crucible-platform
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/metr/crucible-platform
    targetRevision: HEAD
    path: k8s/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: crucible-production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

## Migration Path from EC2 to Kubernetes

### Phase 1: Containerize (Current Sprint)
```bash
# Build container locally
docker build -t crucible-platform:latest .

# Test with docker-compose
docker-compose up -d

# Verify gVisor integration
docker run --runtime=runsc crucible-platform:latest
```

### Phase 2: Local Kubernetes Testing
```bash
# Use kind or minikube
kind create cluster --config=kind-config.yaml

# Install gVisor runtime
kubectl apply -f https://raw.githubusercontent.com/google/gvisor/master/runsc/installer/runsc-installer.yaml

# Deploy your app
kubectl apply -f k8s/base/
```

### Phase 3: EKS Migration
```hcl
# terraform/eks.tf
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "metr-evaluation-platform"
  cluster_version = "1.28"

  node_groups = {
    cpu_nodes = {
      instance_types = ["t3.large"]
      min_size       = 2
      max_size       = 10
      desired_size   = 3
    }
    
    gpu_nodes = {
      instance_types = ["g4dn.xlarge"]
      min_size       = 0
      max_size       = 5
      desired_size   = 1
      
      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}
```

## METR-Specific Security Features

### 1. Admission Controllers
```yaml
# OPA policy to enforce security constraints
package kubernetes.admission

deny[msg] {
  input.request.kind.kind == "Pod"
  input.request.object.metadata.labels.app == "evaluation-pod"
  not input.request.object.spec.runtimeClassName == "gvisor"
  msg := "Evaluation pods must use gVisor runtime"
}
```

### 2. Audit Logging
```yaml
# Falco rules for anomaly detection
- rule: Evaluation Pod Network Access
  desc: Detect network access from evaluation pods
  condition: >
    container.id != host and
    container.label.app = "evaluation-pod" and
    (fd.type = ipv4 or fd.type = ipv6) and
    not fd.sip in (allowed_ips)
  output: >
    Unexpected network access from evaluation pod
    (user=%user.name command=%proc.cmdline)
  priority: WARNING
```

### 3. Result Collection
```yaml
# Sidecar pattern for secure result extraction
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: evaluator
    image: metr/evaluator:latest
    volumeMounts:
    - name: results
      mountPath: /results
  
  - name: result-collector
    image: metr/result-collector:latest
    volumeMounts:
    - name: results
      mountPath: /results
      readOnly: true
    env:
    - name: S3_BUCKET
      value: metr-evaluation-results
```

## Why This Architecture for METR

1. **Isolation**: Multiple layers (gVisor + K8s + Network Policies)
2. **Scale**: Auto-scaling node groups, job queues
3. **Auditability**: Every action logged and traceable
4. **Cost**: Spot instances for non-critical evaluations
5. **Flexibility**: Easy to add new evaluation types
6. **Security**: Defense in depth approach
7. **Compliance**: Meet any regulatory requirements

## Next Steps for Your Project

1. **Start with Docker**: Get your app containerized
2. **Add docker-compose**: Test multi-container setup
3. **Create K8s manifests**: Start with basic deployments
4. **Add security layers**: NetworkPolicies, SecurityContexts
5. **Test locally**: Use kind/minikube with gVisor
6. **Document everything**: METR values thorough documentation

This architecture demonstrates understanding of:
- Container security best practices
- Kubernetes production patterns
- AI/ML infrastructure requirements
- Cost optimization strategies
- Security-first design

This is exactly the kind of system METR would build for evaluating potentially dangerous AI systems at scale.