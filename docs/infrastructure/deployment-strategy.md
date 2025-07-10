# Deployment Strategy for Crucible Platform

## Current Approach: Tagging for Blue-Green

### What We're Doing
- Adding deployment tags to EC2 instance without changing names
- Keeping all resources shared initially
- Planning for future resource separation as needed

### Resources That Can Be Shared
✅ **Always Shared:**
- ECR Repository (use image tags)
- S3 Deployment Bucket  
- GitHub OIDC Provider
- VPC/Subnets (default VPC)

✅ **Currently Shared (May Split Later):**
- Security Groups (can add rules as needed)
- IAM Roles/Policies (permissions are the same)
- Key Pairs (SSH access)

❌ **Cannot Be Shared:**
- EC2 Instances (need separate for blue/green)
- Target Groups (if using ALB)
- Auto Scaling Groups (if implemented)

### Deployment Process

1. **Tag Current Instance as Blue:**
```bash
tofu apply -var="deployment_color=blue" -var="deployment_version=1.0"
```

2. **Deploy Green Instance (When Ready):**
```bash
# First, update ec2.tf to create a second instance
# Then deploy with:
tofu apply -var="deployment_color=green" -var="deployment_version=2.0"
```

3. **View Running Instances:**
```bash
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=crucible-platform" \
  --query 'Reservations[].Instances[].[Tags[?Key==`Name`].Value|[0],Tags[?Key==`DeploymentColor`].Value|[0],PublicIpAddress,State.Name]' \
  --output table
```

### Future Considerations

**When to Split Security Groups:**
- When blue/green need different port configurations
- When testing new services (e.g., adding HTTPS)
- Solution: Create versioned security groups

**When to Split IAM Roles:**
- When permissions need to differ (e.g., new S3 buckets)
- When testing principle of least privilege changes
- Solution: Create deployment-specific roles

**Adding Load Balancer:**
- ALB can route between blue/green based on weights
- Enables gradual rollout (canary deployments)
- True zero-downtime deployments

### For Your Demo Site

Since you want a stable demo site while developing:

1. **Current instance** = Your stable demo (tag as "blue")
2. **New features** = Test on local Docker first
3. **When ready** = Deploy a "green" instance
4. **After testing** = Update DNS/Load balancer to point to green
5. **Keep blue** = Instant rollback if needed

### Cost Optimization

**Free Tier Friendly:**
- 1 t2.micro instance free for 12 months
- Can stop green when not testing
- Use scheduled scaling for test instances

**Commands for Cost Management:**
```bash
# Stop green instance when not needed
aws ec2 stop-instances --instance-ids i-xxxxx

# Start for testing
aws ec2 start-instances --instance-ids i-xxxxx
```

### Next Steps

1. Apply tags to current instance (no downtime)
2. Continue developing locally
3. When ready for v2, we'll add logic for second instance
4. Eventually add ALB for smooth transitions