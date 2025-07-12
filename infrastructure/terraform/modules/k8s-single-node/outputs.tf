output "instance_id" {
  description = "ID of the K8s instance"
  value       = aws_instance.k8s_node.id
}

output "public_ip" {
  description = "Public IP address of the K8s node"
  value       = aws_instance.k8s_node.public_ip
}

output "private_ip" {
  description = "Private IP address of the K8s node"
  value       = aws_instance.k8s_node.private_ip
}

output "security_group_id" {
  description = "ID of the security group"
  value       = aws_security_group.k8s_node.id
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = var.create_vpc ? aws_vpc.k8s_vpc[0].id : var.vpc_id
}

output "subnet_id" {
  description = "ID of the subnet"
  value       = var.create_vpc ? aws_subnet.k8s_public[0].id : var.subnet_id
}

output "ssh_command" {
  description = "SSH command to connect to the node"
  value       = "ssh ubuntu@${aws_instance.k8s_node.public_ip}"
}

output "kubeconfig_command" {
  description = "Command to copy kubeconfig"
  value       = "scp ubuntu@${aws_instance.k8s_node.public_ip}:~/.kube/config ./kubeconfig-${var.cluster_name}"
}

output "iam_role_arn" {
  description = "ARN of the IAM role for the K8s node"
  value       = aws_iam_role.k8s_node.arn
}

output "iam_instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = aws_iam_instance_profile.k8s_node.name
}