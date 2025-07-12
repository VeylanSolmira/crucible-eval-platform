# K8s Single Node Deployment
module "k8s_single_node" {
  source = "./modules/k8s-single-node"
  
  cluster_name = "${var.project_name}-k8s"
  aws_region   = var.aws_region
  
  # Use existing VPC
  create_vpc = false
  vpc_id     = aws_vpc.main.id
  subnet_id  = aws_subnet.public[0].id
  
  # Instance configuration
  instance_type = "t3.micro"
  volume_size   = 20
  
  # Access control
  allowed_ssh_cidr = var.allowed_ssh_ip
  allowed_api_cidr = "0.0.0.0/0"  # Adjust for production
  
  # SSH key
  ssh_public_key = var.ssh_public_key
  
  tags = merge(local.common_tags, {
    Component = "k8s-single-node"
  })
}

# Outputs
output "k8s_node_public_ip" {
  description = "Public IP of the K8s node"
  value       = module.k8s_single_node.public_ip
}

output "k8s_ssh_command" {
  description = "SSH command to connect to K8s node"
  value       = module.k8s_single_node.ssh_command
}

output "k8s_kubeconfig_command" {
  description = "Command to copy kubeconfig"
  value       = module.k8s_single_node.kubeconfig_command
}