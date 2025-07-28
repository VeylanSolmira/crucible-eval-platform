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


variable "key_name" {
  description = "AWS EC2 key pair name"
  type        = string
  default     = ""
}

variable "allowed_ssh_cidr_blocks" {
  description = "CIDR blocks allowed to SSH"
  type        = list(string)
  default     = ["73.41.64.209/32"]
}

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
  default     = "t3.small" # Better baseline performance than t2.micro
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
  default     = ["blue", "green"] # Both environments exist

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

variable "ubuntu_ami_id" {
  description = "Ubuntu AMI ID to use (pinned to prevent updates)"
  type        = string
  default     = "ami-02de260c9d93d7b98"
}

# Public Access Variables
variable "domain_name" {
  description = "Domain name for the platform (e.g., crucible.veylan.dev)"
  type        = string
  default     = "veylan.dev"
}

variable "create_route53_zone" {
  description = "Whether to create a Route 53 hosted zone (true if managing DNS, false if delegating)"
  type        = bool
  default     = false
}

variable "active_deployment_color" {
  description = "Which deployment color (blue/green) should receive traffic"
  type        = string
  default     = "blue"

  validation {
    condition     = contains(["blue", "green"], var.active_deployment_color)
    error_message = "Active deployment color must be 'blue' or 'green'."
  }
}

variable "allowed_web_ips" {
  description = "IP addresses allowed to access HTTPS web interface (CIDR format). REQUIRED for web access - empty list means NO HTTPS access!"
  type        = list(string)
  default     = []
  # SECURITY: Default is NO access. You MUST add IPs to access the web interface.
  # Example: ["73.41.64.209/32", "10.0.0.0/8"]
  # Note: Port 80 remains open for Let's Encrypt, but redirects to HTTPS
}

variable "email" {
  description = "Email address for Let's Encrypt SSL certificate notifications"
  type        = string
  default     = "veylan.solmira+crucible@gmail.com"
  # Required for automated SSL certificate setup
}

# Monitoring Configuration
variable "alert_email_base" {
  description = "Base email for alerts (e.g., 'user@example.com'). Will add suffix for filtering."
  type        = string
  default     = "veylan.solmira@gmail.com"
  # Leave empty to skip email alerts
  # Example: "veylan.solmira@gmail.com" -> "veylan.solmira+crucible-alerts@gmail.com"
}

variable "alert_email_suffix" {
  description = "Suffix to add to alert emails for easy filtering"
  type        = string
  default     = "crucible-alerts"
  # Other options: "crucible-prod", "crucible-critical", "crucible-oom"
}

# Kubernetes Configuration
variable "kubernetes_load_balancer_ip" {
  description = "IP address or hostname of the Kubernetes ingress load balancer (for Route53 A records)"
  type        = string
  default     = ""
  # Example: "a8335c4cb06884e689342a1109e3a3e3-e467caecc5e4a715.elb.us-west-2.amazonaws.com"
  # Leave empty to use placeholder IP in Route53
}

variable "enable_alb" {
  description = "Whether to create an Application Load Balancer"
  type        = bool
  default     = false
  # Set to true if you want ALB health checks monitored
}

# Common Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "crucible-platform"
    ManagedBy   = "terraform"
    Environment = "dev"
  }
}

variable "github_repository_name" {
  description = "GitHub repository in format owner/repo for OIDC"
  type        = string
  default     = "VeylanSolmira/metr-eval-platform"
}