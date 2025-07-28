# NAT Instance Configuration (Cost-effective alternative to NAT Gateway)
# t3.nano costs ~$3.80/month vs NAT Gateway at $45/month
# Trade-offs: Single point of failure, limited bandwidth (~5 Gbps), requires management

# Variable to enable NAT instance
variable "use_nat_instance" {
  description = "Use NAT instance instead of NAT Gateway (cost savings)"
  type        = bool
  default     = true
}

# Get Amazon Linux 2 AMI optimized for NAT
data "aws_ami" "nat_instance" {
  count       = var.use_nat_instance ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-kernel-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for NAT instance
resource "aws_security_group" "nat_instance" {
  count       = var.use_nat_instance ? 1 : 0
  name_prefix = "${var.project_name}-nat-instance-"
  description = "Security group for NAT instance"
  vpc_id      = aws_vpc.main.id

  # Allow all traffic from private subnets
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = [
      aws_subnet.private[0].cidr_block,
      aws_subnet.private[1].cidr_block
    ]
    description = "All traffic from private subnets"
  }

  # SSH access for management
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
    description = "SSH for NAT instance management"
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-instance-sg"
  })
}

# NAT Instance
resource "aws_instance" "nat_instance" {
  count                  = var.use_nat_instance ? 1 : 0
  ami                    = data.aws_ami.nat_instance[0].id
  instance_type          = "t3.nano" # Cheapest instance type
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.nat_instance[0].id]
  source_dest_check      = false # IMPORTANT: Must be disabled for NAT

  # Use existing SSH key
  key_name = aws_key_pair.eval_server_key.key_name

  # Enable monitoring for network metrics
  monitoring = true

  user_data = <<-EOF
    #!/bin/bash
    # Enable IP forwarding
    echo "net.ipv4.ip_forward = 1" >> /etc/sysctl.conf
    sysctl -p
    
    # Configure iptables for NAT
    /sbin/iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    /sbin/iptables -F FORWARD
    
    # Save iptables rules
    service iptables save
    
    # Install updates
    yum update -y
    
    # Install CloudWatch agent for monitoring
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
    rpm -U ./amazon-cloudwatch-agent.rpm
  EOF

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-instance"
    Type = "nat-instance"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP for NAT instance
resource "aws_eip" "nat_instance" {
  count    = var.use_nat_instance ? 1 : 0
  instance = aws_instance.nat_instance[0].id
  domain   = "vpc"

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-nat-instance-eip"
  })
}

# Update private route tables to use NAT instance
# NOTE: You need to update vpc.tf to uncomment the dynamic route block

# Outputs
output "nat_instance_public_ip" {
  value       = var.use_nat_instance ? aws_eip.nat_instance[0].public_ip : null
  description = "Public IP of NAT instance"
}

output "nat_instance_cost_savings" {
  value = var.use_nat_instance ? "Using NAT instance (t3.nano) saves ~$41/month compared to NAT Gateway" : "NAT instance disabled"
}

# Security considerations for NAT instance vs NAT Gateway:
# 
# NAT Gateway (AWS Managed):
# ✓ No SSH access needed - fully managed
# ✓ Automatic patching and updates
# ✓ Built-in redundancy within AZ
# ✓ No single point of failure (with multiple gateways)
# ✓ Scales automatically to 45 Gbps
# ✓ No security group management needed
# 
# NAT Instance (Self-managed):
# ✓ Can be as secure with proper configuration
# ✓ Full control over the instance
# ✓ Can add additional security tools (IDS/IPS)
# ✓ Can use hardened AMIs
# ✗ Requires manual patching
# ✗ Single point of failure (unless you set up HA)
# ✗ Limited bandwidth by instance type
# ✗ Requires security group management
# 
# Security best practices for NAT instance:
# 1. Use Systems Manager for patching (no SSH needed)
# 2. Enable CloudWatch monitoring for anomalies
# 3. Use IMDSv2 only (add to user data)
# 4. Regular AMI updates
# 5. Consider using AWS NAT Instance AMI (pre-configured)
# 6. Implement CloudWatch alarms for instance health