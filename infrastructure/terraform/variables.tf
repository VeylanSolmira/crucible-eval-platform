# variables.tf - Input variables

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "crucible-platform"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "aws_profile" {
  description = "AWS profile to use"
  type        = string
  default     = ""
}

variable "allowed_ssh_ip" {
  description = "IP address allowed to SSH into the EC2 instance (in CIDR format)"
  type        = string
  default     = "73.41.64.209/32"
  
  # To update your IP:
  # 1. Get your current IP: curl -s https://api.ipify.org
  # 2. Update via command line: tofu apply -var="allowed_ssh_ip=YOUR_IP/32"
  # 3. Or update the default value above
}

# SSH Access Instructions:
# 1. If you don't have an SSH key, generate one:
#    ssh-keygen -t ed25519 -C "metr-eval-platform" -f ~/.ssh/id_ed25519_metr -N ""
#
# 2. Update ec2.tf with your public key:
#    cat ~/.ssh/id_ed25519_metr.pub
#
# 3. After deployment, SSH to the instance:
#    ssh -i ~/.ssh/id_ed25519_metr ubuntu@<public-ip>
#
# 4. To get the instance IP after deployment:
#    tofu output eval_server_public_ip

variable "gpu_instances_enabled" {
  description = "Enable GPU instances for model testing (set to true to create)"
  type        = bool
  default     = false
  
  # To enable GPU instances:
  # 1. Set this to true in terraform.tfvars:
  #    echo 'gpu_instances_enabled = true' >> terraform.tfvars
  # 2. Or via command line:
  #    tofu apply -var="gpu_instances_enabled=true"
  #
  # This will create launch templates but not instances by default.
  # Use the launch templates to create spot/on-demand instances as needed.
}

# EC2 Instance Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"  # Free tier eligible
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 access"
  type        = string
  default     = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPhoQtkUCQ78PROjyf0tcZQjEZ/fBX1PkNCZoxWjJhRU metr-eval-platform"
}

# Deployment Configuration
variable "deployment_method" {
  description = "Method for deploying code: 'github' or 's3'"
  type        = string
  default     = "github"
}

variable "github_repo" {
  description = "GitHub repository URL for deployment (leave empty to skip)"
  type        = string
  default     = ""
  # Example: "https://github.com/yourusername/crucible-platform.git"
}

variable "github_branch" {
  description = "GitHub branch to deploy"
  type        = string
  default     = "main"
}

# Note: deployment_bucket is now created by Terraform in s3.tf
# Only the deployment key/path is configurable

variable "deployment_key" {
  description = "S3 key (path) for deployment package"
  type        = string
  default     = "crucible-platform.tar.gz"
}

# Blue-Green Deployment Variables
variable "enabled_deployment_colors" {
  description = "Which deployment colors to create (for blue-green deployments)"
  type        = set(string)
  default     = ["blue"]  # Start with just blue
  
  validation {
    condition     = alltrue([for c in var.enabled_deployment_colors : contains(["blue", "green"], c)])
    error_message = "Deployment colors must be 'blue' or 'green'."
  }
}

variable "deployment_version" {
  description = "Version tag for this deployment"
  type        = string
  default     = "1.0"
}