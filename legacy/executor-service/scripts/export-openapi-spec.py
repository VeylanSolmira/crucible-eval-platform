#!/usr/bin/env python3
"""
Export OpenAPI specification from Executor Service to static files.
This ensures type generation uses the same spec as the service.
"""

import json
import yaml
import sys
from pathlib import Path

# Add paths for imports
executor_service_dir = Path(__file__).parent.parent
project_root = executor_service_dir.parent

# Add both executor-service dir and project root to path
sys.path.insert(0, str(executor_service_dir))
sys.path.insert(0, str(project_root))

# Import the FastAPI app
from app import app

# Get the OpenAPI schema
openapi_schema = app.openapi()

# Output paths
json_path = Path(__file__).parent.parent / "openapi.json"
yaml_path = Path(__file__).parent.parent / "openapi.yaml"

# Write JSON version
with open(json_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
    f.write("\n")  # Ensure file ends with newline
    print(f"✅ Exported Executor Service OpenAPI JSON to: {json_path}")

# Write YAML version
with open(yaml_path, "w") as f:
    yaml.dump(openapi_schema, f, default_flow_style=False, sort_keys=False)
    # yaml.dump already adds a final newline
    print(f"✅ Exported Executor Service OpenAPI YAML to: {yaml_path}")

print("\nExecutor Service OpenAPI spec exported successfully!")
print("These files can be used for:")
print("- Client code generation")
print("- API documentation")
print("- Type generation")