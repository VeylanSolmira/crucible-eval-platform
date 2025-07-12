variable "cluster_name" {
  description = "Name of the K8s cluster"
  type        = string
  default     = "micro-k8s"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 20
}

variable "volume_type" {
  description = "EBS volume type"
  type        = string
  default     = "gp3"
}

variable "create_vpc" {
  description = "Create a new VPC for the cluster"
  type        = bool
  default     = true
}

variable "vpc_id" {
  description = "Existing VPC ID (required if create_vpc is false)"
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Existing subnet ID (required if create_vpc is false)"
  type        = string
  default     = null
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "ssh_public_key" {
  description = "SSH public key content"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allowed_api_cidr" {
  description = "CIDR block allowed to access K8s API"
  type        = string
  default     = "0.0.0.0/0"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}