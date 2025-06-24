# Resource Constraints for t2.micro Deployment

## t2.micro Specifications
- **vCPUs**: 1
- **RAM**: 1 GB
- **Network**: Low to Moderate

## Service Resource Requirements

### Current Services (Modular Architecture)
| Service | RAM (estimated) | Notes |
|---------|-----------------|-------|
| docker-proxy | 50 MB | Lightweight proxy |
| postgres | 200 MB | Database |
| crucible-platform | 200 MB | Main API (Python) |
| crucible-frontend | 100 MB | React app (Node.js) |
| queue | 100 MB | Queue service |
| queue-worker | 100 MB | Task router |
| executor-1 | 256 MB | Container spawner |
| **Total** | **1006 MB** | Over capacity! |

### Optimizations Made

1. **Reduced executors from 3 to 1**
   - Saved 512 MB
   - Still maintains isolation architecture
   - Can scale horizontally on larger instances

2. **Added memory limits**
   - docker-proxy: 50m
   - executor: 256m
   - Prevents any service from consuming all RAM

3. **Services we could disable for development**
   - frontend (save 100 MB) - use API directly
   - Use monolithic mode instead of modular

## Recommendations

### For t2.micro Development
```bash
# Option 1: Run monolithic mode
docker-compose up crucible-platform postgres

# Option 2: Run minimal modular
docker-compose up docker-proxy queue queue-worker executor-1 postgres
```

### For Production (t2.small or larger)
- **t2.small** (2 GB RAM): Can run all services with 1-2 executors
- **t2.medium** (4 GB RAM): Can run 3+ executors comfortably
- **Consider ECS/EKS**: For true production scaling

## Memory Monitoring
```bash
# Check actual memory usage
docker stats --no-stream

# Check container limits
docker inspect <container> | grep -i memory
```

## Future Optimizations
1. Use Alpine-based images where possible
2. Multi-stage builds to reduce image size
3. Consider serverless for executors (AWS Lambda)
4. Use managed services (RDS for Postgres)