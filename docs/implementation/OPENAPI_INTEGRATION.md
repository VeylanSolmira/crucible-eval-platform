# OpenAPI-First Development Integration

## Overview

OpenAPI-first development provides a contract-first approach to API design, where the API specification drives the implementation rather than the other way around. This document explains how OpenAPI is integrated into the Crucible Evaluation Platform.

## Benefits

### 1. **Contract-First Design**
- API design before implementation
- Single source of truth for API structure  
- Framework-agnostic specification
- Version control for API evolution

### 2. **Automatic Validation**
- Request validation against schema
- Response validation for correctness
- Type safety without manual checks
- Detailed error messages for invalid requests

### 3. **Client Generation**
Generate type-safe clients in any language:
```bash
# Python
openapi-generator generate -i api/openapi.yaml -g python -o client/python

# TypeScript
openapi-generator generate -i api/openapi.yaml -g typescript-axios -o client/typescript

# Go
openapi-generator generate -i api/openapi.yaml -g go -o client/go
```

### 4. **Documentation**
Interactive API documentation:
```bash
# Swagger UI
docker run -p 8080:8080 -v $(pwd)/api:/api swaggerapi/swagger-ui

# ReDoc
docker run -p 8080:80 -v $(pwd)/api/openapi.yaml:/usr/share/nginx/html/swagger.yaml redocly/redoc
```

### 5. **Mock Servers**
Test frontend before backend is ready:
```bash
# Using Prism
prism mock api/openapi.yaml

# Enables frontend development in parallel with backend
```

### 6. **API Testing**
- Postman: Import OpenAPI spec directly
- Insomnia: Native OpenAPI support
- Contract testing with Pact
- Automated test generation

## Implementation

### OpenAPI Specification (`api/openapi.yaml`)
- Complete API contract defining all endpoints
- Request/response schemas with validation rules
- Proper error responses and status codes
- Security schemes (API key, JWT ready)
- Full documentation inline

### OpenAPI Validator Component (`components/openapi_validator.py`)
```python
# Instead of regular API:
api = RESTfulAPI(platform)

# Use OpenAPI-validated API:
api = create_openapi_validated_api(platform, "api/openapi.yaml")

# Now all requests are automatically validated!
# Invalid requests get 400 errors with details
# Responses are checked for contract compliance
```

Key features:
- `OpenAPIValidatedAPI` class that validates all requests/responses
- Automatic rejection of invalid requests (400 errors)
- Response validation to ensure contract compliance
- Graceful fallback if openapi-core isn't installed

## Usage in Frontier Platform

The frontier edition includes OpenAPI validation by default:

```python
# In extreme_mvp_frontier.py
if args.openapi:
    # Use OpenAPI-validated API
    api = create_openapi_validated_api(platform, "api/openapi.yaml")
else:
    # Use standard API
    api = create_api(platform, framework=framework, ui_html=frontend.get_html())
```

Run with OpenAPI validation:
```bash
python extreme_mvp_frontier.py --openapi
```

## Installation

Install OpenAPI dependencies:
```bash
# Uncomment OpenAPI section in requirements.txt and install
pip install openapi-core>=0.18.0 pyyaml>=6.0 jsonschema>=4.0.0
```

Install client generator (optional):
```bash
# macOS
brew install openapi-generator

# or via npm
npm install -g @openapitools/openapi-generator-cli
```

## Example Client Usage

After generating a Python client:

```python
from crucible_client import ApiClient, Configuration
from crucible_client.api import evaluations_api

# Configure client
config = Configuration(host="http://localhost:8000")
client = ApiClient(configuration=config)

# Create API instance
api = evaluations_api.EvaluationsApi(api_client=client)

# Submit evaluation
response = api.evaluate_sync(
    evaluation_request={"code": "print('Hello from client!')"}
)
print(f"Result: {response.output}")
```

## API Endpoints

The OpenAPI specification defines these endpoints:

- `GET /health` - Health check
- `GET /status` - Platform status
- `POST /eval` - Synchronous evaluation
- `POST /eval-async` - Asynchronous evaluation
- `GET /eval-status/{evalId}` - Get evaluation status
- `GET /queue-status` - Queue statistics
- `GET /events` - Server-sent events stream
- `GET /storage` - List stored evaluations
- `GET /storage/{evalId}` - Get specific evaluation
- `POST /test` - Run component tests

## Extending the API

To add new endpoints:

1. Update `api/openapi.yaml` with the new endpoint
2. Define request/response schemas
3. Implement the handler in your API service
4. Validation happens automatically!

Example:
```yaml
/metrics:
  get:
    summary: Get platform metrics
    responses:
      '200':
        description: Platform metrics
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Metrics'
```

## Best Practices

1. **Design API First**: Create/update OpenAPI spec before implementing
2. **Use References**: Define schemas once and reference them
3. **Versioning**: Use version in URL path or header
4. **Deprecation**: Mark deprecated endpoints in spec
5. **Examples**: Include example requests/responses
6. **Security**: Define security schemes and apply appropriately

## Troubleshooting

### Validation Errors
If requests are rejected:
1. Check the OpenAPI spec for required fields
2. Verify data types match specification
3. Check enum values are allowed
4. Review error details in response

### Client Generation Issues
- Ensure openapi-generator is installed
- Check OpenAPI spec is valid (use online validators)
- Some generators have specific requirements

### Performance
- OpenAPI validation adds minimal overhead (~1-5ms)
- Can be disabled in production if needed
- Consider caching parsed specifications