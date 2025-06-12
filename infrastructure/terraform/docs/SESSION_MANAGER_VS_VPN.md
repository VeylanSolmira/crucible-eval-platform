# Session Manager vs VPN: Security Comparison for AI Evaluation

## Overview

When accessing EC2 instances in private subnets, two primary approaches exist: AWS Systems Manager Session Manager and VPN. This document compares their security properties specifically for AI safety evaluation platforms.

## AWS Systems Manager Session Manager

### Security Strengths
- **No open ports** - Zero network attack surface
- **IAM-based access** - Fine-grained permissions
- **Full audit logging** - Every command logged to CloudTrail/S3
- **Temporary credentials** - Sessions expire automatically
- **No SSH keys** - Can't be stolen or misused
- **MFA enforced** - Through IAM policies

### Security Limitations
- **AWS-dependent** - If AWS account compromised, game over
- **Limited protocol support** - Only shell/RDP, no arbitrary TCP
- **AWS-specific** - Vendor lock-in

### Access Flow
```
You → AWS API (HTTPS) → Session Manager Agent → Instance
- Attack surface: AWS API only
- Audit: Every keystroke logged
```

## VPN (e.g., AWS Client VPN, WireGuard)

### Security Strengths
- **End-to-end encryption** - All traffic encrypted
- **Protocol flexibility** - Any TCP/UDP traffic works
- **Network-level access** - Can access multiple resources
- **Multi-cloud/hybrid** - Works across providers
- **Client certificates** - Additional authentication layer

### Security Limitations
- **Network exposure** - Once on VPN, broader access
- **Key management** - Certificates/keys can be compromised
- **Open port** - VPN endpoint is internet-facing
- **Client complexity** - Users need VPN client setup

### Access Flow
```
You → VPN Endpoint → Private Network → Instance
- Attack surface: VPN endpoint + network
- Audit: Connection logs, not commands
```

## When Each is "More Secure"

### Session Manager is more secure when:
- You want zero network attack surface
- You need detailed audit trails
- You're already using AWS
- You only need shell/console access

### VPN is more secure when:
- You need to access non-AWS resources
- You want network isolation from AWS
- You need full protocol support
- You want defense against AWS account compromise

## For AI Safety Evaluation Platforms

### Why Session Manager is Recommended

1. **Complete audit trail** - See exactly what the AI tried to do
2. **No network paths** - AI can't probe VPN infrastructure
3. **Instant revocation** - Disable IAM role immediately
4. **AWS-native** - Integrates with other security tools
5. **Simpler implementation** - No additional infrastructure needed

### Implementation Architecture

```
┌─────────────────────────────────────────────────────┐
│                    VPC (10.0.0.0/16)                │
├─────────────────────────┬───────────────────────────┤
│   Public Subnet         │   Private Subnet          │
│   (10.0.1.0/24)        │   (10.0.2.0/24)          │
│                         │                           │
│   ┌─────────────┐      │   ┌──────────────────┐   │
│   │   NAT       │      │   │ EC2 Instance     │   │
│   │   Gateway   │◄─────┼───│ + SSM Agent      │   │
│   └─────────────┘      │   │ + IAM Role       │   │
│          ▲              │   └──────────────────┘   │
│          │              │            ▲              │
└──────────┼──────────────┴────────────┼──────────────┘
           │                           │
           │                           │ Session Manager
     Internet Access                   │ (via AWS API)
     (Outbound Only)                   │
                                       You
```

### Required Components

1. **EC2 Instance in Private Subnet**
   - No public IP
   - Security group allows no inbound (not even SSH)
   - IAM role attached

2. **IAM Role with SSM Policy**
   ```hcl
   resource "aws_iam_role" "ec2_role" {
     name = "crucible-ec2-role"
     
     assume_role_policy = jsonencode({
       Version = "2012-10-17"
       Statement = [{
         Action = "sts:AssumeRole"
         Effect = "Allow"
         Principal = {
           Service = "ec2.amazonaws.com"
         }
       }]
     })
   }
   
   resource "aws_iam_role_policy_attachment" "ssm" {
     role       = aws_iam_role.ec2_role.name
     policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
   }
   
   resource "aws_iam_instance_profile" "ec2_profile" {
     name = "crucible-ec2-profile"
     role = aws_iam_role.ec2_role.name
   }
   ```

3. **NAT Gateway for Outbound** (optional)
   - Only if instance needs internet access
   - Can be omitted for maximum isolation

### Access Commands

```bash
# List available instances
aws ssm describe-instance-information

# Connect to instance
aws ssm start-session --target i-1234567890abcdef0

# Transfer files
aws s3 cp file.txt s3://bucket/
aws ssm start-session --target i-1234567890abcdef0
aws s3 cp s3://bucket/file.txt .
```

## Security Benefits for AI Evaluation

1. **Audit Everything**: Every command the AI tries is logged
2. **No Network Attack Surface**: AI can't scan for open ports
3. **IAM-Based Access**: Granular permissions per user/role
4. **Break Glass Access**: Emergency access without SSH keys
5. **Compliance Ready**: Meets most regulatory requirements

## Conclusion

For AI safety evaluation platforms, Session Manager provides superior security through:
- Zero network attack surface
- Complete audit trails
- Native AWS integration
- Simpler implementation

VPN remains valuable for:
- Multi-cloud environments
- Full protocol support needs
- Network-level resource access

For METR's use case, Session Manager in a private subnet represents the optimal balance of security, auditability, and operational simplicity.