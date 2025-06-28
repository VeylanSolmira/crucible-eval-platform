---
title: "Chapter 8: Next Step - Containerization"
duration: 2
tags: ["docker", "future"]
---

## Chapter 8: Next Step - Containerization
### Problem: Deployment still tied to specific EC2 setup

**Why Docker Next:**

1. **Consistency**: "Works on my machine" → "Works in any container runtime"
2. **Security**: Immutable images, no runtime modifications
3. **Scalability**: Foundation for Kubernetes migration
4. **Speed**: Pre-built images vs. installation on boot

**The Path Forward:**
```dockerfile
FROM python:3.11-slim
# Security: Non-root user
RUN useradd -m evaluator
USER evaluator
# Immutable application
COPY --chown=evaluator . /app
CMD ["python", "app.py"]
```