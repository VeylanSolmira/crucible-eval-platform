# Week 5 METR Platform Tasks

## Refactoring & Professional Improvements

### 1. Docker Compose Build Separation
- **Task**: Separate build-time services from runtime services
- **Current**: Using busybox workaround in prod to avoid pull warnings
- **Target**: Implement proper docker-compose.build.yml pattern
- **Reference**: `/docs/architecture/docker-compose-build-separation.md`
- **Benefits**: 
  - Clean separation of concerns
  - No warnings in production
  - Industry-standard approach

### 2. Python Dependency Caching in Docker
- **Task**: Implement proper pip caching in Dockerfiles
- **Current**: Rebuilding dependencies on every code change
- **Target**: Use BuildKit cache mounts or multi-stage pattern
- **Example**:
  ```dockerfile
  # syntax=docker/dockerfile:1
  RUN --mount=type=cache,target=/root/.cache/pip \
      pip install -r requirements.txt
  ```

### 3. API Response Model Improvements
- **Task**: Add proper error response models to OpenAPI spec
- **Current**: Generic error responses
- **Target**: Structured error responses with codes and details

### 4. Monitoring Infrastructure
- **Task**: Apply and test CloudWatch monitoring setup
- **Status**: Terraform code written, needs testing
- **Components**:
  - Memory alerts
  - OOM detection
  - Container restart tracking

### 5. Development Environment Documentation
- **Task**: Document all development workflows
- **Include**:
  - Local development with hot reload
  - Docker Compose workflows
  - Testing procedures
  - Debugging guides

### 6. Docker Entrypoint Scripts for Secure Volume Permissions
- **Task**: Implement privilege-dropping entrypoint scripts for services
- **Current**: Using chmod 777 or manual permission fixes
- **Target**: Start as root, create directories, drop to service user
- **Example**: Like official postgres/nginx images
- **Benefits**:
  - No world-writable directories
  - Services can create their own structure
  - Secure by default
  - No manual SSH fixes needed

### 7. Review Storage Service Security Model
- **Task**: Revisit the storage service permission model for security
- **Current**: Userdata creates dirs with 1000:1000 ownership, chmod 755
- **Security Considerations**:
  - Verify UID 1000 is correct for all containers
  - Consider read-only containers with specific write mounts
  - Implement proper file isolation between evaluations
  - Add security scanning for uploaded files
  - Consider using named volumes instead of bind mounts
- **Questions to Address**:
  - Should each evaluation have isolated storage?
  - How to prevent cross-evaluation data access?
  - What happens if a malicious evaluation fills the disk?

### 8. Secure Docker Credential Storage
- **Task**: Implement secure credential storage for ECR login
- **Current**: Warning about unencrypted credentials in /root/.docker/config.json
- **Target**: Use docker-credential-ecr-login helper
- **Implementation**:
  - Install amazon-ecr-credential-helper in userdata
  - Configure Docker to use credential helper
  - Eliminates unencrypted credential storage
- **Benefits**:
  - No plaintext credentials on disk
  - Automatic token refresh via IAM role
  - Industry best practice for ECR

## Technical Debt

1. **Remove Legacy Queue Service**
   - Currently disabled but still in codebase
   - Clean up references and dead code

2. **Consolidate Redis Instances**
   - Currently using separate Redis for Celery
   - Consider consolidation with proper key namespacing

3. **Frontend Build Optimization**
   - Current build includes all dependencies
   - Implement proper Next.js optimization

## Performance Optimizations

1. **Database Connection Pooling**
   - Implement proper pooling for all services
   - Add connection limits

2. **Image Size Reduction**
   - Analyze and reduce Docker image sizes
   - Use distroless or Alpine where possible

3. **Build Time Optimization**
   - Parallel builds where possible
   - Better layer caching strategies