output "asg_name" {
  description = "Name of the Auto Scaling Group"
  value       = try(aws_autoscaling_group.k8s_cluster[0].name, null)
}

output "asg_arn" {
  description = "ARN of the Auto Scaling Group"
  value       = try(aws_autoscaling_group.k8s_cluster[0].arn, null)
}

output "security_group_id" {
  description = "ID of the cluster security group"
  value       = try(aws_security_group.k8s_cluster[0].id, null)
}

output "iam_role_arn" {
  description = "ARN of the IAM role for nodes"
  value       = try(aws_iam_role.k8s_cluster[0].arn, null)
}

output "iam_instance_profile_name" {
  description = "Name of the IAM instance profile"
  value       = try(aws_iam_instance_profile.k8s_cluster[0].name, null)
}

output "launch_template_id" {
  description = "ID of the launch template"
  value       = try(aws_launch_template.k8s_node[0].id, null)
}

output "cluster_status" {
  description = "Cluster status information"
  value = {
    enabled      = var.enable_cluster_autoscaler
    min_size     = try(aws_autoscaling_group.k8s_cluster[0].min_size, 0)
    max_size     = try(aws_autoscaling_group.k8s_cluster[0].max_size, 0)
    desired_size = try(aws_autoscaling_group.k8s_cluster[0].desired_capacity, 0)
  }
}