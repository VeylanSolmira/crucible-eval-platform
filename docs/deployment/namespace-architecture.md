# Namespace Architecture & Routing

## Overview

Each namespace is a complete, isolated copy of your application within the same Kubernetes cluster. This provides environment isolation while sharing infrastructure.

## Namespace Structure

```
crucible-platform (EKS Cluster)
│
├── dev (namespace)
│   ├── All services deployed
│   ├── Minimal resources
│   ├── Fast iteration
│   └── URL: dev.crucible-platform.com
│
├── staging (namespace)
│   ├── All services deployed
│   ├── Production-like resources
│   ├── Full test suite runs here
│   └── URL: staging.crucible-platform.com
│
└── production (namespace)
    ├── All services deployed
    ├── Full resources with HPA
    ├── High availability
    └── URL: crucible-platform.com
```

## How Routing Works

### 1. Single Load Balancer, Multiple Ingresses

```yaml
# k8s/overlays/dev/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crucible-ingress
  namespace: dev
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - dev.crucible-platform.com
    secretName: dev-tls-cert
  rules:
  - host: dev.crucible-platform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
---
# k8s/overlays/production/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crucible-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - crucible-platform.com
    - www.crucible-platform.com
    secretName: prod-tls-cert
  rules:
  - host: crucible-platform.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 8080
```

### 2. DNS Configuration

```
# Route53 or your DNS provider
crucible-platform.com         → A    → Load Balancer IP
*.crucible-platform.com       → CNAME → Load Balancer DNS
dev.crucible-platform.com     → CNAME → Load Balancer DNS
staging.crucible-platform.com → CNAME → Load Balancer DNS
```

### 3. How Requests Flow

```
User requests crucible-platform.com
           ↓
    Route53/DNS
           ↓
AWS Application Load Balancer
           ↓
    NGINX Ingress Controller
           ↓
Checks hostname and routes to correct namespace
           ↓
    production/frontend service
```

## Resource Isolation

### 1. ResourceQuotas per Namespace

```yaml
# k8s/overlays/dev/resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: dev-quota
  namespace: dev
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
---
# k8s/overlays/production/resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: prod-quota
  namespace: production
spec:
  hard:
    requests.cpu: "20"
    requests.memory: "40Gi"
    limits.cpu: "40"
    limits.memory: "80Gi"
```

### 2. Network Isolation

```yaml
# k8s/overlays/production/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: production-isolation
  namespace: production
spec:
  podSelector: {}  # Apply to all pods
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: production  # Only allow traffic within production
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx  # Allow ingress controller
  egress:
  - to:
    - namespaceSelector: {}  # Allow all egress (customize as needed)
```

## Database Considerations

### Option 1: Separate Databases per Namespace
```yaml
# Each namespace has its own database
dev:       postgres-dev.cluster.local
staging:   postgres-staging.cluster.local  
production: postgres-prod.cluster.local
```

### Option 2: Shared Database, Different Schemas
```yaml
# Single RDS instance, multiple schemas
DATABASE_URL: postgresql://user:pass@rds.amazon.com/crucible_dev
DATABASE_URL: postgresql://user:pass@rds.amazon.com/crucible_staging
DATABASE_URL: postgresql://user:pass@rds.amazon.com/crucible_production
```

### Option 3: Separate RDS Instances
```yaml
# Most isolated, most expensive
dev:        dev-db.xyz.rds.amazonaws.com
staging:    staging-db.xyz.rds.amazonaws.com
production: prod-db.xyz.rds.amazonaws.com
```

## Cost Optimization

### Shared Resources
- **Ingress Controller**: One for entire cluster
- **Cert-Manager**: One for entire cluster
- **Monitoring Stack**: Shared Prometheus/Grafana
- **Log Aggregation**: Shared ELK/CloudWatch

### Per-Namespace Resources
- **Pods**: Each namespace has its own
- **Services**: Isolated per namespace
- **ConfigMaps/Secrets**: Namespace-scoped
- **PVCs**: Separate storage per environment

## Example Deployment Commands

```bash
# Deploy to dev
kubectl apply -k k8s/overlays/dev -n dev

# Deploy to staging
kubectl apply -k k8s/overlays/staging -n staging

# Deploy to production (with approval)
kubectl apply -k k8s/overlays/production -n production

# Check what's different between environments
diff -r k8s/overlays/dev k8s/overlays/production
```

## Accessing Different Environments

### For Developers
```bash
# Quick access to dev
kubectl config set-context --current --namespace=dev
kubectl get pods  # Shows only dev pods

# Port forward to local for testing
kubectl port-forward svc/api-service 8080:8080 -n dev
```

### For Users
- Dev: https://dev.crucible-platform.com
- Staging: https://staging.crucible-platform.com
- Production: https://crucible-platform.com

## Security Benefits

1. **RBAC per Namespace**
   ```yaml
   # Developers get full access to dev, read-only to prod
   kind: RoleBinding
   metadata:
     name: dev-team
     namespace: dev
   roleRef:
     kind: Role
     name: developer
   subjects:
   - kind: Group
     name: developers
   ```

2. **Separate Secrets**
   ```bash
   # Different API keys per environment
   kubectl create secret generic api-keys -n dev --from-literal=key=dev-key
   kubectl create secret generic api-keys -n production --from-literal=key=prod-key
   ```

3. **Audit Trails**
   - Each namespace has separate audit logs
   - Can track who deployed what to which environment

## Monitoring Across Namespaces

```yaml
# Grafana dashboard shows all namespaces
- query: sum(rate(http_requests_total[5m])) by (namespace)
  legend: "Requests per namespace"

# Alerts can be namespace-specific
- alert: HighErrorRate
  expr: rate(http_errors_total{namespace="production"}[5m]) > 0.05
  annotations:
    summary: "High error rate in production"
```

## Practical Example

When you push code:

1. **Feature Branch** → Deploys to `dev` namespace
   - URL: https://dev.crucible-platform.com
   - Resources: Minimal
   - Data: Test data
   
2. **Main Branch** → Deploys to `staging` namespace
   - URL: https://staging.crucible-platform.com
   - Resources: Production-like
   - Data: Anonymized prod data
   
3. **Tagged Release** → Deploys to `production` namespace
   - URL: https://crucible-platform.com
   - Resources: Full with autoscaling
   - Data: Real production data

All in the same cluster, but completely isolated!