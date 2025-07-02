# Environment Variables in Multi-Host Docker Compose

## The Translation Challenge

In a multi-host Docker Compose setup, environment variables must contain actual network-reachable addresses, not Docker service names. Here's how this works in practice:

## Single Host (What We're Used To)

```yaml
# docker-compose.yml - all on one host
services:
  api:
    environment:
      # Docker DNS resolves 'postgres' to container IP
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      #                                      ^^^^^^^^
      #                                   Docker service name
  
  postgres:
    image: postgres:15
```

## Multi-Host Reality

### Option 1: Direct IP Addresses

```yaml
# Host A: docker-compose.edge.yml
services:
  nginx:
    environment:
      # Must use actual IP of Host B
      - BACKEND_URL=http://10.0.1.20:8080
      #                    ^^^^^^^^^^
      #                  Private IP of Host B

# Host B: docker-compose.backend.yml
services:
  api:
    ports:
      - "8080:8080"  # MUST expose on host network
    environment:
      # Must use actual IP of Host C
      - DATABASE_URL=postgresql://user:pass@10.0.1.30:5432/db
      #                                     ^^^^^^^^^^
      #                                  Private IP of Host C
```

**Deployment Script Must Inject IPs:**
```bash
#!/bin/bash
# Get actual IPs from AWS
BACKEND_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Role,Values=backend" \
  --query "Reservations[0].Instances[0].PrivateIpAddress" \
  --output text)

DB_IP=$(aws ec2 describe-instances \
  --filters "Name=tag:Role,Values=database" \
  --query "Reservations[0].Instances[0].PrivateIpAddress" \
  --output text)

# Deploy to edge with backend IP
ssh edge-host <<EOF
  export BACKEND_IP=$BACKEND_IP
  docker-compose -f docker-compose.edge.yml up -d
EOF

# Deploy to backend with database IP
ssh backend-host <<EOF
  export DATABASE_HOST=$DB_IP
  docker-compose -f docker-compose.backend.yml up -d
EOF
```

### Option 2: DNS Names (Better)

```yaml
# Using Route53 Private Hosted Zone or /etc/hosts
services:
  api:
    environment:
      # DNS name that resolves to actual IP
      - DATABASE_URL=postgresql://user:pass@db.internal.crucible:5432/db
      #                                     ^^^^^^^^^^^^^^^^^^^
      #                                     DNS name → 10.0.1.30
```

**Setup Private DNS:**
```bash
# Create Route53 private hosted zone
aws route53 create-hosted-zone \
  --name internal.crucible \
  --vpc VPCRegion=us-west-2,VPCId=vpc-xxx \
  --hosted-zone-config PrivateZone=true

# Add DNS records for each service
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "db.internal.crucible",
        "Type": "A",
        "TTL": 60,
        "ResourceRecords": [{"Value": "10.0.1.30"}]
      }
    }]
  }'
```

### Option 3: Service Discovery (Most Flexible)

```yaml
# Each service registers itself
services:
  api:
    image: crucible/api
    environment:
      - CONSUL_HOST=consul.internal.crucible
      - SERVICE_NAME=api
      - SERVICE_PORT=8080
    # Startup script registers with Consul
```

**Service Registration Script:**
```python
# In container startup
import consul
import socket

consul_client = consul.Consul(host=os.getenv('CONSUL_HOST'))

# Get container's host IP (not container IP!)
host_ip = socket.gethostbyname(socket.gethostname())

# Register this service instance
consul_client.agent.service.register(
    name='api',
    service_id=f'api-{host_ip}',
    address=host_ip,  # Host IP, not container IP!
    port=8080,        # Host port, not container port!
    check=consul.Check.http(f'http://{host_ip}:8080/health', interval='30s')
)
```

**Service Discovery in Application:**
```python
# In nginx or api container
def get_backend_url():
    consul_client = consul.Consul(host=os.getenv('CONSUL_HOST'))
    _, services = consul_client.health.service('api', passing=True)
    
    if services:
        service = services[0]
        host = service['Service']['Address']
        port = service['Service']['Port']
        return f"http://{host}:{port}"
    
    raise Exception("No healthy API service found")
```

## Real-World Example: Complete Multi-Host Setup

### Infrastructure Setup (Terraform)
```hcl
# Create instances with predictable IPs
resource "aws_instance" "edge" {
  private_ip = "10.0.1.10"
  tags = {
    Name = "crucible-edge"
    Role = "edge"
  }
}

resource "aws_instance" "backend" {
  private_ip = "10.0.1.20"
  tags = {
    Name = "crucible-backend"
    Role = "backend"
  }
}

resource "aws_instance" "database" {
  private_ip = "10.0.1.30"
  tags = {
    Name = "crucible-database"
    Role = "database"
  }
}
```

### Deployment Configuration
```yaml
# deploy-config.yml
environments:
  production:
    edge:
      host: 10.0.1.10
      env:
        BACKEND_HOST: 10.0.1.20
        BACKEND_PORT: 8080
    
    backend:
      host: 10.0.1.20
      env:
        DATABASE_HOST: 10.0.1.30
        DATABASE_PORT: 5432
        REDIS_HOST: 10.0.1.30
        REDIS_PORT: 6379
    
    database:
      host: 10.0.1.30
      env:
        POSTGRES_PASSWORD: ${SECRETS.DB_PASSWORD}
```

### Docker Compose Templates
```yaml
# docker-compose.backend.yml
services:
  api:
    image: ${REGISTRY}/api:${VERSION}
    ports:
      - "8080:8080"  # CRITICAL: Must expose on host
    environment:
      # These MUST be actual IPs or DNS names
      - DATABASE_URL=postgresql://user:${DB_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/db
      - REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}
    networks:
      - backend-net
    extra_hosts:
      # Optional: Add custom DNS entries
      - "db.internal:${DATABASE_HOST}"
      - "cache.internal:${REDIS_HOST}"
```

### Deployment Script
```bash
#!/bin/bash
# deploy-multi-host.sh

# Load configuration
CONFIG_FILE="deploy-config.yml"

# Function to deploy to a specific host
deploy_to_host() {
    local role=$1
    local host=$(yq e ".environments.production.$role.host" $CONFIG_FILE)
    local compose_file="docker-compose.$role.yml"
    
    # Build environment variable string
    ENV_VARS=""
    while IFS= read -r line; do
        ENV_VARS="$ENV_VARS export $line;"
    done < <(yq e ".environments.production.$role.env | to_entries | .[] | .key + \"=\" + .value" $CONFIG_FILE)
    
    # Deploy
    ssh ubuntu@$host <<EOF
        $ENV_VARS
        docker-compose -f $compose_file pull
        docker-compose -f $compose_file up -d
EOF
}

# Deploy to all hosts
deploy_to_host "database"
sleep 10  # Let database start
deploy_to_host "backend"
sleep 10  # Let backend start
deploy_to_host "edge"
```

## Key Points to Remember

1. **Container Names Don't Work Across Hosts**
   - `postgres` only works within the same Docker network
   - Must use IPs or DNS names for cross-host communication

2. **Ports Must Be Exposed on Host Network**
   ```yaml
   ports:
     - "8080:8080"  # Required for other hosts to reach this service
   ```

3. **Environment Variables Need Real Values**
   ```bash
   # Wrong - won't work across hosts
   DATABASE_URL=postgresql://postgres:5432/db
   
   # Right - actual network address
   DATABASE_URL=postgresql://10.0.1.30:5432/db
   DATABASE_URL=postgresql://db.internal.crucible:5432/db
   DATABASE_URL=postgresql://rds.amazonaws.com:5432/db
   ```

4. **Consider Using Managed Services**
   - RDS eliminates database host discovery
   - ElastiCache eliminates Redis host discovery
   - Reduces the number of environment variables to manage

5. **Progressive Enhancement Path**
   - Start with hardcoded IPs (simplest)
   - Move to DNS names (more maintainable)
   - Add service discovery (most flexible)
   - Eventually use orchestration platform (Kubernetes)

## Testing Multi-Host Locally

You can simulate multi-host networking locally using multiple Docker networks:

```bash
# Create separate networks to simulate isolation
docker network create host-a
docker network create host-b

# Run services on different networks
docker run --name nginx --network host-a \
  -e BACKEND_URL=http://172.17.0.1:8080 \
  nginx-image

docker run --name api --network host-b \
  -p 8080:8080 \
  api-image

# 172.17.0.1 is the Docker host IP, accessible from containers
```

This helps test that your services work with real IPs before deploying to multiple EC2 instances.