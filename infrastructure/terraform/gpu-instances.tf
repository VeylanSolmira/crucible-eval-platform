# GPU Instances for Model Testing
# These are scaffolded but not created by default
# To enable: set gpu_instances_enabled = true in terraform.tfvars

variable "gpu_instances_enabled" {
  description = "Enable GPU instances for model testing"
  type        = bool
  default     = false
}

# Different GPU instance configurations for various model sizes
locals {
  gpu_instance_configs = {
    # For small models (1B-3B parameters)
    small_model = {
      instance_type = "g4dn.xlarge"  # T4 GPU, 16GB VRAM
      ami_type      = "AL2_x86_64_GPU"
      disk_size     = 100
      spot_enabled  = true
      description   = "For Llama 3.2-1B, Phi-3-mini, GPT-2"
    }
    
    # For medium models (7B parameters)
    medium_model = {
      instance_type = "g4dn.2xlarge"  # T4 GPU, 16GB VRAM, more CPU
      ami_type      = "AL2_x86_64_GPU"
      disk_size     = 200
      spot_enabled  = true
      description   = "For Mistral-7B, Llama-2-7B"
    }
    
    # For large models or multi-model testing
    large_model = {
      instance_type = "g5.2xlarge"  # A10G GPU, 24GB VRAM
      ami_type      = "AL2_x86_64_GPU"
      disk_size     = 500
      spot_enabled  = false  # More stable for long experiments
      description   = "For 13B models or multiple 7B models"
    }
    
    # Budget option using older generation
    budget_gpu = {
      instance_type = "g3s.xlarge"  # M60 GPU, 8GB VRAM
      ami_type      = "AL2_x86_64_GPU"
      disk_size     = 100
      spot_enabled  = true
      description   = "Budget option for basic testing"
    }
  }
}

# Security group for GPU instances
resource "aws_security_group" "gpu_instance" {
  count = var.gpu_instances_enabled ? 1 : 0
  
  name_prefix = "gpu-model-testing-"
  description = "Security group for GPU model testing instances"
  vpc_id      = aws_vpc.main.id

  # SSH access (restrict to your IP)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
    description = "SSH access"
  }
  
  # Jupyter/notebook access (if needed)
  ingress {
    from_port   = 8888
    to_port     = 8888
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
    description = "Jupyter notebook"
  }
  
  # Model serving API (if needed)
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Model API (VPC only)"
  }

  # Egress - allow model downloads
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow outbound for model downloads"
  }

  tags = {
    Name = "gpu-model-testing"
  }
}

# IAM role for GPU instances
resource "aws_iam_role" "gpu_instance" {
  count = var.gpu_instances_enabled ? 1 : 0
  
  name = "gpu-model-testing-role"

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

# Instance profile for GPU instances
resource "aws_iam_instance_profile" "gpu_instance" {
  count = var.gpu_instances_enabled ? 1 : 0
  
  name = "gpu-model-testing-profile"
  role = aws_iam_role.gpu_instance[0].name
}

# Policy for S3 model storage access
resource "aws_iam_role_policy" "gpu_s3_access" {
  count = var.gpu_instances_enabled ? 1 : 0
  
  name = "gpu-s3-model-access"
  role = aws_iam_role.gpu_instance[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.main.arn}",
          "${aws_s3_bucket.main.arn}/*"
        ]
      }
    ]
  })
}

# Launch template for GPU instances
resource "aws_launch_template" "gpu_instance" {
  for_each = var.gpu_instances_enabled ? local.gpu_instance_configs : {}
  
  name_prefix   = "gpu-${each.key}-"
  description   = each.value.description
  
  image_id      = data.aws_ami.gpu_optimized.id
  instance_type = each.value.instance_type
  
  iam_instance_profile {
    arn = aws_iam_instance_profile.gpu_instance[0].arn
  }
  
  vpc_security_group_ids = [aws_security_group.gpu_instance[0].id]
  
  # GPU-optimized EBS settings
  block_device_mappings {
    device_name = "/dev/xvda"
    
    ebs {
      volume_size           = each.value.disk_size
      volume_type           = "gp3"
      delete_on_termination = true
      encrypted            = true
    }
  }
  
  # User data to install Docker and NVIDIA container toolkit
  user_data = base64encode(templatefile("${path.module}/scripts/gpu-init.sh", {
    model_type = each.key
  }))
  
  tag_specifications {
    resource_type = "instance"
    
    tags = {
      Name        = "gpu-model-testing-${each.key}"
      ModelType   = each.key
      Environment = "testing"
    }
  }
}

# Spot instance requests (cost-optimized)
resource "aws_spot_instance_request" "gpu_instance" {
  for_each = { 
    for k, v in local.gpu_instance_configs : k => v 
    if var.gpu_instances_enabled && v.spot_enabled 
  }
  
  launch_template {
    id      = aws_launch_template.gpu_instance[each.key].id
    version = "$Latest"
  }
  
  spot_type            = "persistent"
  wait_for_fulfillment = true
  
  tags = {
    Name = "gpu-spot-${each.key}"
  }
}

# On-demand instances (for stable workloads)
resource "aws_instance" "gpu_instance" {
  for_each = { 
    for k, v in local.gpu_instance_configs : k => v 
    if var.gpu_instances_enabled && !v.spot_enabled 
  }
  
  launch_template {
    id      = aws_launch_template.gpu_instance[each.key].id
    version = "$Latest"
  }
  
  subnet_id = aws_subnet.private[0].id
  
  tags = {
    Name = "gpu-ondemand-${each.key}"
  }
}

# Data source for GPU-optimized AMI
data "aws_ami" "gpu_optimized" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["Deep Learning AMI GPU PyTorch * (Amazon Linux 2) *"]
  }
  
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Outputs for connection info
output "gpu_instance_connection_info" {
  value = var.gpu_instances_enabled ? {
    security_group_id = aws_security_group.gpu_instance[0].id
    launch_templates = {
      for k, v in aws_launch_template.gpu_instance : k => {
        id           = v.id
        instance_type = local.gpu_instance_configs[k].instance_type
        description  = local.gpu_instance_configs[k].description
      }
    }
    spot_instances = {
      for k, v in aws_spot_instance_request.gpu_instance : k => {
        id         = v.id
        public_ip  = v.public_ip
        private_ip = v.private_ip
      }
    }
  } : null
  
  description = "GPU instance connection information"
}

# Cost estimation outputs
output "gpu_instance_hourly_costs" {
  value = {
    small_model  = "$0.526/hour (on-demand) or ~$0.15-0.25/hour (spot)"
    medium_model = "$1.052/hour (on-demand) or ~$0.30-0.50/hour (spot)"
    large_model  = "$2.012/hour (on-demand)"
    budget_gpu   = "$0.225/hour (on-demand) or ~$0.07-0.15/hour (spot)"
  }
  
  description = "Estimated hourly costs for GPU instances"
}