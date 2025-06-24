#!/usr/bin/env python3
"""
Export OpenAPI specification from FastAPI app to a static file.
This ensures frontend type generation uses the same spec as the API.
"""
import json
import yaml
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the FastAPI app
from api.microservices_gateway import app

# Get the OpenAPI schema
openapi_schema = app.openapi()

# Output paths
json_path = Path(__file__).parent.parent / "openapi.json"
yaml_path = Path(__file__).parent.parent / "openapi.yaml"

# Write JSON version
with open(json_path, 'w') as f:
    json.dump(openapi_schema, f, indent=2)
    f.write('\n')  # Ensure file ends with newline
    print(f"✅ Exported OpenAPI JSON to: {json_path}")

# Write YAML version
with open(yaml_path, 'w') as f:
    yaml.dump(openapi_schema, f, default_flow_style=False, sort_keys=False)
    # yaml.dump already adds a final newline
    print(f"✅ Exported OpenAPI YAML to: {yaml_path}")

print("\nYou can now use these files for:")
print("- Frontend type generation: npm run generate-types")
print("- API documentation")
print("- Docker builds")