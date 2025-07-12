# K8s cluster with Auto Scaling Group for Cluster Autoscaler
# Starts with 1 t3.micro, can scale to 3

# Data source for Ubuntu AMI
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

# Auto Scaling Group for K8s nodes
resource "aws_autoscaling_group" "k8s_cluster" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  
  name                = "${var.project_name}-k8s-cluster"
  vpc_zone_identifier = var.subnet_ids
  
  min_size         = var.min_size
  max_size         = var.max_size
  desired_capacity = var.desired_capacity
  
  launch_template {
    id      = aws_launch_template.k8s_node[0].id
    version = "$Latest"
  }
  
  # Tags required for Cluster Autoscaler to find this ASG
  tag {
    key                 = "Name"
    value               = "${var.project_name}-k8s-node"
    propagate_at_launch = true
  }
  
  tag {
    key                 = "k8s.io/cluster-autoscaler/enabled"
    value               = "true"
    propagate_at_launch = true
  }
  
  tag {
    key                 = "k8s.io/cluster-autoscaler/${var.project_name}"
    value               = "owned"
    propagate_at_launch = true
  }
}

# Launch template for K8s nodes
resource "aws_launch_template" "k8s_node" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  
  name_prefix = "${var.project_name}-k8s-node-"
  
  image_id      = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.key_name
  
  vpc_security_group_ids = [aws_security_group.k8s_cluster[0].id]
  
  iam_instance_profile {
    name = aws_iam_instance_profile.k8s_cluster[0].name
  }
  
  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size = var.volume_size
      volume_type = "gp3"
      encrypted   = true
    }
  }
  
  # User data installs K3s
  user_data = base64encode(templatefile("${path.module}/userdata.sh", {
    cluster_name   = var.project_name
    ssh_public_key = var.ssh_public_key
  }))
  
  tag_specifications {
    resource_type = "instance"
    tags = merge(var.tags, {
      Name = "${var.project_name}-k8s-node"
      Type = "k8s-node"
    })
  }
}

# Security group for cluster
resource "aws_security_group" "k8s_cluster" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  
  name_prefix = "${var.project_name}-k8s-cluster-"
  description = "Security group for K8s cluster"
  vpc_id      = var.vpc_id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_ip]
  }

  # Kubernetes API
  ingress {
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # K3s cluster communication
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true  # Allow all traffic between nodes
  }

  # NodePort services
  ingress {
    from_port   = 30000
    to_port     = 32767
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-k8s-cluster-sg"
  })
}

# IAM role for nodes (with autoscaler permissions)
resource "aws_iam_role" "k8s_cluster" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  name  = "${var.project_name}-k8s-cluster-role"

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

# Policy for Cluster Autoscaler
resource "aws_iam_role_policy" "k8s_autoscaler" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  name  = "${var.project_name}-k8s-autoscaler"
  role  = aws_iam_role.k8s_cluster[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeTags",
          "autoscaling:SetDesiredCapacity",
          "autoscaling:TerminateInstanceInAutoScalingGroup",
          "ec2:DescribeLaunchTemplateVersions"
        ]
        Resource = "*"
      }
    ]
  })
}

# ECR access
resource "aws_iam_role_policy" "k8s_ecr" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  name  = "${var.project_name}-k8s-ecr"
  role  = aws_iam_role.k8s_cluster[0].id

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

resource "aws_iam_instance_profile" "k8s_cluster" {
  count = var.enable_cluster_autoscaler ? 1 : 0
  name  = "${var.project_name}-k8s-cluster-profile"
  role  = aws_iam_role.k8s_cluster[0].name
}

