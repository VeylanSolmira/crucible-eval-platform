# EC2 instance for running evaluation platform with gVisor

# Use data source to get latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for evaluation server
resource "aws_security_group" "eval_server" {
  name        = "crucible-eval-server-sg"
  description = "Security group for Crucible evaluation server"

  # SSH access (restricted to your IP)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
  }

  # Platform web interface (restricted for SSH tunneling)
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]  # Changed from 0.0.0.0/0 for security
  }

  # Future: HTTP/HTTPS for public access (currently commented out)
  # Uncomment these when ready to expose publicly
  # ingress {
  #   from_port   = 80
  #   to_port     = 80
  #   protocol    = "tcp"
  #   cidr_blocks = ["0.0.0.0/0"]
  # }
  # 
  # ingress {
  #   from_port   = 443
  #   to_port     = 443
  #   protocol    = "tcp"
  #   cidr_blocks = ["0.0.0.0/0"]
  # }

  # Additional port for monitoring tools (Prometheus, etc.)
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name    = "crucible-eval-sg"
    Purpose = "Security group for evaluation server SSH and internal access"
  })
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
          "ecr:BatchGetImage"
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
  for_each = var.enabled_deployment_colors
  
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.eval_server.name
  
  key_name               = aws_key_pair.eval_server_key.key_name
  vpc_security_group_ids = [aws_security_group.eval_server.id]

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
  })

  tags = merge(local.common_tags, {
    Name             = "${var.project_name}-eval-server-${each.key}"
    Purpose          = "AI evaluation with gVisor and Docker isolation"
    DeploymentColor  = each.key
    DeploymentVersion = var.deployment_version
  })

  # Force recreation when user_data changes
  user_data_replace_on_change = true
}

# Outputs
output "eval_server_public_ips" {
  value = { for k, v in aws_instance.eval_server : k => v.public_ip }
  description = "Public IP addresses of the evaluation servers by color"
}

output "eval_server_public_dns" {
  value = { for k, v in aws_instance.eval_server : k => v.public_dns }
  description = "Public DNS of the evaluation servers by color"
}

output "ssh_commands" {
  value = { for k, v in aws_instance.eval_server : k => "ssh ubuntu@${v.public_ip}" }
  description = "SSH commands to connect to each server"
}

output "ssh_tunnel_commands" {
  value = { for k, v in aws_instance.eval_server : k => "ssh -L 8080:localhost:8080 -L 3000:localhost:3000 ubuntu@${v.public_ip}" }
  description = "SSH tunnel commands for local access to each server"
}

output "platform_url_local" {
  value = "http://localhost:8080"
  description = "URL to access the platform through SSH tunnel"
}