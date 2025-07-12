# K8s Single Node Module

This module creates a single-node Kubernetes cluster using K3s on AWS.

## Usage

### With new VPC
```terraform
module "k8s_single_node" {
  source = "./modules/k8s-single-node"
  
  cluster_name = "my-k8s"
  aws_region   = "us-west-2"
  
  # Optional
  instance_type = "t3.small"
  volume_size   = 30
  
  tags = {
    Environment = "dev"
  }
}
```

### With existing VPC
```terraform
module "k8s_single_node" {
  source = "./modules/k8s-single-node"
  
  cluster_name = "my-k8s"
  create_vpc   = false
  vpc_id       = aws_vpc.existing.id
  subnet_id    = aws_subnet.existing.id
  
  tags = {
    Environment = "prod"
  }
}
```

## Requirements

- AWS provider ~> 5.0
- Terraform >= 1.0
- SSH key file at the specified path

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| cluster_name | Name of the K8s cluster | string | "micro-k8s" | no |
| aws_region | AWS region | string | "us-west-2" | no |
| instance_type | EC2 instance type | string | "t3.micro" | no |
| volume_size | Root volume size in GB | number | 20 | no |
| volume_type | EBS volume type | string | "gp3" | no |
| create_vpc | Create a new VPC for the cluster | bool | true | no |
| vpc_id | Existing VPC ID (required if create_vpc is false) | string | null | no |
| subnet_id | Existing subnet ID (required if create_vpc is false) | string | null | no |
| vpc_cidr | CIDR block for the VPC | string | "10.0.0.0/16" | no |
| subnet_cidr | CIDR block for the subnet | string | "10.0.1.0/24" | no |
| ssh_public_key | SSH public key content | string | - | yes |
| allowed_ssh_cidr | CIDR block allowed to SSH | string | "0.0.0.0/0" | no |
| allowed_api_cidr | CIDR block allowed to access K8s API | string | "0.0.0.0/0" | no |
| tags | Tags to apply to all resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| instance_id | ID of the K8s instance |
| public_ip | Public IP address of the K8s node |
| private_ip | Private IP address of the K8s node |
| security_group_id | ID of the security group |
| vpc_id | ID of the VPC |
| subnet_id | ID of the subnet |
| ssh_command | SSH command to connect to the node |
| kubeconfig_command | Command to copy kubeconfig |
| iam_role_arn | ARN of the IAM role for the K8s node |
| iam_instance_profile_name | Name of the IAM instance profile |

## Notes

- The module installs K3s, a lightweight Kubernetes distribution
- The instance is configured with a public IP for easy access
- Remember to restrict `allowed_ssh_cidr` and `allowed_api_cidr` in production
- IAM role with ECR permissions is automatically attached for pulling images from ECR