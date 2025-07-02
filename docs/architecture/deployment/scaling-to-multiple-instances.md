# Scaling from Single EC2 to Multiple Instances and Kubernetes

## Current Architecture: Single EC2 with Docker Compose

```
Internet → EC2 Instance → Docker Network
                          ├── Nginx Container (ports 80/443)
                          ├── API Container
                          ├── Frontend Container
                          ├── Queue Worker Container
                          ├── Storage Worker Container
                          ├── PostgreSQL Container
                          └── Redis Container
```

**Advantages:**
- Simple networking (all containers on same Docker bridge)
- Easy service discovery (container names as hostnames)
- Single point of SSL termination
- Minimal infrastructure complexity

**Limitations:**
- Single point of failure
- Limited scalability
- Resource contention between services
- No true high availability

## Evolution Path 1: Multiple EC2 with Role Separation

### Stage 1: Edge/Backend Split (2-3 instances)

```
                     ┌─────────────────┐
Internet ─────────►  │ Edge EC2        │
                     │ - Nginx         │
                     │ - SSL Certs     │
                     └────────┬────────┘
                              │ Private Network
                     ┌────────▼────────┐
                     │ Backend EC2     │
                     │ - API           │
                     │ - Workers       │
                     │ - PostgreSQL   │
                     │ - Redis        │
                     └─────────────────┘
```

**Infrastructure Changes:**

```hcl
# terraform/modules/ec2/main.tf
resource "aws_instance" "edge" {
  count = var.edge_instance_count
  
  tags = {
    Name = "${var.project_name}-edge-${count.index}"
    Role = "edge"
    FetchSSL = "true"
  }
  
  user_data = templatefile("${path.module}/templates/userdata-edge.sh.tpl", {
    fetch_ssl = true
    services = ["nginx"]
  })
}

resource "aws_instance" "backend" {
  count = var.backend_instance_count
  
  tags = {
    Name = "${var.project_name}-backend-${count.index}"
    Role = "backend"
    FetchSSL = "false"
  }
  
  user_data = templatefile("${path.module}/templates/userdata-backend.sh.tpl", {
    fetch_ssl = false
    services = ["api", "workers", "postgres", "redis"]
  })
}
```

**Docker Compose Split:**

```yaml
# docker-compose.edge.yml
services:
  nginx:
    image: ${PROJECT_NAME}/nginx:latest
    ports:
      - "80:80"
      - "443:443"
    environment:
      - BACKEND_URL=http://${BACKEND_PRIVATE_IP}:8080
    volumes:
      - /etc/nginx/ssl:/etc/nginx/ssl:ro

# docker-compose.backend.yml
services:
  api-service:
    image: ${PROJECT_NAME}/api:latest
    ports:
      - "8080:8080"  # Only on private network
  
  postgres:
    image: postgres:15
    volumes:
      - postgres-data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    volumes:
      - redis-data:/data
```

**Deployment Orchestration:**

```yaml
# .github/workflows/deploy-multi-instance.yml
- name: Deploy to Edge Instances
  run: |
    EDGE_INSTANCES=$(aws ec2 describe-instances \
      --filters "Name=tag:Role,Values=edge" \
      --query "Reservations[*].Instances[*].InstanceId")
    
    aws ssm send-command \
      --instance-ids $EDGE_INSTANCES \
      --document-name "AWS-RunShellScript" \
      --parameters "commands=['docker-compose -f docker-compose.edge.yml up -d']"

- name: Deploy to Backend Instances
  run: |
    BACKEND_INSTANCES=$(aws ec2 describe-instances \
      --filters "Name=tag:Role,Values=backend" \
      --query "Reservations[*].Instances[*].InstanceId")
    
    # Get private IPs for backend configuration
    BACKEND_IPS=$(aws ec2 describe-instances \
      --filters "Name=tag:Role,Values=backend" \
      --query "Reservations[*].Instances[*].PrivateIpAddress")
    
    aws ssm send-command \
      --instance-ids $BACKEND_INSTANCES \
      --document-name "AWS-RunShellScript" \
      --parameters "commands=['docker-compose -f docker-compose.backend.yml up -d']"
```

### Stage 2: Service-Based Separation (3-5 instances)

```
                     ┌─────────────────┐
Internet ─────────►  │ Edge EC2        │
                     │ - Nginx Only    │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ API EC2 │          │Worker EC2│          │ DB EC2  │
   │ - API   │          │ - Queue  │          │ - PG    │
   │ Service │          │ - Storage│          │ - Redis │
   └─────────┘          └──────────┘          └─────────┘
```

**Network Challenges & Solutions:**

1. **Service Discovery**
   ```yaml
   # Use environment variables for service locations
   services:
     api-service:
       environment:
         - DATABASE_URL=postgresql://user:pass@${DB_INSTANCE_IP}:5432/db
         - REDIS_URL=redis://${DB_INSTANCE_IP}:6379
   ```

2. **Shared Storage**
   ```yaml
   # Option 1: EFS for shared files
   volumes:
     shared-storage:
       driver: local
       driver_opts:
         type: nfs
         o: addr=${EFS_DNS_NAME},nfsvers=4.1
         device: :${EFS_MOUNT_PATH}
   
   # Option 2: S3 for object storage
   services:
     storage-worker:
       environment:
         - STORAGE_BACKEND=s3
         - S3_BUCKET=${PROJECT_NAME}-storage
   ```

3. **Database Access**
   ```yaml
   # Use RDS instead of containerized PostgreSQL
   services:
     api-service:
       environment:
         - DATABASE_URL=${RDS_CONNECTION_STRING}
   ```

## Evolution Path 2: AWS Application Load Balancer

### ALB with Target Groups (Recommended for 3-10 instances)

```
                     ┌─────────────────┐
Internet ─────────►  │      ALB        │ ◄── SSL/ACM Certificate
                     │ (SSL Term)      │
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
   │ EC2-1   │          │ EC2-2   │          │ EC2-3   │
   │ All     │          │ All     │          │ All     │
   │Services │          │Services │          │Services │
   └─────────┘          └─────────┘          └─────────┘
```

**Benefits:**
- AWS manages SSL certificates (ACM)
- Built-in health checks
- Automatic failover
- Path-based routing
- No nginx needed

**Terraform Configuration:**

```hcl
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = var.public_subnet_ids
}

resource "aws_lb_target_group" "api" {
  name     = "${var.project_name}-api"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  
  health_check {
    path = "/api/health"
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  certificate_arn   = aws_acm_certificate.main.arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
```

## Evolution Path 3: Container Orchestration

### Docker Swarm (Stepping Stone)

```yaml
# docker-stack.yml
version: '3.8'

services:
  nginx:
    image: ${PROJECT_NAME}/nginx:latest
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == manager
    ports:
      - "80:80"
      - "443:443"
    networks:
      - crucible-net
  
  api:
    image: ${PROJECT_NAME}/api:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.labels.type == backend
    networks:
      - crucible-net

networks:
  crucible-net:
    driver: overlay
    attachable: true
```

### Kubernetes (Final Evolution)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: crucible-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - crucible.example.com
      secretName: crucible-tls
  rules:
    - host: crucible.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 8080
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
```

## Network Evolution Comparison

### Docker Compose (Single Host)
```yaml
# Service discovery via container names
services:
  api:
    environment:
      - DATABASE_URL=postgresql://postgres:5432/db
      - REDIS_URL=redis://redis:6379
```

### Multi-Host Docker
```yaml
# Service discovery via environment variables
services:
  api:
    environment:
      - DATABASE_URL=postgresql://${DB_HOST}:5432/db
      - REDIS_URL=redis://${REDIS_HOST}:6379
```

### Kubernetes
```yaml
# Service discovery via DNS
env:
  - name: DATABASE_URL
    value: postgresql://postgres-service.default.svc.cluster.local:5432/db
  - name: REDIS_URL
    value: redis://redis-service.default.svc.cluster.local:6379
```

## Migration Strategy

### Phase 1: Prepare for Distribution
1. **Externalize State**
   - Move to RDS for PostgreSQL
   - Use ElastiCache for Redis
   - Use S3/EFS for file storage

2. **Update Configuration**
   - Use environment variables for all service endpoints
   - Remove hardcoded container names
   - Add health check endpoints

3. **Test Locally**
   ```bash
   # Simulate multi-host with multiple compose files
   docker-compose -f docker-compose.yml \
                  -f docker-compose.external-db.yml \
                  up
   ```

### Phase 2: Split Services
1. **Start with Stateless Services**
   - Frontend can run anywhere
   - API can scale horizontally
   - Workers can run on multiple hosts

2. **Keep Stateful Services Together**
   - Database and cache on same instance initially
   - Or migrate to managed services

### Phase 3: Add Load Balancing
1. **Deploy ALB**
   - Point to all backend instances
   - Use health checks for availability

2. **Update DNS**
   - Point domain to ALB
   - Remove nginx if using ALB

### Phase 4: Full Orchestration
1. **Choose Platform**
   - ECS for AWS-native
   - Kubernetes for portability
   - Both support the same container images

2. **Gradual Migration**
   - Run both systems in parallel
   - Migrate services one at a time
   - Validate at each step

## Key Decisions for Scaling

### 1. State Management
- **Local Files** → S3/EFS
- **PostgreSQL** → RDS
- **Redis** → ElastiCache
- **SSL Certificates** → ALB/ACM or K8s Secrets

### 2. Service Discovery
- **Container Names** → Environment Variables → DNS
- **Hardcoded IPs** → Service Discovery (Consul/K8s DNS)
- **Static Config** → Dynamic Configuration

### 3. Deployment Strategy
- **Manual** → CI/CD with instance targeting
- **docker-compose** → Orchestration platform
- **Single deploy** → Rolling updates

### 4. Monitoring Evolution
- **docker logs** → CloudWatch Logs
- **Local metrics** → Prometheus/CloudWatch
- **No tracing** → Distributed tracing (X-Ray/Jaeger)

## Cost Considerations

### Single EC2 (Current)
- 1 × t3.medium = ~$30/month
- Simple, low cost
- Limited availability

### Multi-EC2 with ALB
- 3 × t3.small = ~$45/month  
- 1 × ALB = ~$20/month
- RDS = ~$30/month
- Total: ~$95/month

### Kubernetes (EKS)
- EKS Control Plane = $73/month
- 3 × t3.medium nodes = ~$90/month
- ALB = ~$20/month
- Total: ~$183/month

## Recommendations

1. **For MVP/Demo**: Stay with single EC2
2. **For Production (Small)**: Use ALB + 2-3 EC2 instances
3. **For Production (Large)**: Migrate to Kubernetes
4. **For Enterprise**: Consider ECS for AWS lock-in benefits

The key is to make your application **distribution-ready** even if running on a single host. This means:
- No hardcoded service locations
- Externalized configuration
- Stateless services where possible
- Health checks on everything
- Structured logging with correlation IDs