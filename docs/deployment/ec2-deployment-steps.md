# EC2 Deployment Steps for Build-Only Services Fix

## Quick Deployment Guide

After updating docker-compose.yml to handle build-only services, follow these steps to deploy to EC2:

### 1. Copy Updated File to EC2
```bash
# From your local machine
scp docker-compose.yml ubuntu@<EC2_IP>:~/crucible/docker-compose.yml
```

### 2. SSH to EC2 Instance
```bash
ssh ubuntu@<EC2_IP>
cd ~/crucible
```

### 3. Test Docker Compose Pull
```bash
# This should now work without "undefined service" errors
sudo docker compose pull
```

### 4. Restart Services
```bash
# Option A: Restart the systemd service
sudo systemctl restart crucible-compose.service

# Option B: Manual restart
sudo docker compose down
sudo docker compose up -d
```

### 5. Verify Deployment
```bash
# Check service status
sudo docker compose ps

# Check logs for any issues
sudo docker compose logs -f --tail=50

# Verify build-only services exited cleanly
sudo docker ps -a | grep -E "base|executor-ml"
```

## Expected Behavior

1. **Build-only services** (base, executor-ml-image):
   - Will show as "Exited (0)" in `docker ps -a`
   - This is normal and expected
   - They exit immediately with success

2. **Runtime services**:
   - Should all be running and healthy
   - No dependency errors

## Troubleshooting

If you see errors:
1. Check ECR login: `sudo /usr/local/bin/docker-ecr-login`
2. Verify environment variables: `cat .env | grep IMAGE`
3. Check service logs: `sudo docker compose logs <service-name>`

## Memory Monitoring

Since we're on a t2.micro:
```bash
# Check memory usage
free -h
docker stats --no-stream

# If memory issues, check CloudWatch metrics (once Terraform is applied)
```