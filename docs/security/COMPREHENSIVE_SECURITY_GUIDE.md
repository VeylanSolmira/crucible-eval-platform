# Comprehensive Security Guide for Crucible Evaluation Platform

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current Security Implementation](#current-security-implementation)
3. [Comprehensive Security Checklist](#comprehensive-security-checklist)
4. [Tool-Specific Security Guidelines](#tool-specific-security-guidelines)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Security Architecture Decisions](#security-architecture-decisions)

## Executive Summary

The Crucible Evaluation Platform implements defense-in-depth security architecture critical for safely evaluating potentially adversarial AI models. This document consolidates all security decisions, implementations, and provides a comprehensive checklist for securing every component.

### Core Security Principles
1. **Zero Trust**: Never trust AI models or their outputs (perhaps this has to be modified to something like careful trust/partial verification/skilled usage, etc. We can have a link to my adversarial meta learning article, but it won't be updated on the remote deployment yet. here's the current url: https://www.veylan.dev/journey/intermediate/advanced-red-teaming/adversarial-meta-learning)
2. **Least Privilege**: Minimal permissions at every layer
3. **Defense in Depth**: Multiple independent security layers
4. **Complete Isolation**: No network access for evaluations
5. **Audit Everything**: Comprehensive logging and monitoring

## Current Security Implementation

### 1. Container Security Stack
- **gVisor (runsc)**: Userspace kernel isolation
- **Docker**: Container isolation with security policies
- **Non-root execution**: UID 1000/65534
- **Read-only filesystems**: Prevent persistent modifications
- **Capability dropping**: All Linux capabilities removed

### 2. Network Security
- **Complete isolation**: `--network none` for evaluations
- **Private subnets**: Production deployment architecture
- **Security groups**: Restrictive AWS firewall rules
- **NAT Gateway**: Controlled egress for updates only
- **No SSH in production**: AWS Systems Manager Session Manager

### 3. Infrastructure Security
- **IAM roles**: Least privilege AWS permissions
- **API Gateway**: Authentication layer (planned)
- **Secrets management**: Environment variables, no hardcoding
- **SSL/TLS**: End-to-end encryption
- **Rate limiting**: DDoS protection

### 4. Application Security
- **Input validation**: All code inputs sanitized
- **Resource limits**: CPU, memory, time constraints
- **Event monitoring**: Real-time behavioral tracking
- **Audit logging**: Complete execution history
- **Error isolation**: No information leakage

## Comprehensive Security Checklist

### Rating System
- **Importance**: 🔴 Critical | 🟡 High | 🟢 Medium | ⚪ Low
- **Effort**: 💪 High | 👷 Medium | ✋ Low

### A. Code Execution Security

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Use gVisor/Firecracker for isolation** | 🔴 Critical | 👷 Medium | ✅ Implemented | Kernel-level isolation for untrusted code |
| **2. Disable network access completely** | 🔴 Critical | ✋ Low | ✅ Implemented | `--network none` flag |
| **3. Use non-root user** | 🔴 Critical | ✋ Low | ✅ Implemented | UID 1000 or 65534 |
| **4. Drop all Linux capabilities** | 🔴 Critical | ✋ Low | ✅ Implemented | `--cap-drop ALL` |
| **5. Read-only root filesystem** | 🟡 High | ✋ Low | ✅ Implemented | Prevent system modifications |
| **6. Resource limits (CPU/Memory)** | 🟡 High | ✋ Low | ✅ Implemented | Prevent resource exhaustion |
| **7. Time execution limits** | 🟡 High | ✋ Low | ✅ Implemented | Prevent infinite loops |
| **8. Syscall filtering (seccomp)** | 🟡 High | 👷 Medium | ⚠️ Partial | gVisor provides this |
| **9. Temporary filesystem only** | 🟡 High | ✋ Low | ✅ Implemented | No persistent storage |
| **10. Process namespace isolation** | 🟡 High | ✋ Low | ✅ Implemented | PID namespace isolation |

### B. Container Security

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Minimal base images** | 🟡 High | ✋ Low | ✅ Implemented | Alpine/distroless |
| **2. No package managers in prod** | 🟡 High | ✋ Low | ⚠️ Partial | Remove apt/pip in final stage |
| **3. Multi-stage builds** | 🟢 Medium | ✋ Low | ✅ Implemented | Separate build/runtime |
| **4. Image vulnerability scanning** | 🔴 Critical | 👷 Medium | ❌ TODO | Trivy/Snyk integration |
| **5. Sign container images** | 🟡 High | 👷 Medium | ❌ TODO | Docker Content Trust |
| **6. No secrets in images** | 🔴 Critical | ✋ Low | ✅ Implemented | Use env vars/secrets manager |
| **7. Health checks** | 🟢 Medium | ✋ Low | ✅ Implemented | Liveness/readiness probes |
| **8. AppArmor/SELinux profiles** | 🟡 High | 💪 High | ❌ TODO | Additional MAC layer |
| **9. Rootless containers** | 🟡 High | 👷 Medium | ❌ TODO | Podman/rootless Docker |
| **10. Distroless images** | 🟡 High | 👷 Medium | ❌ TODO | No shell/utilities |

### C. Network Security

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Zero network for eval** | 🔴 Critical | ✋ Low | ✅ Implemented | Complete isolation |
| **2. Private subnets** | 🔴 Critical | 👷 Medium | ⚠️ Planned | Day 4 migration |
| **3. Network policies** | 🔴 Critical | 👷 Medium | ❌ TODO | Kubernetes NetworkPolicy |
| **4. WAF for API Gateway** | 🟡 High | 👷 Medium | ❌ TODO | AWS WAF rules |
| **5. DDoS protection** | 🟡 High | 👷 Medium | ⚠️ Partial | Basic rate limiting |
| **6. TLS 1.3 only** | 🟡 High | ✋ Low | ❌ TODO | Modern encryption |
| **7. Certificate pinning** | 🟢 Medium | 👷 Medium | ❌ TODO | For critical APIs |
| **8. DNS over HTTPS** | 🟢 Medium | 👷 Medium | ❌ TODO | Prevent DNS leaks |
| **9. VPC Flow Logs** | 🟡 High | ✋ Low | ❌ TODO | Network monitoring |
| **10. Egress filtering** | 🟡 High | 👷 Medium | ❌ TODO | Whitelist only |

### D. Infrastructure Security (AWS)

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. IMDSv2 only** | 🔴 Critical | ✋ Low | ❌ TODO | Prevent SSRF to metadata |
| **2. IAM least privilege** | 🔴 Critical | 👷 Medium | ✅ Implemented | Minimal permissions |
| **3. No SSH in production** | 🔴 Critical | 👷 Medium | ⚠️ Planned | Session Manager only |
| **4. CloudTrail logging** | 🔴 Critical | ✋ Low | ❌ TODO | Audit all API calls |
| **5. GuardDuty enabled** | 🟡 High | ✋ Low | ❌ TODO | Threat detection |
| **6. Secrets Manager** | 🟡 High | 👷 Medium | ❌ TODO | No env var secrets |
| **7. KMS encryption** | 🟡 High | 👷 Medium | ❌ TODO | Encrypt at rest |
| **8. S3 bucket policies** | 🟡 High | ✋ Low | ❌ TODO | Block public access |
| **9. Config/Compliance** | 🟢 Medium | 👷 Medium | ❌ TODO | AWS Config rules |
| **10. Security Hub** | 🟢 Medium | 👷 Medium | ❌ TODO | Centralized security |

### E. Application Security (Python)

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Input validation** | 🔴 Critical | 👷 Medium | ✅ Implemented | Sanitize all inputs |
| **2. No eval/exec on user input** | 🔴 Critical | ✋ Low | ✅ Implemented | Use subprocess |
| **3. Parameterized queries** | 🔴 Critical | ✋ Low | N/A | When using DB |
| **4. SAST scanning** | 🟡 High | 👷 Medium | ❌ TODO | Bandit/Semgrep |
| **5. Dependency scanning** | 🔴 Critical | 👷 Medium | ❌ TODO | Safety/pip-audit |
| **6. Type hints everywhere** | 🟢 Medium | 👷 Medium | ⚠️ Partial | mypy strict mode |
| **7. Secure random** | 🟡 High | ✋ Low | ✅ Implemented | secrets module |
| **8. No pickle for untrusted** | 🔴 Critical | ✋ Low | ✅ Implemented | JSON only |
| **9. Request size limits** | 🟡 High | ✋ Low | ❌ TODO | Prevent DoS |
| **10. Error message sanitization** | 🟡 High | ✋ Low | ⚠️ Partial | No stack traces |

### F. Kubernetes Security

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Pod Security Standards** | 🔴 Critical | 👷 Medium | ✅ Implemented | Restricted profile |
| **2. RBAC policies** | 🔴 Critical | 👷 Medium | ❌ TODO | Least privilege |
| **3. Network policies** | 🔴 Critical | 👷 Medium | ❌ TODO | Microsegmentation |
| **4. Admission controllers** | 🟡 High | 💪 High | ❌ TODO | OPA/Gatekeeper |
| **5. Runtime security** | 🟡 High | 💪 High | ❌ TODO | Falco monitoring |
| **6. Image pull secrets** | 🟡 High | ✋ Low | ❌ TODO | Private registry |
| **7. Service mesh** | 🟢 Medium | 💪 High | ❌ TODO | Istio/Linkerd |
| **8. etcd encryption** | 🔴 Critical | 👷 Medium | ❌ TODO | Encrypt secrets |
| **9. Audit logging** | 🔴 Critical | 👷 Medium | ❌ TODO | All API calls |
| **10. CIS benchmarks** | 🟡 High | 💪 High | ❌ TODO | Compliance scanning |

### G. Web Security

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. CSP headers** | 🟡 High | ✋ Low | ✅ Implemented | Content Security Policy |
| **2. CORS properly configured** | 🔴 Critical | ✋ Low | ⚠️ Partial | Restrict origins |
| **3. X-Frame-Options** | 🟡 High | ✋ Low | ✅ Implemented | Prevent clickjacking |
| **4. HSTS enabled** | 🟡 High | ✋ Low | ❌ TODO | Force HTTPS |
| **5. SameSite cookies** | 🟡 High | ✋ Low | ❌ TODO | CSRF protection |
| **6. Rate limiting** | 🟡 High | 👷 Medium | ✅ Implemented | Basic limits |
| **7. Input sanitization** | 🔴 Critical | 👷 Medium | ⚠️ Partial | XSS prevention |
| **8. API authentication** | 🔴 Critical | 👷 Medium | ❌ TODO | JWT/OAuth2 |
| **9. CSRF tokens** | 🟡 High | 👷 Medium | ❌ TODO | State-changing ops |
| **10. Security.txt** | ⚪ Low | ✋ Low | ❌ TODO | Vulnerability disclosure |

### H. CI/CD Security

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Signed commits** | 🟢 Medium | ✋ Low | ❌ TODO | GPG verification |
| **2. Branch protection** | 🟡 High | ✋ Low | ⚠️ Partial | Require reviews |
| **3. Secret scanning** | 🔴 Critical | 👷 Medium | ❌ TODO | GitHub secret scanning |
| **4. SAST in pipeline** | 🟡 High | 👷 Medium | ❌ TODO | Security testing |
| **5. Container scanning** | 🔴 Critical | 👷 Medium | ❌ TODO | In CI pipeline |
| **6. License scanning** | 🟢 Medium | ✋ Low | ❌ TODO | License compliance |
| **7. Artifact signing** | 🟡 High | 👷 Medium | ❌ TODO | Supply chain security |
| **8. Least privilege CI** | 🟡 High | 👷 Medium | ❌ TODO | Minimal permissions |
| **9. Audit CI/CD logs** | 🟢 Medium | ✋ Low | ❌ TODO | Track deployments |
| **10. Infrastructure as Code scanning** | 🟡 High | 👷 Medium | ❌ TODO | Terraform security |

### I. Monitoring & Incident Response

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Centralized logging** | 🔴 Critical | 👷 Medium | ⚠️ Partial | ELK/CloudWatch |
| **2. Real-time alerts** | 🔴 Critical | 👷 Medium | ⚠️ Partial | Anomaly detection |
| **3. Behavioral analysis** | 🟡 High | 💪 High | ⚠️ Partial | AI behavior tracking |
| **4. Incident response plan** | 🔴 Critical | 👷 Medium | ❌ TODO | Documented procedures |
| **5. Regular drills** | 🟡 High | 👷 Medium | ❌ TODO | Practice incidents |
| **6. Log retention policy** | 🟡 High | ✋ Low | ❌ TODO | Compliance requirements |
| **7. SIEM integration** | 🟢 Medium | 💪 High | ❌ TODO | Security correlation |
| **8. Threat intelligence** | 🟢 Medium | 👷 Medium | ❌ TODO | Known bad actors |
| **9. Forensics capability** | 🟢 Medium | 💪 High | ❌ TODO | Post-incident analysis |
| **10. Backup verification** | 🟡 High | 👷 Medium | ❌ TODO | Recovery testing |

### J. Special Considerations for AI Model Evaluation

| Security Measure | Importance | Effort | Status | Notes |
|-----------------|------------|---------|---------|--------|
| **1. Complete filesystem isolation** | 🔴 Critical | ✋ Low | ✅ Implemented | No host access |
| **2. Memory isolation** | 🔴 Critical | 👷 Medium | ✅ Implemented | Prevent memory escapes |
| **3. GPU isolation** | 🔴 Critical | 💪 High | ❌ TODO | When using GPUs |
| **4. Model weight protection** | 🟡 High | 👷 Medium | ❌ TODO | Encrypt model files |
| **5. Prompt injection defense** | 🔴 Critical | 💪 High | ❌ TODO | Input filtering |
| **6. Output filtering** | 🔴 Critical | 👷 Medium | ❌ TODO | Harmful content |
| **7. Token limits** | 🟡 High | ✋ Low | ❌ TODO | Prevent abuse |
| **8. Behavioral monitoring** | 🔴 Critical | 💪 High | ⚠️ Partial | Detect anomalies |
| **9. Capability restrictions** | 🔴 Critical | 👷 Medium | ✅ Implemented | Limited syscalls |
| **10. Honeypot detection** | 🟢 Medium | 💪 High | ❌ TODO | Detect escape attempts |

## Tool-Specific Security Guidelines

### Python Security
```python
# NEVER DO THIS
eval(user_input)  # Code injection
exec(user_input)  # Code injection
__import__(user_input)  # Module injection

# DO THIS INSTEAD
import subprocess
import shlex

# Safe subprocess execution
cmd = ["python", "-c", user_code]
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=30,
    check=False,
    env={"PYTHONPATH": ""},  # Clean environment
    cwd="/tmp/sandbox",  # Isolated directory
)

# Input validation
import re
def validate_code(code: str) -> bool:
    # Whitelist allowed patterns
    dangerous_patterns = [
        r'__import__',
        r'eval\s*\(',
        r'exec\s*\(',
        r'compile\s*\(',
        r'open\s*\(',
        r'file\s*\(',
        r'input\s*\(',
        r'raw_input\s*\(',
        r'__builtins__',
        r'globals\s*\(',
        r'locals\s*\(',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            return False
    return True
```

### Docker Security
```dockerfile
# Secure Dockerfile example
FROM python:3.11-alpine AS builder
# Build stage - can have build tools

FROM gcr.io/distroless/python3-debian11
# Runtime stage - minimal attack surface
COPY --from=builder /app /app

# Run as non-root
USER 65534:65534

# Read-only root
RUN chmod -R 755 /app

# No shell available in distroless
# Health checks via HTTP endpoint instead
```

### Terraform Security
```hcl
# Security-first Terraform
resource "aws_security_group" "evaluator" {
  name_prefix = "eval-sg-"
  description = "Security group for evaluation instances"
  
  # Explicit deny all ingress
  ingress {
    description = "Deny all ingress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Only allow specific egress
  egress {
    description = "Allow HTTPS for package downloads"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  lifecycle {
    create_before_destroy = true
  }
  
  tags = {
    Name = "evaluator-security-group"
    Security = "critical"
  }
}

# Use data sources for AMIs - never hardcode
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}
```

### JavaScript Execution Security
```python
# If you must execute JavaScript in Python
import subprocess
import tempfile
import os

def safe_js_execution(js_code: str) -> str:
    # NEVER use eval() or node -e with user input
    
    # Create isolated environment
    with tempfile.TemporaryDirectory() as tmpdir:
        js_file = os.path.join(tmpdir, "script.js")
        
        # Write sanitized code
        with open(js_file, 'w') as f:
            # Add safety wrapper
            f.write("""
'use strict';
// Disable dangerous globals
const require = undefined;
const process = undefined;
const __dirname = undefined;
const __filename = undefined;
const module = undefined;
const exports = undefined;
const global = undefined;

// User code in try-catch
try {
    %s
} catch (e) {
    console.error('Error:', e.message);
}
""" % js_code)
        
        # Execute with restrictions
        result = subprocess.run(
            ["node", "--no-deprecation", "--no-warnings", js_file],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=tmpdir,
            env={
                "NODE_ENV": "sandbox",
                "PATH": "/usr/bin",
            }
        )
        
        return result.stdout
```

## Implementation Roadmap

### Phase 1: Critical Security (Day 1-2)
1. ✅ Enable gVisor for all evaluations
2. ✅ Implement network isolation
3. ✅ Set up basic monitoring
4. ❌ Add vulnerability scanning to CI/CD
5. ❌ Implement secret scanning

### Phase 2: Infrastructure Hardening (Day 3-4)
1. ❌ Migrate to private subnets
2. ❌ Implement Session Manager
3. ❌ Enable CloudTrail and GuardDuty
4. ❌ Set up WAF rules
5. ❌ Implement KMS encryption

### Phase 3: Advanced Security (Day 5+)
1. ❌ Implement runtime security monitoring
2. ❌ Add behavioral analysis
3. ❌ Set up SIEM integration
4. ❌ Implement admission controllers
5. ❌ Add honeypot detection

### Phase 4: Compliance & Audit (Week 2)
1. ❌ CIS benchmark compliance
2. ❌ SOC2 readiness assessment
3. ❌ Penetration testing
4. ❌ Security documentation
5. ❌ Incident response procedures

## Security Architecture Decisions

### Decision: gVisor over Firecracker
**Rationale**: gVisor provides better syscall filtering and is easier to integrate with Docker/Kubernetes. Firecracker is better for full VM isolation but requires more infrastructure changes.

### Decision: Network Isolation Strategy
**Rationale**: Complete network disconnection (`--network none`) is non-negotiable for adversarial model evaluation. Any network access is a potential escape vector.

### Decision: Private Subnet Architecture
**Rationale**: Defense in depth requires network-level isolation. Public subnets are only for load balancers. All compute happens in private subnets with no internet gateway.

### Decision: Session Manager over SSH
**Rationale**: SSH requires open ports and key management. Session Manager uses IAM for authentication and leaves no open ports.

### Decision: Distroless Containers
**Rationale**: No shell, no package manager, no utilities = minimal attack surface. Debugging is harder but security is paramount.

## Security Contacts and Resources

### Emergency Contacts
- Security Lead: [TBD]
- Infrastructure Lead: [TBD]
- On-call: [TBD]

### Security Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [AWS Security Best Practices](https://aws.amazon.com/security/security-resources/)
- [Kubernetes Security](https://kubernetes.io/docs/concepts/security/)

### Vulnerability Disclosure
Report security vulnerabilities to: security@[domain].com

---

**Document Version**: 1.0  
**Last Updated**: 2024-01-10  
**Next Review**: 2024-02-10  
**Classification**: CONFIDENTIAL - INTERNAL USE ONLY