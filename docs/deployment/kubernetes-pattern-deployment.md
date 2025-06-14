# The Kubernetes Pattern for EC2 Deployments

## Overview

This document explains why we chose to mirror Kubernetes deployment patterns for our EC2-based infrastructure, moving from traditional "deploy on boot" to "infrastructure ready, awaiting deployment."

## The Traditional Pattern (What We Moved Away From)

### How It Usually Works
```bash
# In userdata/cloud-init
1. Install dependencies
2. Download application code  
3. Start services
4. Hope it all works
```

### Problems with This Approach
1. **Mixing Concerns**: Infrastructure setup mixed with application deployment
2. **Debugging Difficulty**: If deployment fails, is it infrastructure or application?
3. **Multiple Code Paths**: Initial deployment differs from updates
4. **Bootstrap Complexity**: Userdata downloads code to get update scripts to download code again
5. **Testing Challenges**: Can't test deployment pipeline without creating new instances

## The Kubernetes Pattern (What We Adopted)

### How Kubernetes Works
```yaml
# Pod starts empty
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: app
    image: TO_BE_DEPLOYED  # Deployment controller fills this

# Deployment happens separately
kubectl apply -f deployment.yaml
```

### Our EC2 Implementation
```bash
# Userdata: Infrastructure only
1. Install Python, Docker, gVisor
2. Create directories
3. Register as "ready"
4. Wait for deployment

# GitHub Actions: All deployments
on:
  push: [main]           # Automatic updates
  workflow_dispatch:     # Manual initial deployment
```

## Benefits of This Pattern

### 1. **Single Deployment Path**
- Every deployment (initial or update) goes through GitHub Actions
- No special cases or duplicate code
- Easy to test and debug

### 2. **Clear Separation of Concerns**
- **Terraform/Userdata**: Infrastructure (what the app runs on)
- **GitHub Actions**: Application (what actually runs)
- **S3**: Artifact storage (versioned deployments)

### 3. **Observable State**
```bash
# You always know what state an instance is in
/home/ubuntu/infrastructure-ready    # Infrastructure complete
/home/ubuntu/crucible/app.py        # Application deployed
systemctl status crucible-platform   # Application running
```

### 4. **Gitops Principles**
- Git is the source of truth
- Deployments are triggered by Git events
- Infrastructure changes are separate from code changes

### 5. **Failure Isolation**
- Infrastructure failures happen during `terraform apply`
- Deployment failures happen during GitHub Actions
- Never mixed, always clear where the problem is

## Implementation Details

### Infrastructure (Userdata)
```bash
#!/bin/bash
# Only infrastructure concerns
apt-get install -y python3.11 docker-ce gvisor
mkdir -p /home/ubuntu/crucible /var/log/crucible

# Register as ready
aws ssm put-parameter \
  --name "/crucible/instances/$(ec2-metadata --instance-id)/status" \
  --value "ready"

# That's it! No code deployment
```

### Deployment (GitHub Actions)
```yaml
name: Deploy to EC2
on:
  push: [main]
  workflow_dispatch:  # Manual trigger for initial deploy

jobs:
  deploy:
    steps:
      - Deploy to S3
      - Find ready instances via SSM
      - Trigger update script on instances
```

### The Update Script
- Lives in the repository
- Deployed with the code
- Single source of truth for deployment logic
- Can be updated without changing infrastructure

## State of the Art (SOTA) Considerations

### Why This Is Modern Best Practice

1. **Immutable Infrastructure Mindset**
   - Infrastructure is cattle, not pets
   - Easy to recreate from scratch
   - No configuration drift

2. **CI/CD First**
   - Deployment pipeline works from day one
   - No "manual steps for first deploy"
   - Everything is automated

3. **Cloud Native Patterns**
   - Mirrors Kubernetes exactly
   - Familiar to modern developers
   - Uses cloud services (SSM, S3) effectively

4. **Security Benefits**
   - No secrets in userdata
   - Deployment credentials separate from infrastructure
   - Audit trail through GitHub Actions

### Alternative Patterns We Considered

1. **Pull-Based (GitOps Controller)**
   - EC2 runs agent that watches Git
   - Good for Kubernetes, overkill for EC2

2. **Baked AMIs**
   - Application code in the AMI
   - Fast boot but slow updates
   - Version management complexity

3. **Configuration Management**
   - Ansible/Chef/Puppet
   - Another tool to manage
   - Overkill for single application

## Practical Workflow

### Initial Deployment
```bash
# 1. Create infrastructure
cd infrastructure/terraform
tofu apply

# 2. Trigger initial deployment
gh workflow run deploy.yml
# OR: Go to GitHub Actions UI → Run workflow

# 3. Verify deployment
ssh ubuntu@<ec2-ip> cat /home/ubuntu/deployment-instructions.txt
```

### Continuous Deployment
```bash
# Just push to main
git push origin main
# GitHub Actions automatically deploys
```

### Debugging
```bash
# Infrastructure issues
cat /var/log/userdata.log

# Deployment issues  
# Check GitHub Actions logs
# OR: ssh and check systemd
journalctl -u crucible-platform
```

## Key Insights

### "Empty but Ready" is a Feature
- Forces you to make deployment pipeline work immediately
- No hidden "works on my machine" manual steps
- Matches production patterns

### Deployment Should Be Boring
- Same process every time
- No special cases
- Fully automated
- Easy to reason about

### The Bootstrap Problem
Initially we tried:
1. Userdata downloads from S3 to get update script
2. Update script downloads from S3 to get code

This is the **same download twice** - a clear sign of poor design.

The solution: Don't deploy on boot. Let CI/CD handle it.

## Conclusion

By adopting the Kubernetes pattern for EC2 deployments, we achieve:
- **Simplicity**: Clear separation of infrastructure and application
- **Reliability**: Single, tested deployment path
- **Modernization**: Following cloud-native best practices
- **Maintainability**: Easy to understand and modify

The pattern of "infrastructure ready, awaiting deployment" is not just modern - it's the right abstraction for separating concerns in cloud deployments.