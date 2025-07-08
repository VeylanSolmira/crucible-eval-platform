# t2.micro Memory Optimization

## Problem
t2.micro has only 1GB RAM, but our full stack requires more:

### Current Memory Allocation (docker-compose.prod.yml)
- API Service: 256MB
- Celery Worker: 512MB  
- Storage Service: 384MB
- Storage Worker: 128MB
- Postgres: 512MB
- Redis (main): 256MB
- Redis (celery): 300MB
- Nginx: 128MB
- Frontend: 128MB
- Flower: 128MB
- Docker Proxy: 64MB
- Executors (x3): 3 × 128MB = 384MB
**Total: ~3.2GB** (3x available memory!)

## Immediate Optimizations Applied

### 1. Reduced Executors from 3 to 2
- Saves: 128MB
- Modified: docker-compose.yml to disable executor-3
- Updated: EXECUTOR_COUNT=2 in celery-worker

### 2. Further Optimizations Needed

#### Option A: Aggressive Memory Limits (Stay on t2.micro)
```yaml
# docker-compose.prod.yml overrides
api-service:
  mem_limit: 128m      # -128MB
celery-worker:
  mem_limit: 256m      # -256MB  
storage-service:
  mem_limit: 256m      # -128MB
postgres:
  mem_limit: 256m      # -256MB
redis:
  mem_limit: 128m      # -128MB
celery-redis:
  mem_limit: 128m      # -172MB
```
Total savings: ~1GB → Total usage: ~2.2GB (still too high)

#### Option B: Disable Non-Critical Services
- Remove Flower (-128MB)
- Use single Redis instance (-300MB)
- Disable one executor (-128MB)
Total savings: ~556MB

#### Option C: Upgrade Instance (Recommended)
- **t3.small** (2GB RAM): $0.0208/hour (~$15/month)
- **t3.medium** (4GB RAM): $0.0416/hour (~$30/month)

## Recommended Approach

1. **Immediate**: Deploy current optimizations (2 executors)
2. **Short-term**: Apply aggressive memory limits + disable Flower
3. **Long-term**: Upgrade to t3.small for stability

## Deployment Commands

```bash
# Copy optimized files to EC2
scp docker-compose.yml docker-compose.prod.yml ubuntu@<EC2_IP>:~/crucible/

# Stop services to free memory
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Remove unused images/containers
sudo docker system prune -a -f

# Start with new limits
sudo systemctl restart crucible-compose.service
```

## Monitoring Memory Usage

```bash
# Check system memory
free -h

# Check container memory
sudo docker stats --no-stream

# Check for OOM kills
sudo dmesg | grep -i "killed process"
journalctl -u docker.service | grep -i oom
```

## Alternative: Minimal Stack for t2.micro

Run only core services:
```bash
# Start only essential services
sudo docker compose up -d postgres redis api-service storage-service nginx
```

This runs the API but without:
- Executors (no code execution)
- Celery (no async tasks)
- Monitoring services