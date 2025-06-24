# Nginx Container for Crucible Platform

This directory contains the containerized Nginx configuration for the Crucible Platform, replacing the EC2 userdata-based nginx setup.

## Features

- **Rate Limiting**: Protects against abuse with configurable zones
- **SSL/TLS Support**: Automatic SSL with self-signed certs for development
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Health Checks**: Built-in health endpoint
- **Reverse Proxy**: Routes to API and frontend services
- **WebSocket Support**: For SSE/real-time updates

## Configuration

### Ports
- `80`: HTTP (redirects to HTTPS in production)
- `443`: HTTPS with SSL
- `8000`: HTTP-only development port

### SSL Certificates

The container supports three methods for SSL certificates:

1. **Environment Variables** (for production):
   ```bash
   docker run -e SSL_CERT="$(cat cert.pem)" -e SSL_KEY="$(cat key.pem)" ...
   ```

2. **Volume Mount** (for persistent certs):
   ```bash
   docker run -v /path/to/certs:/etc/nginx/ssl ...
   ```

3. **Self-Signed** (default for development):
   If no certificates are provided, the container generates self-signed certificates automatically.

### Rate Limiting Zones

- `general`: 30 requests/second (default for all endpoints)
- `api`: 10 requests/second (for /api/* endpoints)
- `auth`: 2 requests/second (for authentication endpoints)
- `expensive`: 1 request/second (for resource-intensive operations)

## Local Development

Run with docker-compose:
```bash
docker-compose up nginx
```

Access services:
- Frontend: http://localhost:8000
- API: http://localhost:8000/api/
- Health: http://localhost:8000/health

## Production Deployment

In production, the nginx container:
1. Receives SSL certificates from AWS SSM Parameter Store
2. Enables HTTPS redirect
3. Uses the domain name from Terraform configuration

## Files

- `Dockerfile`: Container image definition
- `nginx.conf`: Main nginx configuration
- `conf.d/crucible.conf`: Site-specific configuration
- `docker-entrypoint.sh`: Startup script for SSL setup