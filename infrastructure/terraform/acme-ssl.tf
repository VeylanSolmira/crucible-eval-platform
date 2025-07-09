# SSL Certificate Management with ACME (Let's Encrypt)
# This manages SSL certificates as Infrastructure as Code

# Only create SSL resources if domain and email are configured
locals {
  create_ssl = var.domain_name != "" && var.email != "" && var.create_route53_zone
}

# ACME provider for Let's Encrypt
provider "acme" {
  # Production URL - use this for real certificates
  server_url = "https://acme-v02.api.letsencrypt.org/directory"
  
  # For testing, uncomment this to use staging environment
  # server_url = "https://acme-staging-v02.api.letsencrypt.org/directory"
}

# Private key for ACME account
resource "tls_private_key" "acme_account" {
  count     = local.create_ssl ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Register with Let's Encrypt
resource "acme_registration" "registration" {
  count           = local.create_ssl ? 1 : 0
  account_key_pem = tls_private_key.acme_account[0].private_key_pem
  email_address   = var.email
}

# Private key for the certificate
resource "tls_private_key" "cert_private_key" {
  count     = local.create_ssl ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 2048
}

# Wildcard certificate for *.crucible.veylan.dev (includes crucible.veylan.dev via SAN)
resource "acme_certificate" "crucible_wildcard" {
  count                     = local.create_ssl ? 1 : 0
  account_key_pem           = acme_registration.registration[0].account_key_pem
  common_name               = "*.crucible.veylan.dev"
  subject_alternative_names = ["crucible.veylan.dev"]
  
  dns_challenge {
    provider = "route53"
    
    config = {
      AWS_HOSTED_ZONE_ID = aws_route53_zone.crucible[0].zone_id
      AWS_REGION         = var.aws_region
    }
  }
}

# Store certificate in SSM at the path nginx expects
resource "aws_ssm_parameter" "ssl_certificate" {
  count = local.create_ssl ? 1 : 0
  
  name  = "/${var.project_name}/ssl/certificate"
  type  = "SecureString"
  value = acme_certificate.crucible_wildcard[0].certificate_pem
  
  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-ssl-certificate"
    Purpose = "Wildcard SSL certificate for crucible.veylan.dev and its subdomains"
  })
}

resource "aws_ssm_parameter" "ssl_private_key" {
  count = local.create_ssl ? 1 : 0
  
  name  = "/${var.project_name}/ssl/private_key"
  type  = "SecureString"
  value = acme_certificate.crucible_wildcard[0].private_key_pem
  
  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-ssl-private-key"
    Purpose = "Private key for crucible.veylan.dev and its subdomains SSL certificate"
  })
}

resource "aws_ssm_parameter" "ssl_issuer_pem" {
  count = local.create_ssl ? 1 : 0
  
  name  = "/${var.project_name}/ssl/issuer_pem"
  type  = "SecureString"
  value = acme_certificate.crucible_wildcard[0].issuer_pem
  
  tags = merge(local.common_tags, {
    Name    = "${var.project_name}-ssl-issuer"
    Purpose = "SSL certificate issuer chain"
  })
}

# Update IAM policy to allow EC2 instances to read SSL certificates
resource "aws_iam_role_policy" "eval_server_ssl" {
  count = local.create_ssl ? 1 : 0
  
  name = "crucible-eval-server-ssl-policy"
  role = aws_iam_role.eval_server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/ssl/*"
        ]
      }
    ]
  })
}

# Output certificate information
output "ssl_certificate_coverage" {
  value       = local.create_ssl ? "*.crucible.veylan.dev (wildcard) + crucible.veylan.dev (SAN) - covers all deployment domains" : "SSL not configured"
  description = "SSL certificate coverage"
}