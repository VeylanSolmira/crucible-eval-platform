# AWS Authentication Methods for CI/CD

## Overview

When connecting CI/CD systems (like GitHub Actions) to AWS, there are several authentication methods available. This document explains each method and why we chose OIDC for our deployment pipeline.

## Authentication Methods Comparison

### 1. IAM User with Access Keys (Traditional)

**How it works:**
```yaml
- uses: aws-actions/configure-aws-credentials@v2
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

**Pros:**
- Simple to set up
- Works immediately
- Familiar to most developers

**Cons:**
- Long-lived credentials (security risk)
- Manual rotation required
- If leaked, attacker has persistent access
- Against AWS best practices
- Shows up in security audits as a risk

**When to use:**
- Quick prototypes
- Personal projects
- When OIDC isn't available

### 2. OIDC (OpenID Connect) - Recommended

**How it works:**
```yaml
- uses: aws-actions/configure-aws-credentials@v2
  with:
    role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
    aws-region: us-west-2
```

**Architecture:**
```
GitHub Actions → OIDC Token → AWS STS → Temporary Credentials (1 hour)
```

**Pros:**
- No secrets stored in GitHub
- Credentials expire after 1 hour
- AWS CloudTrail shows "GitHub Actions" as identity
- Can restrict to specific repos/branches/tags
- Follows AWS best practices
- Zero credential management

**Cons:**
- More initial setup
- Requires understanding of OIDC/JWT
- Debugging can be more complex

**When to use:**
- Production deployments
- Any long-term project
- When security matters
- Enterprise environments

### 3. EC2 Instance Profile (Self-Hosted Runners)

**How it works:**
- IAM role attached to EC2 instance
- GitHub Actions runner on that EC2
- Automatic credential injection

**Pros:**
- Most secure option
- No credentials anywhere
- Automatic rotation
- Network-level security possible

**Cons:**
- Requires self-hosted runners
- More infrastructure to manage
- Higher cost (dedicated EC2)
- Complex setup

**When to use:**
- High-security environments
- When you need network isolation
- Already using self-hosted runners

### 4. AWS Systems Manager Parameter Store

**How it works:**
```yaml
- name: Get credentials from SSM
  run: |
    export AWS_ACCESS_KEY_ID=$(aws ssm get-parameter --name /github/aws-key --query Parameter.Value --output text)
    export AWS_SECRET_ACCESS_KEY=$(aws ssm get-parameter --name /github/aws-secret --with-decryption --query Parameter.Value --output text)
```

**Pros:**
- Centralized credential management
- Encryption at rest
- Audit trail
- Can be rotated programmatically

**Cons:**
- Still using long-lived credentials
- Need initial auth to access SSM
- More complex than direct secrets
- Chicken-and-egg problem

**When to use:**
- When you have many credentials to manage
- Need programmatic rotation
- Already invested in SSM

## Why We Chose OIDC

### Security Benefits

1. **No Long-Lived Credentials**
   - Traditional: Access keys valid until manually rotated
   - OIDC: Credentials expire in 1 hour

2. **Granular Access Control**
   ```json
   {
     "Condition": {
       "StringLike": {
         "token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:ref:refs/heads/main"
       }
     }
   }
   ```
   - Can restrict to specific repository
   - Can restrict to specific branch
   - Can restrict to specific GitHub environment

3. **Better Audit Trail**
   - CloudTrail shows GitHub Actions as the identity
   - Can trace actions back to specific workflow runs
   - Clear separation from human users

### Operational Benefits

1. **No Credential Rotation**
   - No quarterly key rotation reminders
   - No risk of expired credentials breaking deployments
   - No coordination needed between teams

2. **Easier Onboarding**
   - New repositories just need the role ARN
   - No need to create and distribute new credentials
   - Developers never see AWS credentials

3. **Simplified Security Reviews**
   - Auditors love OIDC
   - Meets compliance requirements
   - Shows security maturity

## Implementation Guide

### Step 1: Create OIDC Provider (One-time)
```hcl
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}
```

### Step 2: Create IAM Role
```hcl
resource "aws_iam_role" "github_actions" {
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike = {
          "token.actions.githubusercontent.com:sub": "repo:YourOrg/YourRepo:*"
        }
      }
    }]
  })
}
```

### Step 3: Update GitHub Actions
```yaml
jobs:
  deploy:
    permissions:
      id-token: write  # Required for OIDC
      contents: read
    
    steps:
      - uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ vars.AWS_ROLE_ARN }}
          aws-region: us-west-2
```

### Step 4: Add Role ARN to GitHub
- Go to Settings → Secrets and variables → Actions → Variables
- Add `AWS_ROLE_ARN` with the role ARN value
- Note: Use Variables (public) not Secrets since ARNs aren't sensitive

## Troubleshooting OIDC

### Common Issues

1. **"Could not assume role"**
   - Check the trust policy condition matches your repo
   - Verify the OIDC provider thumbprint is correct
   - Ensure permissions include `id-token: write`

2. **"No OIDC token available"**
   - Add `permissions: id-token: write` to job
   - Check you're using `vars.` not `secrets.` for role ARN
   - Verify workflow is running on GitHub-hosted runner

3. **"Access Denied" after assuming role**
   - Check IAM policies attached to role
   - Verify resource ARNs in policies
   - Look at CloudTrail for specific denied action

### Debugging Commands
```bash
# Decode the OIDC token (in Actions)
- name: Debug OIDC Token
  run: |
    echo $ACTIONS_ID_TOKEN_REQUEST_TOKEN
    echo $ACTIONS_ID_TOKEN_REQUEST_URL
    
# Check assumed role
- name: Verify AWS Identity
  run: aws sts get-caller-identity
```

## Migration Path

### From Access Keys to OIDC

1. **Phase 1: Setup** (No downtime)
   - Create OIDC provider and role
   - Test in a separate workflow

2. **Phase 2: Parallel Run** (No downtime)
   - Update workflow to support both methods
   - Use OIDC if available, fall back to keys

3. **Phase 3: Switch** (Minimal change)
   - Update workflow to use only OIDC
   - Keep access keys as emergency backup

4. **Phase 4: Cleanup** (Security improvement)
   - Delete access keys
   - Remove from GitHub secrets
   - Update documentation

## Security Best Practices

1. **Least Privilege**
   - Only grant permissions needed for deployment
   - Use resource-level permissions where possible
   - Regular access reviews

2. **Condition Restrictions**
   - Restrict to specific repository
   - Consider branch restrictions for production
   - Use external ID for additional security

3. **Monitoring**
   - Enable CloudTrail for all regions
   - Set up alerts for role assumptions
   - Regular audit of permissions

4. **Role Naming**
   - Use descriptive names: `github-actions-{repo}-{environment}`
   - Tag roles with purpose and owner
   - Document role purpose in description

## Conclusion

While AWS Access Keys are simpler to set up initially, OIDC provides superior security, better operational practices, and aligns with AWS best practices. The initial setup complexity pays off through:

- Eliminated credential management
- Enhanced security posture
- Better audit trails
- Simplified compliance

For any production deployment pipeline, OIDC should be the default choice.