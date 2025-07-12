# Get latest Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Get available AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC for our cluster (optional)
resource "aws_vpc" "k8s_vpc" {
  count = var.create_vpc ? 1 : 0
  
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-vpc"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "k8s_igw" {
  count = var.create_vpc ? 1 : 0
  
  vpc_id = aws_vpc.k8s_vpc[0].id

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-igw"
  })
}

# Public Subnet
resource "aws_subnet" "k8s_public" {
  count = var.create_vpc ? 1 : 0
  
  vpc_id                  = aws_vpc.k8s_vpc[0].id
  cidr_block              = var.subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-public"
  })
}

# Route Table
resource "aws_route_table" "k8s_public" {
  count = var.create_vpc ? 1 : 0
  
  vpc_id = aws_vpc.k8s_vpc[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.k8s_igw[0].id
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-public-rt"
  })
}

resource "aws_route_table_association" "k8s_public" {
  count = var.create_vpc ? 1 : 0
  
  subnet_id      = aws_subnet.k8s_public[0].id
  route_table_id = aws_route_table.k8s_public[0].id
}

# Security Group
resource "aws_security_group" "k8s_node" {
  name_prefix = "${var.cluster_name}-node-"
  description = "Security group for K8s node"
  vpc_id      = var.create_vpc ? aws_vpc.k8s_vpc[0].id : var.vpc_id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  # Kubernetes API
  ingress {
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = [var.allowed_api_cidr]
  }

  # NodePort Services (for testing)
  ingress {
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-node-sg"
  })
}

# Key Pair
resource "aws_key_pair" "k8s_key" {
  key_name   = "${var.cluster_name}-key"
  public_key = var.ssh_public_key
}

# IAM role for K8s node
resource "aws_iam_role" "k8s_node" {
  name = "${var.cluster_name}-k8s-node-role"

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

# ECR access policy
resource "aws_iam_role_policy" "k8s_ecr" {
  name = "${var.cluster_name}-k8s-ecr"
  role = aws_iam_role.k8s_node.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ]
      Resource = "*"
    }]
  })
}

# Instance profile
resource "aws_iam_instance_profile" "k8s_node" {
  name = "${var.cluster_name}-k8s-node-profile"
  role = aws_iam_role.k8s_node.name
}

# Single K8s instance
resource "aws_instance" "k8s_node" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  
  subnet_id                   = var.create_vpc ? aws_subnet.k8s_public[0].id : var.subnet_id
  vpc_security_group_ids      = [aws_security_group.k8s_node.id]
  key_name                    = aws_key_pair.k8s_key.key_name
  associate_public_ip_address = true
  
  iam_instance_profile = aws_iam_instance_profile.k8s_node.name

  root_block_device {
    volume_size = var.volume_size
    volume_type = var.volume_type
  }

  user_data = templatefile("${path.module}/userdata.sh", {
    cluster_name   = var.cluster_name
    ssh_public_key = var.ssh_public_key
  })

  tags = merge(var.tags, {
    Name = "${var.cluster_name}-node"
    Role = "k8s-single-node"
  })
}

