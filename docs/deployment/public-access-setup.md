# Public Access Setup Guide

This guide walks through setting up secure public access to the Crucible platform using IP whitelisting, Elastic IPs, and HTTPS.

## Prerequisites

- AWS infrastructure deployed (EC2 instances running)
- Terraform state initialized
- Domain name ready (e.g., crucible.veylan.dev)

## Phase 1: Deploy Elastic IPs and Configure DNS

### 1. Update Terraform Variables

Create or update `terraform.tfvars`:

```hcl
# IP Whitelisting (start secure)
allowed_web_ips = [
  "YOUR.IP.ADDRESS/32",    # Your IP (run: curl -s https://api.ipify.org)
  # Add team members as needed
]

# Domain Configuration
domain_name = "crucible.veylan.dev"

# DNS Option 1: Use existing provider (recommended to start)
create_route53_zone = false

# DNS Option 2: Let AWS manage DNS
# create_route53_zone = true
```

### 2. Apply Terraform Changes

```bash
cd infrastructure/terraform
tofu plan  # Review changes
tofu apply
```

This will:
- Create Elastic IPs for each deployment color
- Associate them with EC2 instances
- Update security groups for web access
- Output the Elastic IP to use for DNS

### 3. Configure DNS

#### Option A: Using Vercel (or other DNS provider)

1. Get the Elastic IP from Terraform output:
   ```bash
   tofu output elastic_ips
   ```

2. Add A record in Vercel dashboard:
   - Name: `crucible`
   - Type: `A`
   - Value: `<elastic-ip-for-active-color>`
   - TTL: 60 (for easy switching)

#### Option B: Using Route 53

1. Set `create_route53_zone = true` and apply
2. Get nameservers from output:
   ```bash
   tofu output nameservers
   ```
3. Update your domain registrar to use these nameservers

## Phase 2: Configure Nginx and HTTPS

### 1. SSH to the Active Instance

```bash
# Get SSH command from Terraform
tofu output ssh_commands_elastic

# Connect to active color instance
ssh ubuntu@<elastic-ip>
```

### 2. Install Nginx and Certbot

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 3. Configure Nginx

Create `/etc/nginx/sites-available/crucible`:

```nginx
server {
    listen 80;
    server_name crucible.veylan.dev;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name crucible.veylan.dev;
    
    # SSL will be configured by certbot
    
    # Security headers
    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting (adjust as needed)
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Proxy to backend API
    location /api/ {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Proxy to frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/crucible /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

### 4. Obtain SSL Certificate

**Important**: DNS must be configured and propagated before this step!

```bash
# Test DNS resolution first
nslookup crucible.veylan.dev

# If DNS resolves correctly, get certificate
sudo certbot --nginx -d crucible.veylan.dev \
  --non-interactive --agree-tos \
  --email your-email@example.com
```

### 5. Configure Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically adds cron job for renewal
sudo systemctl list-timers | grep certbot
```

## Phase 3: Testing and Monitoring

### 1. Test Access

From a whitelisted IP:
```bash
# Test HTTPS
curl https://crucible.veylan.dev/api/status

# Test redirect
curl -I http://crucible.veylan.dev
```

From a non-whitelisted IP:
- Should get connection timeout (not even rejection)

### 2. Monitor Logs

```bash
# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Platform logs
sudo journalctl -u crucible-compose -f
```

### 3. Set Up Alerts

In AWS Console:
- CloudWatch alarm for high CPU
- CloudWatch alarm for unusual network traffic
- Billing alert for unexpected charges

## Blue-Green Deployment Switching

To switch traffic between blue and green:

1. Update `terraform.tfvars`:
   ```hcl
   active_deployment_color = "blue"  # or "green"
   ```

2. Apply changes:
   ```bash
   tofu apply
   ```

3. If using external DNS, update the A record to new Elastic IP

## Security Checklist

- [ ] IP whitelist configured and tested
- [ ] HTTPS enabled with valid certificate
- [ ] HTTP redirects to HTTPS
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Monitoring active
- [ ] Backup access via SSH maintained
- [ ] Emergency shutdown procedure documented

## Troubleshooting

### DNS Not Resolving
- Check TTL on DNS records (may take time to propagate)
- Verify nameservers if using Route 53
- Use `dig` or `nslookup` to debug

### Certificate Issues
- Ensure port 80 is open for Let's Encrypt challenge
- Check DNS is resolving correctly
- Review `/var/log/letsencrypt/letsencrypt.log`

### Connection Timeouts
- Verify your IP is in `allowed_web_ips`
- Check security group rules in AWS console
- Ensure Nginx is running: `sudo systemctl status nginx`

## Next Steps

Once Phase 2 is working:
1. Test thoroughly with team members
2. Add more IPs to whitelist as needed
3. Consider CloudFlare for additional protection
4. Plan for Phase 3 (broader access) if needed