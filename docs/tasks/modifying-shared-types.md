# Modifying Shared Types

This document describes how to modify shared types (like evaluation states, event contracts, etc.) and propagate changes through Python and TypeScript codebases.

## Type Generation Flow

```
shared/types/*.yaml → Python generation → FastAPI → OpenAPI spec → TypeScript types
```

## Key Files

### Source of Truth
- `/shared/types/*.yaml` - All shared type definitions (evaluation-status, event-contracts, etc.)

### Generation Scripts  
- `/shared/scripts/generate-python-types.py` - Generates Python from YAML
- TypeScript: Generated from OpenAPI spec using `openapi-typescript`

### Generated Files
- `/shared/generated/python/*.py` - Generated Python types
- `/frontend/types/generated/api.ts` - Generated TypeScript types
- `/api/openapi.yaml` - OpenAPI specification

## Process to Modify Any Shared Type

### 1. Update YAML Source
Edit the relevant file in `/shared/types/`

### 2. Regenerate Python Types
```bash
python shared/scripts/generate-python-types.py
```

### 3. Update OpenAPI Spec
The OpenAPI spec is generated from the running FastAPI app:
```bash
# Restart API service
docker-compose restart api
# OR manually export:
python api/scripts/export-openapi-spec.py
```

### 4. Regenerate TypeScript Types
```bash
cd frontend
npm run generate-types
```

### 5. Check for Manual Updates
- TypeScript code with hardcoded values
- Python code not using generated types
- Any business logic dependent on specific type values

## Current Limitations

1. **Metadata Loss**: Custom YAML extensions (like `x-terminal-states`) don't propagate to TypeScript
2. **No Direct YAML→TypeScript**: Must go through OpenAPI spec
3. **Manual Updates Required**: Some TypeScript code needs manual updates when types change

## Example: Adding an Evaluation State

1. Add to `/shared/types/evaluation-status.yaml`
2. Run Python generator
3. Restart API 
4. Generate TypeScript types
5. Update hardcoded terminal state checks in TypeScript

## Future Improvements Needed

- Direct YAML→TypeScript generation to preserve metadata
- Automated type propagation pipeline
- Better handling of type metadata in TypeScript