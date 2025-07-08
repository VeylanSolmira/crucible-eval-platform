#!/usr/bin/env python3
"""
Export OpenAPI specification from Storage Service to static files.
This ensures type generation uses the same spec as the service.

Run from project root:
    python -m storage-service.scripts.export-openapi-spec
"""

import json
import yaml
from pathlib import Path

# Import directly when run from service directory
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
    print(f"✅ Exported Storage Service OpenAPI JSON to: {json_path}")

# Write YAML version
with open(yaml_path, "w") as f:
    yaml.dump(openapi_schema, f, default_flow_style=False, sort_keys=False)
    # yaml.dump already adds a final newline
    print(f"✅ Exported Storage Service OpenAPI YAML to: {yaml_path}")

print("\nStorage Service OpenAPI spec exported successfully!")
print("These files can be used for:")
print("- Client code generation")
print("- API documentation")
print("- Type generation")