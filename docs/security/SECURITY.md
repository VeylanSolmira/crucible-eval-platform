# Crucible Platform Security Architecture

## Table of Contents
1. [Overview](#overview)
2. [Threat Model](#threat-model)
3. [Container Security](#container-security)
4. [Kubernetes Security](#kubernetes-security)
5. [Infrastructure Security](#infrastructure-security)
6. [Application Security](#application-security)
7. [Build Pipeline Security](#build-pipeline-security)
8. [Deployment Security](#deployment-security)
9. [Monitoring & Incident Response](#monitoring--incident-response)
10. [Compliance & Auditing](#compliance--auditing)

## Overview

The Crucible Platform implements defense-in-depth security architecture designed for safely executing untrusted code. Our security model assumes all submitted code is potentially malicious and implements multiple isolation layers.

### Security Principles
1. **Zero Trust**: Never trust user-submitted code
2. **Least Privilege**: Minimal permissions at every layer
3. **Defense in Depth**: Multiple security boundaries
4. **Fail Secure**: Failures result in denied access, not bypass
5. **Audit Everything**: Comprehensive logging and monitoring

## Threat Model

### Primary Threats
1. **Arbitrary Code Execution**: Users submit code that could:
   - Attempt system compromise
   - Exfiltrate data
   - Consume excessive resources
   - Attack other systems

2. **Container Escape**: Malicious code attempting to:
   - Break out of container isolation
   - Access host system
   - Compromise other containers

3. **Network Attacks**: Code trying to:
   - Scan internal networks
   - Exfiltrate data
   - Launch attacks on external systems

4. **Resource Exhaustion**: 
   - Fork bombs
   - Memory exhaustion
   - CPU spinning
   - Disk filling

### Trust Boundaries
```
Internet → WAF → Load Balancer → API Gateway → Platform → Execution Engine
                                                  │
                                                  ├─→ Docker Container
                                                  └─→ gVisor Sandbox
```

## Container Security

### Docker Runtime Security

#### Security Flags
```bash
docker run \
  --rm                              # Remove after execution
  --network none                    # No network access
  --memory 100m                     # Memory limit
  --memory-swap 100m               # No swap
  --cpus 0.5                       # CPU limit
  --pids-limit 50                  # Process limit
  --read-only                      # Read-only filesystem
  --cap-drop ALL                   # Drop all capabilities
  --security-opt no-new-privileges # No privilege escalation
  --security-opt seccomp=crucible.json  # Custom seccomp profile
  --user 65534:65534               # Run as nobody
  -v /code.py:/code.py:ro         # Mount code read-only
  python:3.11-slim \
  timeout 30 python /code.py       # Execution timeout
```

#### Image Security
- **Base Images**: Only official, minimal images (`python:3.11-slim`)
- **Image Scanning**: Trivy/Snyk scanning in CI/CD
- **No Package Managers**: Remove apt/pip from runtime images
- **Distroless Option**: Consider distroless images for production

### gVisor Security

#### Runtime Configuration
```yaml
# /etc/docker/daemon.json
{
  "runtimes": {
    "runsc": {
      "path": "/usr/local/bin/runsc",
      "runtimeArgs": [
        "--platform=ptrace",
        "--network=none",
        "--debug-log=/var/log/runsc/",
        "--file-access=shared"
      ]
    }
  }
}
```

#### gVisor Benefits
- **Syscall Filtering**: Only ~200 of 400+ syscalls
- **User-space Kernel**: Additional isolation layer
- **Memory Safety**: Written in Go, memory-safe
- **Reduced Attack Surface**: Minimal kernel interaction

## Kubernetes Security

### Pod Security Standards
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65534
    fsGroup: 65534
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: crucible:latest
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
    resources:
      limits:
        memory: "100Mi"
        cpu: "500m"
      requests:
        memory: "50Mi"
        cpu: "100m"
```

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-egress
spec:
  podSelector:
    matchLabels:
      app: executor
  policyTypes:
  - Egress
  egress: []  # No egress allowed
```

### RBAC Configuration
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: executor-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "create", "delete"]
  resourceNames: ["executor-*"]
```

### Admission Controllers
- **Pod Security Admission**: Enforce pod security standards
- **OPA Gatekeeper**: Custom policy enforcement
- **Kyverno**: Policy as code
- **Falco**: Runtime security monitoring

## Infrastructure Security

### AWS Security

#### VPC Architecture
```
┌─────────────────────────────────────────────────────┐
│                   VPC (10.0.0.0/16)                 │
├─────────────────────┬───────────────────────────────┤
│   Public Subnet     │      Private Subnet           │
│   10.0.1.0/24      │      10.0.2.0/24              │
│                     │                                │
│   ┌─────────┐      │      ┌──────────────┐        │
│   │   ALB   │      │      │   EKS Nodes  │        │
│   └────┬────┘      │      └──────────────┘        │
│        │           │                                │
│   ┌────┴────┐      │      ┌──────────────┐        │
│   │   NAT   │◄─────┼──────│   Executors  │        │
│   └─────────┘      │      └──────────────┘        │
└─────────────────────┴───────────────────────────────┘
```

#### IAM Policies
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer"
    ],
    "Resource": "arn:aws:ecr:region:account:repository/crucible/*"
  }]
}
```

#### Security Groups
```hcl
# Executor Security Group
resource "aws_security_group" "executor" {
  name = "crucible-executor"
  
  # No inbound rules - executors don't accept connections
  
  # Minimal outbound - only to S3 for results
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["s3.amazonaws.com"]
  }
}
```

### Secret Management

#### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
type: Opaque
data:
  database-url: <base64-encoded>
  jwt-secret: <base64-encoded>
```

#### AWS Secrets Manager
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']
```

## Application Security

### API Security

#### Authentication & Authorization
```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not validate_jwt(token):
        raise HTTPException(status_code=403, detail="Invalid token")
    return decode_jwt(token)
```

#### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/eval")
@limiter.limit("10/minute")
async def create_evaluation(request: Request):
    # Rate limited to 10 requests per minute per IP
```

#### Input Validation
```python
from pydantic import BaseModel, validator

class EvaluationRequest(BaseModel):
    code: str
    language: str = "python"
    
    @validator('code')
    def validate_code_length(cls, v):
        if len(v) > 100_000:  # 100KB limit
            raise ValueError('Code too large')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        if v not in ['python', 'javascript', 'go']:
            raise ValueError('Unsupported language')
        return v
```

### Code Analysis

#### Static Analysis
```python
import ast

def analyze_code_safety(code: str) -> List[str]:
    """Basic static analysis for obvious malicious patterns"""
    threats = []
    
    # Check for dangerous imports
    dangerous_modules = {'os', 'subprocess', 'socket', '__builtins__'}
    tree = ast.parse(code)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in dangerous_modules:
                    threats.append(f"Dangerous import: {alias.name}")
    
    return threats
```

## Build Pipeline Security

### GitHub Actions Security

#### Workflow Hardening
```yaml
name: Secure Build
on:
  push:
    branches: [main]

permissions:
  contents: read
  id-token: write  # For OIDC

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v4
      with:
        persist-credentials: false
    
    - name: Run security scan
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Build with BuildKit
      env:
        DOCKER_BUILDKIT: 1
      run: |
        docker build \
          --build-arg BUILDKIT_INLINE_CACHE=1 \
          --secret id=github,src=${{ secrets.GITHUB_TOKEN }} \
          -t crucible:${{ github.sha }} .
```

#### Supply Chain Security
- **Dependency Scanning**: Dependabot, Snyk
- **SBOM Generation**: Generate software bill of materials
- **Signed Commits**: Require GPG-signed commits
- **Protected Branches**: Require PR reviews

### Container Registry Security

#### ECR Scanning
```bash
aws ecr put-image-scanning-configuration \
  --repository-name crucible \
  --image-scanning-configuration scanOnPush=true
```

#### Image Signing
```bash
# Sign with Cosign
cosign sign --key cosign.key $ECR_REPO:$TAG

# Verify signature
cosign verify --key cosign.pub $ECR_REPO:$TAG
```

## Deployment Security

### Secure Deployment Pipeline

#### GitOps with ArgoCD
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: crucible
spec:
  source:
    repoURL: https://github.com/org/crucible-k8s
    targetRevision: HEAD
    path: manifests
  destination:
    server: https://kubernetes.default.svc
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=false  # Namespace must exist
    - PruneLast=true        # Delete resources last
```

#### Progressive Rollout
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: crucible
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crucible
  progressDeadlineSeconds: 60
  service:
    port: 8080
  analysis:
    interval: 30s
    threshold: 5
    metrics:
    - name: error-rate
      thresholdRange:
        max: 1  # Max 1% error rate
```

## Monitoring & Incident Response

### Security Monitoring

#### Falco Rules
```yaml
- rule: Unexpected Network Activity
  desc: Detect network activity from executor pods
  condition: >
    container.id != host and
    k8s.pod.label.app = "executor" and
    (fd.type = ipv4 or fd.type = ipv6)
  output: >
    Unexpected network activity from executor
    (pod=%k8s.pod.name fd=%fd.name)
  priority: WARNING
```

#### Prometheus Alerts
```yaml
groups:
- name: security
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High error rate detected"
      
  - alert: ContainerEscapeAttempt
    expr: falco_events{rule="Terminal shell in container"} > 0
    annotations:
      summary: "Possible container escape attempt"
```

### Incident Response Plan

#### Response Levels
1. **Low**: Automated remediation (restart pod)
2. **Medium**: Alert on-call engineer
3. **High**: Page security team, isolate affected systems
4. **Critical**: Full incident response, potential shutdown

#### Runbooks
```markdown
## Container Escape Detection

1. **Isolate**: Cordon affected node
   ```bash
   kubectl cordon node-xyz
   ```

2. **Investigate**: Collect forensics
   ```bash
   kubectl logs pod-name --previous
   docker inspect container-id
   ```

3. **Remediate**: Terminate suspicious pods
   ```bash
   kubectl delete pod suspicious-pod --force
   ```
```

## Compliance & Auditing

### Audit Logging

#### Kubernetes Audit Policy
```yaml
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
- level: RequestResponse
  omitStages:
  - RequestReceived
  resources:
  - group: ""
    resources: ["pods", "pods/exec"]
  namespaces: ["executor"]
```

#### Application Audit Trail
```python
import structlog

logger = structlog.get_logger()

async def audit_evaluation(user_id: str, code: str, result: str):
    await logger.ainfo(
        "evaluation_executed",
        user_id=user_id,
        code_hash=hashlib.sha256(code.encode()).hexdigest(),
        result=result,
        timestamp=datetime.utcnow().isoformat()
    )
```

### Compliance Standards

#### SOC 2 Controls
- **Access Control**: RBAC, MFA, audit logs
- **Encryption**: TLS in transit, encrypted at rest
- **Monitoring**: 24/7 monitoring, incident response
- **Change Management**: GitOps, PR reviews

#### GDPR Considerations
- **Data Minimization**: Don't store user code long-term
- **Right to Erasure**: Automated data deletion
- **Data Portability**: Export user data on request
- **Privacy by Design**: Minimal PII collection

## Security Checklist

### Pre-Deployment
- [ ] All images scanned for vulnerabilities
- [ ] Secrets rotated and stored securely
- [ ] Network policies configured
- [ ] RBAC permissions reviewed
- [ ] Security monitoring enabled

### Runtime
- [ ] No privileged containers
- [ ] All capabilities dropped
- [ ] Network isolation verified
- [ ] Resource limits enforced
- [ ] Audit logging enabled

### Post-Deployment
- [ ] Security scan results reviewed
- [ ] Penetration test scheduled
- [ ] Incident response team notified
- [ ] Runbooks updated
- [ ] Compliance documentation current

## References

- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Cloud Native Security Whitepaper](https://www.cncf.io/blog/2020/11/18/cloud-native-security-whitepaper/)
- [gVisor Security Model](https://gvisor.dev/docs/architecture_guide/security/)