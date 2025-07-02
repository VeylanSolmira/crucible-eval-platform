---
title: 'The Docker Socket Proxy Game-Changer'
duration: 2
tags: ['security', 'docker']
---

## The Docker Socket Proxy Game-Changer

### tecnativa/docker-socket-proxy

**Traditional Approach (Dangerous):**

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
# Full Docker API access = root on host
```

**Our Approach (Secure):**

```yaml
docker-proxy:
  image: tecnativa/docker-socket-proxy
  environment:
    CONTAINERS: 1 # Can manage containers
    IMAGES: 1 # Can pull images
    INFO: 0 # DENIED: No system info
    NETWORKS: 0 # DENIED: No network access
    VOLUMES: 0 # DENIED: No volume mounts
    EXEC: 0 # DENIED: No exec into containers
```

**Security Improvement: 10x reduction in attack surface**
