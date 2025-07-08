# Scripts Directory - Shell Scripts Reference

This directory contains shell scripts for various platform operations including setup, development, deployment, and maintenance.

## Development Setup Scripts

### `setup-venv.sh`
Creates and activates a Python virtual environment for local development.
```bash
./scripts/setup-venv.sh
```
- Creates `.venv` directory in project root
- Installs basic dependencies (pip, setuptools, wheel)
- Displays activation instructions

### `setup-dev.sh`
Sets up a development environment with editable package installation.
```bash
./scripts/setup-dev.sh
```
- Requires virtual environment to be activated first
- Installs the platform package in editable mode
- Enables `crucible` command for development

## Runtime Scripts

### `docker-entrypoint.sh`
Docker entrypoint script that handles dynamic Docker socket permissions.
```bash
# Used automatically in Docker containers
```
- Fixes Docker socket permissions for Docker-in-Docker scenarios
- Adjusts user permissions based on socket ownership
- Critical for executor service functionality

### `run-api.sh`
Starts the FastAPI development server with hot reload.
```bash
./scripts/run-api.sh
```
- Runs on `http://localhost:8000`
- Enables auto-reload for development
- Useful for API-only development without full platform

### `run-migrations.sh`
Executes database migrations using Alembic.
```bash
./scripts/run-migrations.sh
```
- Runs migrations inside Docker container
- Connects to PostgreSQL database
- Must be run when database schema changes

## Documentation Scripts

### `update-openapi-spec.sh` 🔄
Updates the OpenAPI specification from the FastAPI application.
```bash
./scripts/update-openapi-spec.sh
```
- Exports OpenAPI schema to `frontend/src/api/openapi.json`
- Should be run after API endpoint changes
- Required before updating frontend TypeScript types

**Development workflow**:
1. Make changes to API endpoints
2. Run `./scripts/update-openapi-spec.sh`
3. Run `cd frontend && npm run generate-types`
4. Commit API changes and updated OpenAPI spec together

## Deployment Scripts

### `deployment/deploy-to-s3.sh`
Deploys platform artifacts to S3 for EC2 instance pickup.
```bash
./scripts/deployment/deploy-to-s3.sh
```
- Builds deployment package
- Uploads to configured S3 bucket
- Used by GitHub Actions for automated deployment

## Setup & Configuration Scripts

### `setup-deploy-key.sh`
Generates SSH deployment keys for GitHub Actions.
```bash
./scripts/setup-deploy-key.sh
```
- One-time setup for CI/CD
- Creates RSA key pair for secure deployment
- Public key must be added to GitHub repository

### `setup-ssl-container.sh`
Sets up SSL certificates using containerized Nginx and Certbot.
```bash
./scripts/setup-ssl-container.sh <domain>
```
- Obtains Let's Encrypt certificates
- Configures Nginx with SSL
- Required for HTTPS in production

## Debugging Scripts

### `debug_docker_permissions.sh`
Diagnoses Docker socket permission issues.
```bash
./scripts/debug_docker_permissions.sh
```
- Shows Docker socket ownership and permissions
- Lists user and group information
- Helps troubleshoot Docker-in-Docker problems

## Testing Scripts

### `audit-test-markers.py`
Audits pytest markers across the test suite for consistency.
```bash
python scripts/audit-test-markers.py
```
- Finds tests missing expected markers
- Identifies undefined markers being used
- Suggests appropriate markers based on test content
- Generates report at `tests/marker-audit-report.md`
- Helps maintain test organization and filtering

## Directory Structure

### `/deployment`
Deployment and infrastructure scripts.

### `/archive`
Historical scripts preserved for reference but no longer actively used. Includes:
- Old migration scripts from platform restructuring
- Deprecated deployment methods
- Legacy documentation generators

## Usage Notes

1. **Virtual Environment**: Most scripts assume you're in an activated Python virtual environment
2. **Docker**: Several scripts require Docker to be running
3. **Permissions**: Some scripts may require sudo for Docker operations
4. **Working Directory**: Run scripts from the project root directory

## Script Dependencies

- **Python 3.11+**: Required for setup scripts
- **Docker**: Required for container-related scripts
- **PostgreSQL**: Required for migration scripts (via Docker)
- **AWS CLI**: Required for deployment scripts (if using S3)
