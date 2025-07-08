# Blue/Green Infrastructure Updates Complete

## What Changed

1. **EC2 Instances**: 
   - Changed from `for_each = var.enabled_deployment_colors` to `for_each = toset(["blue", "green"])`
   - Added lifecycle blocks to ignore changes when color not in `enabled_deployment_colors`

2. **Elastic IPs**:
   - Changed to always create both blue and green
   - Added lifecycle blocks

3. **Security Groups** (Improved based on feedback):
   - **Shared security group**: Common rules (HTTP/HTTPS) that update for all
   - **Color-specific security groups**: SSH access and testing ports per environment
   - Each instance uses both security groups
   - Allows updating SSH access per color while shared rules affect all

## How It Works

When you run:
```bash
tofu apply -var='enabled_deployment_colors=["green"]'
```

Terraform will:
- ✅ Update green instance (user_data, AMI, etc.)
- ✅ Update green security group (SSH IP, rules)
- ✅ Update green EIP tags
- ✅ Update all shared resources (monitoring, ECR, etc.)
- ❌ Ignore blue instance (due to lifecycle block)
- ❌ Ignore blue security group
- ❌ Keep DNS pointing to blue (active_deployment_color)

## First Time Apply Warning

Since blue resources were created with the old configuration, the first time you run `tofu apply`, it will want to:
- Create the new shared security group
- Create color-specific security groups for both blue and green
- Update instances to use both security groups
- Remove the old single security group

This is a one-time update. After both environments are on the new configuration, the selective updates will work as designed.

## Initial Deployment Note

For brand new deployments, you'll need to enable both colors for the first apply:
```bash
tofu apply  # Creates both blue and green
```

After initial creation, you can use selective updates.

## Commands

```bash
# Update only green (after initial migration)
tofu apply -var='enabled_deployment_colors=["green"]'

# Update only blue (after initial migration)
tofu apply -var='enabled_deployment_colors=["blue"]'

# Update both (default)
tofu apply

# Switch traffic from blue to green
tofu apply -var='active_deployment_color=green'
```