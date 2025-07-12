# EC2 instance for running evaluation platform with gVisor

# AMI is now pinned via var.ubuntu_ami_id to prevent instance recreation
# Keeping this commented for reference when we want to find new AMIs
# data "aws_ami" "ubuntu" {
#   most_recent = true
#   owners      = ["099720109477"] # Canonical
# 
#   filter {
#     name   = "name"
#     values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
#   }
# 
#   filter {
#     name   = "virtualization-type"
#     values = ["hvm"]
#   }
# }

# Shared security group for common rules (always updates)
resource "aws_security_group" "eval_server_shared" {
  name        = "crucible-eval-server-shared-sg"
  description = "Shared security group for all Crucible evaluation servers"

  # HTTP access (for Let's Encrypt challenge and redirect to HTTPS)
  # Note: Port 80 needs to be open for Let's Encrypt HTTP-01 challenge
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Required for Let's Encrypt
    description = "HTTP for LetsEncrypt challenge only"
  }
  
  # HTTPS access (main web interface) - SECURE BY DEFAULT
  dynamic "ingress" {
    for_each = length(var.allowed_web_ips) > 0 ? [1] : []
    content {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = var.allowed_web_ips
      description = "HTTPS web interface (IP restricted)"
    }
  }

  # Platform web interface (for development/debugging)
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["127.0.0.1/32"]  # Only localhost (via SSH tunnel)
    description = "Platform API (SSH tunnel only)"
  }

  # Frontend dev server
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["127.0.0.1/32"]  # Only localhost (via SSH tunnel)
    description = "Frontend dev (SSH tunnel only)"
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name    = "crucible-eval-shared-sg"
    Purpose = "Shared security rules for all evaluation servers"
  })
}

# Color-specific security groups (for SSH access that needs per-environment control)
resource "aws_security_group" "eval_server_color" {
  for_each = toset(["blue", "green"])
  
  name        = "crucible-eval-server-${each.key}-sg"
  description = "Color-specific security group for ${each.key} evaluation server"

  # SSH access (restricted to your IP) - This is what we want to update per-color
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
    description = "SSH access for ${each.key}"
  }

  # Additional monitoring/debugging ports can be added per-color
  # Example: Open port 9090 only on green for testing
  
  tags = merge(local.common_tags, {
    Name             = "crucible-eval-${each.key}-sg"
    Purpose          = "Color-specific security rules"
    DeploymentColor  = each.key
  })
  
  # Note: Use deploy-green or deploy-blue aliases to target specific colors
}

# IAM role for EC2 instance (for S3 access)
resource "aws_iam_role" "eval_server" {
  name = "crucible-eval-server-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name    = "crucible-eval-server-role"
    Purpose = "IAM role for EC2 instances running evaluation platform"
  })
}

# IAM instance profile
resource "aws_iam_instance_profile" "eval_server" {
  name = "crucible-eval-server-profile"
  role = aws_iam_role.eval_server.name

  tags = merge(local.common_tags, {
    Name    = "crucible-eval-server-profile"
    Purpose = "Instance profile for EC2 instances to assume IAM role"
  })
}

# Policy for accessing S3 bucket (always needed for S3 deployment)
resource "aws_iam_role_policy" "eval_server_s3" {
  name = "crucible-eval-server-s3-policy"
  role = aws_iam_role.eval_server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.deployment.arn,
          "${aws_s3_bucket.deployment.arn}/*"
        ]
      }
    ]
  })
}

# Policy for SSM access (needed for remote commands)
resource "aws_iam_role_policy" "eval_server_ssm" {
  name = "crucible-eval-server-ssm-policy"
  role = aws_iam_role.eval_server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
          "ec2messages:AcknowledgeMessage",
          "ec2messages:DeleteMessage",
          "ec2messages:FailMessage",
          "ec2messages:GetEndpoint",
          "ec2messages:GetMessages",
          "ec2messages:SendReply"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/${var.project_name}/*"
      }
    ]
  })
}

# Policy for accessing ECR (for Docker image pulls)
resource "aws_iam_role_policy" "eval_server_ecr" {
  name = "crucible-eval-server-ecr-policy"
  role = aws_iam_role.eval_server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeRepositories"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach AWS managed policy for SSM
resource "aws_iam_role_policy_attachment" "ssm_managed_instance_core" {
  role       = aws_iam_role.eval_server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Attach AWS managed policy for CloudWatch Agent
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_server_policy" {
  role       = aws_iam_role.eval_server.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Key pair for SSH access
resource "aws_key_pair" "eval_server_key" {
  key_name   = "crucible-eval-key"
  public_key = var.ssh_public_key

  tags = merge(local.common_tags, {
    Name    = "crucible-eval-key"
    Purpose = "SSH key pair for accessing evaluation servers"
  })
}

# EC2 instances with for_each for blue-green deployment
resource "aws_instance" "eval_server" {
  for_each = toset(["blue", "green"])  # Always create both
  
  ami                    = var.ubuntu_ami_id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.eval_server.name
  
  key_name               = aws_key_pair.eval_server_key.key_name
  vpc_security_group_ids = [
    aws_security_group.eval_server_shared.id,
    aws_security_group.eval_server_color[each.key].id
  ]

  # Increase root volume to have space for Docker images
  root_block_device {
    volume_size = 30 # GB, free tier includes 30GB
    volume_type = "gp3"
    encrypted   = true
  }

  # User data script to install dependencies and setup systemd service
  user_data = templatefile("${path.module}/templates/userdata-compose.sh.tpl", {
    # Variables from old S3/GitHub deployment - kept for reference
    # github_repo       = var.github_repo
    # github_branch     = var.github_branch
    # deployment_bucket = aws_s3_bucket.deployment.id
    # deployment_key    = var.deployment_key
    
    # Active variables used in template
    ecr_repository_url = aws_ecr_repository.crucible_platform.repository_url
    project_name      = var.project_name
    compose_service_content = file("${path.module}/../systemd/crucible-compose.service")
    deployment_color  = each.key
    
    # SSL refresh automation scripts
    ssl_refresh_script  = file("${path.module}/templates/refresh-ssl-certs.sh")
    ssl_refresh_service = file("${path.module}/../systemd/ssl-refresh.service")
    ssl_refresh_timer   = file("${path.module}/../systemd/ssl-refresh.timer")
    
    # Domain configuration
    domain_name = var.domain_name
  })
  
  # Replace instance when user data changes (ensures updates are applied)
  user_data_replace_on_change = true

  tags = merge(local.common_tags, {
    Name             = "${var.project_name}-eval-server-${each.key}"
    Purpose          = "AI evaluation with gVisor and Docker isolation"
    DeploymentColor  = each.key
    DeploymentVersion = var.deployment_version
  })

  # Note: Use deploy-green or deploy-blue aliases to target specific colors
  # Both instances are always created but updates can be targeted
  
  # Ensure SSL certificates exist before creating instance
  # This prevents the instance from failing during userdata execution
  depends_on = [
    aws_ssm_parameter.ssl_certificate,
    aws_ssm_parameter.ssl_private_key,
    aws_ssm_parameter.ssl_issuer_pem
  ]
}

# Outputs (moved most outputs to route53.tf for Elastic IPs)
output "instance_ids" {
  value = { for k, v in aws_instance.eval_server : k => v.id }
  description = "EC2 instance IDs by deployment color"
}

output "ssh_commands_elastic" {
  value = { for k, v in aws_eip.eval_server : k => "ssh ubuntu@${v.public_ip}" }
  description = "SSH commands using Elastic IPs"
}

output "ssh_tunnel_commands_elastic" {
  value = { for k, v in aws_eip.eval_server : k => "ssh -L 8080:localhost:8080 -L 3000:localhost:3000 ubuntu@${v.public_ip}" }
  description = "SSH tunnel commands using Elastic IPs"
}

output "platform_url_local" {
  value = "http://localhost:8080"
  description = "URL to access the platform through SSH tunnel"
}

output "platform_url_public" {
  value = var.domain_name != "" ? "https://${var.domain_name}" : "Configure domain_name variable"
  description = "Public URL for the platform (once DNS is configured)"
}