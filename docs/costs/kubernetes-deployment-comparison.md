# Kubernetes vs EC2 Blue-Green Deployment Comparison

## Current EC2 Blue-Green Approach

### How It Works
- Two complete, independent EC2 instances (blue & green)
- Full infrastructure duplication (compute, storage, IPs)
- Traffic switched at DNS level (Route53 A record)
- **Cost**: 2x infrastructure = 2x cost

### Limitations
- Coarse-grained: All or nothing traffic switching
- Resource inefficient: 50% of resources idle
- Slow rollback: DNS TTL delays
- No gradual rollout capability

## Kubernetes Modern Deployment Patterns

### 1. Rolling Updates (Default K8s)
```yaml
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2        # Extra pods during update
      maxUnavailable: 1  # Pods that can be down
```
- Gradually replaces old pods with new ones
- Zero downtime with proper readiness probes
- **Cost efficient**: Only temporary extra pods

### 2. Canary Deployments
```yaml
# Using Flagger or Argo Rollouts
spec:
  canaryAnalysis:
    interval: 30s
    threshold: 5
    stepWeight: 10  # Increase traffic by 10% each step
    metrics:
    - name: error-rate
      threshold: 1
    - name: latency
      threshold: 500
```
- Start with 5% traffic to new version
- Gradually increase based on metrics
- Automatic rollback on failures
- **Cost**: Minimal overhead (5-10% extra pods)

### 3. Blue-Green in Kubernetes
```yaml
# Service selector switching
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
    version: green  # Switch from 'blue' to 'green'
```
- Instant traffic switching via label selectors
- Both versions running temporarily
- **Cost**: 2x pods only during deployment

### 4. A/B Testing with Istio
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
spec:
  http:
  - match:
    - headers:
        user-group:
          exact: beta
    route:
    - destination:
        host: myapp
        subset: v2
      weight: 100
  - route:
    - destination:
        host: myapp
        subset: v1
      weight: 90
    - destination:
        host: myapp
        subset: v2
      weight: 10
```
- Route based on headers, cookies, or percentages
- Multiple versions simultaneously
- Fine-grained traffic control

## Cost Comparison

### EC2 Blue-Green (Current)
```
Monthly Cost: $34.44
- Blue environment: $17.22 (always running)
- Green environment: $17.22 (always running)
- Utilization: 50% (one always idle)
```

### Kubernetes Cluster Approach
```
Base EKS Cluster: ~$73/month (control plane)
Worker Nodes: 2x t3.medium = ~$60/month
Total: ~$133/month

BUT serves multiple applications and provides:
- Auto-scaling (pay for what you use)
- Multiple deployment strategies
- Better resource utilization (80-90% vs 50%)
- Built-in monitoring and logging
```

### Cost per Application
- **EC2**: $34.44 for one app
- **K8s**: $133 ÷ 10 apps = $13.30 per app

## Modern Deployment Strategies in K8s

### 1. Progressive Delivery
```yaml
# Flagger canary configuration
apiVersion: flagger.app/v1beta1
kind: Canary
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myapp
  progressDeadlineSeconds: 60
  service:
    port: 80
  analysis:
    interval: 30s
    threshold: 5
    stepWeight: 10
    stepWeightPromotion: 100
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
    - name: request-duration
      thresholdRange:
        max: 500
```

### 2. Feature Flags Integration
```python
# In application code
if feature_flag.is_enabled("new-ml-model", user_id):
    result = new_model.predict(data)
else:
    result = old_model.predict(data)
```
- Deploy code without activating features
- Gradual rollout independent of deployment
- Instant rollback without redeployment

### 3. GitOps with ArgoCD
```yaml
# Automated sync from Git
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: https://github.com/yourrepo
    path: k8s/
    targetRevision: HEAD
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

## Why Kubernetes Patterns are Superior

### 1. Granular Control
- **EC2**: 0% or 100% traffic
- **K8s**: Any percentage (1%, 5%, 10%, 25%, 50%, 100%)

### 2. Faster Rollback
- **EC2**: DNS TTL wait (60+ seconds)
- **K8s**: Instant (label selector change)

### 3. Resource Efficiency
- **EC2**: 50% idle resources
- **K8s**: 5-10% overhead during deployments only

### 4. Automated Validation
- **EC2**: Manual validation required
- **K8s**: Automated metrics-based promotion

### 5. Multi-Version Support
- **EC2**: 2 versions max (blue/green)
- **K8s**: Unlimited versions for A/B testing

## Migration Path from EC2 to K8s

### Phase 1: Containerization (Current) ✓
- Docker images built
- Docker Compose orchestration
- Ready for K8s

### Phase 2: K8s Manifests
```yaml
# Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crucible-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crucible-api
  template:
    metadata:
      labels:
        app: crucible-api
        version: v1
    spec:
      containers:
      - name: api
        image: crucible-platform/api:latest
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

### Phase 3: Progressive Delivery Setup
1. Install Flagger or Argo Rollouts
2. Define canary analysis metrics
3. Set up Prometheus for metrics
4. Configure gradual rollout policies

### Phase 4: Service Mesh (Optional)
- Istio or Linkerd for advanced traffic management
- Observability and security out of the box
- Complex routing rules (header-based, etc.)

## Recommendations

### For METR Evaluation Platform
1. **Current Stage**: EC2 blue-green is fine for single app
2. **Growth Stage**: Move to EKS when you have 3+ services
3. **Deployment Strategy**: Start with rolling updates, add canary when needed
4. **Cost Optimization**: Use spot instances for non-critical workloads

### Modern Best Practices
1. **Never do big-bang deployments**
2. **Always validate with small traffic percentages**
3. **Automate rollback decisions based on metrics**
4. **Separate deployment from feature release (feature flags)**
5. **Use GitOps for audit trail and easy rollback**

## Conclusion

While EC2 blue-green works, Kubernetes enables:
- **10x more deployment flexibility**
- **2-3x better resource utilization**
- **Automated, metric-driven deployments**
- **Per-request routing capabilities**

The future is percentage-based, automated progressive delivery rather than manual all-or-nothing switches.