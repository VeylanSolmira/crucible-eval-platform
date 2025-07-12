# K8s Cluster Module

This module creates a Kubernetes cluster using K3s on AWS with Auto Scaling Group support.

## Usage

```terraform
module "k8s_cluster" {
  source = "./modules/k8s-cluster"
  
  project_name   = "my-project"
  vpc_id         = aws_vpc.main.id
  subnet_ids     = aws_subnet.private[*].id
  key_name       = aws_key_pair.ssh.key_name
  ssh_public_key = var.ssh_public_key
  
  # Optional
  instance_type    = "t3.small"
  min_size         = 2
  max_size         = 5
  desired_capacity = 3
  
  tags = {
    Environment = "production"
  }
}
```

## Requirements

- AWS provider ~> 5.0
- Terraform >= 1.0

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| project_name | Project name for resource naming | string | - | yes |
| vpc_id | VPC ID where cluster will be deployed | string | - | yes |
| subnet_ids | List of subnet IDs for the cluster nodes | list(string) | - | yes |
| key_name | EC2 key pair name for SSH access | string | - | yes |
| ssh_public_key | SSH public key content | string | - | yes |
| allowed_ssh_ip | CIDR block allowed to SSH to nodes | string | "0.0.0.0/0" | no |
| instance_type | EC2 instance type for nodes | string | "t3.micro" | no |
| min_size | Minimum number of nodes | number | 1 | no |
| max_size | Maximum number of nodes | number | 3 | no |
| desired_capacity | Desired number of nodes | number | 1 | no |
| volume_size | Root volume size in GB | number | 20 | no |
| enable_cluster_autoscaler | Enable Kubernetes Cluster Autoscaler | bool | true | no |
| tags | Tags to apply to all resources | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| asg_name | Name of the Auto Scaling Group |
| asg_arn | ARN of the Auto Scaling Group |
| security_group_id | ID of the cluster security group |
| iam_role_arn | ARN of the IAM role for nodes |
| iam_instance_profile_name | Name of the IAM instance profile |
| launch_template_id | ID of the launch template |
| cluster_status | Cluster status information |