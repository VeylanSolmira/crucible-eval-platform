# Architectural Decision: NAT Instance vs NAT Gateway

## Decision Summary
We chose to use a NAT Instance (t3.nano) instead of AWS NAT Gateway for our private subnet internet access, accepting brief downtime during updates in exchange for ~91% cost savings ($3.80/month vs $45/month).

## Context
Our Kubernetes pods in private subnets require internet access for:
- Pulling container images from public registries
- Downloading package dependencies
- Accessing external APIs
- Fetching security updates

## Options Considered

### Option 1: AWS NAT Gateway (Managed Service)
**Pros:**
- Zero downtime with built-in redundancy
- Automatic scaling up to 45 Gbps
- No maintenance required
- Automatic security patching
- Built-in monitoring and CloudWatch metrics

**Cons:**
- Cost: ~$45/month (plus data transfer charges)
- No customization options
- Cannot add additional security tools

### Option 2: NAT Instance (Self-Managed)
**Pros:**
- Cost: ~$3.80/month for t3.nano (91% savings)
- Full control over the instance
- Can add security tools (IDS/IPS)
- Can use custom AMIs

**Cons:**
- Single point of failure
- Limited bandwidth (up to 5 Gbps)
- Requires manual patching
- Brief downtime during updates

## Current Implementation

### Simple Approach (Currently Implemented)
```hcl
# Elastic IP persists across replacements
resource "aws_eip" "nat_instance" {
  lifecycle {
    create_before_destroy = true
  }
}

# Instance with create_before_destroy
resource "aws_instance" "nat_instance" {
  lifecycle {
    create_before_destroy = true
  }
}
```

**Downtime:** ~10-30 seconds during EIP reassociation

### Limitations
1. **Brief Network Interruption**: During instance replacement, there's a 10-30 second window where the EIP is being reassociated
2. **No Health Checks**: If the NAT instance fails, manual intervention required
3. **No Automatic Failover**: Single instance with no redundancy

## Future Enhancement: Zero-Downtime Solution

### Proposed Architecture
1. **Dual NAT Instances**: Primary and standby in different AZs
2. **Health Check Lambda**: Monitors instance health every 30 seconds
3. **Automatic Failover**: Lambda updates route tables on failure
4. **Rolling Updates**: Update standby first, then failover

### Implementation Complexity
- Additional Lambda function for health checks
- More complex terraform configuration
- Cross-AZ traffic costs
- Requires careful orchestration

## Decision Justification

### Why NAT Instance?
1. **Cost Optimization**: 91% savings is significant for a demonstration platform
2. **Learning Opportunity**: Shows understanding of AWS networking fundamentals
3. **Acceptable Trade-offs**: Brief downtime acceptable for non-production workload

### Why Not Zero-Downtime Yet?
1. **Complexity vs Benefit**: The additional complexity isn't justified for our use case
2. **Development Time**: Focus on core platform features first
3. **Demonstration Value**: Current implementation already shows key concepts

## Interview Talking Points

1. **Cost-Conscious Engineering**: "I evaluated both options and chose NAT instance for 91% cost savings, accepting brief downtime as a reasonable trade-off for a development environment."

2. **Understanding Trade-offs**: "While NAT Gateway provides zero downtime, our workload can tolerate 30-second interruptions during maintenance windows."

3. **Upgrade Path**: "I've designed the infrastructure to easily switch to NAT Gateway by changing a single variable, showing forward-thinking design."

4. **Production Considerations**: "In production, I would implement either NAT Gateway or the dual-instance solution with health checks, depending on SLA requirements."

## Monitoring and Mitigation

### Current Mitigations
1. **Maintenance Windows**: Schedule updates during low-usage periods
2. **Connection Retry Logic**: Applications should implement exponential backoff
3. **CloudWatch Alarms**: Alert on instance failures

### Metrics to Track
- Instance CPU/Memory utilization
- Network throughput
- Failed connection count
- Uptime percentage

## Related Decisions
- [EKS Networking Architecture](./eks-networking.md)
- [Cost Optimization Strategies](./cost-optimization.md)
- [High Availability Design](./high-availability.md)

## References
- [AWS NAT Instance Documentation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_NAT_Instance.html)
- [NAT Gateway vs NAT Instance Comparison](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-comparison.html)
- [High Availability NAT Instance Design](https://aws.amazon.com/articles/high-availability-for-amazon-vpc-nat-instances/)