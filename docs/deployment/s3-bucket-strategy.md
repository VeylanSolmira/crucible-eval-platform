# S3 Bucket Strategy: Multiple Buckets vs Single Bucket with Folders

## Current Approach: Multiple Buckets per Environment

```
dev-crucible-deployment-123456/
├── crucible-platform-v1.0.0.tar.gz
└── crucible-platform-v1.0.1.tar.gz

prod-crucible-deployment-123456/
├── crucible-platform-v0.9.0.tar.gz
└── crucible-platform-v1.0.0.tar.gz
```

### Pros
1. **Complete Isolation**: No accidental cross-environment access
2. **IAM Simplicity**: Grant access to entire bucket per environment
3. **Cost Tracking**: CloudWatch costs per environment are clear
4. **Compliance**: Some regulations require environment separation
5. **Blast Radius**: Deleting a bucket only affects one environment
6. **Different Retention**: Easy to set different lifecycle policies

### Cons
1. **More Resources**: Each bucket needs policies, encryption, versioning
2. **Naming Limits**: AWS bucket names are globally unique
3. **Management Overhead**: More buckets to monitor and maintain
4. **Cross-Environment Operations**: Harder to promote artifacts

## Alternative: Single Bucket with Environment Folders

```
crucible-deployment-123456/
├── dev/
│   ├── crucible-platform-v1.0.1.tar.gz
│   └── crucible-platform-v1.0.2.tar.gz
├── staging/
│   └── crucible-platform-v1.0.0.tar.gz
└── prod/
    ├── crucible-platform-v0.9.0.tar.gz
    └── crucible-platform-v1.0.0.tar.gz
```

### Pros
1. **Simplicity**: One bucket to manage
2. **Easy Promotion**: Copy between folders for environment promotion
3. **Shared Policies**: Single set of encryption/versioning rules
4. **Cost Efficiency**: Better S3 request batching
5. **Naming**: Only need one globally unique name

### Cons
1. **IAM Complexity**: Need path-based policies for isolation
2. **Accident Risk**: Easier to accidentally access wrong environment
3. **Audit Complexity**: Harder to track environment-specific access
4. **No Separate Retention**: Same lifecycle rules for all environments
5. **Blast Radius**: Bucket deletion affects all environments

## IAM Policy Comparison

### Multiple Buckets (Simple)
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:::dev-crucible-deployment-*",
      "arn:aws:s3:::dev-crucible-deployment-*/*"
    ]
  }]
}
```

### Single Bucket (Complex)
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:ListBucket",
    "Resource": "arn:aws:s3:::crucible-deployment-*",
    "Condition": {
      "StringLike": {
        "s3:prefix": ["dev/*"]
      }
    }
  }, {
    "Effect": "Allow",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::crucible-deployment-*/dev/*"
  }]
}
```

## Recommendation for METR Use Case

**Use Multiple Buckets** for METR because:

1. **Security First**: METR evaluates potentially dangerous AI - complete isolation is critical
2. **Audit Requirements**: Clear environment boundaries for compliance
3. **Different Retention**: Dev can have short retention, prod needs long-term
4. **Blast Radius**: Production must be protected from dev accidents
5. **Access Control**: Simple IAM policies reduce security mistakes

## Hybrid Approach (Best of Both)

```
crucible-artifacts-123456/          # Shared artifacts
├── docker-images/
└── base-packages/

dev-crucible-deployment-123456/     # Environment specific
├── app-v1.0.1.tar.gz
└── config/

prod-crucible-deployment-123456/    # Isolated production
├── app-v1.0.0.tar.gz
└── config/
```

## Implementation for Single Bucket (If Preferred)

If you prefer the single bucket approach, here's how to modify the Terraform:

```hcl
# Single bucket with environment folders
resource "aws_s3_bucket" "deployment" {
  bucket = "crucible-deployment-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Name = "Crucible Deployment Packages"
    Purpose = "Multi-environment deployments"
  }
}

# Create environment folders
resource "aws_s3_object" "env_folders" {
  for_each = toset(["dev/", "staging/", "prod/"])
  
  bucket = aws_s3_bucket.deployment.id
  key    = each.value
  source = "/dev/null"
}

# Update EC2 to use environment path
user_data = templatefile("${path.module}/templates/userdata.sh.tpl", {
  deployment_bucket = aws_s3_bucket.deployment.id
  deployment_key    = "${var.environment}/${var.deployment_key}"
})
```

## Decision Factors

Choose **Multiple Buckets** if:
- Security and isolation are paramount
- You have regulatory compliance needs
- Different teams manage different environments
- You want simple IAM policies

Choose **Single Bucket** if:
- You have a small team
- You frequently promote artifacts between environments
- You want to minimize AWS resources
- You're comfortable with complex IAM policies

For METR's AI safety platform, multiple buckets provide the security isolation that matches the platform's purpose.