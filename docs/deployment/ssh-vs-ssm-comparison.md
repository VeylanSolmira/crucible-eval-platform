# SSH vs SSM Deployment Comparison

## SSH Approach

### Architecture
```
GitHub Actions → S3 (artifact) → SSH → EC2 → Pull from S3
```

### Pros
- **Simple and direct** - SSH is well-understood
- **Fast feedback** - See output immediately
- **Portable** - Works with any Linux server
- **Debuggable** - Can run same commands manually
- **Atomic deployments** - Using symlinks for zero-downtime
- **Version history** - Keep multiple deployments

### Cons
- **SSH key management** - Need to distribute keys securely
- **Network access** - Requires SSH port open
- **No built-in audit** - Need to add logging

### Infrastructure Requirements
- SSH key in GitHub Secrets
- EC2 with SSH access
- S3 for artifacts
- Instance IAM role for S3 access

## SSM Approach

### Architecture
```
GitHub Actions → S3 (artifact) → SSM SendCommand → EC2 → Pull from S3
```

### Pros
- **No SSH keys** - Uses IAM roles
- **Full audit trail** - CloudTrail logs everything
- **No open ports** - Works through SSM agent
- **AWS native** - Integrated with AWS services
- **Fleet management** - Same command to many instances

### Cons
- **Complex permissions** - Both GitHub and EC2 need SSM access
- **Async execution** - Fire and forget
- **Harder debugging** - Can't easily see output
- **AWS-specific** - Locked to AWS

### Infrastructure Requirements
- SSM Agent on EC2
- IAM roles for GitHub Actions and EC2
- SSM permissions (SendCommand, etc)
- S3 for artifacts

## Verdict

For **single instance**: SSH is simpler and more direct
For **fleet of instances**: SSM scales better
For **security audits**: SSM has better trail
For **developer experience**: SSH is more familiar

## Hybrid Approach

Best of both worlds:
1. Use OIDC for AWS auth (no long-lived credentials)
2. Use S3 as artifact store (versioning, durability)
3. Use SSH for deployment trigger (simple, direct)
4. Keep SSM as option for fleet management later

This gives you:
- ✅ Secure authentication (OIDC)
- ✅ Reliable artifact storage (S3)
- ✅ Simple deployment (SSH)
- ✅ Clear upgrade path (add SSM later)