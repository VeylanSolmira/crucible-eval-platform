# Security Evolution: From MVP to Production

This document traces the security posture of our deployment pipeline as it evolves from a simple MVP to production-ready infrastructure.

## Current Security Posture (MVP/Learning Phase)

### What We Have ✅
- **SSH Key-based Authentication**
  - No passwords, only RSA key pairs
  - Keys stored in GitHub Secrets (encrypted at rest)
  
- **IAM Role-based S3 Access**
  - EC2 instance uses IAM role, not access keys
  - Follows AWS best practices for instance credentials
  
- **OIDC for GitHub Actions**
  - No long-lived AWS credentials in GitHub
  - Temporary credentials with 1-hour expiration
  - Scoped to specific repository

- **SSM Parameter Store**
  - Configuration values stored centrally
  - Not hardcoded in scripts or repos
  - Encrypted at rest by default

### Security Gaps ⚠️
1. **Single SSH Key for All Deployments**
   - One compromised key affects all deployments
   - No per-deployment or per-user keys
   
2. **Broad EC2 Permissions**
   - Instance can read entire deployment bucket
   - Could potentially access other deployments
   
3. **No Audit Trail**
   - Who deployed what when?
   - No CloudTrail logging for deployment actions
   
4. **No Package Verification**
   - Packages aren't signed
   - No checksum verification
   - Trust relies on S3 access control

5. **Manual Rollback**
   - No automated rollback on failure
   - Previous versions not tracked systematically

## Production Security Enhancements

### Level 1: Direct Improvements (Same Architecture)
```yaml
# Enhanced SSH key management
- name: Deploy with ephemeral keys
  run: |
    # Generate deployment-specific key
    ssh-keygen -t ed25519 -f deploy_key_${{ github.run_id }}
    # Add to instance authorized_keys temporarily
    # Remove after deployment
```

### Level 2: Additional Security Layers
- **Signed Packages**
  ```bash
  # Sign during build
  gpg --sign crucible-platform.tar.gz
  # Verify during deployment
  gpg --verify crucible-platform.tar.gz.sig
  ```

- **Deployment Audit Logs**
  ```bash
  # Log all deployments to CloudWatch
  aws logs put-log-events \
    --log-group /aws/crucible/deployments \
    --log-stream $INSTANCE_ID \
    --log-events timestamp=$(date +%s000),message="Deployed version $VERSION by $GITHUB_ACTOR"
  ```

- **Least Privilege S3 Access**
  ```json
  {
    "Effect": "Allow",
    "Action": ["s3:GetObject"],
    "Resource": "arn:aws:s3:::deployment-bucket/crucible-platform-*",
    "Condition": {
      "StringLike": {
        "s3:x-amz-server-side-encryption": "AES256"
      }
    }
  }
  ```

### Level 3: Architecture Changes

#### Container-based Deployment (Next Evolution)
```yaml
# No SSH needed - just update container image
- name: Deploy via ECS/Kubernetes
  run: |
    aws ecs update-service \
      --service crucible-platform \
      --force-new-deployment
```

**Security Benefits:**
- Immutable infrastructure
- No SSH access needed
- Built-in rollback
- Image scanning in registry
- Network isolation by default

#### GitOps Pattern (Final Form)
```yaml
# Deployment = git commit
- name: Update manifest
  run: |
    sed -i "s/image:.*/image: crucible:$VERSION/" k8s/deployment.yaml
    git commit -am "Deploy $VERSION"
    git push
```

**Security Benefits:**
- Git = audit trail
- PR approval = deployment approval  
- Declarative desired state
- No direct cluster access
- Automatic drift detection

## Security Decision Framework

### When to Add Security
1. **Always from Day 1:**
   - Encryption at rest
   - No hardcoded secrets
   - Key-based auth only
   - Least privilege IAM

2. **When Moving to Production:**
   - Audit logging
   - Package signing
   - Automated security scanning
   - Incident response plan

3. **At Scale:**
   - Zero-trust networking
   - Service mesh
   - Policy as code
   - Compliance automation

### Security vs Complexity Trade-offs

| Approach | Security | Complexity | When to Use |
|----------|----------|------------|-------------|
| SSH + Script | Basic | Low | Learning/MVP |
| SSH + Signed Packages | Good | Medium | Small production |
| Containers + RBAC | Better | High | Growing teams |
| GitOps + Policy | Best | Highest | Large scale |

## Key Takeaways

1. **Start Simple, But Secure**
   - Even MVP should have basic security
   - No passwords, no long-lived credentials
   - Encryption by default

2. **Security Evolves with Architecture**
   - Each architecture level enables new security patterns
   - Don't over-engineer security for current needs
   - Plan for next level

3. **Make Security Visible**
   - Document current gaps
   - Show evolution path
   - Explain trade-offs

4. **Automate Security**
   - Manual security = no security
   - Build security into the pipeline
   - Make secure path the easy path

## Interview Talking Points

When discussing this evolution:

1. **Show Security Awareness**
   - "Even in our MVP, we avoided passwords and used IAM roles"
   - "I documented security gaps for transparency"

2. **Demonstrate Pragmatism**
   - "We started with SSH because it was sufficient for one instance"
   - "Each evolution added security appropriate to scale"

3. **Highlight Learning**
   - "This taught me how security requirements drive architecture"
   - "I learned to balance security with development velocity"

4. **Connect to METR's Needs**
   - "AI safety requires defense in depth"
   - "Evaluation infrastructure must be tamper-proof"
   - "Audit trails are critical for AI safety research"