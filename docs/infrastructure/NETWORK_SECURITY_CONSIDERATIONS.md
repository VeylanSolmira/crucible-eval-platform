# Network Security Considerations

## Current Architecture (Development)

The EC2 instance is currently in the default VPC's public subnet with:
- Public IP for direct access
- Security group restricting SSH to specific IP
- This is acceptable for development but not production

## Production Architecture (Recommended)

For production deployment of an AI evaluation platform, we should use:

### 1. Private Subnet Isolation
```
┌─────────────────────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                │
├─────────────────────────┬───────────────────────────┤
│   Public Subnet         │   Private Subnet          │
│   (10.0.1.0/24)        │   (10.0.2.0/24)          │
│                         │                           │
│   ┌─────────────┐      │   ┌──────────────────┐   │
│   │   NAT       │      │   │ Evaluation       │   │
│   │   Gateway   │◄─────┼───│ Server           │   │
│   └─────────────┘      │   └──────────────────┘   │
│                         │                           │
│   ┌─────────────┐      │   ┌──────────────────┐   │
│   │   ALB       │◄─────┼───│ Worker Nodes     │   │
│   └─────────────┘      │   └──────────────────┘   │
└─────────────────────────┴───────────────────────────┘
```

### 2. Access Methods

#### Option A: AWS Systems Manager Session Manager
```bash
# No SSH needed! Access via AWS CLI:
aws ssm start-session --target i-1234567890abcdef0

# Or through AWS Console
```

**Benefits:**
- No open SSH ports
- Full audit logging
- IAM-based access control
- Works with private subnets

#### Option B: Bastion Host
```bash
# Traditional SSH jump host
ssh -J ubuntu@bastion ubuntu@private-instance
```

**Benefits:**
- Familiar SSH workflow
- Can be hardened with fail2ban, etc.
- Supports SCP/SFTP easily

### 3. Why This Matters for AI Safety

**Private subnet isolation is critical for AI evaluation because:**

1. **Defense in Depth**: Even if an AI escapes its container, it can't directly access the internet
2. **Egress Control**: NAT Gateway allows monitoring/blocking of outbound connections
3. **Audit Trail**: All access is logged and traceable
4. **Compliance**: Meets security standards for handling sensitive AI models

### 4. Implementation Plan

To upgrade to private subnet architecture:

```hcl
# 1. Create VPC with public/private subnets
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

# 2. Add NAT Gateway for outbound access
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id
}

# 3. Configure Session Manager
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
```

### 5. Trade-offs

**Development Speed vs Security:**
- Public subnet: Faster iteration, direct access
- Private subnet: More secure, requires additional setup

**For this MVP:**
- Current public subnet setup is acceptable with IP restrictions
- Document the upgrade path to show security awareness
- Implement if time permits (Day 4-5)

### 6. Interview Talking Points

When discussing with METR:

1. **"I started with public subnet for speed but know private is required for production"**
2. **"Session Manager eliminates SSH keys and provides better audit trail"**
3. **"Private subnets add defense-in-depth against AI escape attempts"**
4. **"NAT Gateway allows controlled egress with CloudWatch monitoring"**

This shows you understand:
- Security best practices
- Trade-offs in system design
- Progressive enhancement approach
- Production vs development needs