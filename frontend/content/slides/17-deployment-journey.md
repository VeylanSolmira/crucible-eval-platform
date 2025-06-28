---
title: "The Deployment Journey"
duration: 3
tags: ["deployment", "systemd"]
---

## The Deployment Journey

### Manual Deployment: Feel the Pain First

**What We Experienced:**
```bash
# The manual deployment dance
$ ./scripts/deploy-to-s3.sh
$ ssh ubuntu@ec2-instance
$ tar -xzf crucible-platform.tar.gz
$ sudo systemctl restart crucible-platform
$ sudo systemctl status crucible-platform  # FAILED!
```

**Debugging SystemD (2 hours):**
- Namespace errors (exit code 226)
- Security directive conflicts
- Hidden formatting issues
- The dreaded "ReadWritePaths must be on one line"

**The SystemD Security Journey:**
```ini
# What looked right but failed:
ReadWritePaths=/home/ubuntu/crucible/storage \
    /var/log/crucible  # BROKEN!

# What actually works:
ReadWritePaths=/home/ubuntu/crucible/storage /var/log/crucible

# Security settings we kept:
ProtectSystem=strict      # Entire filesystem read-only
ProtectHome=read-only     # No home directory access
NoNewPrivileges=true      # No privilege escalation
PrivateTmp=true          # Isolated /tmp
```