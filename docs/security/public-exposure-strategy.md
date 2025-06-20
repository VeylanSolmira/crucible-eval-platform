# Public Exposure Security Strategy

## Overview
Exposing a code execution platform to the internet requires extreme caution. This document outlines a phased approach to safely make the platform accessible.

## Why Security Matters

### What Bots Will Attempt Immediately
1. **Crypto Mining** - Use your compute for profit
2. **Reverse Shells** - Establish backdoors into your infrastructure
3. **Network Scanning** - Use your IP to scan/attack others
4. **DDoS Amplification** - Bounce attacks through your service
5. **Data Exfiltration** - Steal environment variables, secrets
6. **Resource Abuse** - Max out CPU/memory/network

### Real Risk: AWS Bill Shock
- Compute abuse can cost thousands in hours
- Network egress charges from attacks
- Your IP gets blacklisted
- AWS suspends your account

## Phased Security Approach

### Phase 1: Private Demo (Current State) ✅
- Security groups restrict to SSH only
- Access via SSH tunneling
- Zero public exposure
- **Status: Implemented**

### Phase 2: IP Whitelist (Recommended Next Step) 
**What**: Open HTTPS but only to specific IPs

**Implementation**:
1. Update security group to allow HTTPS from whitelisted IPs
2. Set up HTTPS with Let's Encrypt
3. Configure Route 53 subdomain
4. No changes to Vercel needed (no CNAME yet)

**Benefits**:
- Can access without SSH tunnel
- Still completely private
- Can share with specific people by adding their IP

**Risks**: Minimal - only trusted IPs can connect

### Phase 3: CloudFlare Protection (Future)
**What**: Use CloudFlare Zero Trust for authentication

**Implementation**:
1. Set up CloudFlare for veylan.dev
2. Configure Access policies (email-based auth)
3. Enable rate limiting and WAF rules
4. Hide origin server IP

**Benefits**:
- Can share with anyone via email invite
- DDoS protection included
- No open ports on EC2

**Risks**: Low - CloudFlare handles security

### Phase 4: Public with Authentication (If Ever Needed)
**What**: Full public access with comprehensive protection

**Required Protections**:
- Mandatory authentication (OAuth2/JWT)
- Aggressive rate limiting (1 request/minute)
- Request size limits (max 10KB)
- Execution timeouts (max 30s)
- Network isolation per execution
- Input sanitization
- WAF rules
- Comprehensive monitoring

**Risks**: High - Requires constant monitoring

## Implementation Guide: Phase 2 (IP Whitelist)

### 1. Update Terraform Variables
```hcl
# terraform/variables.tf
variable "allowed_web_ips" {
  description = "IPs allowed to access web interface"
  type        = list(string)
  default     = []
}
```

### 2. Update Security Group
```hcl
# terraform/ec2.tf
# HTTPS access from whitelisted IPs
ingress {
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = var.allowed_web_ips
  description = "HTTPS from whitelisted IPs"
}

# HTTP for Let's Encrypt challenge
ingress {
  from_port   = 80
  to_port     = 80
  protocol    = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
  description = "HTTP for Let's Encrypt only"
}
```

### 3. Install Nginx and Certbot
```bash
# In userdata or manually on EC2
apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx reverse proxy
cat > /etc/nginx/sites-available/crucible << 'EOF'
server {
    listen 80;
    server_name eval.veylan.dev;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name eval.veylan.dev;
    
    # SSL will be configured by certbot
    
    # Security headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    
    # Proxy to backend
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Proxy to frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/crucible /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

### 4. Set Up Route 53
```hcl
# terraform/route53.tf
resource "aws_route53_record" "eval" {
  zone_id = var.route53_zone_id  # Your hosted zone
  name    = "eval.veylan.dev"
  type    = "A"
  ttl     = 300
  records = [aws_instance.eval_server["green"].public_ip]
}
```

### 5. Get SSL Certificate
```bash
# On EC2 after Route 53 is configured
sudo certbot --nginx -d eval.veylan.dev --non-interactive --agree-tos -m your-email@example.com
```

### 6. DNS Configuration Options

**Option A: If Vercel manages veylan.dev DNS**
- You'll need to add an A record in Vercel dashboard pointing to EC2 IP
- This makes the subdomain immediately public
- Only do this AFTER security is configured

**Option B: If using Route 53 for veylan.dev**
- Add the A record in Route 53
- No Vercel changes needed

**Option C: Split DNS (Recommended for testing)**
- Keep veylan.dev in Vercel
- Use a different domain for testing (e.g., eval-test.com)
- Move to veylan.dev subdomain only when ready

## Security Checklist

### Before Going Public
- [ ] IP whitelist implemented
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Rate limiting in place
- [ ] Monitoring enabled
- [ ] Backup plan ready
- [ ] AWS billing alerts set

### Monitoring Requirements
- CloudWatch alarms for high CPU/network
- Log analysis for suspicious patterns
- Regular security audits
- Automated responses to threats

## Emergency Procedures

### If Compromised
1. **Immediate**: Close security groups
2. **Stop**: All EC2 instances
3. **Rotate**: All credentials
4. **Analyze**: CloudTrail logs
5. **Report**: To AWS if needed

### Rollback Plan
```bash
# Emergency shutdown
aws ec2 modify-security-group-rules --group-id sg-xxx --revoke
docker compose down
systemctl stop nginx
```

## Recommendations

1. **Start with Phase 2** (IP Whitelist) - Safe and simple
2. **Monitor for 1 week** before considering Phase 3
3. **Never skip to Phase 4** without CloudFlare
4. **Keep SSH access** as backup
5. **Set AWS billing alerts** before any public exposure

## Cost Considerations

### With IP Whitelist
- Minimal - only trusted traffic
- ~$10/month for EC2 + Route53

### With Public Access
- Could spike to $1000s if abused
- Requires WAF ($5/month minimum)
- CloudFlare Pro recommended ($20/month)
- Monitoring tools needed

## Conclusion

The platform is powerful but dangerous if exposed. Start with IP whitelisting and only progress to more open access if there's a clear business need and proper security measures are in place.