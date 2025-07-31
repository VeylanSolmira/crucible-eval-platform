# Zero-Downtime NAT Instance Implementation

## Overview
Enhance the current NAT instance implementation to achieve zero downtime during updates by implementing a dual-instance solution with health checks and automatic failover.

## Justification
While our current implementation with `create_before_destroy` lifecycle provides reasonable uptime (30-second interruption), a zero-downtime solution would demonstrate advanced AWS networking skills and high-availability design patterns valuable for METR infrastructure.

## Current State
- Single NAT instance with Elastic IP
- ~30 second downtime during instance replacement
- Manual intervention required for failures
- Cost: ~$3.80/month

## Target State
- Dual NAT instances (primary/standby)
- Automatic health checks every 30 seconds
- Zero-downtime failover
- Automated rolling updates
- Cost: ~$7.60/month (still 83% cheaper than NAT Gateway)

## Implementation Tasks

### Phase 1: Infrastructure Setup
- [ ] Create standby NAT instance in different AZ
- [ ] Set up secondary Elastic IP
- [ ] Configure route table update mechanism
- [ ] Document failover procedures

### Phase 2: Health Check System
- [ ] Create Lambda function for health checks
- [ ] Implement TCP/HTTP health probes
- [ ] Add CloudWatch metrics for tracking
- [ ] Set up SNS notifications for failures

### Phase 3: Failover Logic
- [ ] Implement route table update logic
- [ ] Add connection draining logic
- [ ] Test failover scenarios
- [ ] Document recovery procedures

### Phase 4: Rolling Update System
- [ ] Create update orchestration logic
- [ ] Implement pre-update health verification
- [ ] Add rollback capabilities
- [ ] Create runbook for updates

## Technical Design

### Architecture Components
1. **Primary NAT Instance** (AZ-1)
   - Active route table entry
   - Handles all traffic normally

2. **Standby NAT Instance** (AZ-2)
   - Pre-warmed and configured
   - Ready for immediate failover

3. **Health Check Lambda**
   - Runs every 30 seconds
   - Checks both instances
   - Updates route tables on failure

4. **CloudWatch Alarms**
   - Instance health metrics
   - Failover event tracking
   - Performance monitoring

### Failover Process
1. Health check detects primary failure
2. Lambda updates route tables to standby
3. SNS notification sent to operators
4. Connection states maintained via conntrack

## Testing Strategy
- [ ] Simulate instance failure
- [ ] Test during peak traffic
- [ ] Verify connection persistence
- [ ] Measure failover time

## Documentation Updates
- [ ] Update [NAT Instance Architecture](../../docs/architectural-decisions/nat-instance-vs-nat-gateway.md)
- [ ] Create operations runbook
- [ ] Add monitoring dashboards
- [ ] Document rollback procedures

## Success Metrics
- Failover time < 5 seconds
- Zero dropped connections
- 99.9% uptime over 30 days
- Successful automated updates

## Interview Value
This enhancement demonstrates:
- High-availability design skills
- Cost-conscious engineering
- AWS Lambda and automation expertise
- Understanding of network architecture
- Production-ready thinking

## Alternative Consideration
If time is limited, consider implementing AWS NAT Gateway for truly zero-downtime operation, though at higher cost. The current solution with brief downtime may be sufficient for demonstration purposes.

## References
- [AWS High Availability NAT](https://aws.amazon.com/articles/high-availability-for-amazon-vpc-nat-instances/)
- [Lambda VPC Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html)
- [Route Table Updates via Lambda](https://aws.amazon.com/blogs/networking-and-content-delivery/vpc-route-table-updates-using-lambda/)