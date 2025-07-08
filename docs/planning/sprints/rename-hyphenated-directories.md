# Week 5 Task: Rename Hyphenated Directories to Python Module Names

## Overview
Rename all hyphenated directory names to use underscores for proper Python module compatibility.

## Motivation
- **Current Issue**: Directories like `storage-service` cannot be imported as Python modules
- **Current Workaround**: Using `sys.path` hacks or `cd` into directories
- **Goal**: Enable clean imports like `from storage_service.app import app`

## Directories to Rename

### Services
- `storage-service` → `storage_service`
- `executor-service` → `executor_service` 
- `celery-worker` → `celery_worker`
- `storage-worker` → `storage_worker`

### Other Directories
- `load-tests` → `load_tests`
- `github-integration` → `github_integration`
- Any other hyphenated directories

## Impact Analysis

### 1. Docker Compose Files
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker-compose.dev.yml`
- Service names can stay hyphenated (just build context changes)

### 2. Dockerfiles
- Update all COPY commands
- Update WORKDIR paths
- Update any hardcoded paths

### 3. GitHub Workflows
- `.github/workflows/generate-openapi-spec.yml`
- `.github/workflows/deploy-docker.yml`
- Any workflow referencing service paths

### 4. Shell Scripts
- `start-platform.sh`
- `scripts/generate-all-openapi-specs.sh`
- Any other automation scripts

### 5. Documentation
- Update all references in docs/
- Update README.md
- Update architecture diagrams

### 6. Import Statements
- Update all Python imports across the codebase
- Change from workarounds to clean module imports

### 7. CI/CD Pipelines
- Update any deployment scripts
- Update test paths

## Migration Strategy

1. **Create migration script** that handles all renames atomically
2. **Test in development** environment first
3. **Update all references** in a single PR
4. **Coordinate deployment** to avoid downtime

## Benefits After Migration

- Clean Python imports without hacks
- Follow Python naming conventions
- Easier testing and development
- Better IDE support
- More maintainable codebase

## Example Changes

### Before:
```python
# In storage-service/scripts/export-openapi-spec.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from app import app
```

### After:
```python
# In storage_service/scripts/export-openapi-spec.py
from storage_service.app import app
```

## Priority
Medium - Important for code quality but not blocking functionality

## Estimated Effort
4-6 hours for careful migration and testing