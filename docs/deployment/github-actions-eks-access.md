# GitHub Actions to EKS Access Strategies

## Problem Statement
GitHub Actions needs to deploy to our EKS cluster, but:
- EKS API endpoint needs to be secured
- GitHub Actions uses 5,000+ dynamic IP ranges
- AWS EKS publicAccessCidrs has practical limits
- We need reliable, not intermittent, deployments

## Options Analysis

### 1. SSM-Based Deployment (Recommended for Security)
**How it works:**
- GitHub Actions uses SSM to run kubectl commands on EC2 instance inside VPC
- No direct internet exposure of EKS endpoint

**Implementation:**
```yaml
- name: Deploy via SSM
  run: |
    aws ssm send-command \
      --instance-ids ${{ secrets.BASTION_INSTANCE_ID }} \
      --document-name "AWS-RunShellScript" \
      --parameters 'commands=["kubectl set image deployment/app app=image:tag"]'
```

**Pros:**
- Most secure - EKS never exposed to internet
- Works with private EKS endpoints
- Full audit trail via SSM

**Cons:**
- Requires bastion/jump host
- Slightly more complex
- Additional EC2 costs

### 2. Self-Hosted Runners in VPC
**How it works:**
- Run GitHub Actions runners on EC2 instances in your VPC
- Direct private network access to EKS

**Implementation:**
```bash
# Install runner on EC2 instance
./config.sh --url https://github.com/ORG/REPO --token TOKEN
# Use runs-on: self-hosted in workflows
```

**Pros:**
- Very secure
- Fast deployments (no internet latency)
- Can use instance profiles for auth

**Cons:**
- Need to manage runner infrastructure
- Additional EC2 costs
- Requires autoscaling setup

### 3. Temporary 0.0.0.0/0 Access (Quick but Less Secure)
**How it works:**
- Temporarily open EKS to all IPs during deployment
- Close immediately after

**Implementation:**
```bash
# In workflow
- name: Open EKS access
  run: |
    aws eks update-cluster-config --name cluster \
      --resources-vpc-config publicAccessCidrs='["0.0.0.0/0"]'
    
# Deploy...

- name: Close EKS access
  if: always()
  run: |
    aws eks update-cluster-config --name cluster \
      --resources-vpc-config publicAccessCidrs='["YOUR-OFFICE-IP/32"]'
```

**Pros:**
- Simple to implement
- Works immediately

**Cons:**
- Security risk during open window
- Cluster updates take 10-20 minutes
- Not suitable for production

### 4. Lambda + API Gateway Deployment Service
**How it works:**
- Create API endpoint that triggers Lambda
- Lambda has VPC access and runs kubectl

**Pros:**
- Very secure
- Rate limiting built-in
- Can add custom auth

**Cons:**
- More infrastructure to build
- Need to handle async deployments

### 5. ArgoCD GitOps (Best for Production)
**How it works:**
- ArgoCD runs inside cluster, pulls changes from Git
- No external access needed

**Implementation:**
```yaml
# Application manifest
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: https://github.com/org/repo
    path: k8s/
  destination:
    server: https://kubernetes.default.svc
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**Pros:**
- Most secure - pull-based
- Declarative and auditable
- Self-healing deployments

**Cons:**
- Requires ArgoCD setup
- Different deployment paradigm

## Recommendation

For our current needs, I recommend:

1. **Short term**: Use SSM-based deployment (#1) 
   - Can implement today
   - Secure enough for production
   - Minimal infrastructure changes

2. **Long term**: Migrate to ArgoCD (#5)
   - Industry best practice
   - Most secure
   - Better for scaling

## Implementation Priority

1. Document current manual process
2. Implement SSM-based deployment
3. Test thoroughly in dev
4. Plan ArgoCD migration