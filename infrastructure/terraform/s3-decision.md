# S3 Bucket Strategy Decision

## Current Implementation
Multiple buckets per environment with prefix naming

## Recommendation
**Keep the multiple bucket approach** for this project because:

1. **Matches METR's Security Needs**: Evaluating untrusted AI code requires maximum isolation
2. **Simple IAM**: EC2 instances only access their environment's bucket
3. **Clear Boundaries**: No accidental production deployments from dev
4. **Easy to Reason About**: Each environment is completely separate

## Quick Alternative Implementation

If you prefer single bucket, here's a minimal change to `s3.tf`:

```hcl
# Replace the current deployment bucket with:
resource "aws_s3_bucket" "deployment" {
  bucket = "crucible-deployment-${data.aws_caller_identity.current.account_id}"
  # Remove environment prefix
}

# In EC2 userdata, change deployment path:
deployment_key = "${var.environment}/${var.deployment_key}"
```

But I recommend staying with multiple buckets for security isolation.