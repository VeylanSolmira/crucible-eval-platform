# Docker Networking: From Single Host to Multi-Host

## The Challenge: Container Networking Across Hosts

When Docker Compose runs on a single host, networking is simple - all containers share a bridge network and can communicate using service names. But when you split services across multiple hosts, this breaks down.

## Single Host: How Docker Compose Networking Works

```yaml
# docker-compose.yml on single host
services:
  nginx:
    image: nginx
    # Can use service names directly
    environment:
      - BACKEND_URL=http://api:8080
  
  api:
    image: api
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
  
  postgres:
    image: postgres
  
  redis:
    image: redis
```

**Behind the scenes:**
```bash
# Docker creates a bridge network
docker network create crucible_default

# Each container gets an IP on this network
nginx:    172.18.0.2
api:      172.18.0.3
postgres: 172.18.0.4
redis:    172.18.0.5

# Docker's internal DNS resolves service names
api → 172.18.0.3
postgres → 172.18.0.4
```

## Multi-Host Challenge: Networks Don't Span Hosts

```
Host A                          Host B
┌─────────────────┐            ┌─────────────────┐
│ nginx container │            │ api container   │
│ 172.18.0.2     │            │ 172.19.0.2     │
│                 │            │                 │
│ "http://api" ???│            │ "postgres" ???  │
└─────────────────┘            └─────────────────┘
       ↓                                ↓
  Bridge Network A              Bridge Network B
  (172.18.0.0/16)              (172.19.0.0/16)
```

**The Problems:**
1. Service names don't resolve across hosts
2. Container IPs aren't routable between hosts
3. Each host has its own isolated Docker network

## Solution Patterns

### Pattern 1: Manual IP Configuration

**Simplest but most brittle approach:**

```yaml
# Host A: docker-compose.edge.yml
services:
  nginx:
    environment:
      # Use actual private IP of Host B
      - BACKEND_URL=http://10.0.1.20:8080

# Host B: docker-compose.backend.yml  
services:
  api:
    ports:
      - "8080:8080"  # Expose on host network
    environment:
      # Use actual private IP of Host C
      - DB_HOST=10.0.1.30
      - DB_PORT=5432
```

**Deployment updates required:**
```bash
# Deploy with actual IPs
BACKEND_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Role,Values=backend" \
  --query "Reservations[0].Instances[0].PrivateIpAddress" \
  --output text)

ssh edge-host "BACKEND_IP=$BACKEND_IP docker-compose up -d"
```

### Pattern 2: Host Networking Mode

**Remove network isolation - containers use host network directly:**

```yaml
services:
  api:
    network_mode: host
    # Now listens directly on host's port 8080
    environment:
      - LISTEN_PORT=8080
```

**Pros:**
- Simple port access
- No port mapping needed
- Better performance

**Cons:**
- No network isolation
- Port conflicts possible
- Less secure

### Pattern 3: Overlay Networks (Docker Swarm)

**Docker's built-in solution for multi-host:**

```bash
# Initialize swarm on manager
docker swarm init --advertise-addr 10.0.1.10

# Join workers
docker swarm join --token SWMTKN-1-xxx 10.0.1.10:2377

# Deploy stack
docker stack deploy -c docker-stack.yml crucible
```

```yaml
# docker-stack.yml
version: '3.8'
services:
  nginx:
    image: nginx
    deploy:
      placement:
        constraints: [node.labels.role == edge]
    # Service names work across hosts!
    environment:
      - BACKEND_URL=http://api:8080
  
  api:
    image: api
    deploy:
      placement:
        constraints: [node.labels.role == backend]

networks:
  default:
    driver: overlay
    attachable: true
```

### Pattern 4: Service Mesh (Advanced)

**Add a network layer for service discovery:**

```yaml
# Using Consul for service discovery
services:
  consul:
    image: consul
    ports:
      - "8500:8500"
      - "8600:8600/udp"
  
  api:
    image: api
    environment:
      - CONSUL_HOST=consul
    # Registers itself with Consul
  
  nginx:
    image: nginx
    environment:
      - CONSUL_HOST=consul
    # Discovers api service via Consul
```

### Pattern 5: External Load Balancers

**Let AWS handle the networking:**

```
Internet → ALB → Target Group → EC2 Instances
                                 ├── Host A (api)
                                 ├── Host B (api)
                                 └── Host C (api)
```

```yaml
# Each host runs same services
services:
  api:
    image: api
    ports:
      - "8080:8080"
    environment:
      # Use managed services
      - DATABASE_URL=${RDS_ENDPOINT}
      - REDIS_URL=${ELASTICACHE_ENDPOINT}
```

## Practical Migration Path

### Step 1: Make Services Network-Agnostic

```yaml
# Before: Hardcoded service names
environment:
  - DATABASE_URL=postgresql://postgres:5432/db

# After: Configurable endpoints  
environment:
  - DATABASE_URL=${DATABASE_URL:-postgresql://postgres:5432/db}
```

### Step 2: Externalize Stateful Services

```yaml
# Local development: Use containers
DATABASE_URL=postgresql://postgres:5432/db

# Production: Use managed services
DATABASE_URL=postgresql://prod.rds.amazonaws.com:5432/db
```

### Step 3: Add Service Health Checks

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 3s
      retries: 3
```

### Step 4: Implement Service Discovery

**Option A: DNS-based (Simple)**
```bash
# Use Route53 private hosted zone
api.internal.example.com → Backend IPs
db.internal.example.com → RDS endpoint
```

**Option B: Dynamic (Complex but flexible)**
```python
# Service registration
consul.agent.service.register(
    name="api",
    service_id=f"api-{instance_id}",
    address=private_ip,
    port=8080,
    check=Check.http(f"http://{private_ip}:8080/health", interval="30s")
)

# Service discovery
api_endpoints = consul.health.service("api", passing=True)[1]
```

## Configuration Patterns for Multi-Host

### Environment-Specific Compose Files

```yaml
# docker-compose.yml (base)
services:
  api:
    image: ${PROJECT_NAME}/api:latest
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-info}

# docker-compose.prod.yml (overrides)
services:
  api:
    environment:
      - DATABASE_URL=${RDS_ENDPOINT}
      - REDIS_URL=${ELASTICACHE_ENDPOINT}

# docker-compose.dev.yml (local overrides)
services:
  api:
    environment:
      - DATABASE_URL=postgresql://postgres:5432/db
      - REDIS_URL=redis://redis:6379
```

### Deployment Script Example

```bash
#!/bin/bash
# deploy-to-multi-host.sh

# Get infrastructure details
EDGE_IPS=$(aws ec2 describe-instances \
  --filters "Name=tag:Role,Values=edge" \
  --query "Reservations[*].Instances[*].PrivateIpAddress" \
  --output text)

BACKEND_IPS=$(aws ec2 describe-instances \
  --filters "Name=tag:Role,Values=backend" \
  --query "Reservations[*].Instances[*].PrivateIpAddress" \
  --output text)

DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier crucible-db \
  --query "DBInstances[0].Endpoint.Address" \
  --output text)

# Deploy to edge instances
for ip in $EDGE_IPS; do
  ssh ubuntu@$ip <<EOF
    export BACKEND_IPS="$BACKEND_IPS"
    export COMPOSE_FILE=docker-compose.yml:docker-compose.edge.yml
    docker-compose pull
    docker-compose up -d
EOF
done

# Deploy to backend instances
for ip in $BACKEND_IPS; do
  ssh ubuntu@$ip <<EOF
    export DATABASE_URL="postgresql://user:pass@$DB_ENDPOINT:5432/db"
    export COMPOSE_FILE=docker-compose.yml:docker-compose.backend.yml
    docker-compose pull
    docker-compose up -d
EOF
done
```

## Key Takeaways

1. **Single Host Networking is Simple**
   - Docker handles everything
   - Service names "just work"
   - Great for development

2. **Multi-Host Requires Planning**
   - No automatic service discovery
   - Must expose ports on host network
   - Need external coordination

3. **Design for Distribution Early**
   - Use environment variables
   - Don't hardcode service names
   - Add health checks everywhere

4. **Progressive Enhancement**
   - Start with manual IPs
   - Add load balancer for production
   - Consider orchestration for scale

5. **Managed Services Simplify Multi-Host**
   - RDS eliminates database networking
   - ElastiCache eliminates Redis networking
   - ALB eliminates nginx networking

The journey from single-host to multi-host is really about moving from Docker's implicit networking magic to explicit network configuration. The good news is that the same container images work in both scenarios - you just need to tell them where to find their dependencies.