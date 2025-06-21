# Route 53 and Elastic IP Configuration for Public Access

# Elastic IPs for each deployment color
resource "aws_eip" "eval_server" {
  for_each = var.enabled_deployment_colors
  
  domain = "vpc"
  
  tags = merge(local.common_tags, {
    Name             = "${var.project_name}-eip-${each.key}"
    DeploymentColor  = each.key
    Purpose          = "Static IP for eval server"
  })
}

# Associate Elastic IPs with EC2 instances
resource "aws_eip_association" "eval_server" {
  for_each = var.enabled_deployment_colors
  
  instance_id   = aws_instance.eval_server[each.key].id
  allocation_id = aws_eip.eval_server[each.key].id
}

# Route 53 Hosted Zone (optional - only if managing DNS)
resource "aws_route53_zone" "crucible" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0
  
  name = var.domain_name
  
  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-zone"
    Purpose = "DNS zone for evaluation platform"
  })
}

# A Record pointing to active deployment
resource "aws_route53_record" "crucible_a" {
  count = var.create_route53_zone && var.domain_name != "" ? 1 : 0
  
  zone_id = aws_route53_zone.crucible[0].zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 60  # Low TTL for easy switching between blue/green
  
  # Point to the Elastic IP of the active deployment
  records = [aws_eip.eval_server[var.active_deployment_color].public_ip]
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
    instruction  = "Add these nameservers to your domain registrar for ${var.domain_name}"
    elastic_ip   = aws_eip.eval_server[var.active_deployment_color].public_ip
  } : {
    zone_created = false
    nameservers  = []
    domain       = var.domain_name
    instruction  = "Add A record for ${var.domain_name} pointing to ${aws_eip.eval_server[var.active_deployment_color].public_ip}"
    elastic_ip   = aws_eip.eval_server[var.active_deployment_color].public_ip
  }
  description = "DNS configuration instructions"
}