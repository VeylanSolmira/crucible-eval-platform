# Minimal EKS Cluster Configuration
# Phase 1: Learning Kubernetes with EKS
# Cost: ~$103/month (Control Plane + 2 small nodes)

# EKS Cluster IAM Role
resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-eks-cluster-role"
    Purpose = "IAM role for EKS cluster"
  })
}

# Attach required policies to cluster role
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks_cluster.name
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = var.project_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.28" # Latest stable version

  vpc_config {
    # Use existing subnets from your VPC
    subnet_ids = concat(
      [for s in aws_subnet.private : s.id],
      [for s in aws_subnet.public : s.id]
    )

    # Security settings
    endpoint_private_access = true
    endpoint_public_access  = true
    # Restrict to your IP for security
    public_access_cidrs = length(var.allowed_web_ips) > 0 ? var.allowed_web_ips : ["0.0.0.0/0"]
  }

  # Enable logging for debugging
  enabled_cluster_log_types = ["api", "audit", "authenticator"]

  tags = merge(local.common_tags, {
    Name      = "${var.project_name}-eks-cluster"
    Phase     = "learning"
    ManagedBy = "terraform"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller,
  ]
}

# IAM role for EKS nodes
resource "aws_iam_role" "eks_nodes" {
  name = "${var.project_name}-eks-node-role"

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

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-eks-node-role"
    Purpose = "IAM role for EKS worker nodes"
  })
}

# Attach required policies to node role
resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_nodes.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_nodes.name
}

# Add ECR access for your repositories
resource "aws_iam_role_policy" "eks_ecr_access" {
  name = "${var.project_name}-eks-ecr-policy"
  role = aws_iam_role.eks_nodes.id

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

# EKS Node Group (minimal for learning)
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-workers"
  node_role_arn   = aws_iam_role.eks_nodes.arn

  # Use private subnets for nodes
  subnet_ids = [for s in aws_subnet.private : s.id]

  # Single large instance for better pod capacity
  scaling_config {
    desired_size = 1
    max_size     = 2
    min_size     = 1
  }

  # Large instance for more pods
  instance_types = ["t3.large"] # ~$60/month, supports 35 pods vs 17 on medium

  # Use standard EKS-optimized AMI
  ami_type = "AL2_x86_64"

  # Disk size
  disk_size = 20 # GB, minimum for Kubernetes

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-eks-nodes"
    Purpose = "Worker nodes for EKS cluster"
  })

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]
}

# OIDC Provider for IRSA (IAM Roles for Service Accounts)
data "tls_certificate" "eks" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-eks-oidc"
    Purpose = "OIDC provider for EKS IRSA"
  })
}

# Outputs for kubectl configuration
output "eks_cluster_endpoint" {
  value       = aws_eks_cluster.main.endpoint
  description = "Endpoint for EKS control plane"
}

output "eks_cluster_certificate" {
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
  description = "Base64 encoded certificate data for cluster"
}

output "eks_cluster_name" {
  value       = aws_eks_cluster.main.name
  description = "Name of the EKS cluster"
}

output "kubectl_config_command" {
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${aws_eks_cluster.main.name}"
  description = "Command to configure kubectl"
}

# Cost-saving tip: Use NodePort instead of LoadBalancer
output "access_without_loadbalancer" {
  value       = <<EOF
To access services without a LoadBalancer:
1. Get a node's external IP: kubectl get nodes -o wide
2. Create a NodePort service: kubectl expose deployment my-app --type=NodePort --port=8080 --node-port=30080
3. Access via: http://<node-external-ip>:30080

Or attach an Elastic IP to a node for stable access.
EOF
  description = "How to access services without expensive LoadBalancer"
}