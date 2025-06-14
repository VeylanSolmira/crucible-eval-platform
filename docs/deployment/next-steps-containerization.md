# Next Steps: Containerization for METR Alignment

## Immediate Actions (Today)

### 1. Test Docker Build
```bash
# From project root
docker build -t crucible-platform:test .

# If successful, you should see:
# Successfully tagged crucible-platform:test
```

### 2. Fix Any Build Issues
Common issues and fixes:
- **Missing requirements.txt**: Create from your current environment
- **Import errors**: Ensure all code is in the build context
- **Permission errors**: Check file ownership in Dockerfile

### 3. Run Container Locally
```bash
# Quick test
docker run --rm -p 8080:8080 crucible-platform:test

# With compose for full setup
docker-compose up
```

## This Week's Goals

1. **Containerize Successfully**
   - Get app running in container
   - Ensure all features work
   - Document any issues

2. **Security Hardening**
   - Run as non-root user ✓ (already in Dockerfile)
   - Read-only filesystem ✓ (already configured)
   - Add gVisor runtime class for K8s

3. **Update EC2 Deployment**
   - Option A: Keep current deployment for now
   - Option B: Update userdata to use Docker
   - Option C: Use both (systemd as backup)

## Why This Matters for METR

METR evaluates AI systems that could be dangerous. They need:

1. **Isolation**: Containers + gVisor prevent escape
2. **Reproducibility**: Same environment every time
3. **Scalability**: Run many evaluations in parallel
4. **Auditability**: Every action is logged

Your current EC2 + systemd approach is fine for demo, but containers show you understand production requirements.

## Quick Wins

### Add Health Endpoint (if missing)
```python
# In your app.py or web_frontend.py
@app.route('/health')
def health():
    return {"status": "healthy"}, 200

@app.route('/ready')
def ready():
    # Check dependencies
    return {"status": "ready"}, 200
```

### Create .dockerignore
```
# .dockerignore
__pycache__
*.pyc
.git
.env
venv/
.pytest_cache/
*.log
```

### Test Container Security
```bash
# After building, test security
docker run --rm --security-opt no-new-privileges:true \
  --read-only --tmpfs /tmp \
  -p 8080:8080 crucible-platform:test

# Should work despite restrictions
```

## Decision Point

You have two paths:

### Path A: Minimal Change (Good for Demo)
- Keep EC2 + systemd deployment
- Add container as "future state" documentation
- Focus on features over infrastructure

### Path B: Full Migration (Better for METR)
- Switch to container deployment now
- Learn Kubernetes basics
- Show production-ready thinking

Both are valid. Path B shows more alignment with what METR likely uses in production.

## Questions to Consider

1. Do you want to learn K8s now or focus on platform features?
2. Is your goal to show working code or production architecture?
3. How much time do you have for infrastructure work?

The container setup is ready - you just need to build and test!