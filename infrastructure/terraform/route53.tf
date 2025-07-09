# Route 53 and Elastic IP Configuration for Public Access

# Elastic IPs for each deployment color
resource "aws_eip" "eval_server" {
  for_each = toset(["blue", "green"])  # Always create both
  
  domain = "vpc"
  
  tags = merge(local.common_tags, {
    Name             = "${var.project_name}-eip-${each.key}"
    DeploymentColor  = each.key
    Purpose          = "Static IP for eval server"
  })
  
  # Note: Use deploy-green or deploy-blue aliases to target specific colors
}

# Associate Elastic IPs with EC2 instances
resource "aws_eip_association" "eval_server" {
  for_each = toset(["blue", "green"])  # Always create both
  
  instance_id   = aws_instance.eval_server[each.key].id
  allocation_id = aws_eip.eval_server[each.key].id
  
  # Note: Use deploy-green or deploy-blue aliases to target specific colors
}

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

# A Record pointing to active deployment
resource "aws_route53_record" "crucible_a" {
  # Only create if Route53 is enabled AND the active color is in the enabled set
  count = var.create_route53_zone && var.domain_name != "" && contains(var.enabled_deployment_colors, var.active_deployment_color) ? 1 : 0
  
  zone_id = aws_route53_zone.crucible[0].zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 60  # Low TTL for easy switching between blue/green
  
  # Point to the Elastic IP of the active deployment
  records = [aws_eip.eval_server[var.active_deployment_color].public_ip]
}

# A Records for blue/green in crucible zone (blue.crucible.veylan.dev, green.crucible.veylan.dev)
resource "aws_route53_record" "crucible_subdomains" {
  for_each = var.create_route53_zone && var.domain_name != "" ? toset(["blue", "green"]) : toset([])
  
  zone_id = aws_route53_zone.crucible[0].zone_id
  name    = "${each.key}.${var.domain_name}"
  type    = "A"
  ttl     = 300
  
  records = [aws_eip.eval_server[each.key].public_ip]
}

# Health check for active deployment (optional but recommended)
resource "aws_route53_health_check" "crucible" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0
  
  fqdn              = var.domain_name
  port              = 443
  type              = "HTTPS"
  resource_path     = "/api/status"
  failure_threshold = "3"
  request_interval  = "30"
  
  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-health-check"
    Purpose = "Monitor platform availability"
  })
}

# Outputs for DNS configuration
output "elastic_ips" {
  value = { for k, v in aws_eip.eval_server : k => v.public_ip }
  description = "Elastic IP addresses for each deployment color"
}

output "nameservers" {
  value = var.create_route53_zone && var.domain_name != "" ? aws_route53_zone.crucible[0].name_servers : []
  description = "Route 53 nameservers (if zone created) - add these to your domain registrar"
}

output "dns_configuration" {
  value = var.create_route53_zone ? {
    zone_created = true
    nameservers  = var.domain_name != "" ? aws_route53_zone.crucible[0].name_servers : []
    domain       = var.domain_name
    subdomains   = {
      blue  = "blue.${var.domain_name} → ${aws_eip.eval_server["blue"].public_ip}"
      green = "green.${var.domain_name} → ${aws_eip.eval_server["green"].public_ip}"
    }
    active_deployment = "${var.domain_name} → ${var.active_deployment_color} (${contains(var.enabled_deployment_colors, var.active_deployment_color) ? aws_eip.eval_server[var.active_deployment_color].public_ip : "not enabled"})"
    instruction  = "Add these nameservers to your domain registrar for ${var.domain_name}"
  } : {
    zone_created = false
    nameservers  = []
    domain       = var.domain_name
    subdomains   = {
      blue  = "blue.${var.domain_name} → ${aws_eip.eval_server["blue"].public_ip}"
      green = "green.${var.domain_name} → ${aws_eip.eval_server["green"].public_ip}"
    }
    active_deployment = contains(var.enabled_deployment_colors, var.active_deployment_color) ? "Add A record for ${var.domain_name} pointing to ${aws_eip.eval_server[var.active_deployment_color].public_ip}" : "Active deployment (${var.active_deployment_color}) not enabled"
    instruction  = "Route53 zone not created - manually configure DNS"
  }
  description = "DNS configuration instructions"
}