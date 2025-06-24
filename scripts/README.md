# Scripts

Utility scripts for the Crucible platform.

## Directory Structure

### `/migrations`
Scripts used for code reorganization and migration. These were used during the platform restructuring and can be deleted once the migration is stable.

### `/docs`
Scripts for documentation organization and generation.

### `/deployment`
Deployment and infrastructure scripts.

### `/archive`
Old scripts kept for reference but no longer actively used.

## Development Scripts

### `update-openapi-spec.sh` 🔄
Updates the OpenAPI specification from the FastAPI application.

**When to use**: After making changes to API endpoints in `api/microservices_gateway.py`

**What it does**:
1. Runs `api/scripts/export-openapi-spec.py`
2. Generates `api/openapi.yaml` and `api/openapi.json` from FastAPI routes
3. These files are used by frontend type generation

**Usage**:
```bash
./scripts/update-openapi-spec.sh
```

**Next steps**:
1. Generate TypeScript types: `cd frontend && npm run generate-types`
2. Commit both the API changes and the updated `openapi.yaml` together

### `setup-dev.sh`
Sets up the complete development environment.

### `setup-venv.sh`
Creates and activates a Python virtual environment.

### `run-api.sh`
Starts the API service locally for development.

### `run-migrations.sh`
Runs database migrations.

### `debug_docker_permissions.sh`
Troubleshoots Docker socket permission issues.

### `debug_docker_proxy.py`
Tests the Docker socket proxy connection.

## Important Development Workflow

When changing the API:
1. Make changes to `api/microservices_gateway.py`
2. Run `./scripts/update-openapi-spec.sh`
3. Run `cd frontend && npm run generate-types`
4. Commit API changes and `api/openapi.yaml` together

The OpenAPI spec (`api/openapi.yaml`) is the contract between frontend and backend.
