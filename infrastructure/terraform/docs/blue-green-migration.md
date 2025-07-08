# Blue-Green Deployment Migration Guide

## Overview
This guide helps you migrate the existing infrastructure to become the "blue" environment without downtime, then create "green" as a separate environment.

## Option 1: Import Existing Resources as Blue (Recommended)

This approach keeps your existing infrastructure running and imports it as "blue".

### Step 1: First, let's see what we currently have
```bash
cd infrastructure/terraform
tofu state list
```

### Step 2: Set environment to blue and plan
```bash
tofu plan -var-file=environments/blue.tfvars
```

This will show resources being destroyed and recreated - DON'T APPLY YET!

### Step 3: Use moved blocks to rename without recreation

Create a file `migrations.tf`:

```hcl
# Temporary file for migration - delete after applying
moved {
  from = aws_security_group.eval_server
  to   = aws_security_group.eval_server
}

moved {
  from = aws_iam_role.eval_server
  to   = aws_iam_role.eval_server
}

moved {
  from = aws_iam_instance_profile.eval_server
  to   = aws_iam_instance_profile.eval_server
}

moved {
  from = aws_instance.eval_server
  to   = aws_instance.eval_server
}
```

### Step 4: Apply with blue environment
```bash
tofu apply -var-file=environments/blue.tfvars
```

This will update tags and names without recreating resources.

### Step 5: Clean up
```bash
rm migrations.tf
```

## Option 2: Keep Existing as Default, Create Blue/Green as New

If you prefer to keep the existing infrastructure untouched:

1. Keep your current deployment as-is
2. Only use environment variables for NEW deployments:

```bash
# Deploy green as a new environment
tofu apply -var-file=environments/green.tfvars
```

This will create entirely new resources alongside existing ones.

## Option 3: Terraform State Manipulation (Advanced)

If the moved blocks don't work, we can manually update the state:

```bash
# Backup state first!
tofu state pull > terraform.tfstate.backup

# For each resource, remove and re-import with new name
tofu state rm aws_instance.eval_server
tofu import aws_instance.eval_server i-xxxxx  # Use actual instance ID
```

## Cost Considerations

- **Option 1**: No additional cost - existing resources are renamed
- **Option 2**: 2x cost - running both old and new environments
- **Option 3**: No additional cost - same as Option 1

## Recommended Approach

1. **For immediate safety**: Use Option 2 - deploy green as completely new
2. **For cleaner setup**: Use Option 1 with moved blocks
3. **After testing**: Remove the non-environment-specific resources

## Commands for Blue-Green Deployment

Once migrated:

```bash
# Deploy to blue
tofu apply -var-file=environments/blue.tfvars

# Deploy to green  
tofu apply -var-file=environments/green.tfvars

# Check what's running
aws ec2 describe-instances --filters "Name=tag:Project,Values=crucible-platform" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,Env:Tags[?Key==`Environment`]|[0].Value,IP:PublicIpAddress}'
```

## Zero-Downtime Deployment Process

1. Current traffic → Blue
2. Deploy new version → Green
3. Test Green
4. Switch traffic → Green
5. Keep Blue as rollback
6. Next deployment → Update Blue

## Note on Shared Resources

Some resources don't need environment separation:
- S3 deployment bucket (shared)
- ECR repository (shared, use tags)
- GitHub OIDC (shared)

Only EC2 and its directly related resources (SG, IAM) need blue/green.