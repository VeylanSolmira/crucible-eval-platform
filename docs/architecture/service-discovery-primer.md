# Service Discovery: A Primer

## What is Service Discovery?

You've got it exactly right! Service discovery is essentially a dynamic registry (key-value store) where:
- **Services register themselves**: "I'm api-service and you can reach me at 10.0.1.20:8080"
- **Clients query for services**: "Where can I find api-service?"
- **The registry responds**: "api-service is at 10.0.1.20:8080 (and it's healthy!)"

## Why Do We Need It?

### The Problem
```
Your nginx container needs to talk to 'api-service'
But where is api-service?
- In dev: It's the container named 'api' on the same Docker network
- In prod: It's on a different EC2 instance at... what IP?
- Tomorrow: The IP changed because we redeployed
- Next week: There are 3 instances of api-service
```

### Traditional Solutions (and their problems)
```yaml
# Hardcoded IPs (brittle)
API_URL: http://10.0.1.20:8080

# DNS (better but static)
API_URL: http://api.internal.company.com

# Load Balancer (good but external dependency)
API_URL: http://api-lb.company.com
```

## How Service Discovery Works

### 1. Service Registration
```
┌─────────────────┐
│   API Service   │
│  10.0.1.20:8080 │
└────────┬────────┘
         │ 1. "Hi, I'm api-service at 10.0.1.20:8080"
         ▼
┌─────────────────┐
│Service Registry │
│  (Key-Value)    │
├─────────────────┤
│ api-service:    │
│  - 10.0.1.20    │
│  - port: 8080   │
│  - healthy: yes │
└─────────────────┘
```

### 2. Service Discovery
```
┌─────────────────┐
│  Nginx Service  │
│   Needs API     │
└────────┬────────┘
         │ 2. "Where is api-service?"
         ▼
┌─────────────────┐
│Service Registry │     3. "It's at 10.0.1.20:8080"
└─────────────────┘
```

### 3. Health Checking
```
┌─────────────────┐
│Service Registry │
└────────┬────────┘
         │ Every 30s: "Are you still healthy?"
         ▼
┌─────────────────┐
│   API Service   │     "Yes!" (HTTP 200 on /health)
└─────────────────┘
```

## Service Discovery Patterns

### Pattern 1: Client-Side Discovery
**Client is responsible for finding services**

```python
# In your application code
def get_api_endpoint():
    # Ask registry for healthy instances
    instances = registry.get_healthy_instances('api-service')
    
    # Client picks one (load balancing logic here)
    selected = random.choice(instances)
    
    return f"http://{selected.ip}:{selected.port}"

# Usage
api_url = get_api_endpoint()
response = requests.get(f"{api_url}/data")
```

**Examples**: Consul, Eureka, Zookeeper

### Pattern 2: Server-Side Discovery
**A proxy/load balancer handles discovery**

```nginx
# Your app just uses a stable name
upstream api-service {
    # Nginx dynamically updates this from registry
    server 10.0.1.20:8080;
    server 10.0.1.21:8080;
    server 10.0.1.22:8080;
}
```

**Examples**: AWS ALB + ECS, Kubernetes Services, HAProxy + Consul

## Popular Service Discovery Tools

### 1. Consul (HashiCorp)
**Most popular for Docker/VM environments**

```bash
# Start Consul agent on each host
consul agent -server -bootstrap-expect=3 \
  -data-dir=/tmp/consul \
  -node=server-1 \
  -bind=10.0.1.10

# Register a service
curl -X PUT http://localhost:8500/v1/agent/service/register -d '{
  "ID": "api-1",
  "Name": "api-service",
  "Address": "10.0.1.20",
  "Port": 8080,
  "Check": {
    "HTTP": "http://10.0.1.20:8080/health",
    "Interval": "30s"
  }
}'

# Query for service
curl http://localhost:8500/v1/health/service/api-service?passing
```

**Integration Example:**
```python
import consul
import requests

class ServiceDiscoveryClient:
    def __init__(self):
        self.consul = consul.Consul()
    
    def get_service_url(self, service_name):
        _, services = self.consul.health.service(service_name, passing=True)
        if not services:
            raise Exception(f"No healthy {service_name} instances")
        
        # Simple round-robin
        service = services[0]  # In reality, implement proper LB
        host = service['Service']['Address']
        port = service['Service']['Port']
        
        return f"http://{host}:{port}"

# Usage
client = ServiceDiscoveryClient()
api_url = client.get_service_url('api-service')
response = requests.get(f"{api_url}/data")
```

### 2. Kubernetes Service Discovery
**Built-in via DNS**

```yaml
# Service definition creates DNS entry
apiVersion: v1
kind: Service
metadata:
  name: api-service
spec:
  selector:
    app: api
  ports:
    - port: 8080

# Other pods can use DNS name
# api-service.default.svc.cluster.local
```

**In your app:**
```python
# Kubernetes provides DNS automatically
API_URL = "http://api-service:8080"  # Just works!
```

### 3. AWS Cloud Map
**AWS-native service discovery**

```python
import boto3

client = boto3.client('servicediscovery')

# Register instance
response = client.register_instance(
    ServiceId='srv-xxxx',
    InstanceId='api-instance-1',
    Attributes={
        'AWS_INSTANCE_IPV4': '10.0.1.20',
        'AWS_INSTANCE_PORT': '8080',
    }
)

# Discover instances
response = client.discover_instances(
    NamespaceName='crucible.local',
    ServiceName='api-service',
    HealthStatus='HEALTHY'
)
```

### 4. Eureka (Netflix)
**Popular in Java/Spring ecosystems**

```java
// Service registers itself
@EnableEurekaClient
@SpringBootApplication
public class ApiService {
    // Auto-registers on startup
}

// Client discovers services
@Autowired
private DiscoveryClient discoveryClient;

List<ServiceInstance> instances = 
    discoveryClient.getInstances("api-service");
```

## Implementation Example: Adding Consul to Crucible Platform

### Step 1: Add Consul to Infrastructure
```yaml
# docker-compose.consul.yml
services:
  consul:
    image: consul:latest
    ports:
      - "8500:8500"   # UI and HTTP API
      - "8600:8600/udp"  # DNS
    command: agent -server -bootstrap-expect=1 -ui -client=0.0.0.0
    volumes:
      - consul-data:/consul/data
```

### Step 2: Update Services to Register
```python
# In api-service startup
import consul
import socket
import os

def register_with_consul():
    c = consul.Consul(host='consul')
    
    # Get host IP (not container IP)
    hostname = socket.gethostname()
    host_ip = socket.gethostbyname(hostname)
    
    # Register this instance
    c.agent.service.register(
        name='api-service',
        service_id=f'api-{hostname}',
        address=host_ip,
        port=8080,
        check=consul.Check.http(
            f"http://{host_ip}:8080/health",
            interval="30s",
            timeout="5s"
        )
    )

# Call on startup
register_with_consul()
```

### Step 3: Update Clients to Discover
```python
# In nginx or frontend service
def get_api_endpoint():
    c = consul.Consul(host='consul')
    
    # Get healthy services
    _, services = c.health.service('api-service', passing=True)
    
    if not services:
        # Fallback to environment variable
        return os.getenv('API_URL', 'http://localhost:8080')
    
    # Simple load balancing
    import random
    service = random.choice(services)
    
    return f"http://{service['Service']['Address']}:{service['Service']['Port']}"
```

### Step 4: Use in Application
```python
# Instead of hardcoded URL
# api_url = "http://api:8080"

# Use dynamic discovery
api_url = get_api_endpoint()
response = requests.get(f"{api_url}/data")
```

## Service Discovery Decision Tree

```
Do you have < 3 services?
  └─ Yes → Use environment variables
  └─ No ↓

Are you on Kubernetes?
  └─ Yes → Use K8s Services (built-in)
  └─ No ↓

Are you on AWS with ECS/Fargate?
  └─ Yes → Use AWS Cloud Map
  └─ No ↓

Do you need multi-datacenter?
  └─ Yes → Use Consul
  └─ No ↓

Do you want simplicity?
  └─ Yes → Use Docker Swarm mode
  └─ No → Use Consul or Eureka
```

## Common Pitfalls and Solutions

### 1. Container IP vs Host IP
```python
# Wrong - returns container IP (172.17.0.2)
socket.gethostbyname(socket.gethostname())

# Right - get host IP
# Option 1: Pass as environment variable
host_ip = os.getenv('HOST_IP')

# Option 2: Query metadata service (AWS)
host_ip = requests.get('http://169.254.169.254/latest/meta-data/local-ipv4').text
```

### 2. Stale Entries
```python
# Always include health checks
check=consul.Check.http(
    health_url,
    interval="30s",
    timeout="5s",
    deregister="1m"  # Remove after 1m of failures
)
```

### 3. Network Partitions
```python
# Implement circuit breakers
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_api_service():
    endpoint = get_api_endpoint()
    return requests.get(endpoint)
```

### 4. DNS Caching
```python
# Force DNS refresh
import socket
socket.setdefaulttimeout(30)  # Reduce DNS cache time
```

## When NOT to Use Service Discovery

1. **Single instance services** - Just use environment variables
2. **Static infrastructure** - DNS is simpler
3. **Cloud-managed services** - RDS, ElastiCache don't need discovery
4. **Behind a load balancer** - ALB handles this for you

## Summary

Service discovery solves the problem of "where is my service?" in dynamic environments. It's essentially:
1. A registry where services announce themselves
2. An API where clients can query for services
3. Health checking to ensure only healthy instances are returned

Start simple (environment variables), evolve to DNS, then add dynamic discovery when you need it. The key is making your application discovery-agnostic so you can change the mechanism without changing your code.