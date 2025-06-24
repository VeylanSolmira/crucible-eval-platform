# Immediate Next Steps: Testing SSL & Production Setup

## Local Testing Checklist

### 1. Test SSL Certificate Flow
```bash
# Clean start
docker compose down -v
docker volume rm metr-eval-platform_ssl-certs

# Test development mode (should generate self-signed)
docker compose up nginx

# Check certificate
curl -k https://localhost/health
openssl s_client -connect localhost:443 -servername localhost

# Test production mode (should fail without certs)
PRODUCTION_MODE=true docker compose up nginx
# Should see: "ERROR: Production mode requires valid SSL certificates"
```

### 2. Test Production Override
```bash
# Copy example to test
cp docker-compose.override.yml.example docker-compose.override.yml

# Test with production compose
docker compose -f docker-compose.yml -f docker-compose.prod.yml up

# Verify:
# - No development ports exposed (8080, 3000, 5432, 6379)
# - Nginx health check works
# - Can access via port 80/443 only
```

### 3. Test Multi-Service Communication
```bash
# Submit evaluation via nginx
curl -X POST http://localhost/api/eval \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello from nginx proxy!\")"}'

# Check logs to verify routing
docker compose logs -f nginx
docker compose logs -f api-service
```

## Remote Deployment Testing

### 1. Pre-deployment Verification
```bash
# Check Terraform state
cd infrastructure/terraform
terraform plan

# Verify SSL certificates exist in SSM
aws ssm get-parameter --name "/crucible-platform/ssl/certificate" --region us-west-2
```

### 2. Deploy Updated Configuration
```bash
# Commit and push changes
git add .
git commit -m "Add containerized nginx with production SSL support"
git push origin main

# Trigger deployment (should auto-deploy to blue)
# Or manually:
gh workflow run deploy-compose.yml
```

### 3. Post-deployment Checks
```bash
# SSH to instance
ssh ubuntu@<instance-ip>

# Check SSL certificates were fetched
sudo ls -la /etc/nginx/ssl/

# Check nginx container is healthy
docker compose ps
docker compose logs nginx

# Test HTTPS is working
curl https://<your-domain>/health
```

### 4. Rollback Plan
If issues arise:
```bash
# Quick rollback to previous version
cd /home/ubuntu/crucible
git checkout <previous-commit>
docker compose down
docker compose up -d
```

## After Successful Deployment

Once SSL and production setup are verified, move to the Frontend Sprint:

1. **Set up development environment**
   ```bash
   cd frontend
   npm install @monaco-editor/react recharts
   npm run dev
   ```

2. **Start with MVP features** (2 days):
   - Day 1: Monaco editor + templates + live output
   - Day 2: History view + error display + basic export

3. **Get researcher feedback early**:
   - Deploy MVP to staging
   - Share with 2-3 AI safety researchers
   - Iterate based on their actual usage patterns

## Key Decision Points

### SSL Certificate Management
- ✅ Current: Host fetches, container mounts
- Future: Consider cert-manager in K8s
- Future: Consider AWS Certificate Manager with ALB

### Frontend Architecture
- Start with client-side state (React hooks)
- Add Redux/Zustand when state gets complex
- Consider React Query for API caching

### Monitoring Next Steps
- Add Prometheus metrics to nginx
- Track rate limit hits
- Monitor SSL certificate expiry
- Set up alerts for failures

## Success Criteria

### For SSL/Production Setup:
- [ ] HTTPS works with valid certificate
- [ ] HTTP redirects to HTTPS
- [ ] Rate limiting prevents abuse
- [ ] Development can't accidentally expose secrets
- [ ] Production mode fails safely

### For Frontend MVP:
- [ ] Researchers prefer it over local Python
- [ ] <30s from code to seeing results
- [ ] Clear error messages researchers understand
- [ ] Can handle 10-minute running evaluations
- [ ] Export results for papers/reports