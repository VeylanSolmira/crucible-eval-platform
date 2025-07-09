# Progressive Deployment Strategies in Kubernetes

## Overview

Modern Kubernetes deployments have evolved far beyond simple "replace all pods" strategies. This guide covers the state-of-the-art approaches for rolling out new versions with minimal risk and maximum control.

## Deployment Strategies Comparison

| Strategy | Risk | Speed | Rollback | Cost | Use Case |
|----------|------|-------|----------|------|----------|
| Recreate | High | Fast | Slow | Low | Dev/Test only |
| Rolling Update | Medium | Medium | Fast | Low | Simple apps |
| Blue-Green | Low | Instant | Instant | High | Critical apps |
| Canary | Very Low | Slow | Instant | Medium | Most production apps |
| A/B Testing | Very Low | Variable | Instant | Medium | Feature validation |
| Shadow | None | N/A | N/A | High | Risk-free testing |

## 1. Rolling Updates (Kubernetes Default)

### How It Works
Kubernetes gradually replaces old pods with new ones, ensuring availability throughout.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 2  # Maximum pods that can be unavailable
      maxSurge: 2        # Maximum pods that can be created above replicas
```

### Timeline Example
```
Time 0: v1 v1 v1 v1 v1 v1 v1 v1 v1 v1 (10 pods v1)
Time 1: v1 v1 v1 v1 v1 v1 v1 v1 v2 v2 (8 pods v1, 2 pods v2)
Time 2: v1 v1 v1 v1 v1 v1 v2 v2 v2 v2 (6 pods v1, 4 pods v2)
Time 3: v1 v1 v1 v1 v2 v2 v2 v2 v2 v2 (4 pods v1, 6 pods v2)
Time 4: v1 v1 v2 v2 v2 v2 v2 v2 v2 v2 (2 pods v1, 8 pods v2)
Time 5: v2 v2 v2 v2 v2 v2 v2 v2 v2 v2 (10 pods v2)
```

### Pros & Cons
✅ Zero downtime  
✅ Built into Kubernetes  
✅ Resource efficient  
❌ No control over traffic percentage  
❌ Can't test with small traffic first  
❌ Rollback means another rolling update  

## 2. Canary Deployments

### How It Works
Start with a small percentage of traffic to the new version, gradually increase based on metrics.

### Using Flagger
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: my-app
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  service:
    port: 80
    targetPort: 8080
  analysis:
    # Check metrics every 30 seconds
    interval: 30s
    # Number of checks before promotion
    threshold: 10
    # Max number of failed checks
    maxWeight: 50
    # Percentage of traffic increase
    stepWeight: 5
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 30s
    webhooks:
    - name: load-test
      url: http://loadtester/
      timeout: 5s
```

### Traffic Progression
```
0 min:  100% v1, 0% v2   (Deploy v2, no traffic)
2 min:  95% v1,  5% v2   (Start canary)
4 min:  90% v1,  10% v2  (Metrics good, increase)
6 min:  85% v1,  15% v2  (Metrics good, increase)
8 min:  80% v1,  20% v2  (Metrics good, increase)
...
20 min: 50% v1,  50% v2  (Metrics good, increase)
...
40 min: 0% v1,   100% v2 (Full promotion)
```

### Automatic Rollback
```yaml
# If metrics fail at any point:
10 min: 80% v1, 20% v2  (Error rate spike detected!)
11 min: 100% v1, 0% v2  (Automatic rollback)
```

## 3. Blue-Green Deployments in Kubernetes

### Using Service Selectors
```yaml
# Blue Deployment (Current)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-blue
spec:
  replicas: 10
  selector:
    matchLabels:
      app: my-app
      version: blue
  template:
    metadata:
      labels:
        app: my-app
        version: blue
    spec:
      containers:
      - name: app
        image: my-app:v1

---
# Green Deployment (New)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-green
spec:
  replicas: 10
  selector:
    matchLabels:
      app: my-app
      version: green
  template:
    metadata:
      labels:
        app: my-app
        version: green
    spec:
      containers:
      - name: app
        image: my-app:v2

---
# Service (Switch traffic by changing selector)
apiVersion: v1
kind: Service
metadata:
  name: my-app
spec:
  selector:
    app: my-app
    version: blue  # Change to 'green' to switch
  ports:
  - port: 80
    targetPort: 8080
```

### Using Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "0"  # 0% to green
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: my-app-green
            port:
              number: 80
```

## 4. A/B Testing with Istio

### Traffic Splitting by Percentage
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app
spec:
  hosts:
  - my-app
  http:
  - route:
    - destination:
        host: my-app
        subset: v1
      weight: 80
    - destination:
        host: my-app
        subset: v2
      weight: 20
```

### Traffic Splitting by Headers
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app
spec:
  hosts:
  - my-app
  http:
  - match:
    - headers:
        user-type:
          exact: beta
    route:
    - destination:
        host: my-app
        subset: v2
  - route:
    - destination:
        host: my-app
        subset: v1
```

### Traffic Splitting by User ID
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app
spec:
  hosts:
  - my-app
  http:
  - match:
    - headers:
        cookie:
          regex: "^(.*?;)?(user_id=[0-9]*[02468])(;.*)?$"  # Even user IDs
    route:
    - destination:
        host: my-app
        subset: v2
  - route:
    - destination:
        host: my-app
        subset: v1
```

## 5. Shadow/Mirroring Deployments

### Test New Version Without Risk
```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app
spec:
  hosts:
  - my-app
  http:
  - route:
    - destination:
        host: my-app
        subset: v1
      weight: 100
    mirror:
      host: my-app
      subset: v2
    mirrorPercentage:
      value: 100.0  # Mirror 100% of traffic to v2
```

Traffic goes to v1, but is duplicated to v2. V2 responses are discarded, allowing risk-free testing.

## 6. Progressive Delivery with Argo Rollouts

### Advanced Canary with Multiple Steps
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: my-app
spec:
  replicas: 10
  strategy:
    canary:
      steps:
      - setWeight: 5
      - pause: {duration: 5m}
      - setWeight: 10
      - pause: {duration: 5m}
      - setWeight: 20
      - pause: {duration: 5m}
      - setWeight: 40
      - pause: {duration: 5m}
      - setWeight: 60
      - pause: {duration: 5m}
      - setWeight: 80
      - pause: {duration: 5m}
      - setWeight: 100
      trafficRouting:
        alb:
          ingress: my-app-ingress
          servicePort: 80
      analysis:
        templates:
        - templateName: success-rate
        startingStep: 2
```

### Analysis Template
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
  - name: success-rate
    interval: 5m
    failureLimit: 3
    provider:
      prometheus:
        address: http://prometheus:9090
        query: |
          sum(rate(http_requests_total{job="my-app",status=~"2.."}[5m])) /
          sum(rate(http_requests_total{job="my-app"}[5m])) * 100
    successCondition: result[0] >= 99.0
```

## 7. Feature Flags Integration

### Decouple Deployment from Release
```python
# In your application code
from feature_flags import get_flag

def process_request(user_id, data):
    if get_flag("new-algorithm", user_id):
        # New version
        return new_algorithm(data)
    else:
        # Old version
        return old_algorithm(data)
```

### Progressive Feature Release
```yaml
# Feature flag configuration
flags:
  new-algorithm:
    enabled: true
    rollout:
      - percentage: 1    # 1% of users
        startDate: 2024-01-01
      - percentage: 5    # 5% of users
        startDate: 2024-01-02
      - percentage: 20   # 20% of users
        startDate: 2024-01-03
      - percentage: 50   # 50% of users
        startDate: 2024-01-04
      - percentage: 100  # All users
        startDate: 2024-01-05
```

## Best Practices

### 1. Define Success Criteria
```yaml
metrics:
- name: error-rate
  max: 1.0  # Less than 1% errors
- name: p99-latency
  max: 500  # Less than 500ms
- name: cpu-usage
  max: 80   # Less than 80% CPU
```

### 2. Start Small
- Begin with 1-5% of traffic
- Monitor for at least 5-10 minutes
- Increase gradually (5% → 10% → 25% → 50% → 100%)

### 3. Automate Rollbacks
```yaml
rollbackWindow:
  revisions: 3  # Keep last 3 versions
  analysisRuns: 1  # Rollback after 1 failed analysis
```

### 4. Use Readiness Gates
```yaml
readinessGates:
- conditionType: "app.example.com/ready"
```

### 5. Monitor Everything
- Application metrics (errors, latency)
- Infrastructure metrics (CPU, memory)
- Business metrics (conversion, revenue)

## Tool Comparison

| Tool | Complexity | Features | Community | Best For |
|------|------------|----------|-----------|----------|
| Kubernetes Rolling | Low | Basic | Built-in | Simple apps |
| Flagger | Medium | Comprehensive | Strong | Most use cases |
| Argo Rollouts | Medium | Advanced | Growing | Complex scenarios |
| Istio | High | Everything | Large | Service mesh users |
| Linkerd | Medium | Focused | Growing | Simplicity |

## Migration from EC2 Blue-Green

### Current State (EC2)
```
┌─────────────┐     ┌─────────────┐
│   Blue EC2  │     │  Green EC2  │
│   (Active)  │     │   (Idle)    │
└─────────────┘     └─────────────┘
       ↑                    
       └──── Route53 A Record
```

### Future State (Kubernetes)
```
┌─────────────────────────────────────┐
│         Kubernetes Cluster          │
│  ┌─────────┐  ┌─────────┐         │
│  │  v1 Pod │  │  v2 Pod │         │
│  │  (90%)  │  │  (10%)  │         │
│  └─────────┘  └─────────┘         │
│         ↑          ↑               │
│         └────┬─────┘               │
│              │                     │
│         Ingress/Service            │
└─────────────────────────────────────┘
```

### Benefits
- **Cost**: 10% extra capacity vs 100%
- **Speed**: Instant rollback vs DNS TTL
- **Control**: Fine-grained vs all-or-nothing
- **Risk**: Gradual validation vs big bang

## Conclusion

Modern Kubernetes deployment strategies offer:
- **Reduced risk** through gradual rollouts
- **Better resource utilization** (10-20% overhead vs 100%)
- **Automated decision making** based on metrics
- **Fine-grained control** over traffic routing
- **Instant rollbacks** without DNS delays

The future of deployments is progressive, automated, and metric-driven rather than manual blue-green switches.