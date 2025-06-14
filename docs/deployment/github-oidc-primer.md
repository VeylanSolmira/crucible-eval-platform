# How GitHub OIDC Works: A Primer

## The Problem OIDC Solves

Traditionally, to let GitHub Actions access AWS, you'd create an IAM user, generate access keys, and store them as secrets in GitHub. These keys:
- Never expire (unless you manually rotate them)
- Work from anywhere if leaked
- Are a constant security risk

OIDC eliminates these long-lived credentials entirely.

## What is OIDC?

**OpenID Connect (OIDC)** is a protocol that lets one service prove its identity to another service without sharing passwords. Think of it like showing your driver's license at a bar - you prove who you are without giving them your social security number.

In our case:
- GitHub Actions proves its identity to AWS
- AWS trusts GitHub's identity claims
- AWS gives temporary credentials in return

## The OIDC Flow Explained

### Step 1: GitHub Creates an Identity Token

When your workflow runs with `permissions: id-token: write`, GitHub creates a special token (JWT) that says:

```json
{
  "iss": "https://token.actions.githubusercontent.com",  // Issuer: GitHub
  "sub": "repo:YourOrg/YourRepo:ref:refs/heads/main",   // Subject: Your repo/branch
  "aud": "sts.amazonaws.com",                           // Audience: AWS
  "job_workflow_ref": "YourOrg/YourRepo/.github/workflows/deploy.yml@refs/heads/main",
  "run_id": "1234567890",
  "actor": "your-username",
  // ... more claims about the workflow run
}
```

This token is cryptographically signed by GitHub.

### Step 2: GitHub Actions Presents Token to AWS

The `aws-actions/configure-aws-credentials` action:
1. Gets this token from GitHub
2. Calls AWS STS (Security Token Service)
3. Says "Here's my GitHub token, I want to assume role X"

### Step 3: AWS Validates the Token

AWS:
1. Checks the signature using GitHub's public key
2. Verifies the token hasn't expired
3. Checks if the claims match the role's trust policy

The trust policy looks like:
```json
{
  "Condition": {
    "StringLike": {
      "token.actions.githubusercontent.com:sub": "repo:YourOrg/YourRepo:*"
    }
  }
}
```

If everything matches, AWS trusts that this really is GitHub Actions from your repository.

### Step 4: AWS Issues Temporary Credentials

AWS STS returns temporary credentials:
- Access Key ID (starts with `ASIA...`)
- Secret Access Key
- Session Token
- Expiration (1 hour)

These are automatically configured in the GitHub Actions environment.

## Visual Flow

```
┌─────────────────┐
│ GitHub Actions  │
│   Workflow      │
└────────┬────────┘
         │ 1. "I need AWS access"
         ▼
┌─────────────────┐
│ GitHub OIDC     │
│   Provider      │
└────────┬────────┘
         │ 2. "Here's a signed token proving
         │     this is repo:YourOrg/YourRepo"
         ▼
┌─────────────────┐
│   AWS STS       │
│ (AssumeRole)    │
└────────┬────────┘
         │ 3. "Token is valid, matches trust policy"
         │ 4. "Here are temporary credentials"
         ▼
┌─────────────────┐
│ GitHub Actions  │
│ (with temp AWS  │
│  credentials)   │
└─────────────────┘
```

## Key Concepts

### JWT (JSON Web Token)
The OIDC token is a JWT - a JSON object that's been signed. You can decode it (it's just base64), but you can't modify it without breaking the signature.

### Trust Relationship
The IAM role's trust policy is like a bouncer's list. It says "I'll let in anyone who shows me a valid GitHub token from this specific repository."

### Claims
The data inside the token (repository, branch, actor, etc.) are called "claims". AWS checks these claims against your trust policy conditions.

### STS (Security Token Service)
AWS service that exchanges long-term credentials (or OIDC tokens) for temporary credentials.

## Why This Is Secure

1. **Short-lived**: Tokens expire in minutes, credentials in an hour
2. **Scoped**: Can only be used by specific repo/branch/workflow
3. **Auditable**: Every use is logged with full context
4. **No Secrets**: Nothing to steal from GitHub or accidentally commit

## The Trust Chain

```
GitHub's Private Key → Signs Token → GitHub's Public Key → AWS Verifies → Trust Established
```

AWS trusts GitHub's public key (via the OIDC provider thumbprint). GitHub signs tokens with its private key. This creates a cryptographic chain of trust.

## Common Conditions You Can Use

```json
{
  // Specific repository
  "token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:*"
  
  // Specific branch
  "token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:ref:refs/heads/main"
  
  // Specific environment
  "token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:environment:production"
  
  // Specific tag pattern
  "token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:ref:refs/tags/v*"
  
  // Multiple conditions
  "ForAllValues:StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:MyOrg/MyRepo:*",
      "repo:MyOrg/AnotherRepo:*"
    ]
  }
}
```

## Debugging OIDC

### See the Raw Token
```yaml
- name: Debug OIDC Claims
  run: |
    OIDC_TOKEN=$(curl -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$ACTIONS_ID_TOKEN_REQUEST_URL" | jq -r '.value')
    echo $OIDC_TOKEN | cut -d. -f2 | base64 -d | jq
```

### Check What Identity You Got
```yaml
- name: Who Am I?
  run: |
    aws sts get-caller-identity
    # Shows the assumed role ARN and session name
```

### Common Trust Policy Mistakes

❌ **Wrong**: Checking the wrong claim
```json
"token.actions.githubusercontent.com:aud": "repo:MyOrg/MyRepo:*"  // 'aud' is always sts.amazonaws.com!
```

✅ **Correct**: Check the sub claim
```json
"token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:*"
```

❌ **Wrong**: Forgetting the wildcard
```json
"token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo"  // Won't match anything!
```

✅ **Correct**: Include a wildcard
```json
"token.actions.githubusercontent.com:sub": "repo:MyOrg/MyRepo:*"  // Matches any branch/tag
```

## The Magic Behind the Scenes

When you use:
```yaml
- uses: aws-actions/configure-aws-credentials@v2
  with:
    role-to-assume: arn:aws:iam::123456789012:role/MyRole
```

The action:
1. Requests OIDC token from GitHub (`ACTIONS_ID_TOKEN_REQUEST_URL`)
2. Calls `aws sts assume-role-with-web-identity` with that token
3. Sets environment variables:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_SESSION_TOKEN`
4. All subsequent AWS commands use these temporary credentials

## Summary

OIDC turns GitHub Actions into a trusted identity provider, like how Google or Facebook can log you into other websites. Instead of storing passwords (AWS keys) everywhere, services can just trust each other's identity claims.

The beauty is that once set up, it's invisible - you just specify which role to assume, and the cryptographic magic happens behind the scenes, giving you secure, temporary access to AWS resources.

No more rotating keys, no more leaked credentials, just cryptographically-proven identity.