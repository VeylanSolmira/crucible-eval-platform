# Docker Compose Infrastructure Cleanup List

## Overview

This document lists all infrastructure components related to the old Docker Compose blue-green deployment that can be safely removed now that we're moving to Kubernetes.

## Infrastructure to Delete

### 1. EC2 Instances (Blue-Green)
```bash
# Currently running
- crucible-platform-eval-server-blue
- crucible-platform-eval-server-green
```
**Action**: Terminate both instances via Terraform or AWS Console

### 2. Route53 DNS Records (Keep Zone)
```bash
# Delete these A records
- crucible.veylan.dev → pointing to blue/green IPs -- #KEEP
- blue.crucible.veylan.dev #KEEP BUT CHANGE FROM BLUE TO DEV
- green.crucible.veylan.dev #KEEP BUT CHANGE TO STAGING
```
**Action**: Keep the Route53 zones and Elastic IPs for future use

### 3. GitHub Actions Workflows
```bash
# Delete or disable
- .github/workflows/deploy-compose.yml
- .github/workflows/deploy.yml (if exists)
```
**Action**: Comment out triggers or delete files

### 4. Terraform Files to Modify

#### ec2.tf
- **Delete**: EC2 instance resources for blue/green
- **Keep**: Security groups (can reuse for K8s nodes)
- **Keep**: IAM roles (can reuse for K8s)
- **Keep**: Key pairs

#### route53.tf  
- **Delete**: A records pointing to blue/green # KEEP WITH MODIFICATIONS ABOVE
- **Keep**: Route53 zones
- **Keep**: Elastic IPs (can attach to K8s load balancer)

#### deployment.tf
- **Check**: Any Docker Compose specific deployment logic

### 5. Infrastructure to Keep

#### VPC and Networking
```bash
# KEEP ALL OF THESE
- VPC
- Subnets  
- Internet Gateway
- NAT Instance/Gateway
- Security Groups (modify for K8s)
- Elastic IPs
```

#### IAM Resources
```bash
# KEEP AND MODIFY
- IAM roles (adapt for EKS)
- Instance profiles
- GitHub OIDC provider
```

#### Storage
```bash
# KEEP
- S3 buckets
- ECR repositories
```

#### Secrets
```bash
# KEEP
- SSM Parameters
- Secrets Manager entries #IT'S POSSIBLE SOME SPECIFIC VALUES ARE NOT NEEDED THAT SUPPORTED THE BLUE/GREEN DOCKER COMPOSE PATTERN
```

## Files to Delete/Archive

### Docker Compose Files
```bash
# Archive to legacy/
docker-compose.yml
docker-compose.prod.yml
docker-compose.dev.yml
docker-compose.build.yml
```

### Scripts
```bash
# Delete or archive
scripts/setup-ssl-container.sh #CAN YOU REMIND ME WHAT THIS DOES
scripts/debug_docker_permissions.sh
infrastructure/terraform/templates/userdata-compose.sh.tpl #IN KUBERNETES WILL WE ALSO HAVE USERDATA ON SOME EC2 INSTANCE THAT INSTALLS KUBERNETES ON THAT INSTANCE? I GUESS WE DON'T NEED THIS IF WE'RE USING EKS INSTEAD OF EC2 INSTANCES FOR THE CONTROL PLANE
```

### Documentation
```bash
# Archive to docs/archive/
docs/docker/*
docs/deployment/docker-*
docs/blue-green-*
```

## Cleanup Commands

### 1. Terminate EC2 Instances
```bash
# Via Terraform
cd infrastructure/terraform
terraform destroy -target=aws_instance.eval_server

# Or via AWS CLI
aws ec2 terminate-instances --instance-ids <blue-instance-id> <green-instance-id>
```

### 2. Clean up Route53 Records
```bash
# Delete A records but keep zones
aws route53 list-resource-record-sets --hosted-zone-id <zone-id> # see above
# Then delete specific records
```

### 3. Archive Docker Compose Files
```bash
mkdir -p legacy/docker-compose-archive
mv docker-compose*.yml legacy/docker-compose-archive/
```

## Migration Steps

1. **First**: Deploy Kubernetes cluster
2. **Test**: Ensure K8s deployment works
3. **Update DNS**: Point crucible.veylan.dev to K8s load balancer
4. **Wait**: 24-48 hours for DNS propagation # is that really accurate @ 24-48hours?
5. **Then**: Execute cleanup # we can actually clean up the infrastructure first as crucible.veylan.dev is not actually working

## What Stays

### For Kubernetes
- VPC and all networking
- Security groups (modified)
- IAM roles (adapted)
- ECR repositories
- Elastic IPs (attach to LB)
- Route53 zones

### Modified Terraform
```hcl
# Instead of EC2 instances
resource "aws_eks_cluster" "main" {
  # EKS configuration
}

# Instead of instance security groups  
resource "aws_security_group" "eks_nodes" {
  # Node security group
}
```

## Cost Savings

### Before (Docker Compose)
- 2x t2.micro EC2 instances: ~$20/month
- 2x Elastic IPs (attached): $0
- Total: ~$20/month

### After (Kubernetes)
- EKS Control Plane: $73/month
- 3x t3.medium nodes: ~$90/month # lets switch to 2 at first
- 1x Load Balancer: $25/month # do we have alternatives to this, must we use it? I'm not going full production
- Total: ~$188/month

**Note**: While K8s is more expensive, it provides:
- Better scaling
- Production-grade orchestration
- Industry-standard deployment
- Better isolation
- Easier management

## Checklist

- [ ] Backup any important data from EC2 instances
- [ ] Save docker-compose configurations to legacy/
- [ ] Update DNS to point to new K8s deployment
- [ ] Wait for DNS propagation
- [ ] Terminate blue/green EC2 instances
- [ ] Delete old Route53 A records
- [ ] Archive Docker Compose GitHub Actions
- [ ] Update documentation
- [ ] Clean up Terraform state
- [ ] Celebrate! 🎉