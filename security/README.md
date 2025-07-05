# Security Architecture

Security is a first-class concern for the METR evaluation platform. This directory contains all security-related tools, policies, and assessments.

## Directory Structure

```
security/
├── assessments/      # Runtime security assessment tools
├── policies/         # Security policies and configurations
├── scanners/         # Code and container scanning tools
├── auditing/         # Security audit logs and analysis tools
└── README.md         # This file
```

## Components

### Assessments
Runtime tools that evaluate the security posture of containers and environments:
- `container_check.py` - Performs safe, read-only security checks on container environments

### Policies
Security policies and configurations that define our security stance:
- Container hardening specifications
- Network isolation rules
- Resource limit policies
- Access control definitions

### Scanners
Tools for scanning code, containers, and dependencies for vulnerabilities:
- Static code analysis
- Container image scanning
- Dependency vulnerability checks

### Auditing
Security event logging and analysis:
- Access logs
- Security event correlation
- Compliance reporting

## Security Principles

1. **Defense in Depth** - Multiple layers of security controls
2. **Least Privilege** - Minimal permissions for all components
3. **Zero Trust** - Verify everything, trust nothing
4. **Isolation First** - Strong boundaries between untrusted code and the platform
5. **Audit Everything** - Comprehensive logging for security events

## Usage

### Running Security Assessments
```bash
# Check container security posture
python security/assessments/container_check.py

# Run from inside a container to verify isolation
docker run -v $(pwd)/security:/security python /security/assessments/container_check.py
```

### Applying Security Policies
Security policies are automatically applied during:
- Container creation (Docker security options)
- Network configuration (iptables/network policies)
- Resource allocation (cgroups limits)

## Security Considerations for AI Evaluation

The platform must handle potentially malicious AI-generated code:

1. **Container Escape Prevention** - Using gVisor or similar for kernel isolation
2. **Network Exfiltration Prevention** - Strict egress controls
3. **Resource Exhaustion Protection** - CPU, memory, and I/O limits
4. **Filesystem Isolation** - Read-only root filesystems
5. **Process Isolation** - PID namespace separation

## Integration with Platform Components

- **Executor Service** - Applies security policies when creating containers
- **API Gateway** - Validates and sanitizes all inputs
- **Storage Service** - Encrypts sensitive data
- **Monitoring** - Tracks security metrics and anomalies

## Security Incident Response

If a security issue is detected:
1. Automated containment (kill container, block network)
2. Alert generation to security team
3. Forensic data collection
4. Post-incident analysis

## Contributing

When adding security features:
1. Document the threat model
2. Explain the mitigation strategy
3. Add tests for security controls
4. Update this README

Remember: Security is everyone's responsibility.