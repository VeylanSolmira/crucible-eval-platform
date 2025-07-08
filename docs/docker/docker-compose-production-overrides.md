Docker Compose Production Overrides Explained

  The docker-compose.prod.yml file provides production-specific
  overrides that work with the base docker-compose.yml. Here's what
  each override does:

  1. Image Overrides (All Services)

  image: ${NGINX_IMAGE:-crucible-platform/nginx:latest}
  - Purpose: Use ECR images built by CI/CD instead of local builds
  - How it works: GitHub Actions sets these environment variables
  with ECR URLs
  - Fallback: If variable not set, uses default image name

  2. Nginx Service Overrides

  SSL Certificate Mounting

  volumes:
    - /etc/nginx/ssl:/etc/nginx/ssl:ro
  - Purpose: Mount SSL certificates that EC2 fetches from SSM
  Parameter Store
  - Security: Read-only mount (:ro) prevents container from
  modifying certificates
  - Location: Host stores certificates at /etc/nginx/ssl/

  Production Mode

  environment:
    - PRODUCTION_MODE=true
    - NGINX_DEV_PORT=
  - PRODUCTION_MODE=true: Makes nginx fail-fast if SSL certificates
  are missing
  - NGINX_DEV_PORT=: Disables the development port 8000 (empty
  value)

  Health Check

  healthcheck:
    test: ["CMD", "wget", "--no-check-certificate", "--quiet",
  "--tries=1", "--spider", "https://localhost/health"]
  - Purpose: AWS ALB/ELB health checks
  - HTTPS check: Uses --no-check-certificate for self-signed cert
  compatibility
  - 60s start period: Gives nginx time to fetch/generate
  certificates

  3. Port Disabling

  ports: []
  - Applied to: api-service, frontend, postgres, redis
  - Purpose: Only nginx should be exposed externally
  - Security: Prevents direct access to internal services

  4. Frontend Production Settings

  environment:
    - NODE_ENV=production
    - API_URL=
  - NODE_ENV=production: Enables production optimizations
  - API_URL= (empty): Forces frontend to use relative URLs (/api/*
  instead of http://localhost:8080/api/*)

  5. Logging Configuration

  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "5"
  - Purpose: Prevent disk space exhaustion
  - Rotation: Keeps 5 files of 10MB each (50MB max per service)
  - PostgreSQL exception: Gets 50MB files due to higher log volume

  6. Services Without Port Overrides

  - executor-service: Already internal-only
  - queue/queue-worker: Never had external ports
  - storage-worker: Internal service
  - docker-proxy: Needs to stay accessible to executor

  Usage Pattern

  # Production deployment
  docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
   -d

  # The override file:
  # 1. Replaces all image references with ECR versions
  # 2. Mounts production SSL certificates
  # 3. Disables all development conveniences
  # 4. Adds production health checks
  # 5. Configures log rotation

  Key Security Benefits

  1. No Direct Service Access: Only nginx is exposed
  2. SSL Enforcement: Production mode fails without valid
  certificates
  3. Read-Only Mounts: Certificates can't be modified by containers
  4. Log Rotation: Prevents log-based DoS
  5. ECR Images: Immutable, scanned images instead of local builds

  This design ensures that production deployments are secure by
  default while keeping development convenient with the base
  docker-compose.yml.