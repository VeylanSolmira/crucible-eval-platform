# Nginx Security Hardening Guide

## Port Security Strategy

Once Nginx is configured and tested as the reverse proxy, we need to lock down direct access to backend services.

### Current State (Development/Testing)
```
Internet → EC2 Security Group
           ├── 22 (SSH)       → OK: Keep for management
           ├── 80 (HTTP)      → OK: For Let's Encrypt & redirect
           ├── 443 (HTTPS)    → OK: Main access point
           ├── 3000 (Frontend) → REMOVE: Should only be internal
           └── 8080 (Backend)  → REMOVE: Should only be internal
```

### Target State (Production)
```
Internet → EC2 Security Group
           ├── 22 (SSH)       → Restricted to admin IPs
           ├── 80 (HTTP)      → Open (redirect to HTTPS)
           └── 443 (HTTPS)    → Restricted to allowed_web_ips

Internal only (localhost):
           ├── 3000 (Frontend) → Only accessible from Nginx
           └── 8080 (Backend)  → Only accessible from Nginx
```

## Implementation Steps

### 1. Update Docker Compose (Recommended)

Bind services to localhost only:

```yaml
# docker-compose.yml
services:
  crucible-platform:
    ports:
      - "127.0.0.1:8080:8080"  # Only localhost can access
    # ... rest of config

  crucible-frontend:
    ports:
      - "127.0.0.1:3000:3000"  # Only localhost can access
    # ... rest of config
```

### 2. Update Security Group (After Testing)

Remove the ingress rules for 3000 and 8080:

```hcl
# infrastructure/terraform/ec2.tf
# DELETE these blocks after Nginx is working:

# Platform web interface (restricted for SSH tunneling)
# ingress {
#   from_port   = 8080
#   to_port     = 8080
#   protocol    = "tcp"
#   cidr_blocks = [var.allowed_ssh_ip]
# }

# Frontend port (if it was exposed)
# ingress {
#   from_port   = 3000
#   to_port     = 3000
#   protocol    = "tcp"
#   cidr_blocks = [var.allowed_ssh_ip]
# }
```

### 3. Testing Plan

Before removing port access:

1. **Verify Nginx is working:**
   ```bash
   # From whitelisted IP
   curl https://crucible.veylan.dev/api/status
   curl https://crucible.veylan.dev/
   ```

2. **Test all endpoints through Nginx:**
   - API endpoints: `/api/*`
   - WebSocket: `/api/events/stream`
   - Frontend assets
   - Health checks

3. **Verify internal connectivity:**
   ```bash
   # On EC2 instance
   curl http://localhost:8080/api/status  # Should work
   curl http://localhost:3000             # Should work
   ```

4. **Test from external (should fail after change):**
   ```bash
   # From outside
   curl http://crucible.veylan.dev:8080  # Should timeout
   curl http://crucible.veylan.dev:3000  # Should timeout
   ```

## Rollback Plan

If issues arise after closing ports:

### Quick Rollback (SSH Tunnel)
```bash
# Emergency access via SSH tunnel
ssh -L 8080:localhost:8080 -L 3000:localhost:3000 ubuntu@<elastic-ip>
```

### Terraform Rollback
```hcl
# Temporarily re-add to security group
ingress {
  from_port   = 8080
  to_port     = 8080
  protocol    = "tcp"
  cidr_blocks = ["YOUR.IP/32"]  # Just your IP for debugging
}
```

## Additional Security Hardening

### 1. Container Network Isolation

Create a dedicated network for internal communication:

```yaml
# docker-compose.yml
networks:
  internal:
    driver: bridge
    internal: true  # No external access
  
  proxy:
    driver: bridge

services:
  nginx:
    networks:
      - proxy
      - internal
  
  crucible-platform:
    networks:
      - internal  # Only on internal network
  
  crucible-frontend:
    networks:
      - internal  # Only on internal network
```

### 2. Firewall Rules (Defense in Depth)

Even with security groups, add iptables rules:

```bash
# Allow localhost only for backend services
sudo iptables -A INPUT -p tcp --dport 8080 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP

sudo iptables -A INPUT -p tcp --dport 3000 -s 127.0.0.1 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 3000 -j DROP
```

### 3. Application-Level Security

Update backend to reject non-proxied requests:

```python
# In FastAPI middleware
@app.middleware("http")
async def verify_proxy(request: Request, call_next):
    # Only accept requests from Nginx
    if not request.headers.get("X-Forwarded-For"):
        return Response(status_code=403)
    return await call_next(request)
```

## Monitoring After Changes

### 1. Access Logs
```bash
# Monitor for any direct access attempts
sudo tail -f /var/log/nginx/access.log
docker-compose logs -f crucible-platform | grep -v "127.0.0.1"
```

### 2. Failed Connection Attempts
```bash
# Check for blocked connections
sudo journalctl -u docker | grep "connection refused"
sudo dmesg | grep "dropped"
```

### 3. CloudWatch Alarms
- Set up alarm for unusual traffic patterns
- Alert on any successful connections to 8080/3000 from external IPs

## Summary

Closing ports 3000 and 8080 is a critical security improvement that:

1. **Reduces attack surface** - Only Nginx is exposed
2. **Centralizes security** - All security policies in Nginx
3. **Prevents bypass** - Can't skip Nginx rate limiting
4. **Enables monitoring** - Single point for access logs

The key is careful testing before making the change and having a rollback plan ready.