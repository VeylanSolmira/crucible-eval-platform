# Shared Python Package Proposal

## Current Challenge

The current shared contracts implementation requires:
- `sys.path` manipulation in Python files
- `PYTHONPATH` environment variable in Dockerfiles
- Imports only work from project root

This creates issues for:
- Local development outside Docker
- IDE autocomplete and type checking
- Running tests
- Developer experience

## The Problem

1. **Inside Docker**: The shared imports work because:
   - We copy the `/shared` directory into the container
   - We set `PYTHONPATH=/app` in the Dockerfile
   - The import `from shared.generated.python import EvaluationStatus` resolves correctly

2. **Outside Docker (local development)**:
   - The import fails unless you're at the project root with `PYTHONPATH` set
   - Developers can't just run `python storage-service/app.py` from anywhere
   - IDE imports might break without proper configuration
   - Testing becomes more complicated

## Better Solutions

### 1. **Shared Python Package** (Professional approach)
Create a proper Python package for shared types that can be installed via pip.

### 2. **Docker-only Development**
Accept that services only run in Docker and use docker-compose for all development.

### 3. **Symlinks** (Quick fix)
Create symlinks in each service to the shared directory (fragile).

### 4. **Build-time Generation**
Generate the enums in each service during build (duplication).

## Creating a Python Package for Shared Types

### Directory Structure:
```
shared/
├── setup.py                    # Package configuration
├── pyproject.toml             # Modern Python packaging (optional but recommended)
├── README.md                  # Package documentation
├── crucible_shared/           # The actual package directory
│   ├── __init__.py           # Makes it a package
│   ├── enums.py              # Generated enums
│   ├── models.py             # Shared Pydantic models (if any)
│   └── constants.py          # Shared constants
└── scripts/
    └── generate_types.py      # Your generation script
```

### 1. Create `setup.py`:
```python
from setuptools import setup, find_packages

setup(
    name="crucible-shared",
    version="0.1.0",
    description="Shared types and constants for Crucible platform",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0",
    ],
)
```

### 2. Create `pyproject.toml` (modern approach):
```toml
[project]
name = "crucible-shared"
version = "0.1.0"
description = "Shared types for Crucible platform"
requires-python = ">=3.8"
dependencies = [
    "pydantic>=2.0",
]

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

### 3. Install in each service:

#### Option A - Editable install (for development):
```bash
# In each service's requirements.txt:
-e ../shared

# Or in Dockerfile:
RUN pip install -e /app/shared
```

#### Option B - Regular install (for production):
```bash
# In Dockerfile:
COPY shared/ /tmp/shared/
RUN pip install /tmp/shared/
```

### 4. Import normally:
```python
# No sys.path hacks needed!
from crucible_shared import EvaluationStatus
from crucible_shared.models import EvaluationRequest
```

### Benefits:
- ✅ Works everywhere (local, Docker, tests, IDEs)
- ✅ Proper dependency management
- ✅ Version control if needed
- ✅ Can be published to private PyPI
- ✅ Standard Python practice
- ✅ IDE autocomplete works perfectly

## Handling Mixed Resource Types

The `/shared` folder contains multiple types of resources:

### Current `/shared` Structure:
```
shared/
├── docker/
│   └── base.Dockerfile         # Docker base image
├── types/
│   ├── evaluation-status.yaml  # OpenAPI schemas (source of truth)
│   └── event-contracts.yaml
├── constants/
│   ├── limits.yaml            # Security limits
│   └── events.yaml            # Event channel names
├── generated/
│   └── python/                # Generated Python code
└── scripts/
    └── generate-python-types.py
```

### Recommended Approach - Hybrid Solution:

#### 1. **Keep `/shared` for non-Python resources**:
```
shared/
├── docker/                    # Docker configs stay here
│   └── base.Dockerfile
├── contracts/                 # Source of truth (renamed from types)
│   ├── evaluation-status.yaml
│   └── event-contracts.yaml
├── constants/                 # YAML constants
│   ├── limits.yaml
│   └── events.yaml
└── scripts/                   # Generation scripts
    ├── generate-python-types.py
    └── generate-typescript-types.sh
```

#### 2. **Create Python package in `/shared/python-package`**:
```
shared/
├── python-package/           # The Python package
│   ├── setup.py
│   ├── crucible_shared/
│   │   ├── __init__.py
│   │   ├── enums.py         # Generated from contracts
│   │   ├── constants.py     # Generated from YAML constants
│   │   └── models.py
│   └── README.md
```

#### 3. **Generation workflow**:
```python
# generate-python-types.py would:
1. Read from shared/contracts/*.yaml
2. Read from shared/constants/*.yaml
3. Generate code into shared/python-package/crucible_shared/
4. The package is always installable
```

#### 4. **Docker build process**:
```dockerfile
# In service Dockerfiles:

# Copy and install the Python package
COPY shared/python-package /tmp/crucible-shared
RUN pip install /tmp/crucible-shared

# Copy other shared resources if needed
COPY shared/constants /app/shared/constants  # If runtime access needed
```

#### 5. **For services that need YAML at runtime**:
```python
# If a service needs to read limits.yaml at runtime:
import yaml
from pathlib import Path

# In Docker: /app/shared/constants/limits.yaml
# In local dev: ../shared/constants/limits.yaml
LIMITS_PATH = Path(__file__).parent / "shared/constants/limits.yaml"
```

### Benefits of This Approach:
- ✅ Python code is properly packaged
- ✅ Non-Python resources remain accessible
- ✅ Clear separation of concerns
- ✅ Generation scripts know where everything lives
- ✅ Docker configs stay in shared
- ✅ Can add other language packages (shared/npm-package, etc.)

### Alternative: Multiple Packages
```
shared/
├── docker/                    # Docker configs
├── contracts/                 # Source of truth  
├── python/                    # Python package
├── typescript/                # NPM package
└── scripts/                   # All generation scripts
```

This keeps things even more organized by language/tool type.

## Decision

For now, we'll continue with the Docker-only approach using `PYTHONPATH` since:
1. All services are exclusively run in Docker
2. It's working well for the current use case
3. We can revisit this if we need better local development support

However, this document captures the proper approach for when we want to improve the developer experience or support local development/testing.