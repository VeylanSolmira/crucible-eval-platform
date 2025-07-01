---
title: Docker Security
description: Security features and best practices for Docker containers
tags: [docker, security, containers]
---

# Docker Security

Docker provides multiple security features that we use in [[Container Isolation]] for AI evaluation.

## Security Features

### User Namespaces
Maps container users to non-root host users. Essential for [[gVisor Setup]].

### Capabilities
Linux capabilities can be dropped to reduce attack surface. We drop ALL capabilities in our [[Threat Model]].

### Seccomp Profiles
Restricts system calls available to containers. Works with [[Kubernetes Security]] policies.

## Best Practices

1. **Never run as root** - Always use `USER` directive
2. **Drop capabilities** - Use `--cap-drop ALL`
3. **Read-only filesystem** - Prevent persistence attacks
4. **Network isolation** - Use `--network none` when possible

## Integration Points

- [[Container Isolation]] - How we apply these features
- [[Network Policies]] - Additional network security
- [[Resource Management]] - Preventing DoS attacks
- [[Monitoring and Alerting]] - Detecting security breaches

## Related Security Concepts

For adversarial AI testing, see [[Adversarial Testing]]. For production deployment, refer to [[Kubernetes Security]].