---
title: 'Chapter 2: Adding Isolation'
duration: 2
tags: ['docker', 'security']
---

## Chapter 2: Adding Isolation

### Problem: Direct execution is a security nightmare

**Evolution to Docker:**

```python
# From subprocess...
subprocess.run(['python', '-c', code])

# To containerized execution
docker_client.containers.run(
    'python:3.11-slim',
    command=['python', '-c', code],
    network_disabled=True,  # Key safety feature
    mem_limit='512m',
    cpu_quota=50000
)
```

**What this solved:**

- Process isolation
- Resource limits
- Network restrictions
- Filesystem boundaries
