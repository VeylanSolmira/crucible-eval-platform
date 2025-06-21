# Public Access Deployment Checklist

This checklist guides you through deploying the Crucible platform with secure public access.

## Pre-Deployment Verification

- [ ] AWS credentials configured: `aws sts get-caller-identity`
- [ ] Terraform initialized: `cd infrastructure/terraform && tofu init`
- [ ] Docker images built and pushed to ECR
- [ ] Current deployment is healthy: check EC2 instances

## Phase 1: Infrastructure Updates

### 1. Configure Variables
- [ ] Copy `terraform.tfvars.example` to `terraform.tfvars`
- [ ] Update `allowed_ssh_ip` with your current IP
- [ ] Set `domain_name = "crucible.veylan.dev"`
- [ ] Add IPs to `allowed_web_ips` array
- [ ] Verify `active_deployment_color` matches your target

### 2. Deploy Infrastructure
```bash
cd infrastructure/terraform
```
- [ ] Run `tofu plan` and review changes:
  - [ ] Elastic IPs will be created
  - [ ] Security groups will be updated
  - [ ] Nginx will be configured on new instances
- [ ] Run `tofu apply` and confirm
- [ ] Note the Elastic IP outputs

### 3. Verify Infrastructure
- [ ] Check AWS Console for new Elastic IPs
- [ ] Verify security group rules updated
- [ ] SSH to instance works with new Elastic IP

## Phase 2: DNS Configuration

### Option A: External DNS (Vercel/Cloudflare)
- [ ] Get Elastic IP: `tofu output elastic_ips`
- [ ] Log into DNS provider
- [ ] Add A record:
  - Name: `crucible`
  - Type: `A`
  - Value: `<elastic-ip-for-active-color>`
  - TTL: `60` (for easy updates)
- [ ] Wait for DNS propagation (5-30 minutes)
- [ ] Verify: `nslookup crucible.veylan.dev`

### Option B: Route 53
- [ ] Set `create_route53_zone = true` in `terraform.tfvars`
- [ ] Run `tofu apply`
- [ ] Get nameservers: `tofu output nameservers`
- [ ] Update domain registrar with Route 53 nameservers
- [ ] Wait for propagation (up to 48 hours)

## Phase 3: Service Deployment

### 1. Deploy Latest Code
- [ ] Push code to main branch (triggers deployment)
- [ ] OR manually run: `gh workflow run deploy-compose.yml -f deployment_color=<color>`
- [ ] Monitor deployment in GitHub Actions

### 2. Verify Services
- [ ] SSH to instance: `tofu output ssh_commands_elastic`
- [ ] Check Docker services: `docker-compose ps`
- [ ] Check logs: `docker-compose logs --tail=50`
- [ ] Test internally: `curl http://localhost:8080/api/status`

## Phase 4: Nginx Verification

### 1. Check Nginx Status
```bash
# On EC2 instance
sudo systemctl status nginx
sudo nginx -t
```

### 2. Test HTTP Access
- [ ] From whitelisted IP: `curl http://crucible.veylan.dev`
- [ ] Should redirect to HTTPS (will fail without cert)
- [ ] Check Nginx logs: `sudo tail -f /var/log/nginx/access.log`

## Phase 5: SSL Certificate

### 1. Obtain Certificate
```bash
# On EC2 instance
sudo certbot --nginx -d crucible.veylan.dev \
  --non-interactive --agree-tos \
  --email your-email@example.com
```

### 2. Verify HTTPS
- [ ] Test: `curl https://crucible.veylan.dev/api/status`
- [ ] Check certificate: `curl -vI https://crucible.veylan.dev 2>&1 | grep -A 5 "SSL certificate"`
- [ ] Verify auto-renewal: `sudo certbot renew --dry-run`

## Phase 6: Security Verification

### 1. Test Access Control
- [ ] From whitelisted IP: Should work
- [ ] From non-whitelisted IP: Should timeout
- [ ] Direct port access should fail: `curl http://crucible.veylan.dev:8080`

### 2. Test Application
- [ ] API endpoint: `curl https://crucible.veylan.dev/api/status`
- [ ] Frontend loads: Browse to `https://crucible.veylan.dev`
- [ ] WebSocket works: Check browser console
- [ ] Submit test evaluation

### 3. Monitor Logs
- [ ] No errors in Nginx: `sudo tail -f /var/log/nginx/error.log`
- [ ] Application healthy: `docker-compose logs --tail=100`
- [ ] No security warnings: `sudo journalctl -u nginx -n 50`

## Phase 7: Lock Down Ports (After Testing)

### 1. Update Docker Compose
- [ ] Edit `docker-compose.yml`
- [ ] Change ports to bind localhost only:
  ```yaml
  ports:
    - "127.0.0.1:8080:8080"
  ```
- [ ] Restart services: `docker-compose up -d`

### 2. Update Security Group
- [ ] Remove port 8080 ingress rule from `ec2.tf`
- [ ] Run `tofu apply`
- [ ] Verify services still accessible via HTTPS

## Post-Deployment

### Monitoring Setup
- [ ] Set up CloudWatch alarms for CPU/memory
- [ ] Configure billing alerts
- [ ] Set up uptime monitoring (e.g., UptimeRobot)

### Documentation
- [ ] Document Elastic IPs in team wiki
- [ ] Share access instructions with team
- [ ] Update runbooks with new URLs

### Backup Procedures
- [ ] Test SSH access still works
- [ ] Verify backup access methods documented
- [ ] Ensure rollback plan is clear

## Rollback Plan

If issues arise:

1. **Quick Fix**: Re-add your IP to security group manually in AWS Console
2. **DNS Rollback**: Point DNS back to old IP if needed
3. **Port Access**: Temporarily re-enable port 8080 in security group
4. **Full Rollback**: 
   ```bash
   tofu apply -var="active_deployment_color=blue"  # Switch back
   ```

## Success Criteria

- [ ] Platform accessible at https://crucible.veylan.dev
- [ ] Only whitelisted IPs can access
- [ ] SSL certificate valid and auto-renewing
- [ ] All services healthy
- [ ] Direct port access blocked
- [ ] Monitoring active
- [ ] Team can access platform

## Notes

- Keep `terraform.tfvars` secure (contains IP whitelist)
- Test everything in stages - don't rush
- Have AWS Console open for quick fixes
- Keep SSH access as backup