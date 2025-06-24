# SSL Certificate Strategy for Containerized Nginx

## Problem
When nginx is containerized, it can't directly access SSL certificates from AWS SSM Parameter Store because:
1. The nginx:alpine image doesn't include AWS CLI
2. Even with AWS CLI, the container needs IAM permissions
3. The existing EC2 userdata fetches certs for host nginx, not container nginx

## Current Issue
Without intervention, the containerized nginx will:
1. Generate self-signed certificates on first run
2. Store them in the Docker volume
3. Reuse self-signed certificates forever (never checking SSM)

## Solution Options

### Option 1: Mount Host Certificates (Recommended)
**Pros:**
- Minimal changes needed
- Leverages existing userdata SSL fetch
- No AWS CLI needed in container
- Smaller container image

**Implementation:**
```yaml
# docker-compose.prod.yml
services:
  nginx:
    volumes:
      - /etc/nginx/ssl:/etc/nginx/ssl:ro  # Mount host SSL directory
```

**Modified userdata flow:**
1. EC2 userdata fetches certs from SSM to `/etc/nginx/ssl/`
2. Docker Compose mounts this directory read-only
3. Nginx container uses production certificates

### Option 2: Fetch in Container
**Pros:**
- Self-contained solution
- Can refresh certificates without host access

**Cons:**
- Requires AWS CLI in container (+50MB)
- Needs IAM permissions passed to container
- More complex

### Option 3: Init Container Pattern
**Pros:**
- Separation of concerns
- Only init container needs AWS CLI

**Cons:**
- More complex orchestration
- Not native to docker-compose

## Recommended Approach

1. **For Docker Compose deployment**: Use Option 1 (mount host certificates)
   - Modify userdata to ensure certificates are fetched before docker-compose starts
   - Add volume mount in production docker-compose override

2. **For future Kubernetes**: Use Option 3 (init containers)
   - Init container fetches certs to shared volume
   - Nginx container mounts volume read-only

## Implementation Steps

1. Update EC2 userdata to fetch certificates before starting docker-compose
2. Create docker-compose.prod.yml with certificate volume mount
3. Ensure systemd service uses production compose file
4. Test certificate refresh process

## Security Considerations

- Certificates should be mounted read-only
- Container should run as non-root user
- Minimize container permissions
- Regular certificate rotation