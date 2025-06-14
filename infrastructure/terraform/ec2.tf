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

  tags = {
    Name = "crucible-eval-sg"
  }
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
}

# IAM instance profile
resource "aws_iam_instance_profile" "eval_server" {
  name = "crucible-eval-server-profile"
  role = aws_iam_role.eval_server.name
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

# Key pair for SSH access
resource "aws_key_pair" "eval_server_key" {
  key_name   = "crucible-eval-key"
  public_key = var.ssh_public_key
}

# EC2 instance
resource "aws_instance" "eval_server" {
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
  user_data = templatefile("${path.module}/templates/userdata.sh.tpl", {
    github_repo       = var.github_repo
    github_branch     = var.github_branch
    deployment_bucket = aws_s3_bucket.deployment.id
    deployment_key    = var.deployment_key
  })

  tags = {
    Name = "crucible-eval-server"
    Purpose = "AI evaluation with gVisor"
  }
}

# Outputs
output "eval_server_public_ip" {
  value = aws_instance.eval_server.public_ip
  description = "Public IP of the evaluation server"
}

output "eval_server_public_dns" {
  value = aws_instance.eval_server.public_dns
  description = "Public DNS of the evaluation server"
}

output "ssh_command" {
  value = "ssh ubuntu@${aws_instance.eval_server.public_ip}"
  description = "SSH command to connect to the server"
}

output "ssh_tunnel_command" {
  value = "ssh -L 8080:localhost:8080 -L 9090:localhost:9090 ubuntu@${aws_instance.eval_server.public_ip}"
  description = "SSH tunnel command for local access"
}

output "platform_url_local" {
  value = "http://localhost:8080"
  description = "URL to access the platform through SSH tunnel"
}