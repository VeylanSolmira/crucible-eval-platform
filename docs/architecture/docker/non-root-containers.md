# Non-Root Container Security

## Overview
In the modular architecture, all services run as non-root users, improving security by following the principle of least privilege.

## Service Security Model

### Services Running as Non-Root (appuser)
1. **crucible-platform** - API gateway in modular mode
2. **queue-service** - HTTP wrapper for TaskQueue
3. **queue-worker** - Task routing service
4. **executor-service** - Container creation service

### How Docker Access Works Without Root
The executor service creates containers through the Docker socket proxy:
- Connects via TCP to `tcp://docker-proxy:2375`
- No direct Unix socket access needed
- Docker proxy handles the actual socket communication
- Proxy limits what Docker API calls can be made

## Security Benefits

### 1. Reduced Attack Surface
- If a service is compromised, attacker doesn't get root
- Can't modify system files or install packages
- Limited to user-level permissions

### 2. Defense in Depth
- Even with container escape, limited host access
- Can't bind to privileged ports (<1024)
- Can't access other users' files

### 3. Compliance
- Meets security best practices for production
- Required by many security frameworks (CIS, NIST)
- Essential for SOC2/ISO27001 compliance

## Implementation Details

### Base Image Setup
```dockerfile
# In base.Dockerfile
RUN groupadd -r appuser && useradd -r -g appuser appuser
```

### Service Dockerfiles
```dockerfile
# Before running the service
USER appuser

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Docker Compose Configuration
```yaml
# No special configuration needed
# Services automatically run as appuser from Dockerfile
```

## Migration Notes

### From Monolithic to Modular
- **Monolithic mode**: Main app needs root for Docker socket
- **Modular mode**: No services need root access
- This is a security improvement of the modular architecture

### Testing Non-Root Execution
```bash
# Verify services run as non-root
docker-compose exec queue whoami  # Should output: appuser
docker-compose exec executor ps aux | head -2  # Check process owner
```

## Troubleshooting

### Common Issues
1. **Permission denied on files**
   - Ensure files are owned by appuser in Dockerfile
   - Use `COPY --chown=appuser:appuser` for file copies

2. **Can't bind to port**
   - Use ports > 1024 (we use 8080-8084)
   - Configure reverse proxy for port 80/443

3. **Docker client errors**
   - Verify DOCKER_HOST is set correctly
   - Check docker-proxy is running

## Future Enhancements

### Rootless Docker
Consider migrating to rootless Docker for the host daemon itself:
- Docker daemon runs as non-root user
- Additional isolation layer
- Some limitations (no overlay networks, some storage drivers)

### User Namespaces
Enable user namespace remapping:
```json
{
  "userns-remap": "default"
}
```
This maps container root to unprivileged host user.

## Security Audit Checklist
- [ ] All services run as non-root user
- [ ] No capabilities added (`--cap-add`)
- [ ] Read-only root filesystem where possible
- [ ] No privileged containers
- [ ] Minimal base images (distroless/alpine)
- [ ] Regular security scanning of images