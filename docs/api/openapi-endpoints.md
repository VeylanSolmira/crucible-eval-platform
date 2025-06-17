# OpenAPI Specification Endpoints

The Crucible Evaluation Platform exposes its OpenAPI specification at several standard endpoints, following industry best practices for API discovery.

## Available Endpoints

### `/api/openapi.yaml`
Returns the OpenAPI 3.0 specification in YAML format.
```bash
curl http://localhost:8080/api/openapi.yaml
```

### `/api/openapi.json`
Returns the OpenAPI specification (currently in YAML format as we don't have a separate JSON version).
```bash
curl http://localhost:8080/api/openapi.json
```

### `/api/spec`
Generic endpoint for the API specification.
```bash
curl http://localhost:8080/api/spec
```

## Using the OpenAPI Spec

### Import into Postman
1. Open Postman
2. Click "Import" → "Link"
3. Enter: `http://your-server:8080/api/openapi.yaml`
4. Postman will create a collection with all endpoints

### Generate Client SDKs
Use OpenAPI Generator to create client libraries:
```bash
# Install OpenAPI Generator
brew install openapi-generator

# Generate Python client
openapi-generator generate -i http://localhost:8080/api/openapi.yaml -g python -o ./client-python

# Generate TypeScript client
openapi-generator generate -i http://localhost:8080/api/openapi.yaml -g typescript-axios -o ./client-typescript
```

### View Interactive Documentation
For interactive API documentation, you can use:
- **Swagger UI**: Upload the spec at https://editor.swagger.io/
- **ReDoc**: Use their online demo at https://redocly.github.io/redoc/

## API Discovery Benefits

Having these endpoints enables:
1. **Automatic client generation** in any language
2. **API testing tools** can import the spec directly
3. **Documentation** stays in sync with implementation
4. **Contract testing** between services
5. **Mock server generation** for development

## Industry Standards

This follows common patterns seen in:
- **FastAPI**: `/openapi.json` and `/docs`
- **Spring Boot**: `/v3/api-docs`
- **Express + Swagger**: `/api-docs`
- **Django REST**: `/api/schema/`

Our implementation aligns with these standards, making it familiar to developers and compatible with existing tooling.