# Route 53 and Elastic IP Configuration for Public Access

# Elastic IPs for each deployment color - REMOVED - Using Kubernetes Load Balancer
# resource "aws_eip" "eval_server" {
#   for_each = toset(["blue", "green"]) # Always create both
# 
#   domain = "vpc"
# 
#   tags = merge(local.common_tags, {
#     Name            = "${var.project_name}-eip-${each.key}"
#     DeploymentColor = each.key
#     Purpose         = "Static IP for eval server"
#   })
# 
#   # Note: Use deploy-green or deploy-blue aliases to target specific colors
# }

# Associate Elastic IPs with EC2 instances - REMOVED - Migrated to Kubernetes
# resource "aws_eip_association" "eval_server" {
#   for_each = toset(["blue", "green"]) # Always create both
# 
#   instance_id   = aws_instance.eval_server[each.key].id
#   allocation_id = aws_eip.eval_server[each.key].id
# 
#   # Note: Use deploy-green or deploy-blue aliases to target specific colors
# }

# Route 53 Hosted Zones
# Root domain zone (veylan.dev)
resource "aws_route53_zone" "root" {
  count = var.create_route53_zone ? 1 : 0

  name = "veylan.dev"

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-root-zone"
    Purpose = "Root domain DNS zone"
  })
}

# Subdomain zone (crucible.veylan.dev)
resource "aws_route53_zone" "crucible" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0

  name = var.domain_name

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-zone"
    Purpose = "DNS zone for evaluation platform"
  })
}

# NS delegation from root to subdomain
resource "aws_route53_record" "ns_delegation" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0

  zone_id = aws_route53_zone.root[0].zone_id
  name    = var.domain_name
  type    = "NS"
  ttl     = 300
  records = aws_route53_zone.crucible[0].name_servers
}

# Data source to get the load balancer details
data "aws_lb" "kubernetes_nlb" {
  count = var.create_route53_zone && var.domain_name != "" && var.kubernetes_load_balancer_ip != "" ? 1 : 0

  # Extract the load balancer name from the DNS name
  name = split("-", split(".", var.kubernetes_load_balancer_ip)[0])[0]
}

# ALIAS Record at apex of crucible.veylan.dev zone pointing to Kubernetes load balancer
resource "aws_route53_record" "crucible_apex_alias" {
  # Only create if Route53 is enabled AND load balancer is configured
  count = var.create_route53_zone && var.domain_name != "" && var.kubernetes_load_balancer_ip != "" ? 1 : 0

  zone_id = aws_route53_zone.crucible[0].zone_id # Using crucible subdomain zone
  name    = ""                                   # Empty name means apex of the zone
  type    = "A"

  alias {
    name                   = data.aws_lb.kubernetes_nlb[0].dns_name
    zone_id                = data.aws_lb.kubernetes_nlb[0].zone_id
    evaluate_target_health = true
  }
}

# CNAME Records for dev/staging in crucible zone (dev.crucible.veylan.dev, staging.crucible.veylan.dev)
resource "aws_route53_record" "environment_subdomains" {
  for_each = var.create_route53_zone && var.domain_name != "" && var.kubernetes_load_balancer_ip != "" ? toset(["dev", "staging"]) : toset([])

  zone_id = aws_route53_zone.crucible[0].zone_id
  name    = "${each.value}.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300

  records = [var.kubernetes_load_balancer_ip]

  lifecycle {
    # We'll update these to point to K8s load balancer later
    create_before_destroy = true
  }
}

# Health check for active deployment (optional but recommended)
resource "aws_route53_health_check" "crucible" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0

  fqdn              = var.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/readyz"
  failure_threshold = "3"
  request_interval  = "30"

  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-health-check"
    Purpose = "Monitor platform availability"
  })
}

# Outputs for DNS configuration - REMOVED - Using Kubernetes Load Balancer
# output "elastic_ips" {
#   value       = { for k, v in aws_eip.eval_server : k => v.public_ip }
#   description = "Elastic IP addresses for each deployment color"
# }

output "nameservers" {
  value       = var.create_route53_zone && var.domain_name != "" ? aws_route53_zone.crucible[0].name_servers : []
  description = "Route 53 nameservers (if zone created) - add these to your domain registrar"
}

output "dns_configuration" {
  value = var.create_route53_zone ? {
    zone_created = true
    nameservers  = var.domain_name != "" ? aws_route53_zone.crucible[0].name_servers : []
    domain       = var.domain_name
    subdomains = {
      dev     = "dev.${var.domain_name} → ${var.kubernetes_load_balancer_ip != "" ? var.kubernetes_load_balancer_ip : "Configure kubernetes_load_balancer_ip"}"
      staging = "staging.${var.domain_name} → ${var.kubernetes_load_balancer_ip != "" ? var.kubernetes_load_balancer_ip : "Configure kubernetes_load_balancer_ip"}"
    }
    active_deployment = "${var.domain_name} → ${var.kubernetes_load_balancer_ip != "" ? var.kubernetes_load_balancer_ip : "Configure kubernetes_load_balancer_ip"}"
    instruction       = "Add these nameservers to your domain registrar for ${var.domain_name}"
    } : {
    zone_created = false
    nameservers  = []
    domain       = var.domain_name
    subdomains = {
      dev     = "dev.${var.domain_name} → ${var.kubernetes_load_balancer_ip != "" ? var.kubernetes_load_balancer_ip : "Configure kubernetes_load_balancer_ip"}"
      staging = "staging.${var.domain_name} → ${var.kubernetes_load_balancer_ip != "" ? var.kubernetes_load_balancer_ip : "Configure kubernetes_load_balancer_ip"}"
    }
    active_deployment = var.kubernetes_load_balancer_ip != "" ? "Add A record for ${var.domain_name} pointing to ${var.kubernetes_load_balancer_ip}" : "Configure kubernetes_load_balancer_ip variable"
    instruction       = "Route53 zone not created - manually configure DNS"
  }
  description = "DNS configuration instructions"
}