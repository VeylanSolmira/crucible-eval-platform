# Blue-Green Deployment Strategy

## Overview

This platform uses a blue-green deployment strategy for zero-downtime deployments and easy rollbacks.

## DNS Structure

```
crucible.veylan.dev         → Production (points to active environment)
├── blue.crucible.veylan.dev  → Blue environment (stable/current)
└── green.crucible.veylan.dev → Green environment (new deployments)
```

## Deployment Flow

1. **Current State**: 
   - `crucible.veylan.dev` → Blue (live traffic)
   - `blue.crucible.veylan.dev` → Blue environment
   - `green.crucible.veylan.dev` → Green environment

2. **Deploy New Version**:
   - Deploy to green environment
   - Test at `green.crucible.veylan.dev`
   - Verify all functionality

3. **Switch Traffic**:
   - Update `crucible.veylan.dev` to point to Green
   - Monitor for issues
   - Blue remains available for rollback

4. **Next Deployment**:
   - Blue becomes the new staging environment
   - Deploy next version to Blue
   - Repeat the cycle

## Benefits

- **Zero Downtime**: DNS switch is instantaneous
- **Easy Rollback**: Previous version always available
- **Safe Testing**: Test on actual infrastructure before switching
- **Clear Separation**: Always know which environment is live

## Implementation Details

### Terraform Configuration

The infrastructure creates:
- Two EC2 instances (blue and green)
- Two Elastic IPs (one per instance)
- Route53 records for each subdomain
- Main domain points to active deployment

### Switching Environments

To switch from blue to green:
```bash
cd infrastructure/terraform
terraform apply -var="active_deployment_color=green"
```

To roll back to blue:
```bash
terraform apply -var="active_deployment_color=blue"
```

### SSL Certificates

With the wildcard certificate for `*.veylan.dev`, all subdomains are covered:
- `crucible.veylan.dev` ✓
- `blue.crucible.veylan.dev` ✓
- `green.crucible.veylan.dev` ✓

## Deployment Commands

### Deploy to Green
```bash
# From GitHub Actions or locally
./scripts/deploy.sh green
```

### Deploy to Blue
```bash
./scripts/deploy.sh blue
```

### Check Environment Status
```bash
# Check green
curl https://green.crucible.veylan.dev/api/status

# Check blue
curl https://blue.crucible.veylan.dev/api/status

# Check production
curl https://crucible.veylan.dev/api/status
```

## Cost Considerations

- Route53 Hosted Zone: $0.50/month
- DNS Queries: ~$0.40 per million queries
- Additional A Records: Minimal cost (covered in base pricing)
- Total estimated cost: <$1/month for DNS

## Future Enhancements

1. **Automated Health Checks**: Route53 can automatically failover if health checks fail
2. **Weighted Routing**: Gradually shift traffic (10% → 50% → 100%)
3. **Geo-Routing**: Different regions can use different deployments
4. **Automated Switching**: CI/CD can automatically promote green to production after tests pass