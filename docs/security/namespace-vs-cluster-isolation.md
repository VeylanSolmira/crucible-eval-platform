# Namespace vs Cluster Isolation: Security Considerations

## Executive Summary

For **high-security projects**, the industry best practice is **separate clusters** for production, especially in regulated industries (finance, healthcare, government). However, modern Kubernetes provides strong namespace isolation that's sufficient for many use cases.

## Current Industry Standards

### Separate Clusters Required
- **Financial Services**: PCI-DSS often interpreted as requiring separate clusters
- **Healthcare**: HIPAA compliance typically uses cluster separation
- **Government**: FedRAMP, NIST mandate physical isolation
- **Cryptocurrency**: Always separate clusters (hot/cold wallet separation)

### Namespace Isolation Acceptable
- **SaaS B2B**: Most use namespaces for customer isolation
- **Internal Tools**: Dev/staging/prod in same cluster common
- **Startups**: Resource constraints make namespaces attractive
- **Non-regulated**: E-commerce, social media, content platforms

## Security Comparison

### Namespace Isolation (Virtual)

#### Provides
- **RBAC**: Role-based access control per namespace
- **Network Policies**: Traffic isolation between namespaces
- **Resource Quotas**: Prevent resource exhaustion
- **Pod Security Standards**: Enforce security policies
- **Admission Controllers**: Validate/mutate resources

#### Vulnerabilities
- **Container Escape**: Could access other namespaces
- **Kernel Exploits**: Shared kernel = shared vulnerability
- **Sidecar Attacks**: Service mesh vulnerabilities
- **Misconfiguration**: One mistake can expose everything
- **Compliance**: May not meet regulatory requirements

### Cluster Isolation (Physical)

#### Provides
- **Complete Isolation**: No shared kernel, network, or storage
- **Blast Radius**: Compromise limited to one environment
- **Compliance**: Meets most regulatory requirements
- **Independent Upgrades**: Patch dev without touching prod
- **Network Segregation**: Different VPCs, security groups

#### Costs
- **Infrastructure**: 3x the nodes, control planes, load balancers
- **Operational**: More to monitor, patch, upgrade
- **Complexity**: Cross-cluster communication harder
- **Time**: Slower to promote between environments

## Real-World Architectures

### 1. Netflix/Spotify Model (Namespace Isolation)
```
Single Large Cluster
├── dev-* namespaces
├── staging-* namespaces  
└── prod-* namespaces

Why: Non-regulated, engineering efficiency prioritized
```

### 2. Financial Services Model (Cluster Isolation)
```
Dev Cluster (AWS Account A)
├── All dev namespaces

Staging Cluster (AWS Account B)
├── All staging namespaces

Production Cluster (AWS Account C)
├── All prod namespaces
├── Separate VPC
├── No network connectivity to dev/staging

Why: Regulatory compliance, audit requirements
```

### 3. Hybrid Model (Best of Both)
```
Non-Prod Cluster
├── dev namespace
├── staging namespace
└── test namespaces

Production Cluster (Separate)
└── production namespace only

Why: Cost optimization + production security
```

## Modern Kubernetes Security Features

### Strong Isolation Mechanisms

1. **Pod Security Standards (PSS)**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

2. **Runtime Security (gVisor/Kata)**
```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
---
spec:
  runtimeClassName: gvisor  # Sandboxed container runtime
```

3. **Network Policies**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-cross-namespace
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector: {}  # Only within namespace
  egress:
  - to:
    - podSelector: {}  # Only within namespace
```

4. **mTLS with Service Mesh**
```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT  # All traffic encrypted
```

## Security Decision Framework

### Use Separate Clusters When:

1. **Regulatory Requirements**
   - PCI-DSS Level 1
   - HIPAA with PHI
   - Government classified data
   - Financial transactions

2. **High Value Targets**
   - Cryptocurrency wallets
   - Payment processing
   - PII at scale
   - Trade secrets

3. **Zero Trust Requirements**
   - Air-gapped environments
   - Nation-state threat model
   - Insider threat concerns

### Namespaces Are Sufficient When:

1. **Internal Applications**
   - Developer tools
   - Non-sensitive data
   - Proof of concepts

2. **Modern Security Stack**
   - Using gVisor/Firecracker
   - Service mesh with mTLS
   - Runtime security (Falco)
   - Admission control (OPA)

3. **Cost Constraints**
   - Startups
   - Non-critical workloads
   - Development environments

## Hardening Namespace Isolation

If using namespaces, implement these controls:

### 1. Admission Controllers
```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: security-policies
webhooks:
- name: validate.security.company.com
  rules:
  - operations: ["CREATE", "UPDATE"]
    apiGroups: ["*"]
    apiVersions: ["*"]
    resources: ["pods", "services"]
```

### 2. Resource Quotas
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    persistentvolumeclaims: "10"
```

### 3. RBAC Lockdown
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: developer
rules:
- apiGroups: [""]
  resources: ["pods", "services"]
  verbs: ["get", "list"]  # Read-only
```

### 4. Audit Everything
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  namespaces: ["production"]
  verbs: ["create", "update", "delete"]
```

## Cost Analysis

### Namespace Isolation
```
1 EKS Cluster
- Control Plane: $73/month
- 3x m5.xlarge nodes: $400/month
- 1 Load Balancer: $25/month
Total: ~$500/month
```

### Cluster Isolation
```
3 EKS Clusters
- Control Planes: $219/month
- 9x m5.xlarge nodes: $1,200/month
- 3 Load Balancers: $75/month
Total: ~$1,500/month
```

## Recommendations

### For METR/AI Safety Platform

Given the nature of AI safety evaluation:

1. **Start with Hybrid Model**
   - Dev + Staging in one cluster (namespaces)
   - Production in separate cluster
   - Cost: ~$1,000/month

2. **If Handling Sensitive Models**
   - Separate clusters for each environment
   - Different AWS accounts
   - Network isolation via Transit Gateway

3. **Security Hardening**
   - Implement gVisor for sandboxing
   - Use Falco for runtime detection
   - Enable audit logging
   - Regular penetration testing

### Implementation Priority

1. **Phase 1**: Namespace isolation with full security stack
2. **Phase 2**: Move production to separate cluster  
3. **Phase 3**: Full cluster isolation if required by compliance

## The Bottom Line

**Kubernetes namespaces are NOT a security boundary** according to the Kubernetes security model. However, with proper hardening, they provide reasonable isolation for many use cases. For high-security requirements, separate clusters remain the gold standard.

The trend is toward better namespace isolation (see Google's GKE Autopilot), but we're not there yet for the highest security requirements.