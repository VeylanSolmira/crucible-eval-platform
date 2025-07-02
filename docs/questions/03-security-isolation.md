# Security & Isolation Questions

## 🟢 Basic Level

### Q1: What are the main security threats when executing untrusted code?

**Answer**:
The primary threats include:
1. **Container escape** - Breaking out of Docker isolation
2. **Resource exhaustion** - DoS through CPU/memory consumption  
3. **Data exfiltration** - Accessing host files or network
4. **Privilege escalation** - Gaining root or host access
5. **Side-channel attacks** - Timing attacks, cache inspection

Our platform addresses each through defense-in-depth strategies.

**Deep Dive**:
Threat model for code execution:
```
Attacker Goal: Escape sandbox, access host, exfiltrate data
Attack Vectors: Kernel exploits, resource exhaustion, network access
Defenses: Multiple isolation layers, resource limits, network policies
```

**Real-world examples**:
- CVE-2019-5736: runC container escape
- CVE-2022-0492: cgroups escape via release_agent
- Dirty COW (CVE-2016-5195): Kernel privilege escalation

---

### Q2: Explain the Docker security measures implemented in the platform.

**Answer**:
We implement multiple Docker security layers:

1. **Read-only root filesystem** - Prevents file system modifications
2. **No network access** - `network_mode: none` for executors
3. **Dropped capabilities** - Minimal Linux capabilities
4. **Resource limits** - CPU, memory constraints
5. **Non-root user** - Containers run as unprivileged user

**Code Example** (`executor_service/docker_executor.py`):
```python
container_config = {
    "image": "python:3.11-slim",
    "mem_limit": "256m",
    "cpu_quota": 50000,  # 0.5 CPU
    "network_mode": "none",
    "read_only": True,
    "security_opt": ["no-new-privileges:true"],
    "cap_drop": ["ALL"],
    "user": "nobody"
}
```

**Deep Dive**:
Each measure prevents specific attacks:
- `read_only`: Prevents persistence, malware installation
- `network_mode: none`: Prevents data exfiltration, C2 communication
- `cap_drop: ALL`: Removes all Linux capabilities
- `no-new-privileges`: Prevents suid escalation

---

## 🟡 Intermediate Level

### Q3: How does the Docker Socket Proxy enhance security?

**Answer**:
The Docker Socket Proxy (`docker-proxy` service) provides filtered access to Docker API:

1. **Least privilege** - Only allows required Docker operations
2. **No direct socket access** - Executors can't access `/var/run/docker.sock`
3. **API filtering** - Blocks dangerous operations like `exec`, `build`
4. **Audit trail** - Can log all Docker API calls

**Configuration** (`docker-compose.yml:17-36`):
```yaml
environment:
  CONTAINERS: 1         # Can list containers
  CONTAINERS_CREATE: 1  # Can create (for execution)
  EXEC: 0              # CANNOT exec into containers
  VOLUMES: 0           # CANNOT manage volumes
  BUILD: 0             # CANNOT build images
```

**Deep Dive**:
Without proxy, services need docker.sock access, which equals root:
```bash
# Dangerous - full Docker access
-v /var/run/docker.sock:/var/run/docker.sock

# Safe - filtered access through proxy
DOCKER_HOST=tcp://docker-proxy:2375
```

Attack prevented: Malicious code creating privileged containers

---

### Q4: Describe the network isolation strategy.

**Answer**:
Multi-layer network isolation:

1. **Internal networks** - `docker-api` network is internal-only
2. **No executor network** - Evaluation containers have no network
3. **Service isolation** - Services communicate through defined APIs
4. **Nginx proxy** - Single entry point, security headers
5. **CORS policies** - Restrict browser-based attacks

**Network Architecture**:
```
Internet -> Nginx (ports 80/443) -> Internal Services
                                 -> No route to executors
```

**Deep Dive** (`docker-compose.yml:539-544`):
```yaml
networks:
  default:
    driver: bridge
  docker-api:
    driver: bridge
    internal: true  # No external access
```

**Security Headers** (`nginx/conf.d/crucible.conf:37-46`):
```nginx
add_header X-Frame-Options "DENY";
add_header X-Content-Type-Options "nosniff";
add_header Strict-Transport-Security "max-age=31536000";
```

---

## 🔴 Advanced Level

### Q5: How would you detect and prevent container escape attempts?

**Answer**:
Detection and prevention strategies:

**Prevention**:
1. **Minimal base images** - Less attack surface
2. **Regular updates** - Patch kernel vulnerabilities  
3. **Seccomp profiles** - Restrict system calls
4. **AppArmor/SELinux** - Mandatory access controls
5. **User namespaces** - UID mapping

**Detection**:
1. **System call monitoring** - Detect suspicious syscalls
2. **File system monitoring** - Watch for /proc manipulation
3. **Resource monitoring** - Detect abnormal CPU/memory patterns
4. **Log analysis** - Parse container logs for exploits

**Future Implementation**:
```python
# Planned: Custom seccomp profile
seccomp_profile = {
    "defaultAction": "SCMP_ACT_ERRNO",
    "syscalls": [
        {"name": "read", "action": "SCMP_ACT_ALLOW"},
        {"name": "write", "action": "SCMP_ACT_ALLOW"},
        # Block dangerous syscalls
        {"name": "mount", "action": "SCMP_ACT_ERRNO"},
        {"name": "ptrace", "action": "SCMP_ACT_ERRNO"}
    ]
}
```

**Deep Dive - gVisor Integration** (planned):
```yaml
# Future: Use gVisor for system call filtering
runtime: runsc
runtimeArgs:
  - --network=none
  - --debug-log=/var/log/runsc/
```

---

### Q6: Explain the defense-in-depth strategy for code execution.

**Answer**:
Multiple independent security layers:

```
Layer 1: Input Validation
  ↓ Syntax checking, size limits
Layer 2: Resource Limits  
  ↓ CPU, memory, time bounds
Layer 3: Container Isolation
  ↓ Namespaces, cgroups
Layer 4: Network Isolation
  ↓ No network access
Layer 5: File System Restrictions
  ↓ Read-only, no persistent storage
Layer 6: System Call Filtering (planned)
  ↓ Seccomp, gVisor
Layer 7: Monitoring & Detection
  ↓ Behavioral analysis
```

**Implementation Details**:

1. **Input Validation** (`api/microservices_gateway.py`):
```python
if len(request.code) > 1_000_000:  # 1MB limit
    raise ValueError("Code too large")
```

2. **Resource Limits** (`executor_service/config.py`):
```python
MEMORY_LIMIT = "256m"
CPU_LIMIT = 0.5
TIMEOUT = 30  # seconds
```

3. **Container Hardening**:
```python
security_opts = [
    "no-new-privileges:true",
    "apparmor:docker-default",
    "seccomp:default"
]
```

**Principle**: No single layer should be trusted completely

---

### Q7: How do you handle secrets and sensitive configuration?

**Answer**:
Secrets management approach:

1. **Environment variables** - Never in code or configs
2. **Docker secrets** - For production deployments
3. **Least privilege** - Services only get needed secrets
4. **Rotation capable** - Design supports key rotation
5. **No logging** - Secrets never logged

**Current Implementation**:
```yaml
# docker-compose.yml
environment:
  - DATABASE_URL=postgresql://crucible:${DB_PASSWORD:-changeme}@postgres:5432/crucible
  - INTERNAL_API_KEY=${INTERNAL_API_KEY:-dev-internal-api-key}
```

**Production Approach** (documented):
```yaml
# docker-compose.prod.yml (future)
secrets:
  db_password:
    external: true
  api_key:
    external: true

services:
  api:
    secrets:
      - db_password
      - api_key
```

**Deep Dive - Secret Rotation**:
```python
# Planned implementation
class SecretManager:
    def get_secret(self, name: str, version: str = "latest"):
        # Fetch from AWS Secrets Manager/Vault
        pass
    
    def rotate_secret(self, name: str):
        # Create new version, update services
        pass
```

---

## 🟣 METR-Specific Security

### Q8: What additional security measures would you implement for AI safety evaluation?

**Answer**:
AI safety requires additional measures:

1. **Behavioral Monitoring** - Detect self-replication attempts
2. **Output Filtering** - Prevent prompt injection in results
3. **Resource Budgets** - Cumulative limits per user/model
4. **Audit Logging** - Complete record for analysis
5. **Sandboxed Networking** - Controlled internet access when needed

**Proposed Implementation**:
```python
class SafetyMonitor:
    def __init__(self):
        self.patterns = [
            r"subprocess.*Popen.*python",  # Self-replication
            r"socket\.socket",              # Network attempts
            r"eval\(|exec\(",              # Dynamic execution
        ]
    
    async def analyze_code(self, code: str):
        for pattern in self.patterns:
            if re.search(pattern, code):
                await self.alert_security_team(pattern, code)
```

**Advanced Isolation** (future):
- Firecracker microVMs for stronger isolation
- Time-based network access (allow brief external calls)
- GPU isolation for ML workloads
- Confidential computing (SGX/SEV)

---

## Security Checklist

### Current Implementation ✅
- [x] Container isolation with Docker
- [x] Resource limits (CPU, memory, time)
- [x] Network isolation (no internet access)
- [x] Read-only file systems
- [x] Non-root execution
- [x] Docker socket proxy
- [x] Security headers in nginx
- [x] Internal API authentication

### Planned Enhancements 🚧
- [ ] gVisor/Firecracker integration
- [ ] Seccomp profiles
- [ ] System call monitoring
- [ ] Behavioral analysis
- [ ] Secret rotation system
- [ ] Security scanning in CI/CD
- [ ] Penetration testing
- [ ] Compliance auditing

## Key Takeaways

1. **Defense in Depth** - Multiple layers, no single point of failure
2. **Least Privilege** - Minimal permissions at every level
3. **Isolation First** - Assume code is malicious
4. **Monitor Everything** - Detection as important as prevention
5. **Regular Updates** - Security is ongoing, not one-time

## Hands-On Security Exercises

1. **Try to Escape**: Write code that attempts container escape
2. **Resource Exhaustion**: Try to DoS the platform
3. **Network Access**: Attempt to make external connections
4. **File System**: Try to write to host file system
5. **Privilege Escalation**: Attempt to gain root access

Each exercise helps understand why each security layer exists.