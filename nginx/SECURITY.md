# Nginx Security Configuration

## Port 8000 Security

The nginx container exposes port 8000 as an HTTP-only development port. This port is secured through multiple layers:

### 1. Default Configuration (Production-Safe)
By default, port 8000 is bound only to localhost:
```yaml
- "${NGINX_DEV_PORT:-127.0.0.1:8000}:8000"
```

This means:
- In production (no env var set): Only accessible from the host machine
- Cannot be accessed from external networks
- Requires SSH tunnel for remote access

### 2. Development Override
For local development, copy the example override:
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

This file is:
- Listed in .gitignore (never committed)
- Automatically loaded by docker-compose
- Contains development-specific settings

### 3. Security Group Protection
Even if misconfigured, AWS security groups provide defense in depth:
- Port 8000 is NOT allowed in production security groups
- Only ports 80, 443, and 22 are open

### 4. Environment Variable Control
To expose port 8000 (development only):
```bash
# Expose on all interfaces (development only!)
export NGINX_DEV_PORT=0.0.0.0:8000
docker-compose up

# Or inline:
NGINX_DEV_PORT=0.0.0.0:8000 docker-compose up
```

## SSL/TLS Configuration

### Production SSL
- Certificates fetched from AWS SSM Parameter Store
- Stored encrypted with KMS
- Auto-renewal handled by infrastructure

### Development SSL
- Self-signed certificates auto-generated
- Valid for 365 days
- Regenerated on container rebuild

## Rate Limiting

Configured zones:
- `general`: 30 req/s - Default for all endpoints
- `api`: 10 req/s - API endpoints
- `auth`: 2 req/s - Authentication (future)
- `expensive`: 1 req/s - Resource-intensive operations

## Security Headers

All responses include:
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Strict-Transport-Security` - Force HTTPS
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` - Control resource loading

## Access Control

- Hidden files (.*) are denied
- Health check endpoint has no rate limiting
- WebSocket connections have extended timeouts
- Static assets have long cache headers